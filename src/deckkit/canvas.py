"""Retained, size-dependent 2D drawing content."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from math import cos, isfinite, pi, sin, tan
from types import MappingProxyType
from typing import TYPE_CHECKING, Literal, Union

from typing_extensions import TypeAlias

from .context import Environment
from .drawables import (
    Bounds,
    Drawable,
    DrawableEllipse,
    DrawableLine,
    DrawableMetadata,
    DrawablePath,
    DrawableRectangle,
    DrawableText,
    PathClose,
    PathCubic,
    PathLine,
    PathMove,
    PathQuadratic,
)
from .geometry import Point
from .theme import Color, ColorStyle, ForegroundColor, TextStyle, Typography
from .tokens import DesignToken
from .units import Length, pt, require_length

if TYPE_CHECKING:
    from .fonts import FontResolver
    from .measurement import TextMeasurer


@dataclass(frozen=True)
class CanvasSize:
    width: Length
    height: Length

    def __post_init__(self) -> None:
        require_length(self.width)
        require_length(self.height)
        if self.width < pt(0) or self.height < pt(0):
            raise ValueError("Canvas dimensions must be non-negative")


@dataclass(frozen=True)
class CanvasContext:
    environment: Environment
    measurer: TextMeasurer
    font_resolver: FontResolver

    def color(self, style: ColorStyle = ForegroundColor) -> Color:
        return style if isinstance(style, Color) else self.environment[style]


@dataclass(frozen=True)
class Stroke:
    style: ColorStyle = ForegroundColor
    width: Length = pt(1)
    dash: tuple[Length, ...] = ()

    def __post_init__(self) -> None:
        require_length(self.width)
        if self.width <= pt(0):
            raise ValueError("Stroke width must be positive")
        for segment in self.dash:
            require_length(segment)
            if segment <= pt(0):
                raise ValueError("Stroke dash lengths must be positive")


class CanvasElement(ABC):
    key: str | None

    @property
    @abstractmethod
    def anchor_bounds(self) -> Bounds:
        """Return this element's visible bounds in Canvas-local coordinates."""
        raise NotImplementedError

    @abstractmethod
    def make_drawable(
        self,
        identity: str,
        origin: Point,
        context: CanvasContext,
        metadata: DrawableMetadata,
    ) -> Drawable:
        raise NotImplementedError


@dataclass(frozen=True)
class CanvasText(CanvasElement):
    text: str
    position: Point
    typography: DesignToken[Typography] | Typography = TextStyle
    color: ColorStyle = ForegroundColor
    horizontal_alignment: Literal["left", "center", "right"] = "left"
    vertical_alignment: Literal["top", "center", "bottom"] = "top"
    key: str | None = None

    def __post_init__(self) -> None:
        _validate_key(self.key)
        if not isinstance(self.text, str):
            raise TypeError("CanvasText.text must be a string")
        if "\n" in self.text:
            raise ValueError("CanvasText currently supports one line")
        if self.horizontal_alignment not in ("left", "center", "right"):
            raise ValueError("Unknown horizontal CanvasText alignment")
        if self.vertical_alignment not in ("top", "center", "bottom"):
            raise ValueError("Unknown vertical CanvasText alignment")

    def _measure(self, context: CanvasContext):  # type: ignore[no-untyped-def]
        typography = (
            self.typography
            if isinstance(self.typography, Typography)
            else context.environment[self.typography]
        )
        font = context.font_resolver.resolve(typography.font)
        metrics = context.measurer.measure(
            self.text,
            font,
            typography.size,
            pt(1_000_000_000),
            typography.line_spacing,
            "verbatim",
        )
        return typography, font, metrics

    def _local_bounds(self, context: CanvasContext) -> Bounds:
        _, _, metrics = self._measure(context)
        horizontal = {"left": 0.0, "center": 0.5, "right": 1.0}[
            self.horizontal_alignment
        ]
        vertical = {"top": 0.0, "center": 0.5, "bottom": 1.0}[self.vertical_alignment]
        return Bounds(
            self.position.x - metrics.width * horizontal,
            self.position.y - metrics.height * vertical,
            metrics.width,
            metrics.height,
        )

    @property
    def anchor_bounds(self) -> Bounds:
        # Text bounds depend on font measurement. The Canvas layout replaces this
        # placeholder with measured bounds when exporting keyed element anchors.
        return Bounds(self.position.x, self.position.y, pt(0), pt(0))

    def measured_anchor_bounds(self, context: CanvasContext) -> Bounds:
        return self._local_bounds(context)

    def make_drawable(
        self,
        identity: str,
        origin: Point,
        context: CanvasContext,
        metadata: DrawableMetadata,
    ) -> Drawable:
        typography, font, metrics = self._measure(context)
        bounds = _translate_bounds(self._local_bounds(context), origin)
        return DrawableText(
            identity,
            bounds,
            metadata,
            bounds,
            self.text,
            context.color(self.color).hex,
            font,
            typography.font,
            typography.size,
            metrics,
        )


