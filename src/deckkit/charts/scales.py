from __future__ import annotations

from collections.abc import Hashable, Iterable
from dataclasses import dataclass
from math import ceil, floor, isfinite, log10
from typing import Generic, TypeVar

from ..units import Length, pt, require_length

Category = TypeVar("Category", bound=Hashable)
Output = TypeVar("Output")


def _number(value: float) -> float:
    result = float(value)
    if not isfinite(result):
        raise ValueError("Scale values must be finite")
    return result


@dataclass(frozen=True)
class LinearScaleSpec:
    domain: tuple[float, float] | None = None
    include_zero: bool = False
    nice: bool = True
    tick_count: int = 5

    def __post_init__(self) -> None:
        if self.tick_count < 2:
            raise ValueError("Linear scale tick count must be at least two")

    def infer_domain(self, values: Iterable[float]) -> tuple[float, float]:
        inferred = tuple(_number(value) for value in values)
        if self.domain is not None:
            lower, upper = map(_number, self.domain)
        elif inferred:
            lower, upper = min(inferred), max(inferred)
        else:
            lower, upper = 0.0, 1.0
        if lower > upper:
            raise ValueError("Linear scale domain must be ordered")
        if self.include_zero:
            lower, upper = min(lower, 0.0), max(upper, 0.0)
        if lower == upper:
            padding = abs(lower) * 0.05 or 0.5
            lower, upper = lower - padding, upper + padding
        if self.nice and self.domain is None:
            return nice_domain((lower, upper), self.tick_count)
        return lower, upper

    def resolve(
        self,
        values: Iterable[float],
        output: tuple[Length, Length],
    ) -> LinearScale:
        return LinearScale(self.infer_domain(values), output)


@dataclass(frozen=True)
class LinearScale:
    domain: tuple[float, float]
    output: tuple[Length, Length]

    def __post_init__(self) -> None:
        require_length(self.output[0])
        require_length(self.output[1])

    def __call__(self, value: float) -> Length:
        lower, upper = self.domain
        amount = (_number(value) - lower) / (upper - lower)
        return self.output[0] + (self.output[1] - self.output[0]) * amount


@dataclass(frozen=True)
class BandScaleSpec(Generic[Category]):
    domain: tuple[Category, ...] | None = None
    padding_inner: float = 0.1
    padding_outer: float = 0.05

    def __post_init__(self) -> None:
        if not 0 <= self.padding_inner < 1:
            raise ValueError("Band scale inner padding must be between zero and one")
        if self.padding_outer < 0:
            raise ValueError("Band scale outer padding must be non-negative")

    def infer_domain(self, values: Iterable[Category]) -> tuple[Category, ...]:
        source = self.domain if self.domain is not None else tuple(values)
        return tuple(dict.fromkeys(source))

    def resolve(
        self, values: Iterable[Category], output: tuple[Length, Length]
    ) -> BandScale[Category]:
        return BandScale(
            self.infer_domain(values),
            output,
            self.padding_inner,
            self.padding_outer,
        )


@dataclass(frozen=True)
class BandScale(Generic[Category]):
    domain: tuple[Category, ...]
    output: tuple[Length, Length]
    padding_inner: float
    padding_outer: float

    @property
    def step(self) -> Length:
        return -self._signed_step if self._signed_step < pt(0) else self._signed_step

    @property
    def _signed_step(self) -> Length:
        if not self.domain:
            return pt(0)
        extent = self.output[1] - self.output[0]
        denominator = len(self.domain) - self.padding_inner + 2 * self.padding_outer
        return extent / denominator

    @property
    def bandwidth(self) -> Length:
        return self.step * (1 - self.padding_inner)

    def __call__(self, value: Category) -> Length:
        try:
            index = self.domain.index(value)
        except ValueError as error:
            raise KeyError(value) from error
        offset = self.padding_outer + index
        if self._signed_step < pt(0):
            offset += 1 - self.padding_inner
        return self.output[0] + self._signed_step * offset

    def center(self, value: Category) -> Length:
        return self(value) + self.bandwidth / 2


@dataclass(frozen=True)
class OrdinalScaleSpec(Generic[Category, Output]):
    output: tuple[Output, ...]
    domain: tuple[Category, ...] | None = None

    def __post_init__(self) -> None:
        if not self.output:
            raise ValueError("Ordinal scale requires at least one output")

    def resolve(self, values: Iterable[Category]) -> OrdinalScale[Category, Output]:
        source = self.domain if self.domain is not None else tuple(values)
        return OrdinalScale(tuple(dict.fromkeys(source)), self.output)


@dataclass(frozen=True)
class OrdinalScale(Generic[Category, Output]):
    domain: tuple[Category, ...]
    output: tuple[Output, ...]

    def __call__(self, value: Category) -> Output:
        try:
            index = self.domain.index(value)
        except ValueError as error:
            raise KeyError(value) from error
        return self.output[index % len(self.output)]


def nice_domain(
    domain: tuple[float, float], tick_count: int = 5
) -> tuple[float, float]:
    lower, upper = domain
    step = nice_step(upper - lower, tick_count)
    return (
        _clean_number(floor(lower / step + 1e-10) * step),
        _clean_number(ceil(upper / step - 1e-10) * step),
    )


def nice_ticks(domain: tuple[float, float], tick_count: int = 5) -> tuple[float, ...]:
    lower, upper = domain
    step = nice_step(upper - lower, tick_count)
    first = ceil(lower / step) * step
    last = floor(upper / step) * step
    count = max(0, round((last - first) / step) + 1)
    return tuple(_clean_number(first + index * step) for index in range(count))


def nice_step(span: float, tick_count: int) -> float:
    if not isfinite(span) or span <= 0:
        raise ValueError("Tick span must be positive and finite")
    if tick_count < 2:
        raise ValueError("Tick count must be at least two")
    rough = span / (tick_count - 1)
    magnitude = 10.0 ** floor(log10(rough))
    normalized = rough / magnitude
    if normalized >= 50**0.5:
        factor = 10.0
    elif normalized >= 10**0.5:
        factor = 5.0
    elif normalized >= 2**0.5:
        factor = 2.0
    else:
        factor = 1.0
    return factor * magnitude


def _clean_number(value: float) -> float:
    return 0.0 if abs(value) < 1e-12 else float(f"{value:.12g}")
