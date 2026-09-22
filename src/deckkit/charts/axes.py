from __future__ import annotations

from collections.abc import Callable, Hashable
from dataclasses import dataclass
from math import ceil, isfinite
from typing import Literal

from ..canvas import CanvasContext, CanvasElement, CanvasText, Line, Stroke
from ..drawables import Bounds
from ..geometry import Point
from ..theme import (
    ChartAxisColor,
    ChartAxisTitleTextStyle,
    ChartGridColor,
    ChartTickTextStyle,
)
from ..units import Length, pt
from .context import ResolvedPositionScale
from .scales import BandScale, LinearScale, nice_ticks


def _format_tick(value: object) -> str:
    return f"{value:g}" if isinstance(value, (int, float)) else str(value)


@dataclass(frozen=True)
class Axis:
    title: str | None = None
    tick_count: int = 5
    formatter: Callable[[object], str] = _format_tick
    grid: bool = True
    label_policy: Literal["automatic", "all"] = "automatic"
    label_rotation: float = 0.0

    def __post_init__(self) -> None:
        if self.tick_count < 2:
            raise ValueError("Axis tick count must be at least two")
        if not callable(self.formatter):
            raise TypeError("Axis formatter must be callable")
        if self.label_policy not in ("automatic", "all"):
            raise ValueError("Axis label policy must be automatic or all")
        if not isfinite(self.label_rotation):
            raise ValueError("Axis label rotation must be finite")


DEFAULT_AXIS = Axis()


def required_axis_space(
    canvas: CanvasContext,
    x_scale: ResolvedPositionScale,
    y_scale: ResolvedPositionScale,
    x_axis: Axis | None,
    y_axis: Axis | None,
) -> tuple[Length, Length]:
    bottom = pt(0)
    left = pt(0)
    if x_axis is not None:
        labels = tuple(label for _, label in _tick_items(canvas, x_scale, x_axis, "x"))
        bottom = max(
            (
                _measure_tick(canvas, label, x_axis.label_rotation).height
                for label in labels
            ),
            default=pt(0),
        )
        bottom += pt(8)
        if x_axis.title:
            bottom += _measure_title(canvas, x_axis.title).height + pt(4)
    if y_axis is not None:
        labels = tuple(label for _, label in _tick_items(canvas, y_scale, y_axis, "y"))
        left = max(
            (
                _measure_tick(canvas, label, y_axis.label_rotation).width
                for label in labels
            ),
            default=pt(0),
        )
        left += pt(8)
        if y_axis.title:
            left += _measure_title(canvas, y_axis.title).height + pt(4)
    return bottom, left


