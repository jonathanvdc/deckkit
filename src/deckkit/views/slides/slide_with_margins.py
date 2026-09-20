"""Base class for slides whose content is placed within margins."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ...context import Context
from ..slide import Slide
from ..view import View
from .slide_margins import SlideMargins


class SlideWithMargins(Slide, ABC):
    """A slide whose content is placed within margins."""

    @abstractmethod
    def body_without_margins(self, context: Context) -> View:
        """Return the content to place within the slide margins."""
        raise NotImplementedError

    def body(self, context: Context) -> View:
        return SlideMargins(self.body_without_margins(context))
