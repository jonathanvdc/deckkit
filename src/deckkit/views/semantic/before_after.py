from __future__ import annotations

from dataclasses import dataclass

from ...context import Context
from ...units import pt
from ..hstack import HStack
from ..text import Text
from ..view import View
from ..vstack import VStack
from .semantic_view import SemanticView


@dataclass(frozen=True)
class BeforeAfter(SemanticView):
    title: View
    before: View
    after: View
    takeaway: View

    def __post_init__(self) -> None:
        for name in ("title", "before", "after", "takeaway"):
            if not isinstance(getattr(self, name), View):
                raise TypeError(
                    f"BeforeAfter.{name} must be a View; wrap text in Text(...)"
                )

    def default_body(self, context: Context) -> View:
        before = VStack(Text("BEFORE").font("caption"), self.before).flex()
        after = VStack(
            Text("AFTER").font("caption"), self.after.foreground_style("accent")
        ).flex()
        return VStack(
            self.title.font("title"),
            HStack(before, Text("→"), after, spacing=pt(24)),
            self.takeaway,
            spacing=pt(32),
        )
