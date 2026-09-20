"""Layout contracts and layout assembly. All geometry is measured in points."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
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
class ProposedSize:
    """A parent's suggested size; ``None`` requests the child's ideal size."""

    width: Length | None = None
    height: Length | None = None

    def __post_init__(self) -> None:
        for value in (self.width, self.height):
            if value is not None:
                require_length(value)
                if value < pt(0):
                    raise ValueError("Proposed dimensions must be nonnegative")


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

    def measure(self, proposal: ProposedSize) -> LayoutPlan: ...


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
        proposal: ProposedSize,
        children: Sequence[LayoutChild],
        context: LayoutContext,
    ) -> LayoutPlan: ...


def checked(plan: LayoutPlan, identity: str | None) -> LayoutPlan:
    for value in (plan.width, plan.height):
        require_length(value)
    if not all(v >= pt(0) for v in (plan.width, plan.height)):
        raise ValueError(
            f"Invalid layout size at {identity}: {(plan.width, plan.height)}"
        )
    return plan


class _Child:
    def __init__(self, node: ExpandedView, context: LayoutContext) -> None:
        self.node = node
        self.context = context
        self.identity = node.identity
        self.view_identity = node.view_identity
        self.flex = node.metadata.flex
        self.children = tuple(_Child(child, context) for child in node.children)
        self._cache: dict[ProposedSize, LayoutPlan] = {}

    def measure(self, proposal: ProposedSize) -> LayoutPlan:
        if proposal not in self._cache:
            try:
                plan = self.node.layout.measure(proposal, self.children, self.context)
                plan = checked(plan, self.identity)
                for placement in plan.placements:
                    if not any(placement.child is child for child in self.children):
                        raise ValueError(
                            f"Layout at {self.identity} placed an unrelated child"
                        )
                self._cache[proposal] = plan
            except LayoutOverflow as error:
                if error.identity is not None:
                    raise
                raise LayoutOverflow(
                    self.identity, error.available, error.required
                ) from error
        return self._cache[proposal]

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

    def measure(self, node: ExpandedView, proposal: ProposedSize) -> Drawable:
        child = _Child(node, self.context)
        return child.place(child.measure(proposal))

    def layout_view(
        self, node: ExpandedView, width: Length = pt(960), height: Length = pt(540)
    ) -> Drawable:
        require_length(width)
        require_length(height)
        return DrawableGroup(
            "canvas",
            Bounds(pt(0), pt(0), width, height),
            DrawableMetadata(),
            (self.measure(node, ProposedSize(width, height)),),
        )
