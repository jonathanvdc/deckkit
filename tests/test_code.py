from types import MappingProxyType

import pytest

from deckkit.expanded_views import ExpandedText
from deckkit.theme import CodeTokenStyle
from deckkit.themes import ClarityTheme
from deckkit.views.semantic import Code, CodeLine, CodeSpan, PygmentsHighlighter


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


def test_pygments_highlighting_produces_manual_code_model():
    source = 'def greet(name):\n\treturn f"Hi, {name}"\n'
    code = Code.highlight(source, language="python")

    assert code.language == "python"
    assert (
        "\n".join("".join(span.text for span in line.spans) for line in code.lines)
        == source
    )
    assert [(span.text, span.token) for span in code.lines[0].spans] == [
        ("def", "keyword"),
        (" ", "text.whitespace"),
        ("greet", "name.function"),
        ("(", "punctuation"),
        ("name", "name"),
        ("):", "punctuation"),
    ]
    assert code.lines[-1].spans == (CodeSpan(""),)


def test_pygments_scopes_resolve_through_theme(compiler):
    compiled = compiler.compile_view(
        Code.highlight('message = "hello"', language="python")
    )
    expanded = next(
        node for node in compiled.expanded_tree.walk() if isinstance(node, ExpandedText)
    )
    assert any(
        span.color == "#087F8C" and "hello" in span.text
        for span in expanded.styled_lines[0].spans
    )


def test_code_highlight_accepts_custom_highlighter():
    class Highlighter:
        def highlight(self, source: str, language: str) -> tuple[CodeLine, ...]:
            assert (source, language) == ("SELECT 1", "query")
            return (CodeLine(CodeSpan("SELECT", token="verb"), " 1"),)

    code = Code.highlight("SELECT 1", language="query", highlighter=Highlighter())
    assert code.lines[0].spans[0].token == "verb"


def test_pygments_highlighter_rejects_unknown_language():
    with pytest.raises(ValueError, match="Unknown code language"):
        PygmentsHighlighter().highlight("source", "definitely-not-a-language")


@pytest.mark.parametrize("scope", ["", ".keyword", "keyword.", "two..dots", " space"])
def test_code_rejects_invalid_scopes(scope):
    with pytest.raises(ValueError, match="scope"):
        CodeSpan("value", token=scope)
