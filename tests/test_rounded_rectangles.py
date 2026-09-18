from xml.etree import ElementTree as ET

import pytest

from deckkit import CompiledDeck
from deckkit.backends import pptx, svg
from deckkit.drawables import DrawableRectangle
from deckkit.units import pt
from deckkit.views import Rectangle


def _rectangle(compiled):
    return next(
        node for node in compiled.drawable.walk() if isinstance(node, DrawableRectangle)
    )


def test_corner_radius_is_a_non_negative_length():
    with pytest.raises(TypeError, match="Expected Length"):
        Rectangle(corner_radius=12)
    with pytest.raises(ValueError, match="non-negative"):
        Rectangle(corner_radius=pt(-1))


def test_corner_radius_is_clamped_after_layout(compiler):
    normal = compiler.compile_view(
        Rectangle(pt(12)).frame(width=pt(100), height=pt(50))
    )
    capsule = compiler.compile_view(
        Rectangle(pt(999)).frame(width=pt(100), height=pt(30))
    )

    assert _rectangle(normal).corner_radius == pt(12)
    assert _rectangle(capsule).corner_radius == pt(15)


def test_svg_uses_the_effective_physical_radius(compiler):
    rounded = compiler.compile_view(
        Rectangle(pt(12)).frame(width=pt(100), height=pt(50))
    )
    square = compiler.compile_view(
        Rectangle().frame(width=pt(100), height=pt(50))
    )

    rounded_rect = ET.fromstring(svg.render(rounded.drawable)).find(
        ".//{http://www.w3.org/2000/svg}g//{http://www.w3.org/2000/svg}rect"
    )
    square_rect = ET.fromstring(svg.render(square.drawable)).find(
        ".//{http://www.w3.org/2000/svg}g//{http://www.w3.org/2000/svg}rect"
    )
    assert rounded_rect is not None
    assert rounded_rect.attrib["rx"] == rounded_rect.attrib["ry"] == "12.0"
    assert square_rect is not None
    assert "rx" not in square_rect.attrib


def test_pptx_converts_physical_radius_to_shape_adjustment(compiler, tmp_path):
    from pptx import Presentation
    from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE

    compiled = compiler.compile_view(
        Rectangle(pt(12)).frame(width=pt(100), height=pt(50))
    )
    target = tmp_path / "rounded.pptx"
    pptx.render(CompiledDeck.from_views(compiled), target)

    shape = Presentation(target).slides[0].shapes[0]
    assert shape.auto_shape_type == MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE
    assert shape.adjustments[0] == pytest.approx(12 / 50, abs=1e-5)
