from __future__ import annotations

from dataclasses import dataclass

import pytest

from deckkit import (
    CompositeView,
    Context,
    EnvironmentKey,
    ExpandedComponent,
    ExpandedMetadata,
    ExpandedRectangle,
    ExpandedText,
    FontRoleKey,
    ForegroundStyleKey,
    HStack,
    Image,
    LayoutView,
    PrimitiveView,
    Rectangle,
    Slide,
    Text,
    View,
    VStack,
    ZStack,
)
from deckkit.layouts import ShapeLayout
from deckkit.views.semantic import Metric, SemanticView
from deckkit.views.stack import Stack


def test_only_composites_have_body():
    for view in (
        View,
        PrimitiveView,
        Text,
        Image,
        Rectangle,
        LayoutView,
        HStack,
        VStack,
        ZStack,
    ):
        assert not hasattr(view, "body")
    assert issubclass(Slide, CompositeView)
    assert issubclass(SemanticView, CompositeView)
    assert issubclass(Metric, CompositeView)
    for view in (Text, Image, Rectangle):
        assert issubclass(view, PrimitiveView)
    for view in (HStack, VStack, ZStack):
        assert issubclass(view, LayoutView)


@pytest.mark.parametrize("base", [CompositeView, Slide, SemanticView, Stack])
def test_incomplete_categories_are_abstract(base):
    with pytest.raises(TypeError, match="abstract"):
        base()


def test_composite_expansion(compiler):
    class Greeting(CompositeView):
        def body(self, context: Context) -> View:
            return Text("Hello")

    result = compiler.compile_view(Greeting().key("greeting"))
    assert isinstance(result.expanded_tree, ExpandedComponent)
    assert isinstance(result.expanded_tree.children[0], ExpandedText)


def test_composite_and_primitive_share_inherited_environment(compiler):
    observed = []

    class Greeting(CompositeView):
        def body(self, context: Context) -> View:
            observed.append(
                (
                    context.environment.get(FontRoleKey),
                    context.environment.get(ForegroundStyleKey),
                )
            )
            return Text("Hello")

    result = compiler.compile_view(Greeting().font("title").foreground_style("accent"))
    text = result.expanded_tree.children[0]

    assert observed == [("title", "accent")]
    assert isinstance(text, ExpandedText)
    assert text.color == compiler.environment.theme.color("accent")


def test_custom_environment_modifier_reaches_subtree(compiler):
    class DensityKey(EnvironmentKey[int]):
        @classmethod
        def default(cls) -> int:
            return 1

    observed = []

    class ReadsDensity(CompositeView):
        def body(self, context: Context) -> View:
            observed.append(context.environment.get(DensityKey))
            return Text("Density")

    compiler.compile_view(ReadsDensity().environment(DensityKey, 2))

    assert observed == [2]


def test_plain_view_body_is_not_implicitly_called(compiler):
    class Unsupported(View):
        def body(self, context):
            raise AssertionError("Must not be called")

    with pytest.raises(TypeError, match="inherit CompositeView"):
        compiler.compile_view(Unsupported())


def test_primitive_must_implement_expansion():
    class Unsupported(PrimitiveView):
        pass

    with pytest.raises(TypeError, match="abstract"):
        Unsupported()


def test_custom_primitive_expands_polymorphically(compiler):
    @dataclass(frozen=True)
    class ExpandedBadge(ExpandedRectangle):
        pass

    class Badge(PrimitiveView):
        def expand(self, context: Context, metadata: ExpandedMetadata) -> ExpandedBadge:
            return ExpandedBadge(
                metadata,
                ShapeLayout(),
                context.environment.theme.color(
                    context.environment.get(ForegroundStyleKey)
                ),
            )

    result = compiler.compile_view(Badge().foreground_style("accent"))

    assert isinstance(result.expanded_tree, ExpandedBadge)
    assert result.expanded_tree.color == compiler.environment.theme.color("accent")


def test_invalid_composite_body_has_explicit_error(compiler):
    class Invalid(CompositeView):
        def body(self, context):
            return "not a view"

    with pytest.raises(TypeError, match=r"body\(\) must return a View"):
        compiler.compile_view(Invalid())
