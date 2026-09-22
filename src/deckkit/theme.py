from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from math import isfinite
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, ClassVar, TypeVar, Union, cast

from typing_extensions import TypeAlias

from .fonts import Font
from .tokens import DesignToken, TokenAssignment, TokenResolver
from .units import Length, pt, require_length

if TYPE_CHECKING:
    from .context import Context
    from .views import View
    from .views.semantic import SemanticView

F = TypeVar("F", bound=Callable[..., object])
_SEMANTIC_COMPONENT = "__deckkit_semantic_component__"


def semantic_renderer(component_type: type[object]) -> Callable[[F], F]:
    """Register a theme method as the renderer for a semantic component type."""
    if not isinstance(component_type, type):
        raise TypeError("Semantic renderer targets must be component types")

    def decorate(renderer: F) -> F:
        setattr(renderer, _SEMANTIC_COMPONENT, component_type)
        return renderer

    return decorate


@dataclass(frozen=True)
class Typography:
    """A typography role's font face, physical size and line-height multiplier.

    Font weight/style are selected by the font file, without synthetic styling.
    """

    font: Font
    size: Length
    line_spacing: float = 1.1

    def __post_init__(self) -> None:
        if not isinstance(self.font, Font):
            raise TypeError(
                "Typography.font must be a Font request; configure files on FileFontResolver"
            )
        require_length(self.size)
        if self.size <= pt(0):
            raise ValueError("Font size must be positive")
        if not isfinite(self.line_spacing) or self.line_spacing <= 0:
            raise ValueError("Line spacing must be finite and positive")


@dataclass(frozen=True, init=False)
class Color:
    """A normalized RGB color, distinct from a semantic color token.

    Channels are stored as floats from zero through one. Construct with normalized
    channels or an RGB hex string; rendering converts back to hex only at the
    backend boundary.
    """

    red: float
    green: float
    blue: float

    def __init__(
        self,
        red: float | str,
        green: float | None = None,
        blue: float | None = None,
    ) -> None:
        if isinstance(red, str):
            if green is not None or blue is not None:
                raise TypeError("Hex Color construction does not accept RGB channels")
            parsed = type(self).from_hex(red)
            channels = (parsed.red, parsed.green, parsed.blue)
        else:
            if green is None or blue is None:
                raise TypeError("RGB Color construction requires all three channels")
            channels = (float(red), float(green), float(blue))
        if any(not isfinite(channel) or not 0 <= channel <= 1 for channel in channels):
            raise ValueError(
                "Color channels must be finite values from zero through one"
            )
        object.__setattr__(self, "red", channels[0])
        object.__setattr__(self, "green", channels[1])
        object.__setattr__(self, "blue", channels[2])

    @classmethod
    def from_hex(cls, value: str) -> Color:
        """Parse ``#RRGGBB`` into normalized RGB channels."""
        if not isinstance(value, str) or not value.startswith("#") or len(value) != 7:
            raise ValueError("Color hex values must use #RRGGBB notation")
        try:
            channels = tuple(
                int(value[index : index + 2], 16) / 255 for index in (1, 3, 5)
            )
        except ValueError:
            raise ValueError("Color hex values must use #RRGGBB notation") from None
        result = object.__new__(cls)
        object.__setattr__(result, "red", channels[0])
        object.__setattr__(result, "green", channels[1])
        object.__setattr__(result, "blue", channels[2])
        return result

    def to_hex(self) -> str:
        """Return a canonical uppercase ``#RRGGBB`` representation."""
        channels = (self.red, self.green, self.blue)
        return "#" + "".join(f"{round(channel * 255):02X}" for channel in channels)

    @property
    def hex(self) -> str:
        """Compatibility shorthand for :meth:`to_hex`."""
        return self.to_hex()

    def interpolate(self, other: Color, amount: float) -> Color:
        """Interpolate between two colors in normalized sRGB component space."""
        if not isinstance(other, Color):
            raise TypeError("Color interpolation requires another Color")
        if not isfinite(amount) or not 0 <= amount <= 1:
            raise ValueError("Color interpolation amount must be from zero through one")
        return Color(
            self.red + (other.red - self.red) * amount,
            self.green + (other.green - self.green) * amount,
            self.blue + (other.blue - self.blue) * amount,
        )

    def mix(self, other: Color, amount: float = 0.5) -> Color:
        """Alias for :meth:`interpolate`, convenient in token computations."""
        return self.interpolate(other, amount)


ColorStyle: TypeAlias = Union[DesignToken[Color], Color]


@dataclass(frozen=True)
class CodeTokenStyle:
    """Optional text-style overrides associated with a code token scope."""

    foreground_style: ColorStyle | None = None
    background_style: ColorStyle | None = None
    font_style: DesignToken[Typography] | None = None


def _positive_length(value: Length) -> None:
    require_length(value)
    if value <= pt(0):
        raise ValueError("Design-token length must be positive")


def _positive_number(value: float) -> None:
    if not isfinite(value) or value <= 0:
        raise ValueError("Design-token scale must be finite and positive")


# Foundational tokens. Themes normally override only a small selection of these;
# semantic and component tokens below recompute from them.
BaseFont = DesignToken[Font]("font.base", value_type=Font)
CodeFont = DesignToken[Font](
    "font.code", lambda values: values[BaseFont], value_type=Font
)
BaseFontSize = DesignToken[Length](
    "type.base-size", value_type=Length, validate=_positive_length
)
TypeScale = DesignToken[float](
    "type.scale", lambda values: 1.0, value_type=(int, float), validate=_positive_number
)
LineSpacing = DesignToken[float](
    "type.line-spacing",
    lambda values: 1.1,
    value_type=(int, float),
    validate=_positive_number,
)
SpacingUnit = DesignToken[Length](
    "spacing.unit", value_type=Length, validate=_positive_length
)
RadiusScale = DesignToken[float](
    "radius.scale",
    lambda values: 1.0,
    value_type=(int, float),
    validate=_positive_number,
)

