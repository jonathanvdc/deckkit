from __future__ import annotations

from ..animation import SlideTimeline
from .semantic.semantic_view import SemanticView


class Slide(SemanticView):
    """A theme-overridable top-level presentation view."""

    def timeline(self) -> SlideTimeline:
        """Describe this slide's authored presentation states and triggers."""
        return SlideTimeline.static()
