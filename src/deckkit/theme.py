from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite
from types import MappingProxyType
from typing import TYPE_CHECKING, ClassVar

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


@dataclass(frozen=True)
class CodeTokenStyle:
    """Optional text-style overrides associated with a code token scope."""

    foreground_style: str | None = None
    background_style: str | None = None
    font_role: str | None = None


class Theme(ABC):
    """Design-system contract, independent of any particular palette or type scale."""

    code_styles: ClassVar[Mapping[str, CodeTokenStyle]] = MappingProxyType({})

    @abstractmethod
    def text_style(self, role: str) -> TextStyle:
        """Resolve a semantic typography role."""
        raise NotImplementedError

    @abstractmethod
    def color(self, role: str) -> str:
        """Resolve a semantic color role to an RGB hex color."""
        raise NotImplementedError

    def code_style(self, language: str | None, token: str | None) -> CodeTokenStyle:
        """Resolve cascading language and token scopes to presentation roles."""
        token_parts = token.split(".") if token else []
        keys = ["plain"]
        keys.extend(
            ".".join(token_parts[:end]) for end in range(1, len(token_parts) + 1)
        )
        if language:
            keys.append(language)
            keys.extend(
                f"{language}.{'.'.join(token_parts[:end])}"
                for end in range(1, len(token_parts) + 1)
            )
        result = CodeTokenStyle()
        for key in keys:
            override = self.code_styles.get(key)
            if override is not None:
                result = CodeTokenStyle(
                    override.foreground_style or result.foreground_style,
                    override.background_style or result.background_style,
                    override.font_role or result.font_role,
                )
        return result

    def render_semantic(self, component: SemanticView, context: Context) -> View | None:
        """Optionally override a component; None selects its default composition."""
        return None
