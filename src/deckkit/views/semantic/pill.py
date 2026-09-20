"""A semantic view for compact labeled content."""

from __future__ import annotations

from dataclasses import dataclass

from ...context import Context
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
from ..rectangle import Rectangle
from ..view import View
from ..zstack import ZStack
from .semantic_view import SemanticView


@dataclass(frozen=True)
class PillStyle:
    background: DesignToken[Color]
    foreground: DesignToken[Color]
    padding: Length
    corner_radius: Length


PillStyleToken = DesignToken[PillStyle](
    "component.pill",
    lambda values: PillStyle(
        SurfaceColor,
        PrimaryColor,
        values[SpacingUnit] * 2,
        values[SpacingUnit] * (4.5 * values[RadiusScale]),
    ),
    value_type=PillStyle,
)


@dataclass(frozen=True)
class Pill(SemanticView):
    """Display arbitrary content over a capsule-shaped background.

    Args:
        content: View displayed inside the pill.
        background_style: Theme color role used for the capsule.
        content_style: Theme color role inherited by the content.
    """

    content: View
    background_style: ColorStyle | None = None
    content_style: ColorStyle | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.content, View):
            raise TypeError("Pill.content must be a View; wrap text in Text(...)")

    def body(self, context: Context) -> View:
        """Place padded content over a themed capsule."""
        style = context.environment[PillStyleToken]
        return ZStack(
            Rectangle(corner_radius=style.corner_radius).foreground_style(
                self.background_style or style.background
            ),
            self.content.foreground_style(
                self.content_style or style.foreground
            ).padding(style.padding),
        )
