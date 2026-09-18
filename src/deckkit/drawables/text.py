from __future__ import annotations

from dataclasses import dataclass

from ..fonts import Font, ResolvedFont
from ..measurement import MeasuredText
from ..units import Length
from .bounds import Bounds
from .drawable import Drawable


@dataclass(frozen=True)
class DrawableText(Drawable):
    content_bounds: Bounds
    text: str
    color: str
    font: ResolvedFont
    requested_font: Font
    font_size: Length
    metrics: MeasuredText
