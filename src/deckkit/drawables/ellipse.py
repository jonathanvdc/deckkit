from __future__ import annotations

from dataclasses import dataclass

from ..units import Length
from .bounds import Bounds
from .drawable import Drawable


@dataclass(frozen=True)
class DrawableEllipse(Drawable):
    content_bounds: Bounds
    fill: str | None
    stroke: str | None
    stroke_width: Length
    dash: tuple[Length, ...] = ()