@dataclass(frozen=True)
class Rect(CanvasElement):
    bounds: Bounds
    fill: ColorStyle = ForegroundColor
    stroke: Stroke | None = None
    corner_radius: Length = pt(0)
    key: str | None = None

    def __post_init__(self) -> None:
        _validate_key(self.key)
        _validate_bounds(self.bounds)
        require_length(self.corner_radius)
        if self.corner_radius < pt(0):
            raise ValueError("Rectangle corner radius must be non-negative")

    @property
    def anchor_bounds(self) -> Bounds:
        return self.bounds

    def make_drawable(self, identity, origin, context, metadata):  # type: ignore[no-untyped-def]
        bounds = _translate_bounds(self.bounds, origin)
        radius = Length(
            min(
                self.corner_radius.points,
                bounds.width.points / 2,
                bounds.height.points / 2,
            )
        )
        return DrawableRectangle(
            identity,
            bounds,
            metadata,
            bounds,
            context.color(self.fill).hex,
            radius,
            context.color(self.stroke.style).hex if self.stroke else None,
            self.stroke.width if self.stroke else pt(0),
            self.stroke.dash if self.stroke else (),
        )


@dataclass(frozen=True)
class Line(CanvasElement):
    start: Point
    end: Point
    stroke: Stroke = Stroke()
    key: str | None = None

    def __post_init__(self) -> None:
        _validate_key(self.key)

    @property
    def anchor_bounds(self) -> Bounds:
        return _point_bounds(self.start, self.end)

    def make_drawable(self, identity, origin, context, metadata):  # type: ignore[no-untyped-def]
        start, end = (
            _translate_point(self.start, origin),
            _translate_point(self.end, origin),
        )
        bounds = _point_bounds(start, end)
        return DrawableLine(
            identity,
            bounds,
            metadata,
            start,
            end,
            context.color(self.stroke.style).hex,
            self.stroke.width,
            self.stroke.dash,
        )


@dataclass(frozen=True)
class Ellipse(CanvasElement):
    bounds: Bounds
    fill: ColorStyle | None = ForegroundColor
    stroke: Stroke | None = None
    key: str | None = None

    def __post_init__(self) -> None:
        _validate_key(self.key)
        _validate_bounds(self.bounds)

    @property
    def anchor_bounds(self) -> Bounds:
        return self.bounds

    def make_drawable(self, identity, origin, context, metadata):  # type: ignore[no-untyped-def]
        bounds = _translate_bounds(self.bounds, origin)
        return DrawableEllipse(
            identity,
            bounds,
            metadata,
            bounds,
            context.color(self.fill).hex if self.fill is not None else None,
            context.color(self.stroke.style).hex if self.stroke else None,
            self.stroke.width if self.stroke else pt(0),
            self.stroke.dash if self.stroke else (),
        )


