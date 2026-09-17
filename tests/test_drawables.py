from dataclasses import FrozenInstanceError

import pytest

from deckkit import Text, Rectangle, HStack, pt
from deckkit.drawables import (
    Bounds,
    DrawableGroup,
    DrawableMetadata,
    DrawableRectangle,
    DrawableText,
)
from deckkit.backends import svg, pptx


def test_typed_content_and_allocated_bounds(compiler):
    root = compiler.compile_view(
        HStack(
            Text("Typed").padding(pt(8)), Rectangle().frame(width=pt(10), height=pt(20))
        )
    ).drawable
    assert isinstance(root, DrawableGroup)
    text, rectangle = root.children[0].children
    assert isinstance(text, DrawableText)
    assert isinstance(rectangle, DrawableRectangle)
    assert text.text == "Typed"
    assert text.content_bounds.x == text.bounds.x + pt(8)
    assert text.bounds.width == text.content_bounds.width + pt(16)
    assert text.metrics.lines == ("Typed",)
    for node in root.walk():
        assert not hasattr(node, "kind")
        assert not hasattr(node, "props")
    assert text.children == ()
    with pytest.raises(FrozenInstanceError):
        text.text = "Changed"


def test_manual_drawables_export_without_views(tmp_path):
    from pptx import Presentation

    rectangle = DrawableRectangle(
        "rect",
        Bounds(pt(10), pt(10), pt(80), pt(40)),
        DrawableMetadata(),
        Bounds(pt(10), pt(10), pt(80), pt(40)),
        "#123456",
    )
    root = DrawableGroup(
        "canvas",
        Bounds(pt(0), pt(0), pt(200), pt(100)),
        DrawableMetadata(),
        (rectangle,),
    )
    assert "#123456" in svg.render(root)
    output = tmp_path / "drawing.pptx"
    pptx.render([root], output)
    shape = Presentation(output).slides[0].shapes[0]
    assert shape.width.pt == 80
    assert str(shape.fill.fore_color.rgb) == "123456"
