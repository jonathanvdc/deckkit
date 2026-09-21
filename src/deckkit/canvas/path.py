from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from math import cos, isfinite, pi, sin, tan

from ..drawables import (
    Bounds,
    DrawablePath,
    DrawablePathCommand,
    PathClose,
    PathCubic,
    PathLine,
    PathMove,
    PathQuadratic,
)
from ..geometry import Point
from ..theme import ColorStyle
from ..units import Length, pt, require_length
from ._geometry import points_bounds, translate_point, validate_key, validate_opacity
from .elements import CanvasElement
from .style import Stroke


class CanvasPathCommand(ABC):
    """A path command expressed in Canvas-local coordinates."""

    @property
    @abstractmethod
    def points(self) -> tuple[Point, ...]:
        """Return the points that determine this command's geometry."""
        raise NotImplementedError

    @property
    def draws(self) -> bool:
        return True

    @abstractmethod
    def resolve(self) -> tuple[ResolvedPathCommand, ...]:
        """Resolve the command to primitives supported by every backend."""
        raise NotImplementedError


class ResolvedPathCommand(CanvasPathCommand, ABC):
    """A Canvas path command that can lower directly to a drawable command."""

    def resolve(self) -> tuple[ResolvedPathCommand, ...]:
        return (self,)

    @abstractmethod
    def make_drawable(self, origin: Point) -> DrawablePathCommand:
        raise NotImplementedError


@dataclass(frozen=True)
class MoveTo(ResolvedPathCommand):
    point: Point

    @property
    def points(self) -> tuple[Point, ...]:
        return (self.point,)

    @property
    def draws(self) -> bool:
        return False

    def make_drawable(self, origin: Point) -> PathMove:
        return PathMove(translate_point(self.point, origin))


@dataclass(frozen=True)
class LineTo(ResolvedPathCommand):
    point: Point

    @property
    def points(self) -> tuple[Point, ...]:
        return (self.point,)

    def make_drawable(self, origin: Point) -> PathLine:
        return PathLine(translate_point(self.point, origin))


@dataclass(frozen=True)
class QuadraticTo(ResolvedPathCommand):
    control: Point
    end: Point

    @property
    def points(self) -> tuple[Point, ...]:
        return self.control, self.end

    def make_drawable(self, origin: Point) -> PathQuadratic:
        return PathQuadratic(
            translate_point(self.control, origin), translate_point(self.end, origin)
        )


@dataclass(frozen=True)
class CubicTo(ResolvedPathCommand):
    control1: Point
    control2: Point
    end: Point

    @property
    def points(self) -> tuple[Point, ...]:
        return self.control1, self.control2, self.end

    def make_drawable(self, origin: Point) -> PathCubic:
        return PathCubic(
            translate_point(self.control1, origin),
            translate_point(self.control2, origin),
            translate_point(self.end, origin),
        )


@dataclass(frozen=True)
class ArcTo(CanvasPathCommand):
    """An elliptical arc using center geometry and a clockwise sweep in degrees."""

    center: Point
    radius_x: Length
    radius_y: Length
    start_angle: float
    sweep_angle: float

    def __post_init__(self) -> None:
        require_length(self.radius_x)
        require_length(self.radius_y)
        if self.radius_x <= pt(0) or self.radius_y <= pt(0):
            raise ValueError("Canvas arc radii must be positive")
        if not isfinite(self.start_angle) or not isfinite(self.sweep_angle):
            raise ValueError("Canvas arc angles must be finite")
        if self.sweep_angle == 0 or abs(self.sweep_angle) > 360:
            raise ValueError("Canvas arc sweep must be nonzero and at most 360 degrees")

    @property
    def points(self) -> tuple[Point, ...]:
        return tuple(point for command in self.resolve() for point in command.points)

    def resolve(self) -> tuple[ResolvedPathCommand, ...]:
        result: list[ResolvedPathCommand] = []
        segment_count = max(1, int(abs(self.sweep_angle) / 90 + 0.999999))
        start = self.start_angle * pi / 180
        delta = self.sweep_angle * pi / 180 / segment_count
        for index in range(segment_count):
            a = start + delta * index
            b = a + delta
            factor = 4 / 3 * tan(delta / 4)
            start_point = Point(
                self.center.x + self.radius_x * cos(a),
                self.center.y + self.radius_y * sin(a),
            )
            end_point = Point(
                self.center.x + self.radius_x * cos(b),
                self.center.y + self.radius_y * sin(b),
            )
            result.append(
                CubicTo(
                    Point(
                        start_point.x - self.radius_x * (factor * sin(a)),
                        start_point.y + self.radius_y * (factor * cos(a)),
                    ),
                    Point(
                        end_point.x + self.radius_x * (factor * sin(b)),
                        end_point.y - self.radius_y * (factor * cos(b)),
                    ),
                    end_point,
                )
            )
        return tuple(result)


@dataclass(frozen=True)
class ClosePath(ResolvedPathCommand):
    @property
    def points(self) -> tuple[Point, ...]:
        return ()

    @property
    def draws(self) -> bool:
        return False

    def make_drawable(self, origin: Point) -> PathClose:
        return PathClose()


@dataclass(frozen=True)
class Path(CanvasElement):
    commands: tuple[CanvasPathCommand, ...]
    fill: ColorStyle | None = None
    stroke: Stroke | None = field(default_factory=Stroke)
    fill_opacity: float = 1.0
    key: str | None = None

    def __post_init__(self) -> None:
        validate_key(self.key)
        if not self.commands or not isinstance(self.commands[0], MoveTo):
            raise ValueError("A Canvas path must begin with MoveTo")
        if any(isinstance(command, MoveTo) for command in self.commands[1:]):
            raise ValueError("Canvas paths currently support one subpath")
        if not any(command.draws for command in self.commands):
            raise ValueError("A Canvas path requires at least one drawing command")
        if self.fill is None and self.stroke is None:
            raise ValueError("A Canvas path requires a fill or stroke")
        validate_opacity(self.fill_opacity)

    @property
    def anchor_bounds(self) -> Bounds:
        commands = _resolve_path_commands(self.commands)
        return points_bounds(
            tuple(point for command in commands for point in command.points)
        )

    def make_drawable(self, identity, origin, context, metadata):  # type: ignore[no-untyped-def]
        commands = _resolve_path_commands(self.commands)
        points = tuple(point for command in commands for point in command.points)
        translated = tuple(command.make_drawable(origin) for command in commands)
        bounds = points_bounds(
            tuple(translate_point(point, origin) for point in points)
        )
        return DrawablePath(
            identity,
            bounds,
            metadata,
            translated,
            context.color(self.fill).hex if self.fill is not None else None,
            context.color(self.stroke.style).hex if self.stroke else None,
            self.stroke.width if self.stroke else pt(0),
            self.stroke.dash if self.stroke else (),
            self.fill_opacity,
            self.stroke.opacity if self.stroke else 1.0,
            self.stroke.line_cap if self.stroke else "butt",
            self.stroke.line_join if self.stroke else "miter",
        )


def _resolve_path_commands(
    commands: tuple[CanvasPathCommand, ...],
) -> tuple[ResolvedPathCommand, ...]:
    return tuple(resolved for command in commands for resolved in command.resolve())