@dataclass(frozen=True)
class MoveTo:
    point: Point


@dataclass(frozen=True)
class LineTo:
    point: Point


@dataclass(frozen=True)
class QuadraticTo:
    control: Point
    end: Point


@dataclass(frozen=True)
class CubicTo:
    control1: Point
    control2: Point
    end: Point


@dataclass(frozen=True)
class ArcTo:
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


@dataclass(frozen=True)
class ClosePath:
    pass


CanvasPathCommand = Union[MoveTo, LineTo, QuadraticTo, CubicTo, ArcTo, ClosePath]


@dataclass(frozen=True)
class Path(CanvasElement):
    commands: tuple[CanvasPathCommand, ...]
    fill: ColorStyle | None = None
    stroke: Stroke | None = Stroke()
    key: str | None = None

    def __post_init__(self) -> None:
        _validate_key(self.key)
        if not self.commands or not isinstance(self.commands[0], MoveTo):
            raise ValueError("A Canvas path must begin with MoveTo")
        if any(isinstance(command, MoveTo) for command in self.commands[1:]):
            raise ValueError("Canvas paths currently support one subpath")
        if not any(
            isinstance(command, (LineTo, QuadraticTo, CubicTo, ArcTo))
            for command in self.commands
        ):
            raise ValueError("A Canvas path requires at least one drawing command")
        if self.fill is None and self.stroke is None:
            raise ValueError("A Canvas path requires a fill or stroke")

    @property
    def anchor_bounds(self) -> Bounds:
        commands = _resolve_arcs(self.commands)
        return _points_bounds(
            tuple(point for command in commands for point in _command_points(command))
        )

    def make_drawable(self, identity, origin, context, metadata):  # type: ignore[no-untyped-def]
        commands = _resolve_arcs(self.commands)
        points = tuple(
            point for command in commands for point in _command_points(command)
        )
        translated = tuple(
            PathMove(_translate_point(command.point, origin))
            if isinstance(command, MoveTo)
            else PathLine(_translate_point(command.point, origin))
            if isinstance(command, LineTo)
            else PathQuadratic(
                _translate_point(command.control, origin),
                _translate_point(command.end, origin),
            )
            if isinstance(command, QuadraticTo)
            else PathCubic(
                _translate_point(command.control1, origin),
                _translate_point(command.control2, origin),
                _translate_point(command.end, origin),
            )
            if isinstance(command, CubicTo)
            else PathClose()
            for command in commands
        )
        bounds = _points_bounds(
            tuple(_translate_point(point, origin) for point in points)
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
        )


@dataclass(frozen=True)
class CanvasScene:
    elements: tuple[CanvasElement, ...]
    anchors: Mapping[str, Bounds]
    clip: Bounds | None

    def __init__(
        self,
        *elements: CanvasElement,
        anchors: Mapping[str, Bounds] | None = None,
        clip: Bounds | None = None,
    ) -> None:
        if not all(isinstance(element, CanvasElement) for element in elements):
            raise TypeError("CanvasScene elements must be CanvasElement values")
        if clip is not None:
            if not isinstance(clip, Bounds):
                raise TypeError("CanvasScene.clip must be Bounds")
            _validate_bounds(clip)
        keys = [element.key for element in elements if element.key is not None]
        if len(keys) != len(set(keys)):
            raise ValueError("Canvas element keys must be unique within a scene")
        exported = dict(anchors or {})
        if any(not name for name in exported):
            raise ValueError("Canvas anchor names must not be empty")
        duplicates = set(keys) & set(exported)
        if duplicates:
            raise ValueError(
                "Canvas anchors conflict with element keys: "
                + ", ".join(sorted(duplicates))
            )
        exported.update(
            (element.key, element.anchor_bounds)
            for element in elements
            if element.key is not None
        )
        object.__setattr__(self, "elements", tuple(elements))
        object.__setattr__(self, "anchors", MappingProxyType(exported))
        object.__setattr__(self, "clip", clip)

    def measured_anchors(self, context: CanvasContext) -> Mapping[str, Bounds]:
        return MappingProxyType(
            {
                **self.anchors,
                **{
                    element.key: element.measured_anchor_bounds(context)
                    for element in self.elements
                    if isinstance(element, CanvasText) and element.key is not None
                },
            }
        )


