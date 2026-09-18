from __future__ import annotations

import pytest

from deckkit import Compiler
from deckkit.fonts import (
    FileFontResolver,
    Font,
)
from deckkit.themes import TextStyle, Theme
from deckkit.units import pt
from deckkit.views import EnvironmentKey, Text


def test_theme_requires_color_and_typography():
    with pytest.raises(TypeError, match="abstract"):
        Theme()

    class IncompleteTheme(Theme):
        def color(self, role: str) -> str:
            return "#000000"

    with pytest.raises(TypeError, match="abstract"):
        IncompleteTheme()


def test_custom_theme_needs_no_clarity_state(font):
    request = Font("Custom")

    class CustomTheme(Theme):
        def color(self, role: str) -> str:
            return "#123456"

        def text_style(self, role: str) -> TextStyle:
            return TextStyle(request, pt(18))

    theme = CustomTheme()
    result = Compiler(
        theme, font_resolver=FileFontResolver({request: font})
    ).compile_view(Text("Independent"))
    assert result.drawable.children[0].color == "#123456"
    assert result.drawable.children[0].font_size == pt(18)
    assert not hasattr(theme, "typography")


def test_environment_values_are_typed_immutable_overrides(compiler):
    class DensityKey(EnvironmentKey[int]):
        @classmethod
        def default(cls) -> int:
            return 1

    environment = compiler.environment
    derived = environment.setting(DensityKey, 2)

    assert environment.get(DensityKey) == 1
    assert derived.get(DensityKey) == 2
