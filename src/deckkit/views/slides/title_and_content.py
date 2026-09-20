"""Theme-overridable title-and-content composition."""

from __future__ import annotations

from dataclasses import dataclass

from ...context import Context
from ...theme import SpacingUnit, TitleTextStyle, Typography
from ...tokens import DesignToken, TokenResolver
from ...units import Length
from ..semantic.semantic_view import StyledSemanticView
from ..view import View
from ..vstack import VStack


@dataclass(frozen=True)
class TitleAndContent(StyledSemanticView):
    """A title followed by content."""

    @dataclass(frozen=True)
    class Style:
        title_font: DesignToken[Typography]
        spacing: Length

    @staticmethod
    def _default_style(values: TokenResolver) -> Style:
        return TitleAndContent.Style(TitleTextStyle, values[SpacingUnit] * 8)

    style_token = DesignToken[Style](
        "component.title-and-content",
        lambda values: TitleAndContent._default_style(values),
        value_type=Style,
    )

    title: View
    content: View

    def __post_init__(self) -> None:
        for name in ("title", "content"):
            if not isinstance(getattr(self, name), View):
                raise TypeError(f"TitleAndContent.{name} must be a View")

    def body(self, context: Context) -> View:
        style = context.environment[self.style_token]
        return VStack(
            self.title.font(style.title_font),
            self.content,
            spacing=style.spacing,
        )
