from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..drawables import Bounds
from ..layout import LayoutPlan, Placement
from ..units import Length


def content(
    width: Length,
    height: Length,
    placements: tuple[Placement, ...] = (),
    *,
    anchors: Mapping[str, Bounds] | None = None,
    **properties: Any,
) -> LayoutPlan:
    return LayoutPlan(
        width,
        height,
        placements,
        dict(properties, content_size=(width, height)),
        anchors or {},
    )
