import os
from pathlib import Path

import pytest

from deckkit import Compiler
from deckkit.fonts import FileFontResolver, Font
from deckkit.themes import ClarityTheme


@pytest.fixture
def font():
    candidates = [
        os.environ.get("DECKKIT_FONT", ""),
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    pytest.fail("Set DECKKIT_FONT to a TrueType/OpenType font file")


@pytest.fixture
def compiler(font):
    return Compiler(
        ClarityTheme(),
        font_resolver=FileFontResolver({Font("Aptos"): font}),
    )
