from dataclasses import dataclass
from typing import Literal

from ..geometry import Point
from .drawable import Drawable


@dataclass(frozen=True)
class DrawableConnector(Drawable):
    start: Point
    end: Point
    color: str
    start_cap: Literal["none", "arrow"]
    end_cap: Literal["none", "arrow"]
