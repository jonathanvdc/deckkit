from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Hashable, Iterable, Sequence
from dataclasses import dataclass
from typing import Generic, Literal, TypeVar

from ..canvas import CanvasElement
from ..units import Length, pt, require_length
from .context import ChartContext

Datum = TypeVar("Datum")
ValueType = TypeVar("ValueType")
Channel = Literal["x", "y"]
DomainKind = Literal["quantitative", "categorical"]


@dataclass(frozen=True)
class Value(Generic[Datum, ValueType]):
    label: str
    accessor: Callable[[Datum], ValueType]

    def __post_init__(self) -> None:
        if not self.label:
            raise ValueError("Chart value labels must not be empty")
        if not callable(self.accessor):
            raise TypeError("Chart value accessors must be callable")

    def __call__(self, datum: Datum) -> ValueType:
        return self.accessor(datum)


def value(
    label: str, accessor: Callable[[Datum], ValueType]
) -> Value[Datum, ValueType]:
    return Value(label, accessor)


@dataclass(frozen=True)
class DomainContribution:
    channel: Channel
    kind: DomainKind
    values: tuple[float | Hashable, ...]
    include_zero: bool = False

    @classmethod
    def quantitative(
        cls,
        channel: Channel,
        values: Iterable[float],
        *,
        include_zero: bool = False,
    ) -> DomainContribution:
        return cls(channel, "quantitative", tuple(values), include_zero)

    @classmethod
    def categorical(
        cls, channel: Channel, values: Iterable[Hashable]
    ) -> DomainContribution:
        return cls(channel, "categorical", tuple(values))


@dataclass(frozen=True)
class ChartOverflow:
    top: Length = pt(0)
    right: Length = pt(0)
    bottom: Length = pt(0)
    left: Length = pt(0)

    def __post_init__(self) -> None:
        for value in (self.top, self.right, self.bottom, self.left):
            require_length(value)
            if value < pt(0):
                raise ValueError("Chart overflow must be non-negative")

    @classmethod
    def maximum(cls, values: Iterable[ChartOverflow]) -> ChartOverflow:
        items = tuple(values)
        if not items:
            return cls()
        return cls(
            max(item.top for item in items),
            max(item.right for item in items),
            max(item.bottom for item in items),
            max(item.left for item in items),
        )


class ChartContent(ABC):
    """Declarative chart content that contributes domains and lowers to Canvas."""

    @abstractmethod
    def domain_contributions(self) -> Iterable[DomainContribution]:
        raise NotImplementedError

    def overflow(self) -> ChartOverflow:
        return ChartOverflow()

    @abstractmethod
    def lower(self, context: ChartContext) -> Iterable[CanvasElement]:
        raise NotImplementedError


@dataclass(frozen=True, init=False)
class CompositeChartContent(ChartContent):
    children: tuple[ChartContent, ...]

    def __init__(self, *children: ChartContent) -> None:
        if not all(isinstance(child, ChartContent) for child in children):
            raise TypeError("Composite chart children must be ChartContent values")
        object.__setattr__(self, "children", tuple(children))

    def domain_contributions(self) -> Iterable[DomainContribution]:
        return (
            contribution
            for child in self.children
            for contribution in child.domain_contributions()
        )

    def lower(self, context: ChartContext) -> Iterable[CanvasElement]:
        return (element for child in self.children for element in child.lower(context))

    def overflow(self) -> ChartOverflow:
        return ChartOverflow.maximum(child.overflow() for child in self.children)


def chart_content(children: Sequence[ChartContent]) -> ChartContent:
    if len(children) == 1:
        return children[0]
    return CompositeChartContent(*children)
