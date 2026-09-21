from __future__ import annotations

from dataclasses import replace

import pytest

from deckkit.drawables import DrawableRectangle
from deckkit.fonts import Font
from deckkit.themes import (
    AccentColor,
    BodyTextStyle,
    ClarityTheme,
    Color,
    DesignToken,
    PrimaryColor,
    SurfaceColor,
    TitleTextStyle,
    TokenDependencyCycle,
    TokenResolver,
)
from deckkit.units import pt
from deckkit.views import CompositeView, Context, Rectangle, Text, View, VStack
from deckkit.views.semantic import Card


def test_computed_tokens_recompute_in_child_scopes():
    base = DesignToken[int]("example.base", lambda values: 2)
    doubled = DesignToken[int]("example.doubled", lambda values: values[base] * 2)
    root = TokenResolver()
    child = root.with_tokens({base: base.set(5)})

    assert root[doubled] == 4
    assert child[doubled] == 10
    assert root[doubled] == 4


def test_override_maps_require_explicit_assignments():
    token = DesignToken[int]("example.explicit", lambda values: 1)

    with pytest.raises(TypeError, match="Value, Alias, or Transform"):
        TokenResolver({token: 2})  # type: ignore[dict-item]


def test_inherited_transform_keeps_computed_dependencies_live():
    base = DesignToken[int]("example.transform-base", lambda values: 2)
    computed = DesignToken[int](
        "example.transformed-computed", lambda values: values[base] * 3
    )
    themed = TokenResolver({computed: computed.derive(lambda value: value + 1)})

    assert themed[computed] == 7
    assert themed.with_tokens({base: base.set(5)})[computed] == 16


def test_transform_can_compute_from_other_tokens():
    text_size = DesignToken[int]("example.text-size", lambda values: 20)
    title_size = DesignToken[int]("example.title-size")
    themed = TokenResolver(
        {title_size: title_size.transform(lambda values: values[text_size] * 2)}
    )

    assert themed[title_size] == 40
    assert themed.with_token(text_size, text_size.set(24))[title_size] == 48


def test_tokens_support_aliases_transforms_and_cycles():
    source = DesignToken[int]("example.source", lambda values: 3)
    alias = DesignToken[int]("example.alias")
    resolver = TokenResolver({alias: alias.alias(source)})

    assert resolver[alias] == 3
    assert (
        resolver.with_tokens({source: source.derive(lambda value: value + 4)})[alias]
        == 7
    )

    first: DesignToken[int]
    second: DesignToken[int]
    first = DesignToken("example.first", lambda values: values[second])
    second = DesignToken("example.second", lambda values: values[first])
    with pytest.raises(TokenDependencyCycle, match="example.first -> example.second"):
        TokenResolver()[first]


def test_theme_foundations_drive_computed_typography():
    theme = ClarityTheme(font=Font("Inter"))
    values = theme.token_resolver()

    assert values[BodyTextStyle].font == Font("Inter")
    assert values[TitleTextStyle].font == Font("Inter")
    assert values[TitleTextStyle].size == values[BodyTextStyle].size * 1.6


def test_colors_round_trip_and_interpolate():
    navy = Color.from_hex("#183153")

    assert navy == Color("#183153")
    assert navy.to_hex() == "#183153"
    assert Color(0, 0, 0).mix(Color(1, 1, 1)).to_hex() == "#808080"
    assert navy.interpolate(Color("#FFFFFF"), 0) == navy

    with pytest.raises(ValueError, match="zero through one"):
        Color(1.1, 0, 0)
    with pytest.raises(ValueError, match="interpolation amount"):
        navy.mix(Color("#FFFFFF"), 2)


def test_view_token_scope_recomputes_derived_values(compiler):
    observed: list[str] = []
    emphasis = DesignToken[str](
        "example.emphasis",
        lambda values: f"{values[AccentColor].hex}:{values[PrimaryColor].hex}",
    )

    class ReadsEmphasis(CompositeView):
        def body(self, context: Context) -> View:
            observed.append(context.environment[emphasis])
            return Text("Value")

    compiler.compile_view(
        VStack(
            ReadsEmphasis(),
            ReadsEmphasis().with_tokens(
                {
                    AccentColor: AccentColor.set(Color("#777777")),
                    PrimaryColor: PrimaryColor.set(Color("#333333")),
                }
            ),
        )
    )

    assert observed == ["#087F8C:#183153", "#777777:#333333"]


def test_component_style_can_be_partially_derived_in_a_subtree(compiler):
    square_card = Card(Text("Content")).style(corner_radius=pt(0))
    result = compiler.compile_view(square_card)
    background = next(
        node for node in result.drawable.walk() if isinstance(node, DrawableRectangle)
    )

    assert background.corner_radius == pt(0)


def test_component_styles_resolve_their_token_dependencies(compiler):
    inherited = compiler.environment[Card.style_token]
    recolored = compiler.environment.with_token(
        SurfaceColor, SurfaceColor.set(Color("#ABCDEF"))
    )

    assert inherited.background == compiler.environment[SurfaceColor]
    assert recolored[Card.style_token].background == Color("#ABCDEF")


def test_component_style_can_be_replaced_in_a_subtree(compiler):
    inherited = compiler.environment[Card.style_token]
    compact = Card(Text("Content")).style(
        replace(inherited, padding=pt(3), corner_radius=pt(1))
    )
    result = compiler.compile_view(compact)
    background = next(
        node for node in result.drawable.walk() if isinstance(node, DrawableRectangle)
    )

    assert background.corner_radius == pt(1)


def test_partial_component_style_rejects_invalid_usage(compiler):
    card = Card(Text("Content"))
    inherited = compiler.environment[Card.style_token]

    with pytest.raises(TypeError, match="unexpected keyword"):
        compiler.compile_view(card.style(unknown=pt(1)))
    with pytest.raises(TypeError, match="either a complete style or keyword fields"):
        card.style(inherited, padding=pt(1))


def test_standard_color_modifiers_use_the_active_token_scope(compiler):
    result = compiler.compile_view(
        Rectangle()
        .foreground_style(AccentColor)
        .with_token(AccentColor, AccentColor.set(Color("#AA00CC")))
    )

    assert result.drawable.children[0].color == "#AA00CC"
