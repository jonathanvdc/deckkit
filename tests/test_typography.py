from pathlib import Path
from types import MappingProxyType
from xml.etree import ElementTree as ET

import pytest

from deckkit import Compiler
from deckkit.backends import pptx, svg
from deckkit.drawables import (
    DrawableRectangle,
    DrawableRichText,
    DrawableText,
)
from deckkit.expanded_views import ExpandedText
from deckkit.fonts import (
    FileFontResolver,
    Font,
)
from deckkit.themes import ClarityTheme, TextStyle
from deckkit.units import pt
from deckkit.views import Text, TextLine, TextSpan, VStack
from examples.themes import EditorialTheme


def test_role_fonts_reach_measurement_and_exports(font, tmp_path):
    from pptx import Presentation

    from deckkit.measurement import PillowMeasurer

    # Distinct paths make accidental reuse visible on every supported platform.
    title_font = tmp_path / "title.ttf"
    title_font.write_bytes(Path(font).read_bytes())
    roles = dict(ClarityTheme().typography)
    roles["title"] = TextStyle(Font("Title Font"), pt(36), 1.4)

    class MixedFontTheme(ClarityTheme):
        typography = MappingProxyType(dict(roles))

    theme = MixedFontTheme()
    roles["title"] = TextStyle(Font("Test Font"), pt(12))
    assert theme.text_style("title").size == pt(36)

    class RecordingMeasurer:
        def __init__(self):
            self.requests = []

        def measure(self, *args):
            self.requests.append(args)
            return PillowMeasurer.measure(*args)

    measurer = RecordingMeasurer()
    compiled = Compiler(
        theme,
        measurer=measurer,
        font_resolver=FileFontResolver(
            {Font("Aptos"): font, Font("Title Font"): str(title_font)}
        ),
    ).compile_view(VStack(Text("Title"), Text("Body").font("body")).font("title"))
    layout = compiled.drawable
    assert [(r[1].path, r[2], r[4]) for r in measurer.requests] == [
        (str(title_font), pt(36), 1.4),
        (font, pt(20), 1.1),
    ]
    elements = ET.fromstring(svg.render(layout)).findall(
        ".//{http://www.w3.org/2000/svg}text"
    )
    assert [float(e.attrib["font-size"]) for e in elements] == [36, 20]
    path = tmp_path / "fonts.pptx"
    from deckkit import CompiledDeck

    pptx.render(CompiledDeck.from_views(compiled), path)
    shapes = Presentation(path).slides[0].shapes
    assert [s.text_frame.paragraphs[0].font.size.pt for s in shapes] == [36, 20]


def test_missing_role_is_actionable(font):
    with pytest.raises(ValueError, match="Unknown typography role.*missing"):
        Compiler(
            ClarityTheme(),
            font_resolver=FileFontResolver({Font("Aptos"): font}),
        ).compile_view(Text("Hello").font("missing"))


def test_verbatim_flow_keeps_code_layout(compiler, tmp_path):
    from pptx import Presentation

    source = "\tindented\n\n  spaced"
    compiled = compiler.compile_view(Text(source, flow="verbatim"))
    expanded = next(
        node for node in compiled.expanded_tree.walk() if isinstance(node, ExpandedText)
    )
    drawable = compiled.drawable.children[0]

    assert expanded.flow == "verbatim"
    assert drawable.metrics.lines == ("    indented", "", "  spaced")

    elements = ET.fromstring(svg.render(compiled.drawable)).findall(
        ".//{http://www.w3.org/2000/svg}text"
    )
    assert [element.text for element in elements] == ["    indented", None, "  spaced"]
    assert all(
        element.attrib["{http://www.w3.org/XML/1998/namespace}space"] == "preserve"
        for element in elements
    )

    path = tmp_path / "preserved-whitespace.pptx"
    from deckkit import CompiledDeck

    pptx.render(CompiledDeck.from_views(compiled), path)
    paragraphs = Presentation(path).slides[0].shapes[0].text_frame.paragraphs
    assert [paragraph.text for paragraph in paragraphs] == [
        "    indented",
        "",
        "  spaced",
    ]


