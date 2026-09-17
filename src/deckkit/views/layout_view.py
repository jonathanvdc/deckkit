from __future__ import annotations

from dataclasses import dataclass

from ..layout import Layout
from .view import View


@dataclass(frozen=True, init=False)
class LayoutView(View):
    """Compose children using a custom layout policy."""

    layout: Layout
    children: tuple[View | None, ...]
    layout_kind = "layout"

    def __init__(self, layout: Layout, *children: View | None) -> None:
        object.__setattr__(self, "layout", layout)
        object.__setattr__(self, "children", tuple(children))
