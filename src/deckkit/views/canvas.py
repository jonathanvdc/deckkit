from __future__ import annotations

from dataclasses import dataclass

from ..canvas import CanvasRenderer
from ..context import Context
from ..expanded_views import ExpandedCanvas, ExpandedMetadata
from ..layouts import CanvasLayout
from .primitive_view import PrimitiveView


@dataclass(frozen=True)
class Canvas(PrimitiveView):
    """A size-dependent retained drawing scene in local physical coordinates."""

    renderer: CanvasRenderer

    def __post_init__(self) -> None:
        if not callable(self.renderer):
            raise TypeError("Canvas renderer must be callable")

    def expand(self, context: Context, metadata: ExpandedMetadata) -> ExpandedCanvas:
        return ExpandedCanvas(
            metadata,
            CanvasLayout(self.renderer, context.environment),
            self.renderer,
        )
