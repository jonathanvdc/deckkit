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
from ...tokens import DesignToken
from ...units import Length
from ..view import View
from ..vstack import VStack
from .semantic_view import SemanticView


@dataclass(frozen=True)
class MetricStyle:
    value_font: DesignToken[Typography]
    value_color: DesignToken[Color]
    label_font: DesignToken[Typography]
    spacing: Length


MetricStyleToken = DesignToken[MetricStyle](
    "component.metric",
    lambda values: MetricStyle(
        MetricTextStyle, AccentColor, CaptionTextStyle, values[SpacingUnit] * 2
    ),
    value_type=MetricStyle,
)


@dataclass(frozen=True)
class Metric(SemanticView):
    """Emphasize a value together with a short descriptive label.

    Both slots accept arbitrary :class:`~deckkit.views.View` values. The default
    recipe stacks the value over the label, applies the metric font to the value,
    and colors it with the theme's accent style.

    Args:
        value: The primary value or visualization to emphasize.
        label: Supporting content that explains the value.
    """

    value: View
    label: View

    def __post_init__(self) -> None:
        if not isinstance(self.value, View) or not isinstance(self.label, View):
            raise TypeError(
                "Metric value and label must be Views; wrap text in Text(...)"
            )

    def body(self, context: Context) -> View:
        """Stack and style the value and label using the default recipe."""
        style = context.environment[MetricStyleToken]
        return VStack(
            self.value.font(style.value_font).foreground_style(style.value_color),
            self.label.font(style.label_font),
            spacing=style.spacing,
        )
