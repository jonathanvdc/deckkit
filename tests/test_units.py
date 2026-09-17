from deckkit import Font, FileFontResolver
from dataclasses import FrozenInstanceError
from xml.etree import ElementTree as ET

import pytest

from deckkit import Compiler, HStack, Image, Length, Rectangle, Text, cm, inch, pt
from deckkit.backends import pptx, svg
from deckkit.layout import Constraints, LayoutPlan
from deckkit.drawables import Bounds


def test_conversion_and_dimensional_arithmetic():
    assert inch(1) == pt(72) == cm(2.54)
    assert inch(1) + pt(12) == pt(84)
    assert cm(2.54) - pt(12) == pt(60)
    assert 2 * inch(1) == inch(2)
    assert inch(1) / 2 == pt(36)
    assert inch(2) / pt(72) == 2
    assert pt(1) < inch(1)
    assert -pt(5) == pt(-5)
    assert hash(inch(1)) == hash(pt(72))
    with pytest.raises(FrozenInstanceError):
        inch(1).points = 42


@pytest.mark.parametrize(
    "operation",
    [
        lambda: pt(1) + 1,
        lambda: pt(1) * pt(2),
        lambda: pt(1) < 2,
        lambda: Text("No implicit points").padding(16),
        lambda: Text("No implicit points").frame(width=100),
        lambda: HStack(spacing=12),
        lambda: Constraints(100, pt(100)),
        lambda: LayoutPlan(100, pt(100)),
        lambda: Bounds(0, pt(0), pt(10), pt(10)),
    ],
)
def test_rejects_dimensionally_invalid_values(operation):
    with pytest.raises(TypeError):
        operation()


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_lengths(value):
    with pytest.raises(ValueError, match="finite"):
        pt(value)


def test_mixed_units_and_physical_exports(font, tmp_path):
    from deckkit import ClarityTheme
    from pptx import Presentation

    compiler = Compiler(
        ClarityTheme.from_font(Font("Test Font")),
        width=inch(10),
        height=cm(12.7),
        font_resolver=FileFontResolver({Font("Test Font"): font}),
    )
    layout = compiler.compile_view(
        Rectangle().frame(width=cm(2.54), height=inch(1)).padding(pt(12))
    ).drawable
    assert layout.bounds.width == pt(720)
    assert layout.bounds.height == pt(360)
    assert layout.children[0].bounds.width == pt(96)
    root = ET.fromstring(svg.render(layout))
    assert root.attrib["width"] == "720pt"
    assert root.attrib["height"] == "360pt"
    assert root.attrib["viewBox"] == "0 0 720 360"
    rect = root.find(
        ".//{http://www.w3.org/2000/svg}g//{http://www.w3.org/2000/svg}rect"
    )
    assert rect is not None
    assert float(rect.attrib["x"]) == 12
    assert float(rect.attrib["width"]) == 72
    target = tmp_path / "units.pptx"
    pptx.render([layout], target)
    deck = Presentation(target)
    assert deck.slide_width == 10 * 914400
    shape = deck.slides[0].shapes[0]
    assert shape.width == 914400
    assert shape.left == 12 * 12700


def test_image_dpi_is_explicit(compiler, tmp_path):
    from PIL import Image as PILImage

    asset = tmp_path / "image.png"
    # Embedded metadata deliberately does not override the declared policy.
    PILImage.new("RGB", (192, 96)).save(asset, dpi=(300, 300))
    normal = compiler.compile_view(Image(str(asset))).drawable.children[0]
    dense = compiler.compile_view(Image(str(asset), dpi=192)).drawable.children[0]
    assert normal.bounds.width == inch(2)
    assert normal.bounds.height == inch(1)
    assert dense.bounds.width == inch(1)
    assert dense.bounds.height == inch(0.5)
    with pytest.raises(ValueError, match="DPI"):
        Image(str(asset), dpi=0)
