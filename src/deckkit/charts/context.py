from __future__ import annotations

from collections.abc import Hashable
from dataclasses import dataclass
from typing import Literal, Union

from ..canvas import CanvasContext
from ..drawables import Bounds
from ..theme import ColorStyle
from ..units import Length, pt
from .scales import BandScale, LinearScale, OrdinalScale

ResolvedPositionScale = Union[LinearScale, BandScale[Hashable]]


@dataclass(frozen=True)
class ChartContext:
    canvas: CanvasContext
    plot_bounds: Bounds
    x_scale: ResolvedPositionScale
    y_scale: ResolvedPositionScale
    color_scale: OrdinalScale[Hashable, ColorStyle] | None = None

    def position(self, channel: Literal["x", "y"], value: float | Hashable) -> Length:
        scale = self.x_scale if channel == "x" else self.y_scale
        if isinstance(scale, LinearScale):
            if not isinstance(value, (int, float)):
                raise TypeError("Quantitative chart scales require numeric values")
            return scale(float(value))
        return scale(value)

    def center(self, channel: Literal["x", "y"], value: float | Hashable) -> Length:
        scale = self.x_scale if channel == "x" else self.y_scale
        if isinstance(scale, BandScale):
            return scale.center(value)
        return self.position(channel, value)

    def bandwidth(self, channel: Literal["x", "y"]) -> Length:
        scale = self.x_scale if channel == "x" else self.y_scale
        return scale.bandwidth if isinstance(scale, BandScale) else pt(0)

    def color(self, value: Hashable) -> ColorStyle:
        if self.color_scale is None:
            raise ValueError("Chart has no resolved color scale")
        return self.color_scale(value)
