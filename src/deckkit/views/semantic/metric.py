"""A semantic view for displaying a highlighted value and its label."""

from __future__ import annotations

from dataclasses import dataclass

from ...context import Context
from ...theme import (
    AccentColor,
    CaptionTextStyle,
    Color,
    MetricTextStyle,
    SpacingUnit,
    Typography,
)
from ...tokens import DesignToken, TokenResolver
from ...units import Length
from ..view import View
from ..vstack import VStack
from .semantic_view import StyledSemanticView


@dataclass(frozen=True)
class Metric(StyledSemanticView):
    """Emphasize a value together with a short descriptive label.

    Both slots accept arbitrary :class:`~deckkit.views.View` values. The default
    recipe stacks the value over the label, applies the metric font to the value,
    and colors it with the theme's accent style.

    Args:
        value: The primary value or visualization to emphasize.
        label: Supporting content that explains the value.
    """

    @dataclass(frozen=True)
    class Style:
        value_font: DesignToken[Typography]
        value_color: DesignToken[Color]
        label_font: DesignToken[Typography]
        spacing: Length

    @staticmethod
    def _default_style(values: TokenResolver) -> Style:
        return Metric.Style(
            MetricTextStyle, AccentColor, CaptionTextStyle, values[SpacingUnit] * 2
        )

    style_token = DesignToken[Style](
        "component.metric",
        lambda values: Metric._default_style(values),
        value_type=Style,
    )

    value: View
    label: View

    def __post_init__(self) -> None:
        if not isinstance(self.value, View) or not isinstance(self.label, View):
            raise TypeError(
                "Metric value and label must be Views; wrap text in Text(...)"
            )

    def body(self, context: Context) -> View:
        """Stack and style the value and label using the default recipe."""
        style = context.environment[self.style_token]
        return VStack(
            self.value.font(style.value_font).foreground_style(style.value_color),
            self.label.font(style.label_font),
            spacing=style.spacing,
        )
