from __future__ import annotations

import pytest

from deckkit import Compiler, FileFontResolver, Font, Text, TextStyle, Theme, pt


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
