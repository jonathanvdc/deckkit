from dataclasses import dataclass

from ..units import Length, pt
from .bounds import Bounds
from .drawable import Drawable


@dataclass(frozen=True)
class DrawableRectangle(Drawable):
    content_bounds: Bounds
    color: str
    corner_radius: Length = pt(0)
