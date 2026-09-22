from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from math import cos, isfinite, pi, sin
from typing import Literal

from ..drawables import (
    Bounds,
    Drawable,
    DrawableEllipse,
    DrawableLine,
    DrawableMetadata,
    DrawableRectangle,
    DrawableText,
)
from ..geometry import Point
from ..theme import ColorStyle, ForegroundColor, TextStyle, Typography
from ..tokens import DesignToken
from ..units import Length, pt, require_length
from ._geometry import (
    point_bounds,
    translate_bounds,
    translate_point,
    validate_bounds,
    validate_key,
    validate_opacity,
)
from .context import CanvasContext
from .style import Stroke


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
    rotation: float = 0.0

    def __post_init__(self) -> None:
        validate_key(self.key)
        if not isinstance(self.text, str):
            raise TypeError("CanvasText.text must be a string")
        if "\n" in self.text:
            raise ValueError("CanvasText currently supports one line")
        if self.horizontal_alignment not in ("left", "center", "right"):
            raise ValueError("Unknown horizontal CanvasText alignment")
        if self.vertical_alignment not in ("top", "center", "bottom"):
            raise ValueError("Unknown vertical CanvasText alignment")
        if not isfinite(self.rotation):
            raise ValueError("CanvasText rotation must be finite")

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
        return Bounds(self.position.x, self.position.y, pt(0), pt(0))

    def measured_anchor_bounds(self, context: CanvasContext) -> Bounds:
        return _rotated_bounds(self._local_bounds(context), self.rotation)

    def make_drawable(
        self,
        identity: str,
        origin: Point,
        context: CanvasContext,
        metadata: DrawableMetadata,
    ) -> Drawable:
        typography, font, metrics = self._measure(context)
        content_bounds = translate_bounds(self._local_bounds(context), origin)
        bounds = _rotated_bounds(content_bounds, self.rotation)
        return DrawableText(
            identity,
            content_bounds,
            metadata,
            bounds,
            self.text,
            context.color(self.color).hex,
            font,
            typography.font,
            typography.size,
            metrics,
            self.rotation,
        )


@dataclass(frozen=True)
class Rect(CanvasElement):
    bounds: Bounds
    fill: ColorStyle = ForegroundColor
    stroke: Stroke | None = None
    corner_radius: Length = pt(0)
    fill_opacity: float = 1.0
    key: str | None = None

    def __post_init__(self) -> None:
        validate_key(self.key)
        validate_bounds(self.bounds)
        require_length(self.corner_radius)
        if self.corner_radius < pt(0):
            raise ValueError("Rectangle corner radius must be non-negative")
        validate_opacity(self.fill_opacity)

    @property
    def anchor_bounds(self) -> Bounds:
        return self.bounds

    def make_drawable(self, identity, origin, context, metadata):  # type: ignore[no-untyped-def]
        bounds = translate_bounds(self.bounds, origin)
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
            self.fill_opacity,
            self.stroke.opacity if self.stroke else 1.0,
            self.stroke.line_cap if self.stroke else "butt",
            self.stroke.line_join if self.stroke else "miter",
        )


@dataclass(frozen=True)
class Line(CanvasElement):
    start: Point
    end: Point
    stroke: Stroke = field(default_factory=Stroke)
    key: str | None = None

    def __post_init__(self) -> None:
        validate_key(self.key)

    @property
    def anchor_bounds(self) -> Bounds:
        return point_bounds(self.start, self.end)

    def make_drawable(self, identity, origin, context, metadata):  # type: ignore[no-untyped-def]
        start = translate_point(self.start, origin)
        end = translate_point(self.end, origin)
        bounds = point_bounds(start, end)
        return DrawableLine(
            identity,
            bounds,
            metadata,
            start,
            end,
            context.color(self.stroke.style).hex,
            self.stroke.width,
            self.stroke.dash,
            self.stroke.opacity,
            self.stroke.line_cap,
            self.stroke.line_join,
        )


@dataclass(frozen=True)
class Ellipse(CanvasElement):
    bounds: Bounds
    fill: ColorStyle | None = ForegroundColor
    stroke: Stroke | None = None
    fill_opacity: float = 1.0
    key: str | None = None

    def __post_init__(self) -> None:
        validate_key(self.key)
        validate_bounds(self.bounds)
        validate_opacity(self.fill_opacity)

    @property
    def anchor_bounds(self) -> Bounds:
        return self.bounds

    def make_drawable(self, identity, origin, context, metadata):  # type: ignore[no-untyped-def]
        bounds = translate_bounds(self.bounds, origin)
        return DrawableEllipse(
            identity,
            bounds,
            metadata,
            bounds,
            context.color(self.fill).hex if self.fill is not None else None,
            context.color(self.stroke.style).hex if self.stroke else None,
            self.stroke.width if self.stroke else pt(0),
            self.stroke.dash if self.stroke else (),
            self.fill_opacity,
            self.stroke.opacity if self.stroke else 1.0,
            self.stroke.line_cap if self.stroke else "butt",
            self.stroke.line_join if self.stroke else "miter",
        )


def _rotated_bounds(bounds: Bounds, rotation: float) -> Bounds:
    if rotation % 360 == 0:
        return bounds
    angle = rotation * pi / 180
    cosine, sine = cos(angle), sin(angle)
    center_x = bounds.x + bounds.width / 2
    center_y = bounds.y + bounds.height / 2
    corners = (
        (bounds.x, bounds.y),
        (bounds.x + bounds.width, bounds.y),
        (bounds.x + bounds.width, bounds.y + bounds.height),
        (bounds.x, bounds.y + bounds.height),
    )
    rotated = tuple(
        Point(
            center_x + (x - center_x) * cosine - (y - center_y) * sine,
            center_y + (x - center_x) * sine + (y - center_y) * cosine,
        )
        for x, y in corners
    )
    left = min(point.x for point in rotated)
    top = min(point.y for point in rotated)
    right = max(point.x for point in rotated)
    bottom = max(point.y for point in rotated)
    return Bounds(left, top, right - left, bottom - top)
