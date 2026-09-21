from dataclasses import dataclass
from typing import Literal

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
    opacity: float = 1.0
    line_cap: Literal["butt", "round", "square"] = "butt"
    line_join: Literal["miter", "round", "bevel"] = "miter"
