from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import ClassVar

from .units import Length, require_length


@dataclass(frozen=True)
class Point:
    x: Length
    y: Length

    def __post_init__(self) -> None:
        require_length(self.x)
        require_length(self.y)


@dataclass(frozen=True)
class RelativePoint:
    x: float
    y: float

    center: ClassVar[RelativePoint]
    top: ClassVar[RelativePoint]
    bottom: ClassVar[RelativePoint]
    leading: ClassVar[RelativePoint]
    trailing: ClassVar[RelativePoint]
    top_leading: ClassVar[RelativePoint]
    top_trailing: ClassVar[RelativePoint]
    bottom_leading: ClassVar[RelativePoint]
    bottom_trailing: ClassVar[RelativePoint]

    def __post_init__(self) -> None:
        if not isfinite(self.x) or not isfinite(self.y):
            raise ValueError("RelativePoint coordinates must be finite")


RelativePoint.center = RelativePoint(0.5, 0.5)
RelativePoint.top = RelativePoint(0.5, 0)
RelativePoint.bottom = RelativePoint(0.5, 1)
RelativePoint.leading = RelativePoint(0, 0.5)
RelativePoint.trailing = RelativePoint(1, 0.5)
RelativePoint.top_leading = RelativePoint(0, 0)
RelativePoint.top_trailing = RelativePoint(1, 0)
RelativePoint.bottom_leading = RelativePoint(0, 1)
RelativePoint.bottom_trailing = RelativePoint(1, 1)
