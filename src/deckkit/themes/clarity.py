from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Any, ClassVar

from ..fonts import Font
from ..theme import (
    AccentColor,
    BaseFont,
    BaseFontSize,
    CodeFont,
    CodeTokenStyle,
    Color,
    LineSpacing,
    MutedColor,
    OnAccentColor,
    PrimaryColor,
    SpacingUnit,
    SurfaceColor,
    Theme,
)
from ..tokens import DesignToken, TokenAssignment
from ..units import pt


class ClarityTheme(Theme):
    """A restrained blue/teal design system with a four-role type scale."""

    code_styles: ClassVar[Mapping[str, CodeTokenStyle]] = MappingProxyType(
        {
            "comment": CodeTokenStyle(foreground_style=MutedColor),
            "keyword": CodeTokenStyle(foreground_style=AccentColor),
            "literal.string": CodeTokenStyle(foreground_style=AccentColor),
        }
    )

    def __init__(
        self,
        overrides: Mapping[DesignToken[Any], TokenAssignment[Any]] | None = None,
        *,
        font: Font | None = None,
        code_font: Font | None = None,
        accent: Color | str | None = None,
    ) -> None:
        values: dict[DesignToken[Any], TokenAssignment[Any]] = {
            BaseFont: BaseFont.set(Font("Aptos")),
            CodeFont: CodeFont.set(Font("Aptos Mono")),
            BaseFontSize: BaseFontSize.set(pt(20)),
            LineSpacing: LineSpacing.set(1.1),
            SpacingUnit: SpacingUnit.set(pt(4)),
            PrimaryColor: PrimaryColor.set(Color("#183153")),
            MutedColor: MutedColor.set(Color("#7D8998")),
            SurfaceColor: SurfaceColor.set(Color("#E8EEF5")),
            AccentColor: AccentColor.set(Color("#087F8C")),
            OnAccentColor: OnAccentColor.set(Color("#FFFFFF")),
        }
        values.update(overrides or {})
        if font is not None:
            values[BaseFont] = BaseFont.set(font)
        if code_font is not None:
            values[CodeFont] = CodeFont.set(code_font)
        if accent is not None:
            color = accent if isinstance(accent, Color) else Color(accent)
            values[AccentColor] = AccentColor.set(color)
        super().__init__(values)
