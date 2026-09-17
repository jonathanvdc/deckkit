from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

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


class ResolvedAnnotation(ABC):
    @property
    @abstractmethod
    def dependencies(self) -> tuple[ViewIdentity, ...]:
        raise NotImplementedError

    @abstractmethod
    def place(
        self,
        child: LayoutChild,
        bounds: Mapping[ViewIdentity, Bounds],
        container: Bounds,
    ) -> Placement:
        raise NotImplementedError


@dataclass(frozen=True)
class ResolvedConnector(ResolvedAnnotation):
    start: ResolvedAnchor
    end: ResolvedAnchor

    @property
    def dependencies(self) -> tuple[ViewIdentity, ...]:
        return self.start.target, self.end.target

    def place(
        self,
        child: LayoutChild,
        bounds: Mapping[ViewIdentity, Bounds],
        container: Bounds,
    ) -> Placement:
        start = _point(self.start, bounds)
        end = _point(self.end, bounds)
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
        return Placement(child, plan, x, y)


@dataclass(frozen=True)
class ResolvedLabel(ResolvedAnnotation):
    anchor: ResolvedAnchor
    alignment: RelativePoint

    @property
    def dependencies(self) -> tuple[ViewIdentity, ...]:
        return (self.anchor.target,)

    def place(
        self,
        child: LayoutChild,
        bounds: Mapping[ViewIdentity, Bounds],
        container: Bounds,
    ) -> Placement:
        target = _point(self.anchor, bounds)
        plan = child.measure(Constraints(container.width, container.height))
        x = target.x - plan.width * self.alignment.x
        y = target.y - plan.height * self.alignment.y
        return Placement(child, plan, x, y)


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
        container = Bounds(pt(0), pt(0), main.width, main.height)
        pending = list(enumerate(zip(self.annotations, annotation_children)))
        annotation_placements: dict[int, Placement] = {}
        while pending:
            deferred: list[tuple[int, tuple[ResolvedAnnotation, LayoutChild]]] = []
            for index, (annotation, child) in pending:
                if any(target not in bounds for target in annotation.dependencies):
                    deferred.append((index, (annotation, child)))
                    continue
                placement = annotation.place(child, bounds, container)
                plan, x, y = placement.plan, placement.x, placement.y
                required = (x + plan.width, y + plan.height)
                if (
                    x < pt(0)
                    or y < pt(0)
                    or required[0] > main.width
                    or required[1] > main.height
                ):
                    raise LayoutOverflow(None, (main.width, main.height), required)
                annotation_placements[index] = placement
                _collect_bounds(child, plan, x, y, bounds)
            if len(deferred) == len(pending):
                unresolved = sorted(
                    {
                        str(anchor)
                        for _, (annotation, _) in deferred
                        for anchor in annotation.dependencies
                        if anchor not in bounds
                    }
                )
                raise ValueError(
                    "Annotation dependencies could not be resolved; "
                    "there may be a cycle involving: " + ", ".join(unresolved)
                )
            pending = deferred
        placements = [Placement(content_child, main)]
        placements.extend(
            annotation_placements[index] for index in range(len(self.annotations))
        )
        return content(main.width, main.height, tuple(placements))


@dataclass(frozen=True)
class ConnectorLayout:
    def measure(
        self, c: Constraints, children: Sequence[LayoutChild], context: LayoutContext
    ) -> LayoutPlan:
        return content(c.min_width, c.min_height)
