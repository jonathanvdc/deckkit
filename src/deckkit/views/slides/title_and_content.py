"""Theme-overridable title-and-content composition."""

from __future__ import annotations

from dataclasses import dataclass

from ...context import Context
from ...units import pt
from ..semantic.semantic_view import SemanticView
from ..view import View
from ..vstack import VStack


@dataclass(frozen=True)
class TitleAndContent(SemanticView):
    """A title followed by content."""

    title: View
    content: View

    def __post_init__(self) -> None:
        for name in ("title", "content"):
            if not isinstance(getattr(self, name), View):
                raise TypeError(f"TitleAndContent.{name} must be a View")

    def body(self, context: Context) -> View:
        return VStack(
            self.title.font("title"),
            self.content,
            spacing=pt(32),
        )
