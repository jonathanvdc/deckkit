from __future__ import annotations

from ..layout import Layout
from .stack import Stack


class VStack(Stack):
    layout_kind = "vstack"

    def _make_layout(self) -> Layout:
        from ..layouts import StackLayout

        return StackLayout("vertical", self.spacing)
