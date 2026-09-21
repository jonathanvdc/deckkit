from __future__ import annotations

from dataclasses import dataclass

from ..units import Length, pt
from .bounds import Bounds
from .drawable import Drawable


@dataclass(frozen=True)
class DrawableRectangle(Drawable):
    content_bounds: Bounds
    color: str
    corner_radius: Length = pt(0)
    stroke: str | None = None
    stroke_width: Length = pt(0)
    dash: tuple[Length, ...] = ()
