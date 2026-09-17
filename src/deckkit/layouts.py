"""Composable layout policies, independent of view types and rendering backends."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Any, Literal

from .fonts import ResolvedFont
from .layout import (
    Constraints,
    Layout,
    LayoutChild,
    LayoutOverflow,
    LayoutPlan,
    Placement,
    checked,
)
from .measurement import TextMeasurer
from .units import Length, pt, require_length


def content(
    width: Length,
    height: Length,
    placements: tuple[Placement, ...] = (),
    **properties: Any,
) -> LayoutPlan:
    return LayoutPlan(
        width, height, placements, dict(properties, content_size=(width, height))
    )


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

    def measure(self, c: Constraints, children: Sequence[LayoutChild]) -> LayoutPlan:
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
        w, h = (extent, other) if horizontal else (other, extent)
        return content(w, h, tuple(placements))


@dataclass(frozen=True)
class OverlayLayout:
    def measure(self, c: Constraints, children: Sequence[LayoutChild]) -> LayoutPlan:
        intrinsic = [
            child.measure(Constraints(c.max_width, c.max_height)) for child in children
        ]
        w = max([c.min_width] + [p.width for p in intrinsic])
        h = max([c.min_height] + [p.height for p in intrinsic])
        # A second proposal is necessary to expand flexible backgrounds. Identical
        # proposals hit the per-compilation child cache; placement never measures.
        allocation = Constraints(w, h, w, h)
        return content(
            w, h, tuple(Placement(ch, ch.measure(allocation)) for ch in children)
        )


@dataclass(frozen=True)
class PassthroughLayout:
    def measure(self, c: Constraints, children: Sequence[LayoutChild]) -> LayoutPlan:
        (child,) = children
        plan = child.measure(c)
        return content(plan.width, plan.height, (Placement(child, plan),))


@dataclass(frozen=True)
class PaddingLayout:
    inner: Layout
    amount: Length

    def __post_init__(self) -> None:
        require_length(self.amount)
        if self.amount < pt(0):
            raise ValueError("Padding must be finite and nonnegative")

    def measure(self, c: Constraints, children: Sequence[LayoutChild]) -> LayoutPlan:
        pad = self.amount
        if 2 * pad > min(c.max_width, c.max_height):
            raise LayoutOverflow(None, (c.max_width, c.max_height), (2 * pad, 2 * pad))
        proposal = Constraints(
            c.max_width - 2 * pad,
            c.max_height - 2 * pad,
            max(pt(0), c.min_width - 2 * pad),
            max(pt(0), c.min_height - 2 * pad),
        )
        plan = checked(self.inner.measure(proposal, children), proposal, None)
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
            if dimension is not None and (dimension < pt(0)):
                raise ValueError("Frame dimensions must be finite and nonnegative")

    def measure(self, c: Constraints, children: Sequence[LayoutChild]) -> LayoutPlan:
        w, h = self.width, self.height
        if (w is not None and w > c.max_width) or (h is not None and h > c.max_height):
            raise LayoutOverflow(None, (c.max_width, c.max_height), (w, h))
        proposal = Constraints(
            w if w is not None else c.max_width,
            h if h is not None else c.max_height,
            w if w is not None else c.min_width,
            h if h is not None else c.min_height,
        )
        return checked(self.inner.measure(proposal, children), proposal, None)


@dataclass(frozen=True)
class TextLayout:
    text: str
    font: ResolvedFont
    font_size: Length
    line_spacing: float
    measurer: TextMeasurer

    def measure(self, c: Constraints, children: Sequence[LayoutChild]) -> LayoutPlan:
        metrics = self.measurer.measure(
            self.text, self.font, self.font_size, c.max_width, self.line_spacing
        )
        return content(metrics.width, metrics.height, metrics=metrics)


@dataclass(frozen=True)
class ShapeLayout:
    def measure(self, c: Constraints, children: Sequence[LayoutChild]) -> LayoutPlan:
        return content(c.min_width, c.min_height)


@dataclass(frozen=True)
class ImageLayout:
    width: Length
    height: Length

    def measure(self, c: Constraints, children: Sequence[LayoutChild]) -> LayoutPlan:
        scale = min(c.max_width / self.width, c.max_height / self.height, 1)
        return content(
            max(c.min_width, self.width * scale), max(c.min_height, self.height * scale)
        )
