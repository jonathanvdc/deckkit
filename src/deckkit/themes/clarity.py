from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import ClassVar

from ..fonts import Font
from ..theme import CodeTokenStyle, TextStyle, Theme
from ..units import pt


class ClarityTheme(Theme):
    """A restrained blue/teal design system with a four-role type scale."""

    typography: ClassVar[Mapping[str, TextStyle]] = MappingProxyType(
        {
            "title": TextStyle(Font("Aptos"), pt(32)),
            "body": TextStyle(Font("Aptos"), pt(20)),
            "caption": TextStyle(Font("Aptos"), pt(16)),
            "metric": TextStyle(Font("Aptos"), pt(46)),
            "code": TextStyle(Font("Aptos Mono"), pt(18)),
        }
    )

    code_styles: ClassVar[Mapping[str, CodeTokenStyle]] = MappingProxyType(
        {
            "comment": CodeTokenStyle(foreground_style="muted"),
            "keyword": CodeTokenStyle(foreground_style="accent"),
            "string": CodeTokenStyle(foreground_style="accent"),
        }
    )

    def text_style(self, role: str) -> TextStyle:
        try:
            return self.typography[role]
        except KeyError:
            raise ValueError(
                f"Unknown typography role {role!r}; define it in ClarityTheme.typography"
            ) from None

    def color(self, role: str) -> str:
        colors = {
            "primary": "#183153",
            "muted": "#7D8998",
            "surface": "#E8EEF5",
            "accent": "#087F8C",
            "white": "#FFFFFF",
        }
        if role.startswith("#") and len(role) == 7:
            int(role[1:], 16)
            return role
        return colors[role]
