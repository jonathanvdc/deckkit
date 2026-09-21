"""Typed, resolved views ready for layout and drawable materialization."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, Literal

from .animation import Animation, Transition
from .canvas import CanvasContext, CanvasRenderer, CanvasScene
from .canvas.clipping import clip_drawable
from .drawables import (
    Bounds,
    Drawable,
    DrawableConnector,
    DrawableGroup,
    DrawableImage,
    DrawableMetadata,
    DrawableRectangle,
    DrawableRichText,
    DrawableText,
)
from .geometry import Point
from .identity import KeyScope, ViewIdentity
from .layout import Layout, LayoutPlan
from .measurement import MeasuredRichText, MeasuredText, StyledTextLine, TextFlow
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
    animation: Animation | None = tracked_field()
    transition: Transition | None = tracked_field()
    animation_boundary: bool = tracked_field()
    flex: float = 0.0


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
class ExpandedCanvas(ExpandedPrimitive):
    renderer: CanvasRenderer = tracked_field()

    def make_drawable(
        self,
        plan: LayoutPlan,
        bounds: Bounds,
        content_bounds: Bounds,
        metadata: DrawableMetadata,
        children: tuple[Drawable, ...],
    ) -> Drawable:
        context = plan.properties.get("canvas_context")
        scene = plan.properties.get("canvas_scene")
        if not isinstance(context, CanvasContext) or not isinstance(scene, CanvasScene):
            raise TypeError("Canvas layout must provide a context and resolved scene")
        origin = Point(content_bounds.x, content_bounds.y)
        drawables = tuple(
            element.make_drawable(
                f"{self.identity}/key:{element.key}"
                if element.key is not None
                else f"{self.identity}/element:{index}",
                origin,
                context,
                metadata,
            )
            for index, element in enumerate(scene.elements)
        )
        if scene.clip is not None:
            clip = Bounds(
                origin.x + scene.clip.x,
                origin.y + scene.clip.y,
                scene.clip.width,
                scene.clip.height,
            )
            drawables = tuple(clip_drawable(drawable, clip) for drawable in drawables)
        return DrawableGroup(self.identity, bounds, metadata, drawables)


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
    flow: TextFlow = tracked_field()
    styled_lines: tuple[StyledTextLine, ...] = tracked_field()

    @property
    def text(self) -> str:
        return "\n".join(
            "".join(span.text for span in line.spans) for line in self.styled_lines
        )

    def make_drawable(
        self,
        plan: LayoutPlan,
        bounds: Bounds,
        content_bounds: Bounds,
        metadata: DrawableMetadata,
        children: tuple[Drawable, ...],
    ) -> Drawable:
        measured_text = plan.properties["measured_text"]
        if not isinstance(measured_text, MeasuredRichText):
            raise TypeError("Text layout must produce MeasuredRichText")
        runs = tuple(run for line in measured_text.lines for run in line.runs)
        first = runs[0]
        first_style = (
            first.font,
            first.requested_font,
            first.font_size,
            first.color,
        )
        if all(line.background is None for line in measured_text.lines) and all(
            run.background is None
            and (run.font, run.requested_font, run.font_size, run.color) == first_style
            for run in runs
        ):
            metrics = MeasuredText(
                tuple(
                    "".join(run.text for run in line.runs)
                    for line in measured_text.lines
                ),
                measured_text.width,
                measured_text.height,
                first.metrics.ascent,
                first.metrics.line_height,
                first.metrics.family,
                first.metrics.style,
            )
            return DrawableText(
                self.identity,
                bounds,
                metadata,
                content_bounds,
                self.text,
                first.color,
                first.font,
                first.requested_font,
                first.font_size,
                metrics,
            )

        drawables: list[Drawable] = []
        line_width = plan.properties["line_width"]
        if not isinstance(line_width, Length):
            raise TypeError("Text layout must produce a line width")
        y = content_bounds.y
        for line_index, line in enumerate(measured_text.lines):
            if line.background is not None:
                line_bounds = Bounds(
                    content_bounds.x,
                    y,
                    line_width,
                    line.height,
                )
                drawables.append(
                    DrawableRectangle(
                        f"{self.identity}/line:{line_index}:background",
                        line_bounds,
                        metadata,
                        line_bounds,
                        line.background,
                    )
                )
            for run_index, run in enumerate(line.runs):
                run_y = y + line.ascent - run.metrics.ascent
                run_bounds = Bounds(
                    content_bounds.x + run.x,
                    run_y,
                    run.width,
                    line.height,
                )
                if run.background is not None:
                    background_bounds = Bounds(
                        run_bounds.x,
                        y,
                        run_bounds.width,
                        line.height,
                    )
                    drawables.append(
                        DrawableRectangle(
                            f"{self.identity}/line:{line_index}/run:{run_index}:background",
                            background_bounds,
                            metadata,
                            background_bounds,
                            run.background,
                        )
                    )
                drawables.append(
                    DrawableText(
                        f"{self.identity}/line:{line_index}/run:{run_index}",
                        run_bounds,
                        metadata,
                        run_bounds,
                        run.text,
                        run.color,
                        run.font,
                        run.requested_font,
                        run.font_size,
                        run.metrics,
                    )
                )
            y += line.height
        return DrawableRichText(
            self.identity,
            bounds,
            metadata,
            content_bounds,
            measured_text,
            tuple(drawables),
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
