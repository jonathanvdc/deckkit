"""A semantic view representing one stage in a pipeline."""

from __future__ import annotations

from dataclasses import dataclass

from ...context import Context
from ...units import pt
from ..rectangle import Rectangle
from ..view import View
from ..zstack import ZStack
from .semantic_view import SemanticView


@dataclass(frozen=True)
class PipelineStage(SemanticView):
    """Display a labeled stage suitable for use in a :class:`Pipeline`.

    Args:
        label: Arbitrary view content shown inside the stage.
        emphasis: Foreground style applied to the label by the default recipe.
    """

    label: View
    emphasis: str = "primary"

    def __post_init__(self) -> None:
        if not isinstance(self.label, View):
            raise TypeError(
                "PipelineStage.label must be a View; wrap text in Text(...)"
            )

    def default_body(self, context: Context) -> View:
        """Place the padded label over a themed surface rectangle."""
        return ZStack(
            Rectangle().foreground_style("surface"),
            self.label.foreground_style(self.emphasis).padding(pt(20)),
        )
