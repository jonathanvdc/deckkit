from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Union

from ..geometry import Point
from ..units import Length
from .drawable import Drawable


@dataclass(frozen=True)
class PathMove:
    point: Point


@dataclass(frozen=True)
class PathLine:
    point: Point


@dataclass(frozen=True)
class PathQuadratic:
    control: Point
    end: Point


@dataclass(frozen=True)
class PathCubic:
    control1: Point
    control2: Point
    end: Point


@dataclass(frozen=True)
class PathClose:
    pass


DrawablePathCommand = Union[PathMove, PathLine, PathQuadratic, PathCubic, PathClose]


@dataclass(frozen=True)
class DrawablePath(Drawable):
    commands: tuple[DrawablePathCommand, ...]
    fill: str | None
    stroke: str | None
    stroke_width: Length
    dash: tuple[Length, ...] = ()
    fill_opacity: float = 1.0
    stroke_opacity: float = 1.0
    line_cap: Literal["butt", "round", "square"] = "butt"
    line_join: Literal["miter", "round", "bevel"] = "miter"
