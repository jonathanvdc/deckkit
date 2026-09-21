"""A semantic view for compact labeled content."""

from __future__ import annotations

from dataclasses import dataclass

from ...context import Context
from ...theme import (
    Color,
    PrimaryColor,
    RadiusScale,
    SpacingUnit,
    SurfaceColor,
)
from ...tokens import DesignToken, TokenResolver
from ...units import Length
from ..rectangle import Rectangle
from ..view import View
from ..zstack import ZStack
from .semantic_view import StyledSemanticView


@dataclass(frozen=True)
class Pill(StyledSemanticView["Pill.Style"]):
    """Display arbitrary content over a capsule-shaped background.

    Args:
        content: View displayed inside the pill.
    """

    @dataclass(frozen=True)
    class Style:
        background: Color
        foreground: Color
        padding: Length
        corner_radius: Length

    @staticmethod
    def _default_style(values: TokenResolver) -> Style:
        return Pill.Style(
            values[SurfaceColor],
            values[PrimaryColor],
            values[SpacingUnit] * 2,
            values[SpacingUnit] * (4.5 * values[RadiusScale]),
        )

    style_token = DesignToken[Style](
        "component.pill", lambda values: Pill._default_style(values), value_type=Style
    )

    content: View

    def __post_init__(self) -> None:
        if not isinstance(self.content, View):
            raise TypeError("Pill.content must be a View; wrap text in Text(...)")

    def body(self, context: Context) -> View:
        """Place padded content over a themed capsule."""
        style = context.environment[self.style_token]
        return ZStack(
            Rectangle(corner_radius=style.corner_radius).foreground_style(
                style.background
            ),
            self.content.foreground_style(style.foreground).padding(style.padding),
        )
