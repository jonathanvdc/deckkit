from __future__ import annotations

from math import isfinite

from ..drawables import Bounds
from ..geometry import Point
from ..units import pt


def validate_key(key: str | None) -> None:
    if key is not None and not key:
        raise ValueError("Canvas element keys must not be empty")


def validate_bounds(bounds: Bounds) -> None:
    if bounds.width < pt(0) or bounds.height < pt(0):
        raise ValueError("Canvas element dimensions must be non-negative")


def validate_opacity(value: float) -> None:
    if not isfinite(value) or not 0 <= value <= 1:
        raise ValueError("Canvas opacity must be between zero and one")


def translate_point(point: Point, origin: Point) -> Point:
    return Point(origin.x + point.x, origin.y + point.y)


def translate_bounds(bounds: Bounds, origin: Point) -> Bounds:
    return Bounds(origin.x + bounds.x, origin.y + bounds.y, bounds.width, bounds.height)


def point_bounds(start: Point, end: Point) -> Bounds:
    return Bounds(
        min(start.x, end.x),
        min(start.y, end.y),
        max(start.x, end.x) - min(start.x, end.x),
        max(start.y, end.y) - min(start.y, end.y),
    )


def points_bounds(points: tuple[Point, ...]) -> Bounds:
    if not points:
        return Bounds(pt(0), pt(0), pt(0), pt(0))
    left = min(point.x for point in points)
    top = min(point.y for point in points)
    right = max(point.x for point in points)
    bottom = max(point.y for point in points)
    return Bounds(left, top, right - left, bottom - top)
