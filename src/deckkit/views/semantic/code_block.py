"""A themed container for code text."""

from __future__ import annotations

from dataclasses import dataclass

from ...context import Context
from ...geometry import RelativePoint
from ...units import pt
from ..code import Code
from ..rectangle import Rectangle
from ..view import View
from ..zstack import ZStack
from .semantic_view import SemanticView


@dataclass(frozen=True)
class CodeBlock(SemanticView):
    """Place code on a padded, theme-overridable surface."""

    content: Code
    background_style: str = "surface"

    def __post_init__(self) -> None:
        if not isinstance(self.content, Code):
            raise TypeError("CodeBlock.content must be Code")

    def default_body(self, context: Context) -> View:
        return ZStack(
            Rectangle(corner_radius=pt(8)).foreground_style(self.background_style),
            self.content.padding(pt(16)),
            alignment=RelativePoint.top_left,
        )
