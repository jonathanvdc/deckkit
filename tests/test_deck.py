from dataclasses import FrozenInstanceError

import pytest

from deckkit import Deck, OnAdvance, Slide, SlideTimeline, State, Text
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
    assert [
        slide.initial.drawable.children[0].children[0].text for slide in result.slides
    ] == [
        "One: 2",
        "Two: 2",
    ]
    # Repeated keys are scoped per slide, not per deck.
    output = tmp_path / "deck.pptx"
    pptx.render(result, output)
    assert [slide.shapes[0].text for slide in Presentation(output).slides] == [
        "One: 2",
        "Two: 2",
    ]


def test_empty_deck(compiler):
    assert compiler.compile_deck(Deck([])).slides == ()


def test_slide_timeline_and_static_expansion(compiler):
    class NumberedSlide(NamedSlide):
        def timeline(self):
            return SlideTimeline.steps(3)

    slide = NumberedSlide("One")
    compiled = compiler.compile_deck(Deck([slide]))
    assert compiled.slides[0].is_animated
    assert all(
        isinstance(build.trigger, OnAdvance)
        for build in compiled.slides[0].animation.builds
    )
    static = compiled.expanding_steps()
    assert len(static.slides) == 3
    assert all(not item.is_animated for item in static.slides)
    assert [
        item.initial.drawable.children[0].children[0].text for item in static.slides
    ] == ["One: 0", "One: 1", "One: 2"]


def test_steps_require_a_positive_integer():
    with pytest.raises(ValueError, match="at least one"):
        SlideTimeline.steps(0)
    with pytest.raises(TypeError, match="integer"):
        SlideTimeline.steps(True)


def test_slide_timeline_must_return_a_timeline(compiler):
    class InvalidSlide(NamedSlide):
        def timeline(self):
            return None

    with pytest.raises(TypeError, match="must return SlideTimeline"):
        compiler.compile_slide(InvalidSlide("Invalid"))


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
