from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Union

from ..drawables import Bounds
from ..geometry import Point, RelativePoint
from ..identity import ViewIdentity
from ..layout import (
    Constraints,
    LayoutChild,
    LayoutContext,
    LayoutOverflow,
    LayoutPlan,
    Placement,
)
from ..units import Length, pt
from ._content import content


@dataclass(frozen=True)
class ResolvedAnchor:
    target: ViewIdentity
    position: RelativePoint
    offset_x: Length
    offset_y: Length


@dataclass(frozen=True)
class ResolvedConnector:
    start: ResolvedAnchor
    end: ResolvedAnchor


@dataclass(frozen=True)
class ResolvedLabel:
    anchor: ResolvedAnchor
    alignment: RelativePoint


ResolvedAnnotation = Union[ResolvedConnector, ResolvedLabel]


def _collect_bounds(
    child: LayoutChild,
    plan: LayoutPlan,
    x: Length,
    y: Length,
    result: dict[ViewIdentity, Bounds],
) -> None:
    result[child.view_identity] = Bounds(x, y, plan.width, plan.height)
    for placement in plan.placements:
        _collect_bounds(
            placement.child,
            placement.plan,
            x + placement.x,
            y + placement.y,
            result,
        )


def _point(anchor: ResolvedAnchor, bounds: Mapping[ViewIdentity, Bounds]) -> Point:
    try:
        target = bounds[anchor.target]
    except KeyError:
        raise ValueError(
            f"Anchor target is outside this Annotated: {anchor.target}"
        ) from None
    return Point(
        target.x + target.width * anchor.position.x + anchor.offset_x,
        target.y + target.height * anchor.position.y + anchor.offset_y,
    )


@dataclass(frozen=True)
class AnnotatedLayout:
    annotations: tuple[ResolvedAnnotation, ...]

    def measure(
        self, c: Constraints, children: Sequence[LayoutChild], context: LayoutContext
    ) -> LayoutPlan:
        content_child, *annotation_children = children
        if len(annotation_children) != len(self.annotations):
            raise ValueError("Annotated child and annotation counts differ")
        main = content_child.measure(c)
        bounds: dict[ViewIdentity, Bounds] = {}
        _collect_bounds(content_child, main, pt(0), pt(0), bounds)
        placements = [Placement(content_child, main)]
        for annotation, child in zip(self.annotations, annotation_children):
            if isinstance(annotation, ResolvedConnector):
                start = _point(annotation.start, bounds)
                end = _point(annotation.end, bounds)
                x, y = min(start.x, end.x), min(start.y, end.y)
                width = max(start.x, end.x) - x
                height = max(start.y, end.y) - y
                plan = child.measure(Constraints(width, height, width, height))
                plan = replace(
                    plan,
                    properties=dict(
                        plan.properties,
                        start=Point(start.x - x, start.y - y),
                        end=Point(end.x - x, end.y - y),
                    ),
                )
            else:
                target = _point(annotation.anchor, bounds)
                plan = child.measure(Constraints(main.width, main.height))
                x = target.x - plan.width * annotation.alignment.x
                y = target.y - plan.height * annotation.alignment.y
            required = (x + plan.width, y + plan.height)
            if (
                x < pt(0)
                or y < pt(0)
                or required[0] > main.width
                or required[1] > main.height
            ):
                raise LayoutOverflow(None, (main.width, main.height), required)
            placements.append(Placement(child, plan, x, y))
        return content(main.width, main.height, tuple(placements))


@dataclass(frozen=True)
class ConnectorLayout:
    def measure(
        self, c: Constraints, children: Sequence[LayoutChild], context: LayoutContext
    ) -> LayoutPlan:
        return content(c.min_width, c.min_height)
