"""A semantic container for grouped content on a surface."""

from __future__ import annotations

from dataclasses import dataclass

from ...context import Context
from ...geometry import RelativePoint
from ...units import pt
from ..rectangle import Rectangle
from ..view import View
from ..zstack import ZStack
from .semantic_view import SemanticView


@dataclass(frozen=True)
class Card(SemanticView):
    """Place arbitrary content at the top leading edge of a padded surface."""

    content: View
    background_style: str = "surface"
    content_style: str = "primary"

    def __post_init__(self) -> None:
        if not isinstance(self.content, View):
            raise TypeError("Card.content must be a View")

    def default_body(self, context: Context) -> View:
        return ZStack(
            Rectangle(corner_radius=pt(12)).foreground_style(self.background_style),
            self.content.foreground_style(self.content_style).padding(pt(20)),
            alignment=RelativePoint.top_leading,
        )
