from __future__ import annotations

from dataclasses import dataclass

from ..measurement import MeasuredRichText
from .bounds import Bounds
from .drawable import Drawable


@dataclass(frozen=True)
class DrawableRichText(Drawable):
    """Measured rich text with fallback children for simple drawing backends."""

    content_bounds: Bounds
    metrics: MeasuredRichText
    _children: tuple[Drawable, ...]

    @property
    def children(self) -> tuple[Drawable, ...]:
        return self._children
