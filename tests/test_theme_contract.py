from __future__ import annotations

from deckkit import Compiler
from deckkit.fonts import (
    FileFontResolver,
    Font,
)
from deckkit.themes import (
    BodyTextStyle,
    DesignToken,
    PrimaryColor,
    Theme,
    Typography,
)
from deckkit.units import pt
from deckkit.views import Text


def test_theme_can_be_defined_entirely_by_foundational_tokens():
    from deckkit.fonts import Font
    from deckkit.themes import (
        AccentColor,
        BaseFont,
        BaseFontSize,
        Color,
        MutedColor,
        OnAccentColor,
        PrimaryColor,
        SpacingUnit,
        SurfaceColor,
    )

    theme = Theme(
        {
            BaseFont: BaseFont.set(Font("Custom")),
            BaseFontSize: BaseFontSize.set(pt(18)),
            SpacingUnit: SpacingUnit.set(pt(4)),
            PrimaryColor: PrimaryColor.set(Color("#123456")),
            MutedColor: MutedColor.set(Color("#777777")),
            SurfaceColor: SurfaceColor.set(Color("#EEEEEE")),
            AccentColor: AccentColor.set(Color("#008899")),
            OnAccentColor: OnAccentColor.set(Color("#FFFFFF")),
        }
    )

    resolver = theme.token_resolver()
    assert resolver[AccentColor].hex == "#008899"
    assert resolver[BodyTextStyle] == Typography(Font("Custom"), pt(18))


def test_custom_theme_needs_no_clarity_state(font):
    request = Font("Custom")

    class CustomTheme(Theme):
        def __init__(self) -> None:
            from deckkit.themes import Color

            super().__init__(
                {
                    PrimaryColor: PrimaryColor.set(Color("#123456")),
                    BodyTextStyle: BodyTextStyle.set(Typography(request, pt(18))),
                }
            )

    theme = CustomTheme()
    result = Compiler(
        theme, font_resolver=FileFontResolver({request: font})
    ).compile_view(Text("Independent"))
    assert result.drawable.children[0].color == "#123456"
    assert result.drawable.children[0].font_size == pt(18)
    assert not hasattr(theme, "typography")


def test_environment_values_are_typed_immutable_overrides(compiler):
    density = DesignToken[int]("test.density", lambda values: 1)

    environment = compiler.environment
    derived = environment.with_token(density, density.set(2))

    assert environment[density] == 1
    assert derived[density] == 2
