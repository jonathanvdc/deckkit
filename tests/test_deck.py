from dataclasses import FrozenInstanceError

import pytest

from deckkit import Deck, Slide, Text, State
from deckkit.backends import pptx


class NamedSlide(Slide):
    def __init__(self, title):
        self.title = title

    def body(self, context):
        return Text(f"{self.title}: {context.state.get('step', 0)}").key("title")


def test_deck_is_an_immutable_sequence():
    slides = [NamedSlide("One"), NamedSlide("Two")]
    deck = Deck(iter(slides))
    slides.clear()
    assert len(deck) == 2
    assert deck[-1].title == "Two"
    assert isinstance(deck[:1], Deck)
    assert list(deck[:1]) == [deck[0]]
    with pytest.raises(FrozenInstanceError):
        deck.slides = ()
    with pytest.raises(TypeError, match="Slide"):
        Deck([Text("Not a slide")])


def test_compile_deck_and_export_order(compiler, tmp_path):
    from pptx import Presentation

    deck = Deck([NamedSlide("One"), NamedSlide("Two")])
    result = compiler.compile_deck(deck, State(step=2))
    assert len(result.slides) == 2
    assert [layout.children[0].children[0].text for layout in result.drawables] == [
        "One: 2",
        "Two: 2",
    ]
    # Repeated keys are scoped per slide, not per deck.
    output = tmp_path / "deck.pptx"
    pptx.render(result.drawables, output)
    assert [slide.shapes[0].text for slide in Presentation(output).slides] == [
        "One: 2",
        "Two: 2",
    ]


def test_empty_deck(compiler):
    assert compiler.compile_deck(Deck([])).drawables == ()


def test_canvas_root_preserves_content_bounds(compiler):
    from deckkit import Drawable, pt

    compiled = compiler.compile_view(Text("Small"))
    canvas = compiled.drawable
    assert isinstance(canvas, Drawable)
    from deckkit.drawables import DrawableGroup

    assert isinstance(canvas, DrawableGroup)
    assert canvas.bounds.x == canvas.bounds.y == pt(0)
    assert canvas.bounds.width == compiler.width
    assert canvas.bounds.height == compiler.height
    (content,) = canvas.children
    assert content.bounds.width < canvas.bounds.width
    assert content.identity == compiled.expanded_tree.identity
