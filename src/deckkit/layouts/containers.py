from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from ..geometry import RelativePoint
from ..layout import (
    LayoutChild,
    LayoutContext,
    LayoutOverflow,
    LayoutPlan,
    Placement,
    ProposedSize,
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
            raise ValueError("Spacing must be nonnegative")

    def measure(
        self,
        proposal: ProposedSize,
        children: Sequence[LayoutChild],
        context: LayoutContext,
    ) -> LayoutPlan:
        horizontal = self.axis == "horizontal"
        available = proposal.width if horizontal else proposal.height
        cross_proposal = proposal.height if horizontal else proposal.width

        def main(plan: LayoutPlan) -> Length:
            return plan.width if horizontal else plan.height

        def cross(plan: LayoutPlan) -> Length:
            return plan.height if horizontal else plan.width

        plans: dict[int, LayoutPlan] = {}
        used = self.spacing * max(0, len(children) - 1)
        for i, child in enumerate(children):
            if not child.flex:
                request = (
                    ProposedSize(None, cross_proposal)
                    if horizontal
                    else ProposedSize(cross_proposal, None)
                )
                plans[i] = child.measure(request)
                used += main(plans[i])
        flexible = [child for child in children if child.flex]
        if flexible:
            if available is None:
                for i, child in enumerate(children):
                    if child.flex:
                        request = (
                            ProposedSize(None, cross_proposal)
                            if horizontal
                            else ProposedSize(cross_proposal, None)
                        )
                        plans[i] = child.measure(request)
            else:
                if used > available + pt(1e-6):
                    required = (used, pt(0)) if horizontal else (pt(0), used)
                    raise LayoutOverflow(
                        None,
                        (proposal.width or pt(0), proposal.height or pt(0)),
                        required,
                    )
                total = sum(child.flex for child in flexible)
                for i, child in enumerate(children):
                    if child.flex:
                        share = (available - used) * child.flex / total
                        request = (
                            ProposedSize(share, cross_proposal)
                            if horizontal
                            else ProposedSize(cross_proposal, share)
                        )
                        plans[i] = child.measure(request)
        cursor = pt(0)
        placements = []
        for i, child in enumerate(children):
            plan = plans[i]
            placements.append(
                Placement(
                    child,
                    plan,
                    cursor if horizontal else pt(0),
                    pt(0) if horizontal else cursor,
                )
            )
            cursor += main(plan) + self.spacing
        extent = max(pt(0), cursor - self.spacing)
        other = max((cross(plan) for plan in plans.values()), default=pt(0))
        width, height = (extent, other) if horizontal else (other, extent)
        return content(width, height, tuple(placements))


@dataclass(frozen=True)
class OverlayLayout:
    alignment: RelativePoint = RelativePoint.center

    def measure(
        self,
        proposal: ProposedSize,
        children: Sequence[LayoutChild],
        context: LayoutContext,
    ) -> LayoutPlan:
        initial = [child.measure(proposal) for child in children]
        width = max((plan.width for plan in initial), default=pt(0))
        height = max((plan.height for plan in initial), default=pt(0))
        plans = [child.measure(ProposedSize(width, height)) for child in children]
        width = max([width] + [plan.width for plan in plans])
        height = max([height] + [plan.height for plan in plans])
        placements = tuple(
            Placement(
                child,
                plan,
                (width - plan.width) * self.alignment.x,
                (height - plan.height) * self.alignment.y,
            )
            for child, plan in zip(children, plans)
        )
        return content(width, height, placements)


@dataclass(frozen=True)
class PassthroughLayout:
    def measure(
        self,
        proposal: ProposedSize,
        children: Sequence[LayoutChild],
        context: LayoutContext,
    ) -> LayoutPlan:
        (child,) = children
        plan = child.measure(proposal)
        return content(plan.width, plan.height, (Placement(child, plan),))