def test_verbatim_flow_does_not_wrap(compiler):
    from deckkit.layout import LayoutOverflow

    with pytest.raises(LayoutOverflow):
        compiler.compile_view(
            Text("one two three", flow="verbatim").frame(width=pt(20))
        )


def test_text_rejects_unknown_flow():
    with pytest.raises(ValueError, match="flow"):
        Text("Invalid", flow="collapse")  # type: ignore[arg-type]


def test_structured_text_materializes_styled_runs_and_backgrounds(compiler, tmp_path):
    from pptx import Presentation

    compiled = compiler.compile_view(
        Text(
            TextLine(
                TextSpan("def", foreground_style="accent"),
                TextSpan(" greet", background_style="#FFF2A8"),
                TextSpan("(name):"),
                background_style="surface",
            ),
            flow="verbatim",
        ).frame(width=pt(240))
    )
    group = compiled.drawable.children[0].children[0]
    assert isinstance(group, DrawableRichText)
    runs = [node for node in group.children if isinstance(node, DrawableText)]
    backgrounds = [
        node for node in group.children if isinstance(node, DrawableRectangle)
    ]

    assert [run.text for run in runs] == ["def", " greet", "(name):"]
    assert runs[0].color == "#087F8C"
    assert [background.color for background in backgrounds] == [
        "#E8EEF5",
        "#FFF2A8",
    ]
    assert backgrounds[0].bounds.width == group.content_bounds.width
    assert backgrounds[1].bounds.x == runs[1].bounds.x
    assert backgrounds[1].bounds.width == runs[1].bounds.width

    rendered_svg = svg.render(compiled.drawable)
    assert "#E8EEF5" in rendered_svg
    assert "#FFF2A8" in rendered_svg
    assert ">def<" in rendered_svg

    path = tmp_path / "structured-text.pptx"
    from deckkit import CompiledDeck

    pptx.render(CompiledDeck.from_views(compiled), path)
    shape_text = [
        shape.text
        for shape in Presentation(path).slides[0].shapes
        if shape.has_text_frame and shape.text
    ]
    assert shape_text == ["def greet(name):"]
    text_shape = next(
        shape
        for shape in Presentation(path).slides[0].shapes
        if shape.has_text_frame and shape.text
    )
    assert [run.text for run in text_shape.text_frame.paragraphs[0].runs] == [
        "def",
        " greet",
        "(name):",
    ]


def test_structured_text_wraps_across_span_boundaries(compiler):
    compiled = compiler.compile_view(
        Text(
            TextLine(
                TextSpan("alpha "),
                TextSpan("beta gamma", foreground_style="accent"),
                background_style="surface",
            )
        ).frame(width=pt(70))
    )
    group = compiled.drawable.children[0].children[0]
    assert isinstance(group, DrawableRichText)
    runs = [node for node in group.children if isinstance(node, DrawableText)]
    backgrounds = [
        node for node in group.children if isinstance(node, DrawableRectangle)
    ]

    assert "".join(run.text for run in runs).replace(" ", "") == "alphabetagamma"
    assert len({run.bounds.y for run in runs}) > 1
    assert len(backgrounds) > 1
    assert all(
        background.bounds.width == group.content_bounds.width
        for background in backgrounds
    )


def test_editorial_is_an_example_subclass(font):
    theme = ClarityTheme()
    assert not hasattr(theme, "editorial")
    assert isinstance(EditorialTheme(), EditorialTheme)
    with pytest.raises(TypeError):
        theme.typography["title"] = TextStyle(Font("Test Font"), pt(100))


@pytest.mark.parametrize(
    "size,spacing", [(pt(0), 1), (pt(12), 0), (pt(12), float("nan"))]
)
def test_invalid_typography(size, spacing):
    with pytest.raises(ValueError):
        TextStyle(Font("Test Font"), size, spacing)
