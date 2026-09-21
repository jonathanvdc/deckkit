from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Union

from typing_extensions import TypeAlias

from ..drawables import Bounds
from ._geometry import validate_bounds
from .context import CanvasContext, CanvasSize
from .elements import CanvasElement, CanvasText


@dataclass(frozen=True)
class CanvasScene:
    elements: tuple[CanvasElement, ...]
    anchors: Mapping[str, Bounds]
    clip: Bounds | None

    def __init__(
        self,
        *elements: CanvasElement,
        anchors: Mapping[str, Bounds] | None = None,
        clip: Bounds | None = None,
    ) -> None:
        if not all(isinstance(element, CanvasElement) for element in elements):
            raise TypeError("CanvasScene elements must be CanvasElement values")
        if clip is not None:
            if not isinstance(clip, Bounds):
                raise TypeError("CanvasScene.clip must be Bounds")
            validate_bounds(clip)
        keys = [element.key for element in elements if element.key is not None]
        if len(keys) != len(set(keys)):
            raise ValueError("Canvas element keys must be unique within a scene")
        exported = dict(anchors or {})
        if any(not name for name in exported):
            raise ValueError("Canvas anchor names must not be empty")
        duplicates = set(keys) & set(exported)
        if duplicates:
            raise ValueError(
                "Canvas anchors conflict with element keys: "
                + ", ".join(sorted(duplicates))
            )
        exported.update(
            (element.key, element.anchor_bounds)
            for element in elements
            if element.key is not None
        )
        object.__setattr__(self, "elements", tuple(elements))
        object.__setattr__(self, "anchors", MappingProxyType(exported))
        object.__setattr__(self, "clip", clip)

    def measured_anchors(self, context: CanvasContext) -> Mapping[str, Bounds]:
        return MappingProxyType(
            {
                **self.anchors,
                **{
                    element.key: element.measured_anchor_bounds(context)
                    for element in self.elements
                    if isinstance(element, CanvasText) and element.key is not None
                },
            }
        )


CanvasRenderer: TypeAlias = Callable[
    [CanvasContext, CanvasSize], Union[CanvasScene, Iterable[CanvasElement]]
]


def scene_from(value: CanvasScene | Iterable[CanvasElement]) -> CanvasScene:
    return value if isinstance(value, CanvasScene) else CanvasScene(*tuple(value))
