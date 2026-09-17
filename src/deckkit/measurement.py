"""Real shaped font metrics behind a replaceable measurement interface."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Protocol

import uharfbuzz as hb
from PIL import ImageFont

from .fonts import ResolvedFont
from .units import Length, pt, require_length


@dataclass(frozen=True)
class TextMetrics:
    lines: tuple[str, ...]
    width: Length
    height: Length
    ascent: Length
    line_height: Length
    family: str
    style: str


class TextMeasurer(Protocol):
    def measure(
        self,
        text: str,
        face: ResolvedFont,
        size: Length,
        width: Length,
        line_spacing: float,
    ) -> TextMetrics: ...


class PillowMeasurer:
    @staticmethod
    @lru_cache(maxsize=128)
    def _shaping_font(path: str, index: int) -> hb.Font:
        return hb.Font(hb.Face(Path(path).read_bytes(), index))

    @staticmethod
    @lru_cache(maxsize=128)
    def _font(path: str, index: int, size: float) -> ImageFont.FreeTypeFont:
        return ImageFont.truetype(
            path, round(size * 4), index=index, layout_engine=ImageFont.Layout.BASIC
        )

    @staticmethod
    @lru_cache(maxsize=2048)
    def measure(
        text: str,
        face: ResolvedFont,
        size: Length,
        width: Length,
        line_spacing: float = 1.1,
    ) -> TextMetrics:
        require_length(size)
        require_length(width)
        font = PillowMeasurer._font(face.path, face.index, size.points)
        shaping_font = PillowMeasurer._shaping_font(face.path, face.index)

        def length(value: str) -> float:
            if not value:
                return 0.0
            buffer = hb.Buffer()
            buffer.add_str(value)
            buffer.guess_segment_properties()
            hb.shape(shaping_font, buffer)
            return float(
                sum(p.x_advance for p in buffer.glyph_positions)
                * size.points
                / shaping_font.face.upem
            )

        lines = []
        for paragraph in text.split("\n"):
            line = ""
            for word in paragraph.split():
                candidate = f"{line} {word}" if line else word
                if line and length(candidate) > width.points:
                    lines.append(line)
                    line = word
                else:
                    line = candidate
            lines.append(line)
        ascent, descent = (v / 4 for v in font.getmetrics())
        line_height = (ascent + descent) * line_spacing
        family, style = font.getname()
        return TextMetrics(
            tuple(lines),
            pt(max(map(length, lines), default=0)),
            pt(len(lines) * line_height),
            pt(ascent),
            pt(line_height),
            family or face.family,
            style or "Regular",
        )
