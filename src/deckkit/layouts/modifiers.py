from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ..layout import (
    LayoutChild,
    LayoutContext,
    LayoutOverflow,
    LayoutPlan,
    Placement,
    ProposedSize,
)
from ..units import Length, pt
from ..views.modifier_views import Edge, EdgeSet, FrameMaximum, FrameSpec, unbounded


def _subtract(value: Length | None, amount: Length) -> Length | None:
    return None if value is None else max(pt(0), value - amount)


@dataclass(frozen=True)
class PaddingLayout:
    amount: Length
    edges: EdgeSet

    def measure(
        self,
        proposal: ProposedSize,
        children: Sequence[LayoutChild],
        context: LayoutContext,
    ) -> LayoutPlan:
        (child,) = children
        left = self.amount if Edge.leading in self.edges.values else pt(0)
        right = self.amount if Edge.trailing in self.edges.values else pt(0)
        top = self.amount if Edge.top in self.edges.values else pt(0)
        bottom = self.amount if Edge.bottom in self.edges.values else pt(0)
        horizontal, vertical = left + right, top + bottom
        plan = child.measure(
            ProposedSize(
                _subtract(proposal.width, horizontal),
                _subtract(proposal.height, vertical),
            )
        )
        return LayoutPlan(
            plan.width + horizontal,
            plan.height + vertical,
            (Placement(child, plan, left, top),),
            {"content_offset": (left, top), "content_size": (plan.width, plan.height)},
        )


def _clamp(
    value: Length, minimum: Length | None, maximum: FrameMaximum | None
) -> Length:
    if minimum is not None:
        value = max(value, minimum)
    if isinstance(maximum, Length):
        value = min(value, maximum)
    return value


def _child_dimension(
    proposed: Length | None,
    exact: Length | None,
    minimum: Length | None,
    ideal: Length | None,
    maximum: FrameMaximum | None,
) -> Length | None:
    if exact is not None:
        return exact
    value = ideal if proposed is None and ideal is not None else proposed
    return None if value is None else _clamp(value, minimum, maximum)


def _frame_dimension(
    proposed: Length | None,
    child: Length,
    exact: Length | None,
    minimum: Length | None,
    ideal: Length | None,
    maximum: FrameMaximum | None,
) -> Length:
    if exact is not None:
        return exact
    if maximum is unbounded and proposed is not None:
        return max(proposed, minimum or pt(0))
    if proposed is None and ideal is not None:
        return _clamp(ideal, minimum, maximum)
    return _clamp(child, minimum, maximum)


@dataclass(frozen=True)
class FrameLayout:
    spec: FrameSpec

    def measure(
        self,
        proposal: ProposedSize,
        children: Sequence[LayoutChild],
        context: LayoutContext,
    ) -> LayoutPlan:
        (child,) = children
        s = self.spec
        child_proposal = ProposedSize(
            _child_dimension(
                proposal.width, s.width, s.min_width, s.ideal_width, s.max_width
            ),
            _child_dimension(
                proposal.height, s.height, s.min_height, s.ideal_height, s.max_height
            ),
        )
        plan = child.measure(child_proposal)
        width = _frame_dimension(
            proposal.width, plan.width, s.width, s.min_width, s.ideal_width, s.max_width
        )
        height = _frame_dimension(
            proposal.height,
            plan.height,
            s.height,
            s.min_height,
            s.ideal_height,
            s.max_height,
        )
        if plan.width > width + pt(1e-6) or plan.height > height + pt(1e-6):
            raise LayoutOverflow(None, (width, height), (plan.width, plan.height))
        x = (width - plan.width) * s.alignment.x
        y = (height - plan.height) * s.alignment.y
        return LayoutPlan(
            width,
            height,
            (Placement(child, plan, x, y),),
            {"content_offset": (x, y), "content_size": (plan.width, plan.height)},
        )
