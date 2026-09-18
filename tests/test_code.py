from types import MappingProxyType

import pytest

from deckkit.expanded_views import ExpandedText
from deckkit.theme import CodeTokenStyle
from deckkit.themes import ClarityTheme
from deckkit.views.semantic import Code, CodeLine, CodeSpan


def test_code_resolves_cascading_language_token_scopes(compiler):
    class CodeTheme(ClarityTheme):
        code_styles = MappingProxyType(
            {
                "plain": CodeTokenStyle(foreground_style="primary"),
                "keyword": CodeTokenStyle(foreground_style="muted"),
                "keyword.declaration": CodeTokenStyle(background_style="#FFF2A8"),
                "python.keyword": CodeTokenStyle(foreground_style="accent"),
            }
        )

    compiler.environment = compiler.environment.__class__(CodeTheme())
    compiled = compiler.compile_view(
        Code(
            CodeLine(
                CodeSpan("def", token="keyword.declaration"),
                " ",
                CodeSpan("greet", token="name.function"),
                background_style="surface",
            ),
            language="python",
        )
    )
    expanded = next(
        node for node in compiled.expanded_tree.walk() if isinstance(node, ExpandedText)
    )
    spans = expanded.styled_lines[0].spans

    assert expanded.flow == "verbatim"
    assert [span.color for span in spans] == ["#087F8C", "#183153", "#183153"]
    assert spans[0].background == "#FFF2A8"
    assert expanded.styled_lines[0].background == "#E8EEF5"


def test_code_preserves_source_whitespace(compiler):
    compiled = compiler.compile_view(Code("\tvalue\n\n  return value"))
    text = next(node for node in compiled.drawable.walk() if hasattr(node, "metrics"))
    assert text.metrics.lines == ("    value", "", "  return value")


@pytest.mark.parametrize("scope", ["", ".keyword", "keyword.", "two..dots", " space"])
def test_code_rejects_invalid_scopes(scope):
    with pytest.raises(ValueError, match="scope"):
        CodeSpan("value", token=scope)
