from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..context import Environment
from ..theme import Color, ColorStyle, ForegroundColor
from ..units import Length, pt, require_length

if TYPE_CHECKING:
    from ..fonts import FontResolver
    from ..measurement import TextMeasurer


@dataclass(frozen=True)
class CanvasSize:
    width: Length
    height: Length

    def __post_init__(self) -> None:
        require_length(self.width)
        require_length(self.height)
        if self.width < pt(0) or self.height < pt(0):
            raise ValueError("Canvas dimensions must be non-negative")


@dataclass(frozen=True)
class CanvasContext:
    environment: Environment
    measurer: TextMeasurer
    font_resolver: FontResolver

    def color(self, style: ColorStyle = ForegroundColor) -> Color:
        return style if isinstance(style, Color) else self.environment[style]