def lower_axes(
    canvas: CanvasContext,
    plot: Bounds,
    x_scale: ResolvedPositionScale,
    y_scale: ResolvedPositionScale,
    x_axis: Axis | None,
    y_axis: Axis | None,
) -> tuple[CanvasElement, ...]:
    result: list[CanvasElement] = []
    axis_stroke = Stroke(ChartAxisColor, pt(1))
    grid_stroke = Stroke(ChartGridColor, pt(0.5))
    if x_axis is not None:
        baseline = plot.y + plot.height
        result.append(
            Line(
                Point(plot.x, baseline),
                Point(plot.x + plot.width, baseline),
                axis_stroke,
            )
        )
        for value, label in _tick_items(canvas, x_scale, x_axis, "x"):
            x = _position(x_scale, value)
            if x_axis.grid and plot.x < x < plot.x + plot.width:
                result.append(Line(Point(x, plot.y), Point(x, baseline), grid_stroke))
            result.append(
                Line(Point(x, baseline), Point(x, baseline + pt(4)), axis_stroke)
            )
            result.append(
                CanvasText(
                    label,
                    Point(x, baseline + pt(6)),
                    typography=ChartTickTextStyle,
                    color=ChartAxisColor,
                    horizontal_alignment="center",
                    rotation=x_axis.label_rotation,
                )
            )
        if x_axis.title:
            tick_height = max(
                (
                    _measure_tick(canvas, label).height
                    for _, label in _tick_items(canvas, x_scale, x_axis, "x")
                ),
                default=pt(0),
            )
            result.append(
                CanvasText(
                    x_axis.title,
                    Point(
                        plot.x + plot.width / 2,
                        baseline + pt(8) + tick_height + pt(4),
                    ),
                    typography=ChartAxisTitleTextStyle,
                    color=ChartAxisColor,
                    horizontal_alignment="center",
                )
            )
    if y_axis is not None:
        result.append(
            Line(
                Point(plot.x, plot.y),
                Point(plot.x, plot.y + plot.height),
                axis_stroke,
            )
        )
        for value, label in _tick_items(canvas, y_scale, y_axis, "y"):
            y = _position(y_scale, value)
            if y_axis.grid and plot.y < y < plot.y + plot.height:
                result.append(
                    Line(Point(plot.x, y), Point(plot.x + plot.width, y), grid_stroke)
                )
            result.append(Line(Point(plot.x - pt(4), y), Point(plot.x, y), axis_stroke))
            result.append(
                CanvasText(
                    label,
                    Point(plot.x - pt(6), y),
                    typography=ChartTickTextStyle,
                    color=ChartAxisColor,
                    horizontal_alignment="right",
                    vertical_alignment="center",
                    rotation=y_axis.label_rotation,
                )
            )
        if y_axis.title:
            label_width = max(
                (
                    _measure_tick(canvas, label).width
                    for _, label in _tick_items(canvas, y_scale, y_axis, "y")
                ),
                default=pt(0),
            )
            result.append(
                CanvasText(
                    y_axis.title,
                    Point(
                        plot.x
                        - label_width
                        - pt(12)
                        - _measure_title(canvas, y_axis.title).height / 2,
                        plot.y + plot.height / 2,
                    ),
                    typography=ChartAxisTitleTextStyle,
                    color=ChartAxisColor,
                    horizontal_alignment="center",
                    vertical_alignment="center",
                    rotation=-90,
                )
            )
    return tuple(result)


def _ticks(scale: ResolvedPositionScale, axis: Axis) -> tuple[float | Hashable, ...]:
    if isinstance(scale, BandScale):
        return scale.domain
    return nice_ticks(scale.domain, axis.tick_count)


def _tick_labels(scale: ResolvedPositionScale, axis: Axis) -> tuple[str, ...]:
    return tuple(axis.formatter(value) for value in _ticks(scale, axis))


def _tick_items(
    canvas: CanvasContext,
    scale: ResolvedPositionScale,
    axis: Axis,
    channel: Literal["x", "y"],
) -> tuple[tuple[float | Hashable, str], ...]:
    items = tuple(zip(_ticks(scale, axis), _tick_labels(scale, axis)))
    if not isinstance(scale, BandScale) or axis.label_policy == "all" or not items:
        return items
    extent = max(
        (
            _measure_tick(canvas, label, axis.label_rotation).width
            if channel == "x"
            else _measure_tick(canvas, label, axis.label_rotation).height
            for _, label in items
        ),
        default=pt(0),
    )
    if scale.step <= pt(0):
        return items
    stride = max(1, ceil((extent + pt(6)).points / scale.step.points))
    return items[::stride]


def _position(scale: ResolvedPositionScale, value: float | Hashable) -> Length:
    if isinstance(scale, LinearScale):
        assert isinstance(value, (int, float))
        return scale(float(value))
    return scale.center(value)


def _measure_tick(canvas: CanvasContext, text: str, rotation: float = 0.0) -> Bounds:
    return CanvasText(
        text,
        Point(pt(0), pt(0)),
        typography=ChartTickTextStyle,
        rotation=rotation,
    ).measured_anchor_bounds(canvas)


def _measure_title(canvas: CanvasContext, text: str) -> Bounds:
    return CanvasText(
        text, Point(pt(0), pt(0)), typography=ChartAxisTitleTextStyle
    ).measured_anchor_bounds(canvas)
