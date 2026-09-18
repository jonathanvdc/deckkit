"""Base support for semantic, theme-overridable presentation components."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import final

from ...context import Context
from ..composite_view import CompositeView
from ..view import View


class SemanticView(CompositeView, ABC):
    """Base class for composites whose presentation may be supplied by a theme.

    Subclasses implement :meth:`default_body` to describe their fallback
    presentation. Themes may provide a recipe through ``render_semantic``;
    otherwise that fallback is used.

    Subclasses should override :meth:`default_body`, not :meth:`body`, so every
    semantic component follows the same theme-first resolution path.
    """

    @final
    def body(self, context: Context) -> View:
        """Resolve a theme recipe, falling back to :meth:`default_body`."""
        recipe = context.environment.theme.render_semantic(self, context)
        if recipe is None:
            recipe = self.default_body(context)
        if not isinstance(recipe, View):
            raise TypeError(f"{type(self).__name__} recipe must return a View")
        return recipe

    @abstractmethod
    def default_body(self, context: Context) -> View:
        """Compose the component when the theme does not supply an override."""
        raise NotImplementedError