CanvasRenderer: TypeAlias = Callable[
    [CanvasContext, CanvasSize], Union[CanvasScene, Iterable[CanvasElement]]
]


def scene_from(value: CanvasScene | Iterable[CanvasElement]) -> CanvasScene:
    return value if isinstance(value, CanvasScene) else CanvasScene(*tuple(value))


def _validate_key(key: str | None) -> None:
    if key is not None and not key:
        raise ValueError("Canvas element keys must not be empty")


def _validate_bounds(bounds: Bounds) -> None:
    if bounds.width < pt(0) or bounds.height < pt(0):
        raise ValueError("Canvas element dimensions must be non-negative")


def _command_points(command: CanvasPathCommand) -> tuple[Point, ...]:
    if isinstance(command, (MoveTo, LineTo)):
        return (command.point,)
    if isinstance(command, QuadraticTo):
        return command.control, command.end
    if isinstance(command, CubicTo):
        return command.control1, command.control2, command.end
    return ()


def _resolve_arcs(
    commands: tuple[CanvasPathCommand, ...],
) -> tuple[CanvasPathCommand, ...]:
    result = []
    for command in commands:
        if not isinstance(command, ArcTo):
            result.append(command)
            continue
        segment_count = max(1, int(abs(command.sweep_angle) / 90 + 0.999999))
        start = command.start_angle * pi / 180
        delta = command.sweep_angle * pi / 180 / segment_count
        for index in range(segment_count):
            a = start + delta * index
            b = a + delta
            factor = 4 / 3 * tan(delta / 4)
            start_point = Point(
                command.center.x + command.radius_x * cos(a),
                command.center.y + command.radius_y * sin(a),
            )
            end_point = Point(
                command.center.x + command.radius_x * cos(b),
                command.center.y + command.radius_y * sin(b),
            )
            result.append(
                CubicTo(
                    Point(
                        start_point.x - command.radius_x * (factor * sin(a)),
                        start_point.y + command.radius_y * (factor * cos(a)),
                    ),
                    Point(
                        end_point.x + command.radius_x * (factor * sin(b)),
                        end_point.y - command.radius_y * (factor * cos(b)),
                    ),
                    end_point,
                )
            )
    return tuple(result)


def _translate_point(point: Point, origin: Point) -> Point:
    return Point(origin.x + point.x, origin.y + point.y)


def _translate_bounds(bounds: Bounds, origin: Point) -> Bounds:
    return Bounds(origin.x + bounds.x, origin.y + bounds.y, bounds.width, bounds.height)


def _point_bounds(start: Point, end: Point) -> Bounds:
    return Bounds(
        min(start.x, end.x),
        min(start.y, end.y),
        max(start.x, end.x) - min(start.x, end.x),
        max(start.y, end.y) - min(start.y, end.y),
    )


def _points_bounds(points: tuple[Point, ...]) -> Bounds:
    if not points:
        return Bounds(pt(0), pt(0), pt(0), pt(0))
    left = min(point.x for point in points)
    top = min(point.y for point in points)
    right = max(point.x for point in points)
    bottom = max(point.y for point in points)
    return Bounds(left, top, right - left, bottom - top)


__all__ = [
    "ArcTo",
    "CanvasContext",
    "CanvasElement",
    "CanvasPathCommand",
    "CanvasRenderer",
    "CanvasScene",
    "CanvasSize",
    "CanvasText",
    "ClosePath",
    "CubicTo",
    "Ellipse",
    "Line",
    "LineTo",
    "MoveTo",
    "Path",
    "QuadraticTo",
    "Rect",
    "Stroke",
]
