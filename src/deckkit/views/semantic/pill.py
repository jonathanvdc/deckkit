"""A semantic view for compact labeled content."""

from __future__ import annotations

from dataclasses import dataclass

from ...context import Context
from ...units import pt
from ..rectangle import Rectangle
from ..view import View
from ..zstack import ZStack
from .semantic_view import SemanticView


@dataclass(frozen=True)
class Pill(SemanticView):
    """Display arbitrary content over a capsule-shaped background.

    Args:
        content: View displayed inside the pill.
        background_style: Theme color role used for the capsule.
        content_style: Theme color role inherited by the content.
    """

    content: View
    background_style: str = "surface"
    content_style: str = "primary"

    def __post_init__(self) -> None:
        if not isinstance(self.content, View):
            raise TypeError("Pill.content must be a View; wrap text in Text(...)")

    def body(self, context: Context) -> View:
        """Place padded content over a themed capsule."""
        return ZStack(
            Rectangle(corner_radius=pt(18)).foreground_style(self.background_style),
            self.content.foreground_style(self.content_style).padding(pt(8)),
        )
