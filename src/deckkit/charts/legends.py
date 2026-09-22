from __future__ import annotations

from collections.abc import Hashable
from dataclasses import dataclass

from ..canvas import CanvasContext, CanvasElement, CanvasText, Rect
from ..drawables import Bounds
from ..geometry import Point
from ..theme import ChartLegendTextStyle, ColorStyle
from ..units import Length, pt
from .scales import OrdinalScale


@dataclass(frozen=True)
class Legend:
    title: str | None = None


DEFAULT_LEGEND = Legend()


def required_legend_width(
    canvas: CanvasContext,
    scale: OrdinalScale[Hashable, ColorStyle] | None,
    legend: Legend | None,
    inferred_title: str | None,
) -> Length:
    if scale is None or legend is None:
        return pt(0)
    labels = tuple(str(value) for value in scale.domain)
    title = legend.title if legend.title is not None else inferred_title
    text_width = max(
        (
            _measure(canvas, text).width
            for text in (*labels, *((title,) if title else ()))
        ),
        default=pt(0),
    )
    return pt(12) + pt(8) + text_width + pt(16)


def lower_legend(
    canvas: CanvasContext,
    plot: Bounds,
    scale: OrdinalScale[Hashable, ColorStyle] | None,
    legend: Legend | None,
    inferred_title: str | None,
) -> tuple[CanvasElement, ...]:
    if scale is None or legend is None:
        return ()
    result: list[CanvasElement] = []
    x = plot.x + plot.width + pt(16)
    y = plot.y
    title = legend.title if legend.title is not None else inferred_title
    if title:
        result.append(CanvasText(title, Point(x, y), typography=ChartLegendTextStyle))
        y += _measure(canvas, title).height + pt(8)
    for category in scale.domain:
        label = str(category)
        row_height = max(pt(12), _measure(canvas, label).height)
        result.append(
            Rect(
                Bounds(x, y + (row_height - pt(10)) / 2, pt(10), pt(10)),
                fill=scale(category),
            )
        )
        result.append(
            CanvasText(
                label,
                Point(x + pt(18), y + row_height / 2),
                typography=ChartLegendTextStyle,
                vertical_alignment="center",
            )
        )
        y += row_height + pt(6)
    return tuple(result)


def _measure(canvas: CanvasContext, text: str) -> Bounds:
    return CanvasText(
        text, Point(pt(0), pt(0)), typography=ChartLegendTextStyle
    ).measured_anchor_bounds(canvas)
