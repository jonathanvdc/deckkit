from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ..identity import ViewIdentity
from ..layout import Layout
from ..units import Length
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

    def resolve_layout(self, lookup: Callable[[str], ViewIdentity]) -> Layout:
        return self.layout

    @property
    def _expanded_spacing(self) -> Length | None:
        """Spacing metadata retained for logical reconciliation, when applicable."""
        return None
