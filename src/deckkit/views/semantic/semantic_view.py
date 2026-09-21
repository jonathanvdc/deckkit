"""Base support for semantic, theme-overridable presentation components."""

from __future__ import annotations

from abc import ABC
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Any, Generic, TypeVar, cast, overload

from typing_extensions import Self

from ...context import Context
from ...tokens import DesignToken, TokenAssignment, TokenResolver
from ..composite_view import CompositeView
from ..view import View

StyleT = TypeVar("StyleT")
_MISSING_STYLE = object()


@dataclass(frozen=True)
class _StyleFields(TokenAssignment[StyleT]):
    token: DesignToken[StyleT]
    changes: tuple[tuple[str, object], ...]

    def resolve(self, values: TokenResolver) -> StyleT:
        inherited = values.inherited(self.token)
        return cast(StyleT, replace(cast(Any, inherited), **dict(self.changes)))


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

    @overload
    def style(self, style: StyleT, /) -> Self: ...

    @overload
    def style(self, **changes: object) -> Self: ...

    def style(  # type: ignore[misc]  # mypy cannot model positional-only-or-kwargs
        self,
        replacement: object = _MISSING_STYLE,
        /,
        **changes: object,
    ) -> Self:
        """Replace the complete style or derive selected dataclass fields."""
        if replacement is not _MISSING_STYLE:
            if changes:
                raise TypeError(
                    "style accepts either a complete style or keyword fields"
                )
            return self.with_token(
                self.style_token, self.style_token.set(cast(StyleT, replacement))
            )
        return self.with_token(
            self.style_token,
            _StyleFields(self.style_token, tuple(sorted(changes.items()))),
        )

    def transform_style(self, transform: Callable[[StyleT], StyleT]) -> Self:
        """Derive this component's style from the inherited style."""
        return self.with_token(self.style_token, self.style_token.derive(transform))
