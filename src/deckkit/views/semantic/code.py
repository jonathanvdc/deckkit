"""Semantic source-code blocks with theme-resolved token scopes."""

from __future__ import annotations

from dataclasses import dataclass

from ...context import Context
from ...geometry import RelativePoint
from ...units import pt
from ..rectangle import Rectangle
from ..text import Text, TextLine, TextSpan
from ..view import View
from ..zstack import ZStack
from .semantic_view import SemanticView


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
    foreground_style: str | None = None
    background_style: str | None = None
    font_role: str | None = None

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
    background_style: str | None

    def __init__(
        self,
        *spans: CodeSpan | str,
        background_style: str | None = None,
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


@dataclass(frozen=True, init=False)
class Code(SemanticView):
    """A themed, whitespace-preserving source-code block."""

    lines: tuple[CodeLine, ...]
    language: str | None
    background_style: str

    def __init__(
        self,
        content: str | CodeLine,
        *lines: CodeLine,
        language: str | None = None,
        background_style: str = "surface",
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
        object.__setattr__(self, "background_style", background_style)

    def default_body(self, context: Context) -> View:
        theme = context.environment.theme
        lines = []
        for line in self.lines:
            spans = []
            for span in line.spans:
                style = theme.code_style(self.language, span.token)
                spans.append(
                    TextSpan(
                        span.text,
                        span.font_role or style.font_role,
                        span.foreground_style or style.foreground_style,
                        span.background_style or style.background_style,
                    )
                )
            lines.append(TextLine(*spans, background_style=line.background_style))
        text = Text(lines[0], *lines[1:], flow="verbatim").font("code")
        return ZStack(
            Rectangle(corner_radius=pt(8)).foreground_style(self.background_style),
            text.padding(pt(16)),
            alignment=RelativePoint.top_left,
        )
