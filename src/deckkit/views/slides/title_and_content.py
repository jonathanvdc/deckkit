"""Theme-overridable title-and-content composition."""

from __future__ import annotations

from dataclasses import dataclass

from ...context import Context
from ...theme import SpacingUnit, TitleTextStyle, Typography
from ...tokens import DesignToken
from ...units import Length
from ..semantic.semantic_view import SemanticView
from ..view import View
from ..vstack import VStack


@dataclass(frozen=True)
class TitleAndContentStyle:
    title_font: DesignToken[Typography]
    spacing: Length


TitleAndContentStyleToken = DesignToken[TitleAndContentStyle](
    "component.title-and-content",
    lambda values: TitleAndContentStyle(TitleTextStyle, values[SpacingUnit] * 8),
    value_type=TitleAndContentStyle,
)


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
        style = context.environment[TitleAndContentStyleToken]
        return VStack(
            self.title.font(style.title_font),
            self.content,
            spacing=style.spacing,
        )
