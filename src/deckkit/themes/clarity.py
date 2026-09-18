from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import ClassVar

from ..fonts import Font
from ..theme import TextStyle, Theme
from ..units import pt


class ClarityTheme(Theme):
    """A restrained blue/teal design system with a four-role type scale."""

    typography: ClassVar[Mapping[str, TextStyle]] = MappingProxyType(
        {
            role: TextStyle(Font("Aptos"), pt(size))
            for role, size in {
                "title": 32,
                "body": 20,
                "caption": 16,
                "metric": 46,
            }.items()
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
