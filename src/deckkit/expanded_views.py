"""Typed, resolved views ready for layout and drawable materialization."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, Literal

from .animation import Animation, Transition
from .drawables import (
    Bounds,
    Drawable,
    DrawableConnector,
    DrawableGroup,
    DrawableImage,
    DrawableMetadata,
    DrawableRectangle,
    DrawableText,
)
from .fonts import Font, ResolvedFont
from .geometry import Point
from .identity import KeyScope, ViewIdentity
from .layout import Layout, LayoutPlan
from .measurement import TextMetrics
from .units import Length
from .views.view import Modifier


def tracked_field() -> Any:
    """Declare a required dataclass field that participates in change tracking."""
    return field(metadata={"tracked": True})


@dataclass(frozen=True)
class ExpandedMetadata:
    """Compiler-owned identity and behavior shared by every expanded view."""

    view_identity: ViewIdentity
    key: str | None
    key_scope: KeyScope
    modifiers: tuple[Modifier, ...]
    animation: Animation | None = field(metadata={"tracked": True})
    transition: Transition | None = field(metadata={"tracked": True})
    animation_boundary: bool = field(metadata={"tracked": True})


@dataclass(frozen=True)
class ExpandedView(ABC):
    """A resolved view occurrence with a concrete layout policy."""

    metadata: ExpandedMetadata
    layout: Layout

    @property
    def identity(self) -> str:
        return str(self.metadata.view_identity)

    @property
    def view_identity(self) -> ViewIdentity:
        return self.metadata.view_identity

    @property
    def modifiers(self) -> tuple[Modifier, ...]:
        return self.metadata.modifiers

    @property
    def animation(self) -> Animation | None:
        return self.metadata.animation

    @property
    def transition(self) -> Transition | None:
        return self.metadata.transition

    @property
    def animation_boundary(self) -> bool:
        return self.metadata.animation_boundary

    @property
    def children(self) -> tuple[ExpandedView, ...]:
        return ()

    def walk(self) -> Iterator[ExpandedView]:
        yield self
        for child in self.children:
            yield from child.walk()

    @abstractmethod
    def make_drawable(
        self,
        plan: LayoutPlan,
        bounds: Bounds,
        content_bounds: Bounds,
        metadata: DrawableMetadata,
        children: tuple[Drawable, ...],
    ) -> Drawable:
        """Materialize this resolved node after layout has been measured."""
        raise NotImplementedError


@dataclass(frozen=True)
class ExpandedPrimitive(ExpandedView, ABC):
    """A resolved rendering leaf."""


@dataclass(frozen=True)
class ExpandedContainer(ExpandedView):
    _children: tuple[ExpandedView, ...]

    @property
    def children(self) -> tuple[ExpandedView, ...]:
        return self._children

    def make_drawable(
        self,
        plan: LayoutPlan,
        bounds: Bounds,
        content_bounds: Bounds,
        metadata: DrawableMetadata,
        children: tuple[Drawable, ...],
    ) -> Drawable:
        return DrawableGroup(self.identity, bounds, metadata, children)


@dataclass(frozen=True)
class ExpandedLayout(ExpandedContainer):
    spacing: Length | None = tracked_field()


@dataclass(frozen=True)
class ExpandedComponent(ExpandedContainer):
    component_type: str = tracked_field()
    semantic: tuple[tuple[str, Any], ...] = tracked_field()


@dataclass(frozen=True)
class ExpandedText(ExpandedPrimitive):
    text: str = tracked_field()
    requested_font: Font = tracked_field()
    font_size: Length = tracked_field()
    color: str = tracked_field()
    line_spacing: float = tracked_field()

    def make_drawable(
        self,
        plan: LayoutPlan,
        bounds: Bounds,
        content_bounds: Bounds,
        metadata: DrawableMetadata,
        children: tuple[Drawable, ...],
    ) -> Drawable:
        metrics = plan.properties["metrics"]
        if not isinstance(metrics, TextMetrics):
            raise TypeError("Text layout must produce TextMetrics")
        font = plan.properties["font"]
        if not isinstance(font, ResolvedFont):
            raise TypeError("Text layout must produce a ResolvedFont")
        return DrawableText(
            self.identity,
            bounds,
            metadata,
            content_bounds,
            self.text,
            self.color,
            font,
            self.requested_font,
            self.font_size,
            metrics,
        )


@dataclass(frozen=True)
class ExpandedRectangle(ExpandedPrimitive):
    color: str = tracked_field()
    corner_radius: Length = field(default=Length(0), metadata={"tracked": True})

    def make_drawable(
        self,
        plan: LayoutPlan,
        bounds: Bounds,
        content_bounds: Bounds,
        metadata: DrawableMetadata,
        children: tuple[Drawable, ...],
    ) -> Drawable:
        effective_radius = Length(
            min(
                self.corner_radius.points,
                content_bounds.width.points / 2,
                content_bounds.height.points / 2,
            )
        )
        return DrawableRectangle(
            self.identity,
            bounds,
            metadata,
            content_bounds,
            self.color,
            effective_radius,
        )


@dataclass(frozen=True)
class ExpandedImage(ExpandedPrimitive):
    data: bytes = tracked_field()
    mime: str = tracked_field()
    intrinsic_pixels: tuple[int, int] = tracked_field()
    fit: Literal["contain", "cover"] = tracked_field()

    def make_drawable(
        self,
        plan: LayoutPlan,
        bounds: Bounds,
        content_bounds: Bounds,
        metadata: DrawableMetadata,
        children: tuple[Drawable, ...],
    ) -> Drawable:
        return DrawableImage(
            self.identity,
            bounds,
            metadata,
            content_bounds,
            self.data,
            self.mime,
            self.intrinsic_pixels,
            self.fit,
        )


@dataclass(frozen=True)
class ExpandedConnector(ExpandedPrimitive):
    color: str = tracked_field()
    start_cap: Literal["none", "arrow"] = tracked_field()
    end_cap: Literal["none", "arrow"] = tracked_field()

    def make_drawable(
        self,
        plan: LayoutPlan,
        bounds: Bounds,
        content_bounds: Bounds,
        metadata: DrawableMetadata,
        children: tuple[Drawable, ...],
    ) -> Drawable:
        start = plan.properties.get("start")
        end = plan.properties.get("end")
        if not isinstance(start, Point) or not isinstance(end, Point):
            raise TypeError("Connector must be placed by an Annotated layout")
        return DrawableConnector(
            self.identity,
            bounds,
            metadata,
            Point(bounds.x + start.x, bounds.y + start.y),
            Point(bounds.x + end.x, bounds.y + end.y),
            self.color,
            self.start_cap,
            self.end_cap,
        )
