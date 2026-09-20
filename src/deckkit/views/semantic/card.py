"""A semantic container for grouped content on a surface."""

from __future__ import annotations

from dataclasses import dataclass

from ...context import Context
from ...geometry import RelativePoint
from ...theme import (
    Color,
    ColorStyle,
    PrimaryColor,
    RadiusScale,
    SpacingUnit,
    SurfaceColor,
)
from ...tokens import DesignToken, TokenResolver
from ...units import Length
from ..modifier_views import unbounded
from ..rectangle import Rectangle
from ..view import View
from ..zstack import ZStack
from .semantic_view import StyledSemanticView


@dataclass(frozen=True)
class Card(StyledSemanticView):
    """Place arbitrary content at the top-left edge of a padded surface."""

    @dataclass(frozen=True)
    class Style:
        background: DesignToken[Color]
        foreground: DesignToken[Color]
        padding: Length
        corner_radius: Length
        alignment: RelativePoint = RelativePoint.top_left

    @staticmethod
    def _default_style(values: TokenResolver) -> Style:
        return Card.Style(
            SurfaceColor,
            PrimaryColor,
            values[SpacingUnit] * 5,
            values[SpacingUnit] * (3 * values[RadiusScale]),
        )

    style_token = DesignToken[Style](
        "component.card", lambda values: Card._default_style(values), value_type=Style
    )

    content: View
    background_style: ColorStyle | None = None
    content_style: ColorStyle | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.content, View):
            raise TypeError("Card.content must be a View")

    def body(self, context: Context) -> View:
        style = context.environment[self.style_token]
        return ZStack(
            Rectangle(corner_radius=style.corner_radius).foreground_style(
                self.background_style or style.background
            ),
            self.content.foreground_style(self.content_style or style.foreground)
            .frame(max_width=unbounded, alignment=style.alignment)
            .padding(style.padding),
            alignment=style.alignment,
        )
