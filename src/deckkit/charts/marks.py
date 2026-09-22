from __future__ import annotations

from collections.abc import Callable, Hashable, Iterable
from dataclasses import dataclass
from typing import Generic, Literal, TypeVar, Union, cast

from ..canvas import CanvasElement, Ellipse, Rect
from ..drawables import Bounds
from ..theme import AccentColor, ColorStyle
from ..units import Length, pt, require_length
from .content import ChartContent, DomainContribution, DomainKind, Value
from .context import ChartContext

Datum = TypeVar("Datum")
PositionValue = Union[float, Hashable]
StyleValue = Union[ColorStyle, Callable[[Datum], ColorStyle]]
RadiusValue = Union[Length, Callable[[Datum], Length]]


@dataclass(frozen=True)
class PointMark(ChartContent, Generic[Datum]):
    data: tuple[Datum, ...]
    x: Value[Datum, PositionValue]
    y: Value[Datum, PositionValue]
    fill: StyleValue[Datum] = AccentColor
    radius: RadiusValue[Datum] = pt(3)
    key: Callable[[Datum], str | int] | None = None
    series: str | None = None
    x_kind: DomainKind | None = None
    y_kind: DomainKind | None = None

    def __init__(
        self,
        data: Iterable[Datum],
        *,
        x: Value[Datum, PositionValue],
        y: Value[Datum, PositionValue],
        fill: StyleValue[Datum] = AccentColor,
        radius: RadiusValue[Datum] = pt(3),
        key: Callable[[Datum], str | int] | None = None,
        series: str | None = None,
        x_kind: DomainKind | None = None,
        y_kind: DomainKind | None = None,
    ) -> None:
        object.__setattr__(self, "data", tuple(data))
        object.__setattr__(self, "x", x)
        object.__setattr__(self, "y", y)
        object.__setattr__(self, "fill", fill)
        object.__setattr__(self, "radius", radius)
        object.__setattr__(self, "key", key)
        object.__setattr__(self, "series", series or y.label)
        object.__setattr__(self, "x_kind", x_kind)
        object.__setattr__(self, "y_kind", y_kind)
        if not callable(x) or not callable(y):
            raise TypeError("PointMark x and y values must be callable")
        if key is not None and not callable(key):
            raise TypeError("PointMark key must be callable")
        if not callable(radius):
            require_length(radius)
            if radius <= pt(0):
                raise ValueError("PointMark radius must be positive")

    def domain_contributions(self) -> tuple[DomainContribution, ...]:
        x_values = tuple(self.x(datum) for datum in self.data)
        y_values = tuple(self.y(datum) for datum in self.data)
        return (
            _contribution("x", x_values, self.x_kind),
            _contribution("y", y_values, self.y_kind),
        )

    def lower(self, context: ChartContext) -> Iterable[CanvasElement]:
        result: list[CanvasElement] = []
        for datum in self.data:
            radius = self.radius(datum) if callable(self.radius) else self.radius
            require_length(radius)
            if radius <= pt(0):
                raise ValueError("PointMark radius must be positive")
            fill = self.fill(datum) if callable(self.fill) else self.fill
            center_x = context.center("x", self.x(datum))
            center_y = context.center("y", self.y(datum))
            result.append(
                Ellipse(
                    Bounds(
                        center_x - radius,
                        center_y - radius,
                        radius * 2,
                        radius * 2,
                    ),
                    fill=fill,
                    key=_datum_key(self.series or self.y.label, self.key(datum))
                    if self.key
                    else None,
                )
            )
        return tuple(result)


@dataclass(frozen=True)
class BarMark(ChartContent, Generic[Datum]):
    data: tuple[Datum, ...]
    x: Value[Datum, PositionValue]
    y: Value[Datum, PositionValue]
    orientation: Literal["vertical", "horizontal"]
    baseline: float
    fill: StyleValue[Datum]
    key: Callable[[Datum], str | int] | None
    series: str

    def __init__(
        self,
        data: Iterable[Datum],
        *,
        x: Value[Datum, PositionValue],
        y: Value[Datum, PositionValue],
        orientation: Literal["vertical", "horizontal"] = "vertical",
        baseline: float = 0,
        fill: StyleValue[Datum] = AccentColor,
        key: Callable[[Datum], str | int] | None = None,
        series: str | None = None,
    ) -> None:
        if orientation not in ("vertical", "horizontal"):
            raise ValueError("BarMark orientation must be vertical or horizontal")
        object.__setattr__(self, "data", tuple(data))
        object.__setattr__(self, "x", x)
        object.__setattr__(self, "y", y)
        object.__setattr__(self, "orientation", orientation)
        object.__setattr__(self, "baseline", float(baseline))
        object.__setattr__(self, "fill", fill)
        object.__setattr__(self, "key", key)
        object.__setattr__(
            self,
            "series",
            series or (y.label if orientation == "vertical" else x.label),
        )
        if key is not None and not callable(key):
            raise TypeError("BarMark key must be callable")

    def domain_contributions(self) -> tuple[DomainContribution, ...]:
        x_values = tuple(self.x(datum) for datum in self.data)
        y_values = tuple(self.y(datum) for datum in self.data)
        if self.orientation == "vertical":
            return (
                _contribution("x", x_values, "categorical"),
                _quantitative_with_baseline("y", y_values, self.baseline),
            )
        return (
            _quantitative_with_baseline("x", x_values, self.baseline),
            _contribution("y", y_values, "categorical"),
        )

    def lower(self, context: ChartContext) -> Iterable[CanvasElement]:
        result: list[CanvasElement] = []
        for datum in self.data:
            fill = self.fill(datum) if callable(self.fill) else self.fill
            if self.orientation == "vertical":
                x = context.position("x", self.x(datum))
                width = context.bandwidth("x")
                value = context.position("y", self.y(datum))
                baseline = context.position("y", self.baseline)
                bounds = Bounds(
                    x, min(value, baseline), width, _distance(value, baseline)
                )
            else:
                y = context.position("y", self.y(datum))
                height = context.bandwidth("y")
                value = context.position("x", self.x(datum))
                baseline = context.position("x", self.baseline)
                bounds = Bounds(
                    min(value, baseline), y, _distance(value, baseline), height
                )
            result.append(
                Rect(
                    bounds,
                    fill=fill,
                    key=_datum_key(self.series, self.key(datum)) if self.key else None,
                )
            )
        return tuple(result)


def _contribution(
    channel: Literal["x", "y"],
    values: tuple[PositionValue, ...],
    kind: DomainKind | None,
) -> DomainContribution:
    resolved_kind = kind or (
        "quantitative"
        if all(isinstance(item, (int, float)) for item in values)
        else "categorical"
    )
    if resolved_kind == "quantitative":
        if not all(isinstance(item, (int, float)) for item in values):
            raise TypeError(f"PointMark {channel} values must be numeric")
        return DomainContribution.quantitative(
            channel, (float(cast(float, item)) for item in values)
        )
    return DomainContribution.categorical(channel, values)


def _datum_key(series: str, key: str | int) -> str:
    return f"series:{series}/datum:{key}"


def _quantitative_with_baseline(
    channel: Literal["x", "y"], values: tuple[PositionValue, ...], baseline: float
) -> DomainContribution:
    contribution = _contribution(channel, values, "quantitative")
    return DomainContribution.quantitative(
        channel,
        (*(float(cast(float, value)) for value in contribution.values), baseline),
        include_zero=baseline == 0,
    )


def _distance(first: Length, second: Length) -> Length:
    return first - second if first >= second else second - first
