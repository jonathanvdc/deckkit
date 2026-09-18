from __future__ import annotations

from dataclasses import dataclass

from ..geometry import RelativePoint
from ..layout import Layout
from ..units import pt
from .stack import Stack
from .view import View


@dataclass(frozen=True, init=False)
class ZStack(Stack):
    alignment: RelativePoint

    def __init__(
        self, *children: View | None, alignment: RelativePoint = RelativePoint.center
    ) -> None:
        if not isinstance(alignment, RelativePoint):
            raise TypeError("ZStack alignment must be a RelativePoint")
        object.__setattr__(self, "alignment", alignment)
        super().__init__(*children, spacing=pt(0))

    def _make_layout(self) -> Layout:
        from ..layouts import OverlayLayout

        return OverlayLayout(self.alignment)
