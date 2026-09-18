from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ..fonts import Font
from ..layout import Constraints, LayoutChild, LayoutContext, LayoutPlan
from ..measurement import TextFlow
from ..units import Length
from ._content import content


@dataclass(frozen=True)
class TextLayout:
    text: str
    font: Font
    font_size: Length
    line_spacing: float
    flow: TextFlow = "wrapped"

    def measure(
        self, c: Constraints, children: Sequence[LayoutChild], context: LayoutContext
    ) -> LayoutPlan:
        font = context.font_resolver.resolve(self.font)
        arguments = (self.text, font, self.font_size, c.max_width, self.line_spacing)
        metrics = (
            context.measurer.measure(*arguments, self.flow)
            if self.flow == "verbatim"
            else context.measurer.measure(*arguments)
        )
        return content(metrics.width, metrics.height, metrics=metrics, font=font)


@dataclass(frozen=True)
class ShapeLayout:
    def measure(
        self, c: Constraints, children: Sequence[LayoutChild], context: LayoutContext
    ) -> LayoutPlan:
        return content(c.min_width, c.min_height)


@dataclass(frozen=True)
class ImageLayout:
    width: Length
    height: Length

    def measure(
        self, c: Constraints, children: Sequence[LayoutChild], context: LayoutContext
    ) -> LayoutPlan:
        scale = min(c.max_width / self.width, c.max_height / self.height, 1)
        return content(
            max(c.min_width, self.width * scale),
            max(c.min_height, self.height * scale),
        )
