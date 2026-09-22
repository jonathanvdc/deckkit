from __future__ import annotations

from collections.abc import Hashable
from dataclasses import dataclass
from typing import Union, cast

from ..canvas import CanvasContext, CanvasElement, CanvasScene, CanvasSize
from ..context import Context
from ..drawables import Bounds
from ..units import Length, pt, require_length
from ..views.canvas import Canvas
from ..views.composite_view import CompositeView
from ..views.view import View
from .content import ChartContent, DomainContribution, chart_content
from .context import ChartContext, ResolvedPositionScale
from .scales import BandScaleSpec, LinearScaleSpec

PositionScaleSpec = Union[LinearScaleSpec, BandScaleSpec[Hashable]]


@dataclass(frozen=True)
class ChartInsets:
    top: Length = pt(12)
    right: Length = pt(12)
    bottom: Length = pt(12)
    left: Length = pt(12)

    def __post_init__(self) -> None:
        for value in (self.top, self.right, self.bottom, self.left):
            require_length(value)
            if value < pt(0):
                raise ValueError("Chart insets must be non-negative")


@dataclass(frozen=True, init=False)
class Chart(CompositeView):
    content: ChartContent
    x_scale: PositionScaleSpec | None
    y_scale: PositionScaleSpec | None
    plot_insets: ChartInsets

    def __init__(
        self,
        *content: ChartContent,
        x_scale: PositionScaleSpec | None = None,
        y_scale: PositionScaleSpec | None = None,
        plot_insets: ChartInsets | None = None,
    ) -> None:
        if not content:
            raise ValueError("Chart requires at least one ChartContent value")
        resolved_insets = ChartInsets() if plot_insets is None else plot_insets
        if not isinstance(resolved_insets, ChartInsets):
            raise TypeError("Chart.plot_insets must be ChartInsets")
        object.__setattr__(self, "content", chart_content(content))
        object.__setattr__(self, "x_scale", x_scale)
        object.__setattr__(self, "y_scale", y_scale)
        object.__setattr__(self, "plot_insets", resolved_insets)

    def body(self, context: Context) -> View:
        return Canvas(self._render)

    def _render(self, canvas: CanvasContext, size: CanvasSize) -> CanvasScene:
        plot_bounds = _plot_bounds(size, self.plot_insets)
        contributions = tuple(self.content.domain_contributions())
        chart_context = ChartContext(
            canvas,
            plot_bounds,
            _resolve_scale("x", contributions, self.x_scale, plot_bounds),
            _resolve_scale("y", contributions, self.y_scale, plot_bounds),
        )
        elements = tuple(self.content.lower(chart_context))
        if not all(isinstance(element, CanvasElement) for element in elements):
            raise TypeError("Chart content must lower to CanvasElement values")
        return CanvasScene(*elements, clip=plot_bounds)


def _plot_bounds(size: CanvasSize, insets: ChartInsets) -> Bounds:
    return Bounds(
        insets.left,
        insets.top,
        max(pt(0), size.width - insets.left - insets.right),
        max(pt(0), size.height - insets.top - insets.bottom),
    )


def _resolve_scale(
    channel: str,
    contributions: tuple[DomainContribution, ...],
    specification: PositionScaleSpec | None,
    plot: Bounds,
) -> ResolvedPositionScale:
    selected = tuple(item for item in contributions if item.channel == channel)
    kinds = {item.kind for item in selected}
    if len(kinds) > 1:
        raise ValueError(
            f"Chart {channel}-axis mixes quantitative and categorical data"
        )
    kind = next(iter(kinds), "quantitative")
    if specification is not None:
        expected = (
            "quantitative"
            if isinstance(specification, LinearScaleSpec)
            else "categorical"
        )
        if selected and kind != expected:
            raise TypeError(f"Chart {channel}-scale does not match its data")
        scale_spec = specification
    elif kind == "categorical":
        scale_spec = BandScaleSpec[Hashable]()
    else:
        scale_spec = LinearScaleSpec(
            include_zero=any(item.include_zero for item in selected)
        )
    start = plot.x if channel == "x" else plot.y + plot.height
    end = plot.x + plot.width if channel == "x" else plot.y
    values = tuple(value for item in selected for value in item.values)
    if isinstance(scale_spec, LinearScaleSpec):
        numeric = tuple(float(cast(float, value)) for value in values)
        return scale_spec.resolve(numeric, (start, end))
    return scale_spec.resolve(values, (start, end))
