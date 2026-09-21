"""Retained, size-dependent 2D drawing content."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Union

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
    PathClose,
    PathLine,
    PathMove,
)
from .geometry import Point
from .theme import Color, ColorStyle, ForegroundColor
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
class ClosePath:
    pass


CanvasPathCommand = Union[MoveTo, LineTo, ClosePath]


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
        if not any(isinstance(command, LineTo) for command in self.commands):
            raise ValueError("A Canvas path requires at least one LineTo")
        if self.fill is None and self.stroke is None:
            raise ValueError("A Canvas path requires a fill or stroke")

    @property
    def anchor_bounds(self) -> Bounds:
        return _points_bounds(
            tuple(
                command.point
                for command in self.commands
                if isinstance(command, (MoveTo, LineTo))
            )
        )

    def make_drawable(self, identity, origin, context, metadata):  # type: ignore[no-untyped-def]
        points = tuple(
            command.point
            for command in self.commands
            if isinstance(command, (MoveTo, LineTo))
        )
        translated = tuple(
            PathMove(_translate_point(command.point, origin))
            if isinstance(command, MoveTo)
            else PathLine(_translate_point(command.point, origin))
            if isinstance(command, LineTo)
            else PathClose()
            for command in self.commands
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

    def __init__(
        self,
        *elements: CanvasElement,
        anchors: Mapping[str, Bounds] | None = None,
    ) -> None:
        if not all(isinstance(element, CanvasElement) for element in elements):
            raise TypeError("CanvasScene elements must be CanvasElement values")
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
    "CanvasContext",
    "CanvasElement",
    "CanvasPathCommand",
    "CanvasRenderer",
    "CanvasScene",
    "CanvasSize",
    "ClosePath",
    "Ellipse",
    "Line",
    "LineTo",
    "MoveTo",
    "Path",
    "Rect",
    "Stroke",
]
