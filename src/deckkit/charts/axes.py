from __future__ import annotations

from collections.abc import Callable, Hashable
from dataclasses import dataclass

from ..canvas import CanvasContext, CanvasElement, CanvasText, Line, Stroke
from ..drawables import Bounds
from ..geometry import Point
from ..theme import MutedColor
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

    def __post_init__(self) -> None:
        if self.tick_count < 2:
            raise ValueError("Axis tick count must be at least two")
        if not callable(self.formatter):
            raise TypeError("Axis formatter must be callable")


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
        labels = _tick_labels(x_scale, x_axis)
        bottom = max(
            (_measure(canvas, label).height for label in labels), default=pt(0)
        )
        bottom += pt(8)
        if x_axis.title:
            bottom += _measure(canvas, x_axis.title).height + pt(4)
    if y_axis is not None:
        labels = _tick_labels(y_scale, y_axis)
        left = max((_measure(canvas, label).width for label in labels), default=pt(0))
        left += pt(8)
        if y_axis.title:
            left += _measure(canvas, y_axis.title).height + pt(4)
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
    stroke = Stroke(MutedColor, pt(0.75), opacity=0.7)
    if x_axis is not None:
        baseline = plot.y + plot.height
        result.append(
            Line(Point(plot.x, baseline), Point(plot.x + plot.width, baseline), stroke)
        )
        for value, label in zip(_ticks(x_scale, x_axis), _tick_labels(x_scale, x_axis)):
            x = _position(x_scale, value)
            if x_axis.grid:
                result.append(Line(Point(x, plot.y), Point(x, baseline), stroke))
            result.append(Line(Point(x, baseline), Point(x, baseline + pt(4)), stroke))
            result.append(
                CanvasText(
                    label,
                    Point(x, baseline + pt(6)),
                    color=MutedColor,
                    horizontal_alignment="center",
                )
            )
        if x_axis.title:
            result.append(
                CanvasText(
                    x_axis.title,
                    Point(plot.x + plot.width / 2, baseline + pt(22)),
                    color=MutedColor,
                    horizontal_alignment="center",
                )
            )
    if y_axis is not None:
        result.append(
            Line(Point(plot.x, plot.y), Point(plot.x, plot.y + plot.height), stroke)
        )
        for value, label in zip(_ticks(y_scale, y_axis), _tick_labels(y_scale, y_axis)):
            y = _position(y_scale, value)
            if y_axis.grid:
                result.append(
                    Line(Point(plot.x, y), Point(plot.x + plot.width, y), stroke)
                )
            result.append(Line(Point(plot.x - pt(4), y), Point(plot.x, y), stroke))
            result.append(
                CanvasText(
                    label,
                    Point(plot.x - pt(6), y),
                    color=MutedColor,
                    horizontal_alignment="right",
                    vertical_alignment="center",
                )
            )
        if y_axis.title:
            label_width = max(
                (
                    _measure(canvas, label).width
                    for label in _tick_labels(y_scale, y_axis)
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
                        - _measure(canvas, y_axis.title).height / 2,
                        plot.y + plot.height / 2,
                    ),
                    color=MutedColor,
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


def _position(scale: ResolvedPositionScale, value: float | Hashable) -> Length:
    if isinstance(scale, LinearScale):
        assert isinstance(value, (int, float))
        return scale(float(value))
    return scale.center(value)


def _measure(canvas: CanvasContext, text: str) -> Bounds:
    return CanvasText(text, Point(pt(0), pt(0))).measured_anchor_bounds(canvas)
