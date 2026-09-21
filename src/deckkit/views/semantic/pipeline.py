"""A semantic view for a connected sequence of pipeline stages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from ...annotations import Anchor, Annotated, Annotation, Connector
from ...context import Context
from ...geometry import RelativePoint
from ...theme import Color, PrimaryColor, SpacingUnit
from ...tokens import DesignToken, TokenResolver
from ...units import Length
from ..hstack import HStack
from ..view import View
from .pipeline_stage import PipelineStage
from .semantic_view import StyledSemanticView


@dataclass(frozen=True, init=False)
class Pipeline(StyledSemanticView["Pipeline.Style"]):
    """Lay out pipeline stages and connect each adjacent pair.

    Stages are assigned stable generated keys unless they already have explicit
    keys. These keys anchor the connectors produced by the default recipe. Extra
    annotations are layered onto the same content and may refer to explicit or
    generated stage keys.

    Args:
        *stages: One or more stages in display order.
        annotations: Additional annotations to render with the pipeline.

    Raises:
        ValueError: If no stages are supplied.
        TypeError: If stages or annotations have invalid types.
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
    annotations: tuple[Annotation, ...]

    def __init__(
        self,
        *stages: PipelineStage,
        annotations: tuple[Annotation, ...] = (),
    ) -> None:
        if not stages:
            raise ValueError("Pipeline requires at least one PipelineStage")
        if not all(isinstance(stage, PipelineStage) for stage in stages):
            raise TypeError("Pipeline children must be PipelineStage instances")
        if not all(isinstance(annotation, Annotation) for annotation in annotations):
            raise TypeError("Pipeline annotations must inherit Annotation")
        object.__setattr__(self, "stages", tuple(stages))
        object.__setattr__(self, "annotations", tuple(annotations))

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

        content: View = HStack(*keyed_stages, spacing=style.spacing)
        connectors = tuple(
            Connector(
                Anchor(start, RelativePoint.right),
                Anchor(end, RelativePoint.left),
                style=style.connector,
            )
            for start, end in zip(keys, keys[1:])
        )
        return Annotated(content, *connectors, *self.annotations)
