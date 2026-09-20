"""Structural views produced by layout modifiers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import ClassVar, Union

from ..geometry import RelativePoint
from ..layout import Layout
from ..units import Length, pt, require_length
from .layout_view import LayoutView
from .view import View


class _Unbounded:
    def __repr__(self) -> str:
        return "unbounded"


unbounded = _Unbounded()
FrameMaximum = Union[Length, _Unbounded]


class Edge(Enum):
    top = "top"
    leading = "leading"
    bottom = "bottom"
    trailing = "trailing"


@dataclass(frozen=True)
class EdgeSet:
    values: frozenset[Edge]
    all: ClassVar[EdgeSet]
    horizontal: ClassVar[EdgeSet]
    vertical: ClassVar[EdgeSet]

    def __init__(self, *values: Edge) -> None:
        if not all(isinstance(value, Edge) for value in values):
            raise TypeError("EdgeSet values must be Edge values")
        object.__setattr__(self, "values", frozenset(values))


EdgeSet.all = EdgeSet(*Edge)
EdgeSet.horizontal = EdgeSet(Edge.leading, Edge.trailing)
EdgeSet.vertical = EdgeSet(Edge.top, Edge.bottom)


@dataclass(frozen=True)
class FrameSpec:
    width: Length | None = None
    height: Length | None = None
    min_width: Length | None = None
    ideal_width: Length | None = None
    max_width: FrameMaximum | None = None
    min_height: Length | None = None
    ideal_height: Length | None = None
    max_height: FrameMaximum | None = None
    alignment: RelativePoint = RelativePoint.center

    def __post_init__(self) -> None:
        if not isinstance(self.alignment, RelativePoint):
            raise TypeError("Frame alignment must be a RelativePoint")
        self._validate_axis(
            "width", self.width, self.min_width, self.ideal_width, self.max_width
        )
        self._validate_axis(
            "height", self.height, self.min_height, self.ideal_height, self.max_height
        )
        if all(
            value is None
            for value in (
                self.width,
                self.height,
                self.min_width,
                self.ideal_width,
                self.max_width,
                self.min_height,
                self.ideal_height,
                self.max_height,
            )
        ):
            raise ValueError("frame() requires at least one dimension")

    @staticmethod
    def _validate_axis(
        name: str,
        exact: Length | None,
        minimum: Length | None,
        ideal: Length | None,
        maximum: FrameMaximum | None,
    ) -> None:
        if exact is not None and any(v is not None for v in (minimum, ideal, maximum)):
            raise ValueError(f"Exact {name} cannot be combined with flexible {name}")
        for value in (exact, minimum, ideal):
            if value is not None:
                require_length(value)
                if value < pt(0):
                    raise ValueError("Frame dimensions must be nonnegative")
        if maximum is not None and not isinstance(maximum, _Unbounded):
            require_length(maximum)
            if maximum < pt(0):
                raise ValueError("Frame dimensions must be nonnegative")
        if minimum is not None and isinstance(maximum, Length) and minimum > maximum:
            raise ValueError(f"Minimum {name} exceeds maximum {name}")
        if ideal is not None and (
            (minimum is not None and ideal < minimum)
            or (isinstance(maximum, Length) and ideal > maximum)
        ):
            raise ValueError(f"Ideal {name} is outside the frame range")


@dataclass(frozen=True, init=False)
class Frame(LayoutView):
    spec: FrameSpec

    def __init__(self, content: View, spec: FrameSpec) -> None:
        object.__setattr__(self, "spec", spec)
        super().__init__(content)

    @property
    def _layout_flex(self) -> float:
        own = super()._layout_flex
        if own:
            return own
        child = self.children[0]
        return 0.0 if child is None else child._layout_flex

    def resolve_layout(self, lookup: object) -> Layout:
        from ..layouts import FrameLayout

        return FrameLayout(self.spec)


@dataclass(frozen=True, init=False)
class Padding(LayoutView):
    amount: Length
    edges: EdgeSet

    def __init__(self, content: View, amount: Length, edges: EdgeSet) -> None:
        require_length(amount)
        if amount < pt(0):
            raise ValueError("Padding must be nonnegative")
        if not isinstance(edges, EdgeSet):
            raise TypeError("padding edges must be an EdgeSet")
        object.__setattr__(self, "amount", amount)
        object.__setattr__(self, "edges", edges)
        super().__init__(content)

    @property
    def _layout_flex(self) -> float:
        own = super()._layout_flex
        if own:
            return own
        child = self.children[0]
        return 0.0 if child is None else child._layout_flex

    def resolve_layout(self, lookup: object) -> Layout:
        from ..layouts import PaddingLayout

        return PaddingLayout(self.amount, self.edges)
