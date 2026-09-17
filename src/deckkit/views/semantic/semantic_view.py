from __future__ import annotations

from abc import ABC, abstractmethod
from typing import final

from ...context import Context
from ..composite_view import CompositeView
from ..view import View


class SemanticView(CompositeView, ABC):
    """An ordinary composite with an optional theme recipe and a default body.

    Override default_body, not body: every semantic component follows the same
    theme-first resolution path. Recipes return views, never backend objects.
    """

    @final
    def body(self, context: Context) -> View:
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
