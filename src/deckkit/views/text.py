from __future__ import annotations

from dataclasses import dataclass

from ..context import Context, FontRoleKey, ForegroundStyleKey
from ..expanded_views import ExpandedMetadata, ExpandedText
from ..layouts import TextLayout
from ..measurement import TextFlow
from .primitive_view import PrimitiveView


@dataclass(frozen=True)
class Text(PrimitiveView):
    text: str
    flow: TextFlow = "wrapped"

    def __post_init__(self) -> None:
        if self.flow not in ("wrapped", "verbatim"):
            raise ValueError("Text flow must be 'wrapped' or 'verbatim'")

    def expand(self, context: Context, metadata: ExpandedMetadata) -> ExpandedText:
        environment = context.environment
        typography = environment.theme.text_style(environment.get(FontRoleKey))
        return ExpandedText(
            metadata,
            TextLayout(
                self.text,
                typography.font,
                typography.size,
                typography.line_spacing,
                self.flow,
            ),
            self.text,
            typography.font,
            typography.size,
            environment.theme.color(environment.get(ForegroundStyleKey)),
            typography.line_spacing,
            self.flow,
        )
