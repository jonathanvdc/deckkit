from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace

from ..layout import (
    Constraints,
    Layout,
    LayoutChild,
    LayoutContext,
    LayoutOverflow,
    LayoutPlan,
    checked,
)
from ..units import Length, pt, require_length


@dataclass(frozen=True)
class PaddingLayout:
    inner: Layout
    amount: Length

    def __post_init__(self) -> None:
        require_length(self.amount)
        if self.amount < pt(0):
            raise ValueError("Padding must be finite and nonnegative")

    def measure(
        self, c: Constraints, children: Sequence[LayoutChild], context: LayoutContext
    ) -> LayoutPlan:
        pad = self.amount
        if 2 * pad > min(c.max_width, c.max_height):
            raise LayoutOverflow(None, (c.max_width, c.max_height), (2 * pad, 2 * pad))
        proposal = Constraints(
            c.max_width - 2 * pad,
            c.max_height - 2 * pad,
            max(pt(0), c.min_width - 2 * pad),
            max(pt(0), c.min_height - 2 * pad),
        )
        plan = checked(self.inner.measure(proposal, children, context), proposal, None)
        dx, dy = plan.properties.get("content_offset", (pt(0), pt(0)))
        return LayoutPlan(
            plan.width + 2 * pad,
            plan.height + 2 * pad,
            tuple(replace(p, x=p.x + pad, y=p.y + pad) for p in plan.placements),
            dict(plan.properties, content_offset=(dx + pad, dy + pad)),
        )


@dataclass(frozen=True)
class FrameLayout:
    inner: Layout
    width: Length | None = None
    height: Length | None = None

    def __post_init__(self) -> None:
        for dimension in (self.width, self.height):
            if dimension is not None:
                require_length(dimension)
            if dimension is not None and dimension < pt(0):
                raise ValueError("Frame dimensions must be finite and nonnegative")

    def measure(
        self, c: Constraints, children: Sequence[LayoutChild], context: LayoutContext
    ) -> LayoutPlan:
        width, height = self.width, self.height
        if (width is not None and width > c.max_width) or (
            height is not None and height > c.max_height
        ):
            raise LayoutOverflow(None, (c.max_width, c.max_height), (width, height))
        proposal = Constraints(
            width if width is not None else c.max_width,
            height if height is not None else c.max_height,
            width if width is not None else c.min_width,
            height if height is not None else c.min_height,
        )
        return checked(self.inner.measure(proposal, children, context), proposal, None)
