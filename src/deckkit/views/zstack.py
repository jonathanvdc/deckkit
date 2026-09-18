from __future__ import annotations

from ..layout import Layout
from .stack import Stack


class ZStack(Stack):
    def _make_layout(self) -> Layout:
        from ..layouts import OverlayLayout

        return OverlayLayout()
