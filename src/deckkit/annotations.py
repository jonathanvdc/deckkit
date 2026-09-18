"""Anchor-relative overlays resolved after their content has been measured."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Literal

from .context import Context, ForegroundStyleKey
from .expanded_views import ExpandedConnector, ExpandedMetadata
from .geometry import RelativePoint
from .identity import ViewIdentity
from .layouts import AnnotatedLayout, ConnectorLayout
from .layouts.annotations import (
    ResolvedAnchor,
    ResolvedAnnotation,
    ResolvedConnector,
    ResolvedLabel,
)
from .units import Length, pt, require_length
from .views.layout_view import LayoutView
from .views.primitive_view import PrimitiveView
from .views.view import View


@dataclass(frozen=True)
class Anchor:
    target: str
    position: RelativePoint = RelativePoint.center
    offset_x: Length = pt(0)
    offset_y: Length = pt(0)

    def __post_init__(self) -> None:
        if not self.target:
            raise ValueError("Anchor target must not be empty")
        require_length(self.offset_x)
        require_length(self.offset_y)

    def resolve(self, lookup: Callable[[str], ViewIdentity]) -> ResolvedAnchor:
        return ResolvedAnchor(
            lookup(self.target),
            self.position,
            self.offset_x,
            self.offset_y,
        )


class Annotation(ABC):
    @property
    @abstractmethod
    def view(self) -> View:
        raise NotImplementedError

    @abstractmethod
    def resolve(self, lookup: Callable[[str], ViewIdentity]) -> ResolvedAnnotation:
        raise NotImplementedError


@dataclass(frozen=True)
class _Connector(PrimitiveView):
    start_cap: Literal["none", "arrow"]
    end_cap: Literal["none", "arrow"]

    def expand(self, context: Context, metadata: ExpandedMetadata) -> ExpandedConnector:
        return ExpandedConnector(
            metadata,
            ConnectorLayout(),
            context.environment.theme.color(
                context.environment.get(ForegroundStyleKey)
            ),
            self.start_cap,
            self.end_cap,
        )


@dataclass(frozen=True)
class Connector(Annotation):
    start: Anchor
    end: Anchor
    start_cap: Literal["none", "arrow"] = "none"
    end_cap: Literal["none", "arrow"] = "arrow"
    style: str = "primary"

    @property
    def view(self) -> View:
        return _Connector(self.start_cap, self.end_cap).foreground_style(self.style)

    def resolve(self, lookup: Callable[[str], ViewIdentity]) -> ResolvedConnector:
        return ResolvedConnector(self.start.resolve(lookup), self.end.resolve(lookup))


@dataclass(frozen=True)
class Label(Annotation):
    anchor: Anchor
    content: View
    alignment: RelativePoint = RelativePoint.center

    def __post_init__(self) -> None:
        if not isinstance(self.content, View):
            raise TypeError("Label.content must be a View")

    @property
    def view(self) -> View:
        return self.content

    def resolve(self, lookup: Callable[[str], ViewIdentity]) -> ResolvedLabel:
        return ResolvedLabel(self.anchor.resolve(lookup), self.alignment)


@dataclass(frozen=True, init=False)
class Annotated(LayoutView):
    annotations: tuple[Annotation, ...]

    def __init__(self, content: View, *annotations: Annotation) -> None:
        if not isinstance(content, View):
            raise TypeError("Annotated.content must be a View")
        if not all(isinstance(annotation, Annotation) for annotation in annotations):
            raise TypeError("Annotated annotations must inherit Annotation")
        object.__setattr__(self, "annotations", tuple(annotations))
        super().__init__(
            content,
            *(annotation.view for annotation in annotations),
        )

    def resolve_layout(self, lookup: Callable[[str], ViewIdentity]) -> AnnotatedLayout:
        return AnnotatedLayout(tuple(a.resolve(lookup) for a in self.annotations))
