"""Typed, resolved views ready for layout and drawable materialization."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, Literal

from .drawables import (
    Bounds,
    Drawable,
    DrawableGroup,
    DrawableImage,
    DrawableMetadata,
    DrawableRectangle,
    DrawableText,
)
from .fonts import Font, ResolvedFont
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

    identity: str
    modifiers: tuple[Modifier, ...]
    animation: str | None = field(metadata={"tracked": True})
    transition: str | None = field(metadata={"tracked": True})
    animation_boundary: bool = field(metadata={"tracked": True})


@dataclass(frozen=True)
class ExpandedView(ABC):
    """A resolved view occurrence with a concrete layout policy."""

    metadata: ExpandedMetadata
    layout: Layout

    @property
    def identity(self) -> str:
        return self.metadata.identity

    @property
    def modifiers(self) -> tuple[Modifier, ...]:
        return self.metadata.modifiers

    @property
    def animation(self) -> str | None:
        return self.metadata.animation

    @property
    def transition(self) -> str | None:
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

    def make_drawable(
        self,
        plan: LayoutPlan,
        bounds: Bounds,
        content_bounds: Bounds,
        metadata: DrawableMetadata,
        children: tuple[Drawable, ...],
    ) -> Drawable:
        return DrawableRectangle(
            self.identity, bounds, metadata, content_bounds, self.color
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
