from __future__ import annotations

from dataclasses import dataclass

import pytest

from deckkit import Compiler, Deck
from deckkit.backends import pptx, svg
from deckkit.drawables import DrawableConnector, DrawableRectangle, DrawableText
from deckkit.expanded_views import ExpandedText
from deckkit.fonts import (
    FileFontResolver,
    Font,
)
from deckkit.themes import ClarityTheme
from deckkit.units import pt
from deckkit.views import Context, HStack, Rectangle, Slide, Text, View, VStack
from deckkit.views.semantic import (
    BeforeAfter,
    Card,
    Metric,
    Pill,
    Pipeline,
    PipelineStage,
    SemanticView,
)
from examples.themes import EditorialTheme


def texts(compilation):
    return [
        n.text for n in compilation.expanded_tree.walk() if isinstance(n, ExpandedText)
    ]


@dataclass(frozen=True)
class CustomSemantic(SemanticView):
    content: View

    def body(self, context: Context) -> View:
        return VStack(Text("Default"), self.content)


@dataclass(frozen=True)
class CustomSlide(Slide):
    content: View

    def body(self, context: Context) -> View:
        return VStack(Text("Default slide"), self.content)


class RecipeTheme(ClarityTheme):
    def render_semantic(self, component: SemanticView, context: Context) -> View | None:
        if isinstance(component, Metric):
            return HStack(component.label, component.value)
        if isinstance(component, PipelineStage):
            return VStack(Text("ClarityTheme stage"), component.label)
        if isinstance(component, CustomSemantic):
            return VStack(Text("ClarityTheme custom"), component.content)
        if isinstance(component, CustomSlide):
            return VStack(Text("ClarityTheme slide"), component.content)
        return super().render_semantic(component, context)


def test_rich_content_in_every_semantic_slot(font, tmp_path):
    from pptx import Presentation

    component = BeforeAfter(
        title=HStack(Text("A"), Text("comparison")),
        before=PipelineStage(HStack(Text("Old"), Text("pipeline"))),
        after=Metric(
            VStack(Text("2.7×"), Rectangle().frame(width=pt(20), height=pt(5))),
            HStack(Text("New"), Text("pipeline")),
        ),
        takeaway=VStack(Text("Fewer passes"), Text("Less work")),
    )
    for theme_type in (ClarityTheme, EditorialTheme):
        result = Compiler(
            theme_type(),
            font_resolver=FileFontResolver({Font("Aptos"): font}),
        ).compile_view(component)
        assert set(texts(result)) >= {
            "A",
            "comparison",
            "Old",
            "pipeline",
            "2.7×",
            "New",
            "Fewer passes",
            "Less work",
        }
        assert "Less work" in svg.render(result.drawable)
        output = tmp_path / f"rich-{theme_type.__name__}.pptx"
        from deckkit import CompiledDeck

        pptx.render(CompiledDeck.from_views(result), output)
        assert any(
            s.has_text_frame and s.text == "Less work"
            for s in Presentation(output).slides[0].shapes
        )


def test_pill_accepts_any_view_and_before_after_uses_pills(compiler):
    pill = compiler.compile_view(Pill(HStack(Text("New"), Text("label"))))
    assert texts(pill) == ["New", "label"]
    background = next(
        node for node in pill.drawable.walk() if isinstance(node, DrawableRectangle)
    )
    assert background.color == "#E8EEF5"
    assert background.corner_radius == pt(18)

    comparison = compiler.compile_view(
        BeforeAfter(Text("Change"), Text("Old"), Text("New"), Text("Result"))
    )
    assert (
        sum(
            1
            for node in comparison.expanded_tree.walk()
            if getattr(node, "component_type", "").endswith(".Pill")
        )
        == 2
    )
    labels = [
        node
        for node in comparison.drawable.walk()
        if isinstance(node, DrawableText) and node.text in ("BEFORE", "AFTER")
    ]
    backgrounds = [
        node
        for node in comparison.drawable.walk()
        if isinstance(node, DrawableRectangle) and node.bounds.width == pt(88)
    ]
    assert len(labels) == len(backgrounds) == 2
    assert all(background.bounds.height >= pt(36) for background in backgrounds)
    for label, background in zip(labels, backgrounds):
        assert (
            label.content_bounds.x + label.content_bounds.width / 2
        ).points == pytest.approx(
            (background.bounds.x + background.bounds.width / 2).points
        )
        assert (
            label.content_bounds.y + label.content_bounds.height / 2
        ).points == pytest.approx(
            (background.bounds.y + background.bounds.height / 2).points
        )
    cards = [
        node
        for node in comparison.drawable.walk()
        if isinstance(node, DrawableRectangle) and node.bounds.width > pt(88)
    ]
    assert len(cards) == 2
    for pill_background, card_background in zip(backgrounds, cards):
        assert pill_background.bounds.x == card_background.bounds.x + pt(20)
        assert pill_background.bounds.y == card_background.bounds.y + pt(20)


