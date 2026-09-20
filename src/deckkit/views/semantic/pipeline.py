"""A semantic view for a connected sequence of pipeline stages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from ...annotations import Anchor, Annotated, Annotation, Connector
from ...context import Context
from ...geometry import RelativePoint
from ...theme import Color, ColorStyle, PrimaryColor, SpacingUnit
from ...tokens import DesignToken, TokenResolver
from ...units import Length, require_length
from ..hstack import HStack
from ..view import View
from .pipeline_stage import PipelineStage
from .semantic_view import SemanticView


@dataclass(frozen=True, init=False)
class Pipeline(SemanticView):
    """Lay out pipeline stages and connect each adjacent pair.

    Stages are assigned stable generated keys unless they already have explicit
    keys. These keys anchor the connectors produced by the default recipe. Extra
    annotations are layered onto the same content and may refer to explicit or
    generated stage keys.

    Args:
        *stages: One or more stages in display order.
        spacing: Horizontal distance between adjacent stages.
        annotations: Additional annotations to render with the pipeline.
        connector_style: Theme style applied to generated connectors.

    Raises:
        ValueError: If no stages are supplied or spacing is negative.
        TypeError: If stages, annotations, or spacing have invalid types.
    """

    @dataclass(frozen=True)
    class Style:
        spacing: Length
        connector: DesignToken[Color]

    @staticmethod
    def _default_style(values: TokenResolver) -> Style:
        return Pipeline.Style(values[SpacingUnit] * 8, PrimaryColor)

    style_token = DesignToken[Style](
        "component.pipeline",
        lambda values: Pipeline._default_style(values),
        value_type=Style,
    )

    stages: tuple[PipelineStage, ...]
    spacing: Length | None
    annotations: tuple[Annotation, ...]
    connector_style: ColorStyle | None

    def __init__(
        self,
        *stages: PipelineStage,
        spacing: Length | None = None,
        annotations: tuple[Annotation, ...] = (),
        connector_style: ColorStyle | None = None,
    ) -> None:
        if not stages:
            raise ValueError("Pipeline requires at least one PipelineStage")
        if not all(isinstance(stage, PipelineStage) for stage in stages):
            raise TypeError("Pipeline children must be PipelineStage instances")
        if not all(isinstance(annotation, Annotation) for annotation in annotations):
            raise TypeError("Pipeline annotations must inherit Annotation")
        if spacing is not None:
            require_length(spacing)
            if spacing.points < 0:
                raise ValueError("Pipeline spacing must be non-negative")
        object.__setattr__(self, "stages", tuple(stages))
        object.__setattr__(self, "spacing", spacing)
        object.__setattr__(self, "annotations", tuple(annotations))
        object.__setattr__(self, "connector_style", connector_style)

    def body(self, context: Context) -> View:
        """Arrange stages horizontally and connect adjacent stage anchors."""
        style = context.environment[self.style_token]
        keyed_stages: list[PipelineStage] = []
        keys: list[str] = []
        for index, stage in enumerate(self.stages):
            modifiers = dict(stage._modifiers)
            key = (
                cast(str, modifiers["key"])
                if "key" in modifiers
                else f"pipeline-stage-{index}"
            )
            keys.append(key)
            keyed_stages.append(stage if "key" in modifiers else stage.key(key))

        spacing = self.spacing if self.spacing is not None else style.spacing
        connector_style = (
            self.connector_style
            if self.connector_style is not None
            else style.connector
        )
        content: View = HStack(*keyed_stages, spacing=spacing)
        connectors = tuple(
            Connector(
                Anchor(start, RelativePoint.right),
                Anchor(end, RelativePoint.left),
                style=connector_style,
            )
            for start, end in zip(keys, keys[1:])
        )
        return Annotated(content, *connectors, *self.annotations)
