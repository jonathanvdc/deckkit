"""Theme-overridable margins around slide content."""

from __future__ import annotations

from dataclasses import dataclass

from ...context import Context
from ...units import pt
from ..semantic.semantic_view import SemanticView
from ..view import View


@dataclass(frozen=True)
class SlideMargins(SemanticView):
    """Content placed within slide margins."""

    content: View

    def __post_init__(self) -> None:
        if not isinstance(self.content, View):
            raise TypeError("SlideMargins.content must be a View")

    def body(self, context: Context) -> View:
        return self.content.padding(pt(40))
