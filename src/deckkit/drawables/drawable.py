from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from ..animation import Animation, Transition
from .bounds import Bounds


@dataclass(frozen=True)
class DrawableMetadata:
    animation: Animation | None = None
    transition: Transition | None = None
    animation_boundary: bool = False


@dataclass(frozen=True)
class Drawable:
    """Shared geometry and source identity; concrete subclasses define rendering."""

    identity: str
    bounds: Bounds
    metadata: DrawableMetadata

    @property
    def children(self) -> tuple[Drawable, ...]:
        return ()

    def walk(self) -> Iterator[Drawable]:
        yield self
        for child in self.children:
            yield from child.walk()
