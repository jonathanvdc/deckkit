"""Theme-overridable margins around slide content."""

from __future__ import annotations

from dataclasses import dataclass

from ...context import Context
from ...theme import SpacingUnit
from ...tokens import DesignToken
from ...units import Length
from ..semantic.semantic_view import SemanticView
from ..view import View

SlideMargin = DesignToken[Length](
    "component.slide-margin",
    lambda values: values[SpacingUnit] * 10,
    value_type=Length,
)


@dataclass(frozen=True)
class SlideMargins(SemanticView):
    """Content placed within slide margins."""

    content: View

    def __post_init__(self) -> None:
        if not isinstance(self.content, View):
            raise TypeError("SlideMargins.content must be a View")

    def body(self, context: Context) -> View:
        return self.content.padding(context.environment[SlideMargin])
