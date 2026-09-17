from __future__ import annotations

from dataclasses import dataclass

from ...context import Context
from ...units import pt
from ..view import View
from ..vstack import VStack
from .semantic_view import SemanticView


@dataclass(frozen=True)
class Metric(SemanticView):
    value: View
    label: View

    def __post_init__(self) -> None:
        if not isinstance(self.value, View) or not isinstance(self.label, View):
            raise TypeError(
                "Metric value and label must be Views; wrap text in Text(...)"
            )

    def default_body(self, context: Context) -> View:
        return VStack(
            self.value.font("metric").foreground_style("accent"),
            self.label.font("caption"),
            spacing=pt(8),
        )
