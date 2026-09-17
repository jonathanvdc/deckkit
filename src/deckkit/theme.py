from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from math import isfinite
from typing import TYPE_CHECKING

from .fonts import Font
from .units import Length, pt, require_length

if TYPE_CHECKING:
    from .context import Context
    from .views import View
    from .views.semantic import SemanticView


@dataclass(frozen=True)
class TextStyle:
    """A typography role's font face, physical size and line-height multiplier.

    Font weight/style are selected by the font file, without synthetic styling.
    """

    font: Font
    size: Length
    line_spacing: float = 1.1

    def __post_init__(self) -> None:
        if not isinstance(self.font, Font):
            raise TypeError(
                "TextStyle.font must be a Font request; configure files on FileFontResolver"
            )
        require_length(self.size)
        if self.size <= pt(0):
            raise ValueError("Font size must be positive")
        if not isfinite(self.line_spacing) or self.line_spacing <= 0:
            raise ValueError("Line spacing must be finite and positive")


class Theme(ABC):
    """Design-system contract, independent of any particular palette or type scale."""

    @abstractmethod
    def text_style(self, role: str) -> TextStyle:
        """Resolve a semantic typography role."""
        raise NotImplementedError

    @abstractmethod
    def color(self, role: str) -> str:
        """Resolve a semantic color role to an RGB hex color."""
        raise NotImplementedError

    def render_semantic(self, component: SemanticView, context: Context) -> View | None:
        """Optionally override a component; None selects its default composition."""
        return None