PrimaryColor = DesignToken[Color]("color.primary", value_type=Color)
MutedColor = DesignToken[Color]("color.muted", value_type=Color)
SurfaceColor = DesignToken[Color]("color.surface", value_type=Color)
AccentColor = DesignToken[Color]("color.accent", value_type=Color)
OnAccentColor = DesignToken[Color]("color.on-accent", value_type=Color)

BodyTextStyle = DesignToken[Typography](
    "text.body",
    lambda values: Typography(
        values[BaseFont], values[BaseFontSize], values[LineSpacing]
    ),
    value_type=Typography,
)
TitleTextStyle = DesignToken[Typography](
    "text.title",
    lambda values: Typography(
        values[BaseFont],
        values[BaseFontSize] * (1.6 * values[TypeScale]),
        values[LineSpacing],
    ),
    value_type=Typography,
)
CaptionTextStyle = DesignToken[Typography](
    "text.caption",
    lambda values: Typography(
        values[BaseFont],
        values[BaseFontSize] * (0.8 * values[TypeScale]),
        values[LineSpacing],
    ),
    value_type=Typography,
)
ChartTickTextStyle = DesignToken[Typography](
    "chart.text.tick",
    lambda values: Typography(
        values[BaseFont],
        values[BaseFontSize] * (0.7 * values[TypeScale]),
        values[LineSpacing],
    ),
    value_type=Typography,
)
ChartAxisTitleTextStyle = DesignToken[Typography](
    "chart.text.axis-title",
    lambda values: Typography(
        values[BaseFont],
        values[BaseFontSize] * (0.8 * values[TypeScale]),
        values[LineSpacing],
    ),
    value_type=Typography,
)
ChartLegendTextStyle = DesignToken[Typography](
    "chart.text.legend",
    lambda values: values[ChartTickTextStyle],
    value_type=Typography,
)
ChartDataLabelTextStyle = DesignToken[Typography](
    "chart.text.data-label",
    lambda values: values[ChartTickTextStyle],
    value_type=Typography,
)
MetricTextStyle = DesignToken[Typography](
    "text.metric",
    lambda values: Typography(
        values[BaseFont],
        values[BaseFontSize] * (2.3 * values[TypeScale]),
        values[LineSpacing],
    ),
    value_type=Typography,
)
CodeTextStyle = DesignToken[Typography](
    "text.code",
    lambda values: Typography(
        values[CodeFont],
        values[BaseFontSize] * (0.9 * values[TypeScale]),
        values[LineSpacing],
    ),
    value_type=Typography,
)
TextStyle = DesignToken[Typography](
    "environment.text-style",
    lambda values: values[BodyTextStyle],
    value_type=Typography,
)
ForegroundColor = DesignToken[Color](
    "environment.foreground-color",
    lambda values: values[PrimaryColor],
    value_type=Color,
)
ChartAxisColor = DesignToken[Color](
    "chart.color.axis", lambda values: values[MutedColor], value_type=Color
)
ChartGridColor = DesignToken[Color](
    "chart.color.grid",
    lambda values: values[MutedColor].mix(values[SurfaceColor], 0.65),
    value_type=Color,
)


class Theme:
    """Root configuration for an extensible graph of design tokens."""

    code_styles: ClassVar[Mapping[str, CodeTokenStyle]] = MappingProxyType({})
    _semantic_renderers: ClassVar[Mapping[type[object], Callable[..., object]]] = (
        MappingProxyType({})
    )

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        renderers: dict[type[object], Callable[..., object]] = {}
        for base in reversed(cls.__mro__[1:]):
            renderers.update(getattr(base, "_semantic_renderers", {}))
        for value in cls.__dict__.values():
            component_type = getattr(value, _SEMANTIC_COMPONENT, None)
            if component_type is not None:
                renderers[component_type] = cast(Callable[..., object], value)
        cls._semantic_renderers = MappingProxyType(renderers)

    def __init__(
        self,
        overrides: Mapping[DesignToken[Any], TokenAssignment[Any]] | None = None,
    ) -> None:
        self._token_overrides = MappingProxyType(dict(overrides or {}))

    def token_overrides(self) -> dict[DesignToken[Any], TokenAssignment[Any]]:
        """Return root values for the open-ended design-token graph."""
        return dict(self._token_overrides)

    def token_resolver(self) -> TokenResolver:
        """Create the root token-resolution scope for this theme."""
        return TokenResolver(self.token_overrides())

    def code_style(self, language: str | None, token: str | None) -> CodeTokenStyle:
        """Resolve cascading language and token scopes to presentation roles."""
        token_parts = token.split(".") if token else []
        keys = ["plain"]
        keys.extend(
            ".".join(token_parts[:end]) for end in range(1, len(token_parts) + 1)
        )
        if language:
            keys.append(language)
            keys.extend(
                f"{language}.{'.'.join(token_parts[:end])}"
                for end in range(1, len(token_parts) + 1)
            )
        result = CodeTokenStyle()
        for key in keys:
            override = self.code_styles.get(key)
            if override is not None:
                result = CodeTokenStyle(
                    override.foreground_style or result.foreground_style,
                    override.background_style or result.background_style,
                    override.font_style or result.font_style,
                )
        return result

    def render_semantic(self, component: SemanticView, context: Context) -> View | None:
        """Optionally override a component; None selects its default composition."""
        for component_type in type(component).__mro__:
            renderer = self._semantic_renderers.get(component_type)
            if renderer is not None:
                return cast("View", renderer(self, component, context))
        return None
