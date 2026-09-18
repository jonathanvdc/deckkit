from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ..layout import Constraints, LayoutChild, LayoutContext, LayoutPlan
from ..measurement import StyledTextLine, TextFlow, layout_styled_text
from ..units import Length
from ._content import content


@dataclass(frozen=True)
class TextLayout:
    styled_lines: tuple[StyledTextLine, ...]
    flow: TextFlow = "wrapped"

    def measure(
        self, c: Constraints, children: Sequence[LayoutChild], context: LayoutContext
    ) -> LayoutPlan:
        measured_text = layout_styled_text(
            context.measurer,
            context.font_resolver,
            self.styled_lines,
            c.max_width,
            self.flow,
        )
        return content(
            measured_text.width,
            measured_text.height,
            measured_text=measured_text,
            line_width=max(measured_text.width, c.min_width),
        )


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
