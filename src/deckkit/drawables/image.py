from dataclasses import dataclass
from typing import Literal

from .bounds import Bounds
from .drawable import Drawable


@dataclass(frozen=True)
class DrawableImage(Drawable):
    content_bounds: Bounds
    data: bytes
    mime: str
    intrinsic_pixels: tuple[int, int]
    fit: Literal["contain", "cover"]
