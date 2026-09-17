from dataclasses import dataclass

from .bounds import Bounds
from .drawable import Drawable


@dataclass(frozen=True)
class DrawableRectangle(Drawable):
    content_bounds: Bounds
    color: str
