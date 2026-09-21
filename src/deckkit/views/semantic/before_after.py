"""A semantic view for presenting a before-and-after comparison."""

from __future__ import annotations

from dataclasses import dataclass

from ...context import Context
from ...theme import (
    AccentColor,
    CaptionTextStyle,
    Color,
    OnAccentColor,
    PrimaryColor,
    SpacingUnit,
    SurfaceColor,
)
from ...tokens import DesignToken, TokenResolver
from ...units import Length
from ..hstack import HStack
from ..text import Text
from ..view import View
from ..vstack import VStack
from .card import Card
from .pill import Pill
from .semantic_view import StyledSemanticView


@dataclass(frozen=True)
class BeforeAfter(StyledSemanticView["BeforeAfter.Style"]):
    """Present two states side by side.

    Both content slots accept arbitrary :class:`~deckkit.views.View` values,
    so callers can use text, stacks, shapes, or other semantic components. The
    default recipe labels the states ``BEFORE`` and ``AFTER`` and highlights the
    latter with the theme's accent style.

    Args:
        before: Content describing the initial state.
        after: Content describing the resulting state.
    """

    @dataclass(frozen=True)
    class Style:
        label_width: Length
        label_height: Length
        column_spacing: Length
        before_background: Color
        before_foreground: Color
        after_background: Color
        after_foreground: Color

    @staticmethod
    def _default_style(values: TokenResolver) -> Style:
        return BeforeAfter.Style(
            values[SpacingUnit] * 22,
            values[SpacingUnit] * 9,
            values[SpacingUnit] * 6,
            values[SurfaceColor],
            values[PrimaryColor],
            values[AccentColor],
            values[OnAccentColor],
        )

    style_token = DesignToken[Style](
        "component.before-after",
        lambda values: BeforeAfter._default_style(values),
        value_type=Style,
    )

    before: View
    after: View

    def __post_init__(self) -> None:
        for name in ("before", "after"):
            if not isinstance(getattr(self, name), View):
                raise TypeError(
                    f"BeforeAfter.{name} must be a View; wrap text in Text(...)"
                )

    def body(self, context: Context) -> View:
        """Arrange the comparison using the default horizontal recipe."""
        style = context.environment[self.style_token]
        before = Card(
            VStack(
                Pill(
                    Text("BEFORE").font(CaptionTextStyle),
                )
                .style(
                    background=style.before_background,
                    foreground=style.before_foreground,
                )
                .frame(width=style.label_width, height=style.label_height),
                self.before,
            )
        ).flex()
        after = Card(
            VStack(
                Pill(
                    Text("AFTER").font(CaptionTextStyle),
                )
                .style(
                    background=style.after_background,
                    foreground=style.after_foreground,
                )
                .frame(width=style.label_width, height=style.label_height),
                self.after.foreground_style(AccentColor),
            )
        ).flex()
        return HStack(before, after, spacing=style.column_spacing)
