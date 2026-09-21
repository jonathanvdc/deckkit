from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

from ..geometry import Point
from ..units import Length
from .drawable import Drawable


class DrawablePathCommand(ABC):
    """A backend-independent command in a resolved drawable path."""

    @property
    @abstractmethod
    def points(self) -> tuple[Point, ...]:
        """Return the points referenced by this command."""
        raise NotImplementedError


@dataclass(frozen=True)
class PathMove(DrawablePathCommand):
    point: Point

    @property
    def points(self) -> tuple[Point, ...]:
        return (self.point,)


@dataclass(frozen=True)
class PathLine(DrawablePathCommand):
    point: Point

    @property
    def points(self) -> tuple[Point, ...]:
        return (self.point,)


@dataclass(frozen=True)
class PathQuadratic(DrawablePathCommand):
    control: Point
    end: Point

    @property
    def points(self) -> tuple[Point, ...]:
        return self.control, self.end


@dataclass(frozen=True)
class PathCubic(DrawablePathCommand):
    control1: Point
    control2: Point
    end: Point

    @property
    def points(self) -> tuple[Point, ...]:
        return self.control1, self.control2, self.end


@dataclass(frozen=True)
class PathClose(DrawablePathCommand):
    @property
    def points(self) -> tuple[Point, ...]:
        return ()


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
