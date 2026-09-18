from __future__ import annotations

from ..layout import Layout
from .stack import Stack


class HStack(Stack):
    def _make_layout(self) -> Layout:
        from ..layouts import StackLayout

        return StackLayout("horizontal", self.spacing)
