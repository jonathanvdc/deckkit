from xml.etree import ElementTree as ET
from zipfile import ZipFile

import pytest

from deckkit.backends import pptx, svg
from deckkit.canvas import (
    CanvasScene,
    ClosePath,
    Ellipse,
    Line,
    LineTo,
    MoveTo,
    Path,
    Rect,
    Stroke,
)
from deckkit.compiler import CompiledDeck
from deckkit.drawables import (
    Bounds,
    DrawableEllipse,
    DrawableLine,
    DrawablePath,
    DrawableRectangle,
)
from deckkit.geometry import Point
from deckkit.theme import AccentColor, Color, MutedColor
from deckkit.units import pt
from deckkit.views import Canvas


def _point(x, y):
    return Point(pt(x), pt(y))


def test_canvas_renderer_receives_resolved_size_and_materializes_scene(compiler):
    observed = []

    def draw(context, size):
        observed.append(size)
        return CanvasScene(
            Rect(
                Bounds(pt(0), pt(0), size.width / 2, size.height),
                fill=AccentColor,
                stroke=Stroke(MutedColor, pt(2), (pt(4), pt(2))),
                key="bar",
            ),
            Line(
                _point(0, 0),
                Point(size.width, size.height),
                Stroke(Color("#112233"), pt(3)),
                key="rule",
            ),
            Ellipse(
                Bounds(size.width / 2, pt(10), pt(12), pt(8)),
                fill=None,
                stroke=Stroke(AccentColor, pt(1)),
                key="point",
            ),
            Path(
                (
                    MoveTo(_point(10, 60)),
                    LineTo(_point(30, 30)),
                    LineTo(_point(50, 60)),
                    ClosePath(),
                ),
                fill=MutedColor,
                stroke=None,
                key="area",
            ),
        )

    compiled = compiler.compile_view(Canvas(draw).frame(width=pt(120), height=pt(80)))
    canvas = compiled.drawable.children[0].children[0]

    assert observed[-1].width == pt(120)
    assert observed[-1].height == pt(80)
    assert [type(child) for child in canvas.children] == [
        DrawableRectangle,
        DrawableLine,
        DrawableEllipse,
        DrawablePath,
    ]
    assert [child.identity.rsplit("/", 1)[-1] for child in canvas.children] == [
        "key:bar",
        "key:rule",
        "key:point",
        "key:area",
    ]

    markup = svg.render(compiled.drawable)
    root = ET.fromstring(markup)
    namespace = {"svg": "http://www.w3.org/2000/svg"}
    assert len(root.findall(".//svg:ellipse", namespace)) == 1
    assert len(root.findall(".//svg:path", namespace)) == 1
    assert 'stroke-dasharray="4.0 2.0"' in markup
    assert "#087F8C" in markup


def test_canvas_coordinates_are_translated_but_not_rescaled(compiler):
    view = Canvas(
        lambda context, size: (Rect(Bounds(pt(5), pt(7), pt(20), pt(10)), key="rect"),)
    ).frame(width=pt(100), height=pt(50))
    drawable = compiler.compile_view(view.padding(pt(11))).drawable
    canvas = drawable.children[0].children[0].children[0]
    rectangle = canvas.children[0]
    assert rectangle.bounds == Bounds(pt(16), pt(18), pt(20), pt(10))


def test_canvas_rejects_duplicate_keys(compiler):
    view = Canvas(
        lambda context, size: (
            Line(_point(0, 0), _point(1, 1), key="same"),
            Line(_point(1, 0), _point(0, 1), key="same"),
        )
    )
    with pytest.raises(ValueError, match="unique"):
        compiler.compile_view(view)


def test_canvas_exports_native_powerpoint_shapes(compiler, tmp_path):
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE_TYPE

    view = Canvas(
        lambda context, size: (
            Rect(Bounds(pt(5), pt(5), pt(30), pt(20)), key="rect"),
            Ellipse(Bounds(pt(45), pt(5), pt(20), pt(20)), key="ellipse"),
            Line(
                _point(5, 35),
                _point(65, 35),
                Stroke(width=pt(2), dash=(pt(4), pt(2))),
                key="line",
            ),
            Path(
                (
                    MoveTo(_point(5, 50)),
                    LineTo(_point(30, 40)),
                    LineTo(_point(65, 50)),
                ),
                key="path",
            ),
        )
    ).frame(width=pt(80), height=pt(60))
    compiled = compiler.compile_view(view)
    output = tmp_path / "canvas.pptx"
    pptx.render(CompiledDeck.from_views(compiled), output)

    shapes = Presentation(output).slides[0].shapes
    assert len(shapes) == 4
    assert shapes[0].shape_type == MSO_SHAPE_TYPE.AUTO_SHAPE
    assert shapes[1].shape_type == MSO_SHAPE_TYPE.AUTO_SHAPE
    assert shapes[2].shape_type == MSO_SHAPE_TYPE.LINE
    assert shapes[3].shape_type == MSO_SHAPE_TYPE.FREEFORM
    with ZipFile(output) as archive:
        slide_xml = archive.read("ppt/slides/slide1.xml")
    assert b"custDash" in slide_xml
