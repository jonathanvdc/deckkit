"""A semantic view for displaying a highlighted value and its label."""

from __future__ import annotations

from dataclasses import dataclass

from ...context import Context
from ...units import pt
from ..view import View
from ..vstack import VStack
from .semantic_view import SemanticView


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

    def default_body(self, context: Context) -> View:
        """Stack and style the value and label using the default recipe."""
        return VStack(
            self.value.font("metric").foreground_style("accent"),
            self.label.font("caption"),
            spacing=pt(8),
        )
