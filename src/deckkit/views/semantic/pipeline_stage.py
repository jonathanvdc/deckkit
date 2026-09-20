"""A semantic view representing one stage in a pipeline."""

from __future__ import annotations

from dataclasses import dataclass

from ...context import Context
from ...theme import Color, ColorStyle, PrimaryColor, SpacingUnit, SurfaceColor
from ...tokens import DesignToken, TokenResolver
from ...units import Length
from ..rectangle import Rectangle
from ..view import View
from ..zstack import ZStack
from .semantic_view import SemanticView


@dataclass(frozen=True)
class PipelineStage(SemanticView):
    """Display a labeled stage suitable for use in a :class:`Pipeline`.

    Args:
        label: Arbitrary view content shown inside the stage.
        emphasis: Foreground style applied to the label by the default recipe.
    """

    @dataclass(frozen=True)
    class Style:
        background: DesignToken[Color]
        foreground: DesignToken[Color]
        padding: Length

    @staticmethod
    def _default_style(values: TokenResolver) -> Style:
        return PipelineStage.Style(SurfaceColor, PrimaryColor, values[SpacingUnit] * 5)

    style_token = DesignToken[Style](
        "component.pipeline-stage",
        lambda values: PipelineStage._default_style(values),
        value_type=Style,
    )

    label: View
    emphasis: ColorStyle | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.label, View):
            raise TypeError(
                "PipelineStage.label must be a View; wrap text in Text(...)"
            )

    def body(self, context: Context) -> View:
        """Place the padded label over a themed surface rectangle."""
        style = context.environment[self.style_token]
        return ZStack(
            Rectangle().foreground_style(style.background),
            self.label.foreground_style(self.emphasis or style.foreground).padding(
                style.padding
            ),
        )
