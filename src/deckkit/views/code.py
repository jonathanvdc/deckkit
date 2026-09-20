"""Syntax-aware, whitespace-preserving code text."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..context import Context
from ..theme import CodeTextStyle, ColorStyle, Typography
from ..tokens import DesignToken
from .composite_view import CompositeView
from .text import Text, TextLine, TextSpan
from .view import View


def _scope(value: str | None, name: str) -> None:
    if value is not None and (
        not value
        or value != value.strip()
        or any(not part for part in value.split("."))
    ):
        raise ValueError(f"{name} must be a dot-separated scope")


@dataclass(frozen=True)
class CodeSpan:
    """A source fragment classified by a language-defined token scope."""

    text: str
    token: str | None = None
    foreground_style: ColorStyle | None = None
    background_style: ColorStyle | None = None
    font_style: DesignToken[Typography] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.text, str):
            raise TypeError("CodeSpan.text must be a string")
        if "\n" in self.text:
            raise ValueError(
                "CodeSpan cannot contain newlines; use separate CodeLine values"
            )
        _scope(self.token, "CodeSpan.token")


@dataclass(frozen=True, init=False)
class CodeLine:
    """One logical source line, optionally highlighted across its full width."""

    spans: tuple[CodeSpan, ...]
    background_style: ColorStyle | None

    def __init__(
        self,
        *spans: CodeSpan | str,
        background_style: ColorStyle | None = None,
    ) -> None:
        normalized = []
        for span in spans:
            if isinstance(span, CodeSpan):
                normalized.append(span)
            elif isinstance(span, str):
                normalized.append(CodeSpan(span))
            else:
                raise TypeError("CodeLine values must be strings or CodeSpan values")
        object.__setattr__(self, "spans", tuple(normalized) or (CodeSpan(""),))
        object.__setattr__(self, "background_style", background_style)


class CodeHighlighter(Protocol):
    """Convert source text into Deckkit's code representation."""

    def highlight(self, source: str, language: str) -> tuple[CodeLine, ...]: ...


@dataclass(frozen=True, init=False)
class Code(CompositeView):
    """Syntax-aware code text without block-level decoration."""

    lines: tuple[CodeLine, ...]
    language: str | None

    def __init__(
        self,
        content: str | CodeLine,
        *lines: CodeLine,
        language: str | None = None,
    ) -> None:
        _scope(language, "Code.language")
        if isinstance(content, str):
            if lines:
                raise TypeError("Additional CodeLine values require a CodeLine first")
            structured = tuple(CodeLine(line) for line in content.split("\n"))
        elif isinstance(content, CodeLine):
            structured = (content, *lines)
        else:
            raise TypeError("Code content must be a string or CodeLine")
        object.__setattr__(self, "lines", structured)
        object.__setattr__(self, "language", language)

    @classmethod
    def highlight(
        cls,
        source: str,
        *,
        language: str,
        highlighter: CodeHighlighter | None = None,
    ) -> Code:
        """Tokenize source into semantic spans using a pluggable highlighter."""
        if not isinstance(source, str):
            raise TypeError("Code source must be a string")
        _scope(language, "Code.language")
        if highlighter is None:
            from .pygments_highlighter import PygmentsHighlighter

            highlighter = PygmentsHighlighter()
        lines = highlighter.highlight(source, language)
        if (
            not isinstance(lines, tuple)
            or not lines
            or not all(isinstance(line, CodeLine) for line in lines)
        ):
            raise TypeError(
                "Code highlighters must return a nonempty tuple of CodeLine"
            )
        return cls(lines[0], *lines[1:], language=language)

    def body(self, context: Context) -> View:
        theme = context.environment.theme
        lines = []
        for line in self.lines:
            spans = []
            for span in line.spans:
                style = theme.code_style(self.language, span.token)
                spans.append(
                    TextSpan(
                        span.text,
                        span.font_style or style.font_style,
                        span.foreground_style or style.foreground_style,
                        span.background_style or style.background_style,
                    )
                )
            lines.append(TextLine(*spans, background_style=line.background_style))
        return Text(lines[0], *lines[1:], flow="verbatim").font(CodeTextStyle)
