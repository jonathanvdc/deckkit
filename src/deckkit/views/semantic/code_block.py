"""A themed container for code text."""

from __future__ import annotations

from dataclasses import dataclass

from ...context import Context
from ..code import Code
from ..view import View
from .card import Card
from .semantic_view import SemanticView


@dataclass(frozen=True)
class CodeBlock(SemanticView):
    """Place code on a padded, theme-overridable surface."""

    content: Code
    background_style: str = "surface"

    def __post_init__(self) -> None:
        if not isinstance(self.content, Code):
            raise TypeError("CodeBlock.content must be Code")

    def body(self, context: Context) -> View:
        return Card(self.content, background_style=self.background_style)
