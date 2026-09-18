from pathlib import Path

import pytest

from deckkit import Compiler
from deckkit.backends import pptx, svg
from deckkit.fonts import (
    FileFontResolver,
    Font,
    FontFile,
    FontNotFoundError,
    SystemFontResolver,
)
from deckkit.measurement import PillowMeasurer
from deckkit.themes import ClarityTheme, TextStyle
from deckkit.units import pt
from deckkit.views import Text


def test_file_resolver_and_system_discovery_agree(font, tmp_path):
    source = Path(font)
    copy = tmp_path / ("font" + source.suffix)
    copy.write_bytes(source.read_bytes())
    pinned = FileFontResolver({Font("Alias"): str(copy)}).resolve(Font("Alias"))
    request = Font(pinned.family)
    discovered = SystemFontResolver((tmp_path,)).resolve(request)
    assert discovered == pinned
    assert (
        SystemFontResolver((tmp_path,)).resolve(Font(pinned.family.lower())) == pinned
    )
    assert PillowMeasurer.measure("Hello", discovered, pt(20), pt(400), 1.1).width > pt(
        0
    )


def test_missing_font_does_not_substitute(tmp_path):
    with pytest.raises(FontNotFoundError, match="No font was substituted"):
        SystemFontResolver((tmp_path,)).resolve(Font("Absent Font"))
    with pytest.raises(FontNotFoundError, match="No file mapping"):
        FileFontResolver({}).resolve(Font("Absent Font"))
    with pytest.raises(FontNotFoundError, match="Cannot load"):
        FileFontResolver({Font("Missing"): str(tmp_path / "missing.ttf")}).resolve(
            Font("Missing")
        )


def test_collection_face_index(font):
    from PIL import ImageFont

    if Path(font).suffix.lower() not in (".ttc", ".otc"):
        pytest.skip("Fixture is not a collection")
    try:
        expected = ImageFont.truetype(font, 16, index=1).getname()
    except OSError:
        pytest.skip("Collection has one face")
    face = FileFontResolver({Font("Second"): FontFile(font, 1)}).resolve(Font("Second"))
    assert (face.family, face.style) == expected
    assert face.index == 1
    assert PillowMeasurer.measure("Second face", face, pt(20), pt(400), 1.1).width > pt(
        0
    )


def test_exports_use_resolved_family_not_file_alias(font, tmp_path):
    from pptx import Presentation

    request = Font("Build font")
    resolver = FileFontResolver({request: font})

    class BuildTheme(ClarityTheme):
        def text_style(self, role):
            style = super().text_style(role)
            return TextStyle(request, style.size, style.line_spacing)

    compiled = Compiler(BuildTheme(), font_resolver=resolver).compile_view(Text("Hello"))
    layout = compiled.drawable
    face = resolver.resolve(request)
    assert layout.children[0].requested_font == request
    assert layout.children[0].font == face
    assert f'font-family="{face.family}"' in svg.render(layout)
    output = tmp_path / "fonts.pptx"
    from deckkit import CompiledDeck

    pptx.render(CompiledDeck.from_views(compiled), output)
    para = Presentation(output).slides[0].shapes[0].text_frame.paragraphs[0]
    assert para.font.name == face.family
    assert para.font.bold == face.bold
    assert para.font.italic == face.italic
