from __future__ import annotations

import pytest

from deckkit import (
    CompositeView,
    Context,
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
    assert result.expanded_tree.kind == "component"
    assert result.expanded_tree.children[0].kind == "text"


def test_plain_view_body_is_not_implicitly_called(compiler):
    class Unsupported(View):
        def body(self, context):
            raise AssertionError("Must not be called")

    with pytest.raises(TypeError, match="inherit CompositeView"):
        compiler.compile_view(Unsupported())


def test_unknown_primitive_has_explicit_error(compiler):
    class Unsupported(PrimitiveView):
        pass

    with pytest.raises(TypeError, match="Unsupported primitive view"):
        compiler.compile_view(Unsupported())


def test_invalid_composite_body_has_explicit_error(compiler):
    class Invalid(CompositeView):
        def body(self, context):
            return "not a view"

    with pytest.raises(TypeError, match=r"body\(\) must return a View"):
        compiler.compile_view(Invalid())
