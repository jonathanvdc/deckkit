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
from ...tokens import DesignToken
from ...units import Length
from ..modifier_views import unbounded
from ..rectangle import Rectangle
from ..view import View
from ..zstack import ZStack
from .semantic_view import SemanticView


@dataclass(frozen=True)
class CardStyle:
    background: DesignToken[Color]
    foreground: DesignToken[Color]
    padding: Length
    corner_radius: Length
    alignment: RelativePoint = RelativePoint.top_left


CardStyleToken = DesignToken[CardStyle](
    "component.card",
    lambda values: CardStyle(
        SurfaceColor,
        PrimaryColor,
        values[SpacingUnit] * 5,
        values[SpacingUnit] * (3 * values[RadiusScale]),
    ),
    value_type=CardStyle,
)


@dataclass(frozen=True)
class Card(SemanticView):
    """Place arbitrary content at the top-left edge of a padded surface."""

    content: View
    background_style: ColorStyle | None = None
    content_style: ColorStyle | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.content, View):
            raise TypeError("Card.content must be a View")

    def body(self, context: Context) -> View:
        style = context.environment[CardStyleToken]
        return ZStack(
            Rectangle(corner_radius=style.corner_radius).foreground_style(
                self.background_style or style.background
            ),
            self.content.foreground_style(self.content_style or style.foreground)
            .frame(max_width=unbounded, alignment=style.alignment)
            .padding(style.padding),
            alignment=style.alignment,
        )
