from dataclasses import dataclass

from ..geometry import Point
from ..units import Length
from .drawable import Drawable


@dataclass(frozen=True)
class DrawableLine(Drawable):
    start: Point
    end: Point
    color: str
    width: Length
    dash: tuple[Length, ...] = ()
