from __future__ import annotations

from ..animation import SlideTimeline
from .composite_view import CompositeView


class Slide(CompositeView):
    def timeline(self) -> SlideTimeline:
        """Describe this slide's authored presentation states and triggers."""
        return SlideTimeline.static()
