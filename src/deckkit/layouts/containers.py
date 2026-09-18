from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from ..geometry import RelativePoint
from ..layout import (
    Constraints,
    LayoutChild,
    LayoutContext,
    LayoutOverflow,
    LayoutPlan,
    Placement,
)
from ..units import Length, pt, require_length
from ._content import content


@dataclass(frozen=True)
class StackLayout:
    axis: Literal["horizontal", "vertical"] = "horizontal"
    spacing: Length = pt(16)

    def __post_init__(self) -> None:
        if self.axis not in ("horizontal", "vertical"):
            raise ValueError("Stack axis must be horizontal or vertical")
        require_length(self.spacing)
        if self.spacing < pt(0):
            raise ValueError("Spacing must be finite and nonnegative")

    def measure(
        self, c: Constraints, children: Sequence[LayoutChild], context: LayoutContext
    ) -> LayoutPlan:
        horizontal = self.axis == "horizontal"

        def main(plan: LayoutPlan) -> Length:
            return plan.width if horizontal else plan.height

        def cross(plan: LayoutPlan) -> Length:
            return plan.height if horizontal else plan.width

        available = c.max_width if horizontal else c.max_height
        used = self.spacing * max(0, len(children) - 1)
        plans = {}
        total_weight = sum(child.flex for child in children)
        for i, child in enumerate(children):
            if not child.flex:
                plans[i] = child.measure(Constraints(c.max_width, c.max_height))
                used += main(plans[i])
        if used > available + pt(1e-6):
            raise LayoutOverflow(
                None,
                (c.max_width, c.max_height),
                (used, pt(0)) if horizontal else (pt(0), used),
            )
        for i, child in enumerate(children):
            if child.flex:
                share = max(pt(0), available - used) * child.flex / total_weight
                allocation = (
                    Constraints(share, c.max_height, share, pt(0))
                    if horizontal
                    else Constraints(c.max_width, share, pt(0), share)
                )
                plans[i] = child.measure(allocation)
        cursor = pt(0)
        placements = []
        for i, child in enumerate(children):
            placements.append(
                Placement(
                    child,
                    plans[i],
                    cursor if horizontal else pt(0),
                    pt(0) if horizontal else cursor,
                )
            )
            cursor += main(plans[i]) + self.spacing
        extent = max(pt(0), cursor - self.spacing)
        other = max((cross(p) for p in plans.values()), default=pt(0))
        width, height = (extent, other) if horizontal else (other, extent)
        return content(width, height, tuple(placements))


@dataclass(frozen=True)
class OverlayLayout:
    alignment: RelativePoint = RelativePoint.center

    def measure(
        self, c: Constraints, children: Sequence[LayoutChild], context: LayoutContext
    ) -> LayoutPlan:
        intrinsic = [
            child.measure(Constraints(c.max_width, c.max_height)) for child in children
        ]
        width = max([c.min_width] + [plan.width for plan in intrinsic])
        height = max([c.min_height] + [plan.height for plan in intrinsic])
        allocation = Constraints(width, height, width, height)
        placements = []
        for child, ideal in zip(children, intrinsic):
            proposed = child.measure(allocation)
            proposed_content = proposed.properties.get("content_size")
            plan = proposed if proposed_content == (width, height) else ideal
            placements.append(
                Placement(
                    child,
                    plan,
                    (width - plan.width) * self.alignment.x,
                    (height - plan.height) * self.alignment.y,
                )
            )
        return content(
            width,
            height,
            tuple(placements),
        )


@dataclass(frozen=True)
class PassthroughLayout:
    def measure(
        self, c: Constraints, children: Sequence[LayoutChild], context: LayoutContext
    ) -> LayoutPlan:
        (child,) = children
        plan = child.measure(c)
        return content(plan.width, plan.height, (Placement(child, plan),))
