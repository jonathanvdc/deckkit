from __future__ import annotations

from deckkit import Font, FileFontResolver


from examples.themes import EditorialTheme

from dataclasses import dataclass

import pytest

from deckkit import (
    Compiler,
    Context,
    ExpandedText,
    HStack,
    Rectangle,
    Text,
    ClarityTheme,
    View,
    VStack,
    pt,
)
from deckkit.views.semantic import BeforeAfter, Metric, SemanticView, Stage
from deckkit.backends import pptx, svg


def texts(compilation):
    return [
        n.text for n in compilation.expanded_tree.walk() if isinstance(n, ExpandedText)
    ]


@dataclass(frozen=True)
class CustomSemantic(SemanticView):
    content: View

    def default_body(self, context: Context) -> View:
        return VStack(Text("Default"), self.content)


class RecipeTheme(ClarityTheme):
    def render_semantic(self, component: SemanticView, context: Context) -> View | None:
        if isinstance(component, Metric):
            return HStack(component.label, component.value)
        if isinstance(component, Stage):
            return VStack(Text("ClarityTheme stage"), component.label)
        if isinstance(component, CustomSemantic):
            return VStack(Text("ClarityTheme custom"), component.content)
        return super().render_semantic(component, context)


def test_rich_content_in_every_semantic_slot(font, tmp_path):
    from pptx import Presentation

    component = BeforeAfter(
        title=HStack(Text("A"), Text("comparison")),
        before=Stage(HStack(Text("Old"), Text("pipeline"))),
        after=Metric(
            VStack(Text("2.7×"), Rectangle().frame(width=pt(20), height=pt(5))),
            HStack(Text("New"), Text("pipeline")),
        ),
        takeaway=VStack(Text("Fewer passes"), Text("Less work")),
    )
    for theme_type in (ClarityTheme, EditorialTheme):
        result = Compiler(
            theme_type.from_font(Font("Test Font")),
            font_resolver=FileFontResolver({Font("Test Font"): font}),
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
        pptx.render([result.drawable], output)
        assert any(
            s.has_text_frame and s.text == "Less work"
            for s in Presentation(output).slides[0].shapes
        )


def test_theme_hook_applies_to_all_semantic_types(font):
    source = VStack(
        Metric(Text("Value"), Text("Label")),
        Stage(Text("Parse")),
        CustomSemantic(Text("Content")),
    )
    normal = Compiler(
        ClarityTheme.from_font(Font("Test Font")),
        font_resolver=FileFontResolver({Font("Test Font"): font}),
    ).compile_view(source)
    themed = Compiler(
        RecipeTheme.from_font(Font("Test Font")),
        font_resolver=FileFontResolver({Font("Test Font"): font}),
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


def test_keyed_children_survive_recipe_changes(font):
    content = Text("Same content").key("content")
    source = CustomSemantic(content).key("semantic")
    compiler = Compiler(
        ClarityTheme.from_font(Font("Test Font")),
        font_resolver=FileFontResolver({Font("Test Font"): font}),
    )
    before = compiler.compile_view(source)
    after = Compiler(
        RecipeTheme.from_font(Font("Test Font")),
        font_resolver=FileFontResolver({Font("Test Font"): font}),
    ).compile_view(source)
    changes = compiler.changes(before, after)
    assert not any(
        c.kind in ("insert", "remove") and "key:content:" in c.identity
        for c in changes
    )
    assert content._modifiers == (("key", "content"),)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: BeforeAfter(Text("Title"), "old", Text("new"), Text("Takeaway")),
        lambda: Metric("value", Text("label")),
        lambda: Metric(Text("value"), "label"),
        lambda: Stage("label"),
    ],
)
def test_semantic_content_requires_views(factory):
    with pytest.raises(TypeError, match="View"):
        factory()
