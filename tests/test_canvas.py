from xml.etree import ElementTree as ET
from zipfile import ZipFile

import pytest

from deckkit.annotations import Anchor, Annotated, Connector, Label
from deckkit.backends import pptx, svg
from deckkit.canvas import (
    ArcTo,
    CanvasScene,
    CanvasText,
    ClosePath,
    CubicTo,
    Ellipse,
    Line,
    LineTo,
    MoveTo,
    Path,
    QuadraticTo,
    Rect,
    Stroke,
)
from deckkit.compiler import CompiledDeck
from deckkit.drawables import (
    Bounds,
    DrawableConnector,
    DrawableEllipse,
    DrawableLine,
    DrawablePath,
    DrawableRectangle,
    DrawableText,
)
from deckkit.geometry import Point, RelativePoint
from deckkit.theme import AccentColor, Color, MutedColor
from deckkit.units import pt
from deckkit.views import Canvas, Text


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


def test_canvas_text_measures_aligns_and_exports_natively(compiler, tmp_path):
    from pptx import Presentation

    compiled = compiler.compile_view(
        Canvas(
            lambda context, size: (
                CanvasText(
                    "Axis label",
                    Point(size.width / 2, size.height),
                    color=AccentColor,
                    horizontal_alignment="center",
                    vertical_alignment="bottom",
                    key="label",
                ),
            )
        ).frame(width=pt(200), height=pt(80))
    )
    canvas = compiled.drawable.children[0].children[0]
    text = canvas.children[0]
    assert isinstance(text, DrawableText)
    assert text.bounds.x + text.bounds.width / 2 == pt(100)
    assert text.bounds.y + text.bounds.height == pt(80)
    assert text.color == "#087F8C"
    assert ">Axis label<" in svg.render(compiled.drawable)

    output = tmp_path / "canvas-text.pptx"
    pptx.render(CompiledDeck.from_views(compiled), output)
    shape = Presentation(output).slides[0].shapes[0]
    assert shape.text == "Axis label"


def test_canvas_bezier_paths_export_natively(compiler, tmp_path):
    compiled = compiler.compile_view(
        Canvas(
            lambda context, size: (
                Path(
                    (
                        MoveTo(_point(10, 50)),
                        QuadraticTo(_point(30, 10), _point(50, 50)),
                        CubicTo(
                            _point(65, 80),
                            _point(85, 20),
                            _point(100, 50),
                        ),
                    ),
                    key="curve",
                ),
            )
        ).frame(width=pt(120), height=pt(90))
    )
    markup = svg.render(compiled.drawable)
    assert "Q 30 10 50 50" in markup
    assert "C 65 80 85 20 100 50" in markup

    output = tmp_path / "canvas-curves.pptx"
    pptx.render(CompiledDeck.from_views(compiled), output)
    with ZipFile(output) as archive:
        slide_xml = archive.read("ppt/slides/slide1.xml")
    assert b"quadBezTo" in slide_xml
    assert b"cubicBezTo" in slide_xml


def test_canvas_arcs_lower_to_equivalent_native_curves(compiler, tmp_path):
    compiled = compiler.compile_view(
        Canvas(
            lambda context, size: (
                Path(
                    (
                        MoveTo(_point(100, 60)),
                        ArcTo(_point(60, 60), pt(40), pt(30), 0, 270),
                    ),
                    key="arc",
                ),
            )
        ).frame(width=pt(120), height=pt(110))
    )
    markup = svg.render(compiled.drawable)
    assert markup.count(" C ") == 3

    output = tmp_path / "canvas-arc.pptx"
    pptx.render(CompiledDeck.from_views(compiled), output)
    with ZipFile(output) as archive:
        slide_xml = archive.read("ppt/slides/slide1.xml")
    drawing = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
    assert len(ET.fromstring(slide_xml).findall(".//a:cubicBezTo", drawing)) == 3


def test_canvas_arc_validates_geometry():
    with pytest.raises(ValueError, match="radii"):
        ArcTo(_point(0, 0), pt(0), pt(10), 0, 90)
    with pytest.raises(ValueError, match="sweep"):
        ArcTo(_point(0, 0), pt(10), pt(10), 0, 0)


def test_canvas_scene_clips_geometry_before_backend_export(compiler, tmp_path):
    clip = Bounds(pt(20), pt(20), pt(60), pt(40))
    compiled = compiler.compile_view(
        Canvas(
            lambda context, size: CanvasScene(
                Line(_point(0, 40), _point(100, 40), key="line"),
                Rect(Bounds(pt(10), pt(10), pt(30), pt(30)), key="rect"),
                Ellipse(Bounds(pt(65), pt(35), pt(30), pt(30)), key="ellipse"),
                Path(
                    (
                        MoveTo(_point(0, 30)),
                        CubicTo(_point(25, 0), _point(75, 80), _point(100, 30)),
                    ),
                    key="curve",
                ),
                clip=clip,
            )
        ).frame(width=pt(100), height=pt(80))
    )
    canvas = compiled.drawable.children[0].children[0]
    line = next(node for node in canvas.walk() if isinstance(node, DrawableLine))
    rectangle = next(
        node for node in canvas.walk() if isinstance(node, DrawableRectangle)
    )
    assert line.start == _point(20, 40)
    assert line.end == _point(80, 40)
    assert rectangle.bounds == Bounds(pt(20), pt(20), pt(20), pt(20))
    for node in canvas.walk():
        if isinstance(node, (DrawableLine, DrawableRectangle, DrawablePath)):
            assert node.bounds.x >= clip.x
            assert node.bounds.y >= clip.y
            assert node.bounds.x + node.bounds.width <= clip.x + clip.width
            assert node.bounds.y + node.bounds.height <= clip.y + clip.height

    assert 'x1="20.0"' in svg.render(compiled.drawable)
    output = tmp_path / "canvas-clipping.pptx"
    pptx.render(CompiledDeck.from_views(compiled), output)
    from pptx import Presentation

    assert len(Presentation(output).slides[0].shapes) == 4


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


def test_annotations_target_keyed_canvas_elements(compiler):
    canvas = Canvas(
        lambda context, size: (
            Rect(Bounds(pt(20), pt(30), pt(40), pt(25)), key="bar"),
            Ellipse(Bounds(pt(75), pt(35), pt(10), pt(10)), key="point"),
        )
    ).key("plot")
    compiled = compiler.compile_view(
        Annotated(
            canvas.frame(width=pt(100), height=pt(80)).padding(pt(10)),
            Label(
                Anchor.descendant("plot", "bar", RelativePoint.top),
                Text("Peak"),
                alignment=RelativePoint.bottom,
            ),
            Connector(
                Anchor.descendant("plot", "bar", RelativePoint.right),
                Anchor.descendant("plot", "point", RelativePoint.left),
                end_cap="none",
            ),
        )
    )
    bar = next(
        node
        for node in compiled.drawable.walk()
        if isinstance(node, DrawableRectangle) and node.identity.endswith("key:bar")
    )
    label = next(
        node
        for node in compiled.drawable.walk()
        if isinstance(node, DrawableText) and node.text == "Peak"
    )
    connector = next(
        node for node in compiled.drawable.walk() if isinstance(node, DrawableConnector)
    )

    assert (
        label.bounds.x + label.bounds.width / 2 == bar.bounds.x + bar.bounds.width / 2
    )
    assert label.bounds.y + label.bounds.height == bar.bounds.y
    assert connector.start.x == bar.bounds.x + bar.bounds.width
    assert connector.start.y == bar.bounds.y + bar.bounds.height / 2
    assert connector.end.x == bar.bounds.x + pt(55)


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
