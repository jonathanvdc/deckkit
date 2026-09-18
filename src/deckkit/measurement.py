"""Real shaped font metrics behind a replaceable measurement interface."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from re import finditer
from typing import Literal, Protocol

import uharfbuzz as hb
from PIL import ImageFont

from .fonts import Font, FontResolver, ResolvedFont
from .units import Length, pt, require_length

TextFlow = Literal["wrapped", "verbatim"]


@dataclass(frozen=True)
class StyledTextSpan:
    text: str
    font: Font
    size: Length
    line_spacing: float
    color: str
    background: str | None = None


@dataclass(frozen=True)
class StyledTextLine:
    spans: tuple[StyledTextSpan, ...]
    background: str | None = None


@dataclass(frozen=True)
class MeasuredTextRun:
    text: str
    x: Length
    width: Length
    metrics: MeasuredText
    font: ResolvedFont
    requested_font: Font
    font_size: Length
    color: str
    background: str | None


@dataclass(frozen=True)
class MeasuredTextLine:
    runs: tuple[MeasuredTextRun, ...]
    width: Length
    height: Length
    ascent: Length
    background: str | None


@dataclass(frozen=True)
class MeasuredRichText:
    lines: tuple[MeasuredTextLine, ...]
    width: Length
    height: Length


@dataclass(frozen=True)
class MeasuredText:
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
        flow: TextFlow = "wrapped",
    ) -> MeasuredText: ...


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
        flow: TextFlow = "wrapped",
    ) -> MeasuredText:
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

        if flow == "verbatim":
            lines = text.expandtabs(4).split("\n")
        else:
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
        return MeasuredText(
            tuple(lines),
            pt(max(map(length, lines), default=0)),
            pt(len(lines) * line_height),
            pt(ascent),
            pt(line_height),
            family or face.family,
            style or "Regular",
        )


def layout_styled_text(
    measurer: TextMeasurer,
    resolver: FontResolver,
    lines: tuple[StyledTextLine, ...],
    width: Length,
    flow: TextFlow,
) -> MeasuredRichText:
    """Shape and wrap styled logical lines into positioned visual runs."""

    @dataclass(frozen=True)
    class Piece:
        text: str
        source: StyledTextSpan
        font: ResolvedFont
        metrics: MeasuredText

        @property
        def width(self) -> Length:
            return self.metrics.width

    def piece(text: str, source: StyledTextSpan) -> Piece:
        font = resolver.resolve(source.font)
        metrics = measurer.measure(
            text,
            font,
            source.size,
            width,
            source.line_spacing,
            "verbatim",
        )
        return Piece(text, source, font, metrics)

    def words(line: StyledTextLine) -> list[tuple[Piece | None, list[Piece]]]:
        result: list[tuple[Piece | None, list[Piece]]] = []
        pending_space: Piece | None = None
        current: list[Piece] = []
        for span in line.spans:
            for match in finditer(r"\s+|\S+", span.text):
                value = match.group()
                if value.isspace():
                    if current:
                        result.append((pending_space, current))
                        current = []
                    pending_space = piece(" ", span)
                else:
                    current.append(piece(value, span))
        if current:
            result.append((pending_space, current))
        return result

    def preserved(line: StyledTextLine) -> list[Piece]:
        result: list[Piece] = []
        column = 0
        for span in line.spans:
            value = ""
            for character in span.text:
                if character == "\t":
                    spaces = 4 - column % 4
                    value += " " * spaces
                    column += spaces
                else:
                    value += character
                    column += 1
            if value or not result:
                result.append(piece(value, span))
        return result

    def visual(
        pieces: list[Piece],
        background: str | None,
        fallback: StyledTextSpan,
    ) -> MeasuredTextLine:
        if not pieces:
            pieces = [piece("", fallback)]
        ascent = max((item.metrics.ascent for item in pieces), default=pt(0))
        height = max((item.metrics.line_height for item in pieces), default=pt(0))
        x = pt(0)
        runs = []
        for item in pieces:
            runs.append(
                MeasuredTextRun(
                    item.text,
                    x,
                    item.width,
                    item.metrics,
                    item.font,
                    item.source.font,
                    item.source.size,
                    item.source.color,
                    item.source.background,
                )
            )
            x += item.width
        return MeasuredTextLine(tuple(runs), x, height, ascent, background)

    visual_lines: list[MeasuredTextLine] = []
    for logical in lines:
        if flow == "verbatim":
            visual_lines.append(
                visual(preserved(logical), logical.background, logical.spans[0])
            )
            continue
        current: list[Piece] = []
        current_width = pt(0)
        for separator, word in words(logical):
            separator_width = (
                separator.width if separator is not None and current else pt(0)
            )
            word_width = sum((item.width for item in word), pt(0))
            if current and current_width + separator_width + word_width > width:
                visual_lines.append(
                    visual(current, logical.background, logical.spans[0])
                )
                current, current_width = [], pt(0)
                separator_width = pt(0)
            if separator is not None and current:
                current.append(separator)
                current_width += separator_width
            current.extend(word)
            current_width += word_width
        visual_lines.append(visual(current, logical.background, logical.spans[0]))
    return MeasuredRichText(
        tuple(visual_lines),
        max((line.width for line in visual_lines), default=pt(0)),
        sum((line.height for line in visual_lines), pt(0)),
    )
