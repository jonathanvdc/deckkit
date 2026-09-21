"""Author-facing views; implementations live in individual modules."""

from ..context import (
    Context,
    Environment,
    State,
)
from .canvas import Canvas
from .code import Code, CodeHighlighter, CodeLine, CodeSpan
from .hstack import HStack
from .image import Image
from .layout_view import LayoutView
from .modifier_views import Edge, EdgeSet, FrameSpec, unbounded
from .rectangle import Rectangle
from .slide import Slide
from .stack import Stack
from .text import Text, TextLine, TextSpan
from .view import Modifier, View
from .vstack import VStack
from .zstack import ZStack

__all__ = [
    "Canvas",
    "Context",
    "Edge",
    "EdgeSet",
    "Environment",
    "FrameSpec",
    "HStack",
    "Image",
    "LayoutView",
    "Modifier",
    "Rectangle",
    "Slide",
    "Stack",
    "State",
    "Text",
    "TextLine",
    "TextSpan",
    "VStack",
    "View",
    "ZStack",
    "unbounded",
]

from .composite_view import CompositeView
from .primitive_view import PrimitiveView
from .pygments_highlighter import PygmentsHighlighter

__all__ += [
    "Code",
    "CodeHighlighter",
    "CodeLine",
    "CodeSpan",
    "CompositeView",
    "PrimitiveView",
    "PygmentsHighlighter",
]
