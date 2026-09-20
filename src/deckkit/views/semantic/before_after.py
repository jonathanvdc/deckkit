"""A semantic view for presenting a before-and-after comparison."""

from __future__ import annotations

from dataclasses import dataclass

from ...context import Context
from ...units import pt
from ..hstack import HStack
from ..text import Text
from ..view import View
from ..vstack import VStack
from .card import Card
from .pill import Pill
from .semantic_view import SemanticView


@dataclass(frozen=True)
class BeforeAfter(SemanticView):
    """Present two states side by side with a concluding takeaway.

    All three content slots accept arbitrary :class:`~deckkit.views.View` values,
    so callers can use text, stacks, shapes, or other semantic components. The
    default recipe labels the states ``BEFORE`` and ``AFTER`` and highlights the
    latter with the theme's accent style.

    Args:
        before: Content describing the initial state.
        after: Content describing the resulting state.
        takeaway: Conclusion displayed below the comparison.
    """

    before: View
    after: View
    takeaway: View

    def __post_init__(self) -> None:
        for name in ("before", "after", "takeaway"):
            if not isinstance(getattr(self, name), View):
                raise TypeError(
                    f"BeforeAfter.{name} must be a View; wrap text in Text(...)"
                )

    def body(self, context: Context) -> View:
        """Arrange the comparison using the default horizontal recipe."""
        label_width, label_height = pt(88), pt(36)
        before = Card(
            VStack(
                Pill(Text("BEFORE").font("caption")).frame(
                    width=label_width, height=label_height
                ),
                self.before,
            )
        ).flex()
        after = Card(
            VStack(
                Pill(
                    Text("AFTER").font("caption"),
                    background_style="accent",
                    content_style="white",
                ).frame(width=label_width, height=label_height),
                self.after.foreground_style("accent"),
            )
        ).flex()
        return VStack(
            HStack(before, after, spacing=pt(24)),
            self.takeaway,
            spacing=pt(32),
        )
