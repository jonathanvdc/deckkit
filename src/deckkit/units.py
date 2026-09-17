"""Physical lengths, normalized to points (72 points per inch)."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import overload


@dataclass(frozen=True, order=True)
class Length:
    points: float

    def __post_init__(self) -> None:
        if isinstance(self.points, bool) or not isinstance(self.points, (int, float)):
            raise TypeError("Length requires a numeric point value")
        if not isfinite(self.points):
            raise ValueError("Lengths must be finite")
        object.__setattr__(self, "points", float(self.points))

    def __add__(self, other: Length) -> Length:
        if not isinstance(other, Length):
            return NotImplemented
        return Length(self.points + other.points)

    def __sub__(self, other: Length) -> Length:
        if not isinstance(other, Length):
            return NotImplemented
        return Length(self.points - other.points)

    def __mul__(self, factor: float) -> Length:
        if not isinstance(factor, (int, float)):
            return NotImplemented
        return Length(self.points * factor)

    def __rmul__(self, factor: float) -> Length:
        return self * factor

    @overload
    def __truediv__(self, other: Length) -> float: ...
    @overload
    def __truediv__(self, other: float) -> Length: ...

    def __truediv__(self, other: Length | float) -> Length | float:
        if isinstance(other, Length):
            return self.points / other.points
        if isinstance(other, (int, float)):
            return Length(self.points / other)
        return NotImplemented

    def __neg__(self) -> Length:
        return Length(-self.points)

    def __repr__(self) -> str:
        return f"pt({self.points:g})"


def pt(value: float) -> Length:
    return Length(value)


def inch(value: float) -> Length:
    return Length(value * 72)


def cm(value: float) -> Length:
    return Length(value * 72 / 2.54)


def require_length(value: Length) -> None:
    """Reject untyped callers' bare numbers at public geometry boundaries."""
    if not isinstance(value, Length):
        raise TypeError("Expected Length; use pt(...), inch(...), or cm(...)")
