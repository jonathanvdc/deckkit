from __future__ import annotations

from dataclasses import dataclass

from ..context import Context
from ..expanded_views import ExpandedMetadata, ExpandedRectangle
from ..layouts import ShapeLayout
from ..theme import ForegroundColor
from ..units import Length, pt, require_length
from .primitive_view import PrimitiveView


@dataclass(frozen=True)
class Rectangle(PrimitiveView):
    corner_radius: Length = pt(0)

    def __post_init__(self) -> None:
        require_length(self.corner_radius)
        if self.corner_radius.points < 0:
            raise ValueError("Rectangle corner radius must be non-negative")

    def expand(self, context: Context, metadata: ExpandedMetadata) -> ExpandedRectangle:
        return ExpandedRectangle(
            metadata,
            ShapeLayout(),
            context.environment[ForegroundColor].hex,
            self.corner_radius,
        )
