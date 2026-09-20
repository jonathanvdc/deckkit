"""Base support for semantic, theme-overridable presentation components."""

from __future__ import annotations

from abc import ABC
from collections.abc import Callable
from typing import Generic, TypeVar

from typing_extensions import Self

from ...context import Context
from ...tokens import DesignToken
from ..composite_view import CompositeView
from ..view import View

StyleT = TypeVar("StyleT")


class SemanticView(CompositeView, ABC):
    """Base class for composites whose presentation may be supplied by a theme.

    Subclasses implement :meth:`body` just like any other composite. During
    expansion, themes may provide a recipe through ``render_semantic``;
    otherwise that body is used.
    """

    def _resolve_body(self, context: Context) -> View:
        """Resolve a theme recipe, falling back to the authored body."""
        recipe = context.environment.theme.render_semantic(self, context)
        if recipe is None:
            recipe = self.body(context)
        return recipe


class StyledSemanticView(SemanticView, Generic[StyleT]):
    """A semantic component with a scoped, replaceable style token."""

    style_token: DesignToken[StyleT]

    def with_style(self, style: StyleT) -> Self:
        """Replace this component's style within its view subtree."""
        return self.with_token(self.style_token, self.style_token.set(style))

    def transform_style(self, transform: Callable[[StyleT], StyleT]) -> Self:
        """Derive this component's style from the inherited style."""
        return self.with_token(self.style_token, self.style_token.derive(transform))
