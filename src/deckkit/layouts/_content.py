from __future__ import annotations

from typing import Any

from ..layout import LayoutPlan, Placement
from ..units import Length


def content(
    width: Length,
    height: Length,
    placements: tuple[Placement, ...] = (),
    **properties: Any,
) -> LayoutPlan:
    return LayoutPlan(
        width, height, placements, dict(properties, content_size=(width, height))
    )
