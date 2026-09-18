"""Layout contracts and layout assembly. All geometry is measured in points."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Protocol, cast

from .fonts import FontResolver
from .identity import ViewIdentity
from .measurement import TextMeasurer
from .units import Length, pt, require_length

if TYPE_CHECKING:
    from .expanded_views import ExpandedView

from .drawables import (
    Bounds,
    Drawable,
    DrawableGroup,
    DrawableMetadata,
)


@dataclass(frozen=True)
class Constraints:
    max_width: Length
    max_height: Length
    min_width: Length = pt(0)
    min_height: Length = pt(0)

    def __post_init__(self) -> None:
        for value in (self.max_width, self.max_height, self.min_width, self.min_height):
            require_length(value)
        if not (
            pt(0) <= self.min_width <= self.max_width
            and pt(0) <= self.min_height <= self.max_height
        ):
            raise ValueError("Constraints must be nonnegative and ordered")


@dataclass(frozen=True)
class LayoutContext:
    """Services available while views respond to layout proposals."""

    measurer: TextMeasurer
    font_resolver: FontResolver


class LayoutOverflow(ValueError):
    def __init__(
        self,
        identity: str | None,
        available: tuple[Length, Length],
        required: tuple[Length | None, Length | None],
    ) -> None:
        self.identity, self.available, self.required = identity, available, required
        super().__init__(
            f"LayoutOverflow at {identity}: available {available}, required {required}. "
            "Shorten content, increase its frame, or allocate flexible space."
        )


class LayoutChild(Protocol):
    """A layout's opaque child: identity, allocation weight and cached measurement."""

    identity: str
    view_identity: ViewIdentity
    flex: float

    def measure(self, constraints: Constraints) -> LayoutPlan: ...


@dataclass(frozen=True)
class Placement:
    child: LayoutChild
    plan: LayoutPlan
    x: Length = pt(0)
    y: Length = pt(0)

    def __post_init__(self) -> None:
        require_length(self.x)
        require_length(self.y)


@dataclass(frozen=True)
class LayoutPlan:
    width: Length
    height: Length
    placements: tuple[Placement, ...] = ()
    properties: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require_length(self.width)
        require_length(self.height)
        object.__setattr__(self, "properties", MappingProxyType(dict(self.properties)))


class Layout(Protocol):
    """Policies measure children and return placements; they never create layout nodes."""

    def measure(
        self,
        constraints: Constraints,
        children: Sequence[LayoutChild],
        context: LayoutContext,
    ) -> LayoutPlan: ...


def checked(plan: LayoutPlan, c: Constraints, identity: str | None) -> LayoutPlan:
    for value in (plan.width, plan.height):
        require_length(value)
    if not all(v >= pt(0) for v in (plan.width, plan.height)):
        raise ValueError(
            f"Invalid layout size at {identity}: {(plan.width, plan.height)}"
        )
    if plan.width > c.max_width + pt(1e-6) or plan.height > c.max_height + pt(1e-6):
        raise LayoutOverflow(
            identity, (c.max_width, c.max_height), (plan.width, plan.height)
        )
    width, height = max(plan.width, c.min_width), max(plan.height, c.min_height)
    dx, dy = (width - plan.width) / 2, (height - plan.height) / 2
    content_x, content_y = plan.properties.get("content_offset", (pt(0), pt(0)))
    return replace(
        plan,
        width=width,
        height=height,
        placements=tuple(
            replace(placement, x=placement.x + dx, y=placement.y + dy)
            for placement in plan.placements
        ),
        properties=dict(
            plan.properties,
            content_offset=(content_x + dx, content_y + dy),
        ),
    )


class _Child:
    def __init__(self, node: ExpandedView, context: LayoutContext) -> None:
        self.node = node
        self.context = context
        self.identity = node.identity
        self.view_identity = node.view_identity
        self.flex = next(
            (
                modifier[1]
                for modifier in reversed(node.modifiers)
                if modifier[0] == "flex"
            ),
            0.0,
        )
        self.children = tuple(_Child(child, context) for child in node.children)
        self._cache: dict[Constraints, LayoutPlan] = {}

    def measure(self, constraints: Constraints) -> LayoutPlan:
        if constraints not in self._cache:
            try:
                plan = self.node.layout.measure(
                    constraints, self.children, self.context
                )
                plan = checked(plan, constraints, self.identity)
                for placement in plan.placements:
                    if not any(placement.child is child for child in self.children):
                        raise ValueError(
                            f"Layout at {self.identity} placed an unrelated child"
                        )
                    if not all(v >= pt(0) for v in (placement.x, placement.y)):
                        raise ValueError(f"Invalid child placement at {self.identity}")
                    required = (
                        placement.x + placement.plan.width,
                        placement.y + placement.plan.height,
                    )
                    if required[0] > plan.width + pt(1e-6) or required[
                        1
                    ] > plan.height + pt(1e-6):
                        raise LayoutOverflow(
                            self.identity, (plan.width, plan.height), required
                        )
                self._cache[constraints] = plan
            except LayoutOverflow as error:
                if error.identity is not None:
                    raise
                raise LayoutOverflow(
                    self.identity, error.available, error.required
                ) from error
        return self._cache[constraints]

    def place(self, plan: LayoutPlan, x: Length = pt(0), y: Length = pt(0)) -> Drawable:
        bounds = Bounds(x, y, plan.width, plan.height)
        metadata = DrawableMetadata(
            self.node.animation,
            self.node.transition,
            self.node.animation_boundary,
        )
        dx, dy = plan.properties.get("content_offset", (pt(0), pt(0)))
        w, h = plan.properties.get("content_size", (plan.width, plan.height))
        content_bounds = Bounds(x + dx, y + dy, w, h)
        children = tuple(
            cast(_Child, placement.child).place(
                placement.plan, x + placement.x, y + placement.y
            )
            for placement in plan.placements
        )
        return self.node.make_drawable(
            plan,
            bounds,
            content_bounds,
            metadata,
            children,
        )


class LayoutEngine:
    """Coordinate measurement, validate plans, then materialize the layout once."""

    def __init__(self, context: LayoutContext) -> None:
        self.context = context

    def measure(self, node: ExpandedView, constraints: Constraints) -> Drawable:
        child = _Child(node, self.context)
        return child.place(child.measure(constraints))

    def layout_view(
        self, node: ExpandedView, width: Length = pt(960), height: Length = pt(540)
    ) -> Drawable:
        require_length(width)
        require_length(height)
        return DrawableGroup(
            "canvas",
            Bounds(pt(0), pt(0), width, height),
            DrawableMetadata(),
            (self.measure(node, Constraints(width, height)),),
        )
