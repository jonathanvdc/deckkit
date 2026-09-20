from __future__ import annotations

from dataclasses import dataclass

from ..context import Context
from ..expanded_views import ExpandedMetadata, ExpandedText
from ..layouts import TextLayout
from ..measurement import StyledTextLine, StyledTextSpan, TextFlow
from ..theme import Color, ColorStyle, ForegroundColor, TextStyle, Typography
from ..tokens import DesignToken
from .primitive_view import PrimitiveView


@dataclass(frozen=True)
class TextSpan:
    text: str
    font_style: DesignToken[Typography] | None = None
    foreground_style: ColorStyle | None = None
    background_style: ColorStyle | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.text, str):
            raise TypeError("TextSpan.text must be a string")
        if "\n" in self.text:
            raise ValueError(
                "TextSpan cannot contain newlines; use separate TextLine values"
            )


@dataclass(frozen=True, init=False)
class TextLine:
    spans: tuple[TextSpan, ...]
    background_style: ColorStyle | None

    def __init__(
        self,
        *spans: TextSpan | str,
        background_style: ColorStyle | None = None,
    ) -> None:
        normalized = []
        for span in spans:
            if isinstance(span, TextSpan):
                normalized.append(span)
            elif isinstance(span, str):
                normalized.append(TextSpan(span))
            else:
                raise TypeError("TextLine values must be strings or TextSpan values")
        object.__setattr__(
            self,
            "spans",
            tuple(normalized) or (TextSpan(""),),
        )
        object.__setattr__(self, "background_style", background_style)


@dataclass(frozen=True, init=False)
class Text(PrimitiveView):
    lines: tuple[TextLine, ...]
    flow: TextFlow = "wrapped"

    def __init__(
        self,
        content: str | TextLine,
        *lines: TextLine,
        flow: TextFlow = "wrapped",
    ) -> None:
        if flow not in ("wrapped", "verbatim"):
            raise ValueError("Text flow must be 'wrapped' or 'verbatim'")
        if isinstance(content, str):
            if lines:
                raise TypeError("Additional TextLine values require a TextLine first")
            structured = tuple(TextLine(line) for line in content.split("\n"))
        elif isinstance(content, TextLine):
            structured = (content, *lines)
        else:
            raise TypeError("Text content must be a string or TextLine")
        object.__setattr__(self, "lines", structured)
        object.__setattr__(self, "flow", flow)

    @property
    def text(self) -> str:
        return "\n".join(
            "".join(span.text for span in line.spans) for line in self.lines
        )

    def _resolved_lines(self, context: Context) -> tuple[StyledTextLine, ...]:
        environment = context.environment

        def color(style: ColorStyle) -> str:
            return (style if isinstance(style, Color) else environment[style]).hex

        base_typography = environment[TextStyle]
        base_foreground = environment[ForegroundColor]
        result = []
        for line in self.lines:
            spans = []
            for span in line.spans:
                typography = (
                    environment[span.font_style]
                    if span.font_style is not None
                    else base_typography
                )
                foreground = span.foreground_style or base_foreground
                spans.append(
                    StyledTextSpan(
                        span.text,
                        typography.font,
                        typography.size,
                        typography.line_spacing,
                        color(foreground),
                        color(span.background_style)
                        if span.background_style is not None
                        else None,
                    )
                )
            result.append(
                StyledTextLine(
                    tuple(spans),
                    color(line.background_style)
                    if line.background_style is not None
                    else None,
                )
            )
        return tuple(result)

    def expand(self, context: Context, metadata: ExpandedMetadata) -> ExpandedText:
        resolved_lines = self._resolved_lines(context)
        return ExpandedText(
            metadata,
            TextLayout(resolved_lines, self.flow),
            self.flow,
            resolved_lines,
        )