def test_theme_hook_applies_to_all_semantic_types(font):
    source = VStack(
        Metric(Text("Value"), Text("Label")),
        PipelineStage(Text("Parse")),
        CustomSemantic(Text("Content")),
    )
    normal = Compiler(
        ClarityTheme(),
        font_resolver=FileFontResolver({Font("Aptos"): font}),
    ).compile_view(source)
    themed = Compiler(
        RecipeTheme(),
        font_resolver=FileFontResolver({Font("Aptos"): font}),
    ).compile_view(source)
    assert texts(normal) == ["Value", "Label", "Parse", "Default", "Content"]
    assert texts(themed) == [
        "Label",
        "Value",
        "ClarityTheme stage",
        "Parse",
        "ClarityTheme custom",
        "Content",
    ]


def test_theme_can_replace_a_slide_recipe(font):
    resolver = FileFontResolver({Font("Aptos"): font})
    slide = CustomSlide(Text("Content"))

    normal = Deck([slide], theme=ClarityTheme()).compile(font_resolver=resolver)
    themed = Deck([slide], theme=RecipeTheme()).compile(font_resolver=resolver)

    assert texts(normal.slides[0].initial) == ["Default slide", "Content"]
    assert texts(themed.slides[0].initial) == ["ClarityTheme slide", "Content"]


def test_pipeline_connects_adjacent_stages(compiler):
    result = compiler.compile_view(
        Pipeline(
            PipelineStage(Text("Parse")),
            PipelineStage(Text("Lower")),
            PipelineStage(Text("Optimize")),
        )
    )

    connectors = [
        node for node in result.drawable.walk() if isinstance(node, DrawableConnector)
    ]
    assert len(connectors) == 2
    assert all(connector.start.x < connector.end.x for connector in connectors)


def test_pipeline_requires_stages_and_typed_annotations():
    with pytest.raises(ValueError, match="at least one"):
        Pipeline()
    with pytest.raises(TypeError, match="PipelineStage"):
        Pipeline(Text("Not a stage"))
    with pytest.raises(TypeError, match="annotations"):
        Pipeline(PipelineStage(Text("Parse")), annotations=("not an annotation",))


def test_keyed_children_survive_recipe_changes(font):
    content = Text("Same content").key("content")
    source = CustomSemantic(content).key("semantic")
    compiler = Compiler(
        ClarityTheme(),
        font_resolver=FileFontResolver({Font("Aptos"): font}),
    )
    before = compiler.compile_view(source)
    after = Compiler(
        RecipeTheme(),
        font_resolver=FileFontResolver({Font("Aptos"): font}),
    ).compile_view(source)
    changes = compiler.changes(before, after)
    assert not any(
        c.kind in ("insert", "remove") and "key:content:" in c.identity for c in changes
    )
    assert content._modifiers == (("key", "content"),)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: BeforeAfter(Text("Title"), "old", Text("new"), Text("Takeaway")),
        lambda: Metric("value", Text("label")),
        lambda: Metric(Text("value"), "label"),
        lambda: PipelineStage("label"),
        lambda: Pill("label"),
        lambda: Card("content"),
    ],
)
def test_semantic_content_requires_views(factory):
    with pytest.raises(TypeError, match="View"):
        factory()
