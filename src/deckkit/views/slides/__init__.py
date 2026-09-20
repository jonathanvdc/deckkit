"""Semantic slide structures with theme-overridable compositions."""

from .slide_margins import SlideMargins
from .slide_with_margins import SlideWithMargins
from .title_and_content import TitleAndContent
from .title_and_content_slide import TitleAndContentSlide

__all__ = [
    "SlideMargins",
    "SlideWithMargins",
    "TitleAndContent",
    "TitleAndContentSlide",
]
