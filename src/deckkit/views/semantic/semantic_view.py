"""Base support for semantic, theme-overridable presentation components."""

from __future__ import annotations

from abc import ABC

from ...context import Context
from ..composite_view import CompositeView
from ..view import View


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
