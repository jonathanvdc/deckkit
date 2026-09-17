from __future__ import annotations

from dataclasses import dataclass

from ..context import Context, ForegroundStyleKey
from ..expanded_views import ExpandedMetadata, ExpandedRectangle
from ..layouts import ShapeLayout
from .primitive_view import PrimitiveView


@dataclass(frozen=True)
class Rectangle(PrimitiveView):
    def expand(self, context: Context, metadata: ExpandedMetadata) -> ExpandedRectangle:
        return ExpandedRectangle(
            metadata,
            ShapeLayout(),
            context.environment.theme.color(
                context.environment.get(ForegroundStyleKey)
            ),
        )
