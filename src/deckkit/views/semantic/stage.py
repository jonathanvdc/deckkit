from __future__ import annotations

from dataclasses import dataclass

from ...context import Context
from ...units import pt
from ..rectangle import Rectangle
from ..view import View
from ..zstack import ZStack
from .semantic_view import SemanticView


@dataclass(frozen=True)
class Stage(SemanticView):
    label: View
    emphasis: str = "primary"

    def __post_init__(self) -> None:
        if not isinstance(self.label, View):
            raise TypeError("Stage.label must be a View; wrap text in Text(...)")

    def default_body(self, context: Context) -> View:
        return ZStack(
            Rectangle().foreground_style("surface"),
            self.label.foreground_style(self.emphasis).padding(pt(20)),
        )
