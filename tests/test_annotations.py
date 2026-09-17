from __future__ import annotations

from dataclasses import dataclass

import pytest

from deckkit import (
    Anchor,
    Annotated,
    CompositeView,
    Connector,
    Context,
    HStack,
    Label,
    Rectangle,
    RelativePoint,
    Text,
    View,
    VStack,
    pt,
)
from deckkit.backends import pptx, svg
from deckkit.drawables import DrawableConnector, DrawableText


def test_connector_resolves_nested_keyed_bounds(compiler):
    result = compiler.compile_view(
        Annotated(
            HStack(
                Rectangle().frame(width=pt(40), height=pt(30)).key("from"),
                Rectangle().frame(width=pt(50), height=pt(30)).key("to"),
                spacing=pt(20),
            ),
            Connector(
                Anchor("from", RelativePoint.trailing),
                Anchor("to", RelativePoint.leading),
            ),
        )
    )
    connector = next(
        node for node in result.drawable.walk() if isinstance(node, DrawableConnector)
    )

    assert connector.start.x == pt(40)
    assert connector.end.x == pt(60)
    assert connector.start.y == connector.end.y == pt(15)


def test_label_aligns_any_view_to_an_anchor(compiler):
    result = compiler.compile_view(
        Annotated(
            Rectangle().frame(width=pt(200), height=pt(100)).key("target"),
            Label(
                Anchor("target", RelativePoint(0.25, 0.75)),
                Text("Here"),
                alignment=RelativePoint.center,
            ),
        )
    )
    label = next(
        node
        for node in result.drawable.walk()
        if isinstance(node, DrawableText) and node.text == "Here"
    )

    assert label.bounds.x + label.bounds.width / 2 == pt(50)
    assert label.bounds.y + label.bounds.height / 2 == pt(75)


def test_reusable_annotated_components_have_scoped_keys(compiler):
    @dataclass(frozen=True)
    class Pipeline(CompositeView):
        def body(self, context: Context) -> View:
            return Annotated(
                HStack(
                    Rectangle().frame(width=pt(20), height=pt(20)).key("from"),
                    Rectangle().frame(width=pt(20), height=pt(20)).key("to"),
                ),
                Connector(Anchor("from"), Anchor("to")),
            )

    result = compiler.compile_view(VStack(Pipeline(), Pipeline()))

    assert (
        len(
            [
                node
                for node in result.drawable.walk()
                if isinstance(node, DrawableConnector)
            ]
        )
        == 2
    )


def test_unknown_anchor_key_is_diagnosed(compiler):
    with pytest.raises(ValueError, match="Unknown key 'missing'"):
        compiler.compile_view(
            Annotated(Rectangle(), Connector(Anchor("missing"), Anchor("missing")))
        )


def test_connector_renders_in_both_backends(compiler, tmp_path):
    from pptx import Presentation

    drawable = compiler.compile_view(
        Annotated(
            HStack(
                Rectangle().frame(width=pt(20), height=pt(20)).key("a"),
                Rectangle().frame(width=pt(20), height=pt(20)).key("b"),
            ),
            Connector(Anchor("a"), Anchor("b")),
        )
    ).drawable

    markup = svg.render(drawable)
    assert "<line" in markup
    assert "marker-end" in markup

    target = tmp_path / "connector.pptx"
    pptx.render([drawable], target)
    connector = Presentation(target).slides[0].shapes[-1]
    assert "tailEnd" in connector.element.xml
