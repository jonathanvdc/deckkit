"""A semantic slide with a title and context-dependent content."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ...context import Context
from ..view import View
from .slide_with_margins import SlideWithMargins
from .title_and_content import TitleAndContent


class TitleAndContentSlide(SlideWithMargins, ABC):
    """A slide with a title and content."""

    @property
    @abstractmethod
    def title(self) -> View:
        """The slide's title."""
        raise NotImplementedError

    @abstractmethod
    def content(self, context: Context) -> View:
        """Return the slide's content for the current presentation state."""
        raise NotImplementedError

    def body_without_margins(self, context: Context) -> View:
        return TitleAndContent(self.title, self.content(context))
