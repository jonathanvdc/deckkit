"""Optional Pygments adapter for semantic code spans."""

from __future__ import annotations

from re import finditer
from typing import Any

from .code import CodeLine, CodeSpan


def _scope(token: object) -> str | None:
    value = str(token)
    if value == "Token":
        return None
    prefix = "Token."
    return value[len(prefix) :].lower() if value.startswith(prefix) else value.lower()


class PygmentsHighlighter:
    """Produce CodeLine values from any installed Pygments lexer."""

    def highlight(self, source: str, language: str) -> tuple[CodeLine, ...]:
        try:
            from pygments import lex  # type: ignore[import-untyped]
            from pygments.lexers import (  # type: ignore[import-untyped]
                get_lexer_by_name,
            )
            from pygments.util import ClassNotFound  # type: ignore[import-untyped]
        except ImportError as error:
            raise ImportError(
                "Automatic code highlighting requires Pygments; "
                "install deckkit[highlight]"
            ) from error

        try:
            lexer = get_lexer_by_name(
                language,
                stripnl=False,
                stripall=False,
                ensurenl=False,
                tabsize=0,
            )
        except ClassNotFound as error:
            raise ValueError(f"Unknown code language {language!r}") from error

        lines: list[list[CodeSpan]] = [[]]

        def append(text: str, token: Any) -> None:
            if not text:
                return
            scope = _scope(token)
            current = lines[-1]
            if current and current[-1].token == scope:
                previous = current[-1]
                current[-1] = CodeSpan(previous.text + text, scope)
            else:
                current.append(CodeSpan(text, scope))

        for token, value in lex(source, lexer):
            start = 0
            for newline in finditer(r"\r\n?|\n", value):
                append(value[start : newline.start()], token)
                lines.append([])
                start = newline.end()
            append(value[start:], token)

        return tuple(CodeLine(*line) for line in lines)
