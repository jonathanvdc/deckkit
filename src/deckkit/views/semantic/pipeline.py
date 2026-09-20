"""A semantic view for a connected sequence of pipeline stages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from ...annotations import Anchor, Annotated, Annotation, Connector
from ...context import Context
from ...geometry import RelativePoint
from ...units import Length, pt, require_length
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

    stages: tuple[PipelineStage, ...]
    spacing: Length
    annotations: tuple[Annotation, ...]
    connector_style: str

    def __init__(
        self,
        *stages: PipelineStage,
        spacing: Length = pt(32),
        annotations: tuple[Annotation, ...] = (),
        connector_style: str = "primary",
    ) -> None:
        if not stages:
            raise ValueError("Pipeline requires at least one PipelineStage")
        if not all(isinstance(stage, PipelineStage) for stage in stages):
            raise TypeError("Pipeline children must be PipelineStage instances")
        if not all(isinstance(annotation, Annotation) for annotation in annotations):
            raise TypeError("Pipeline annotations must inherit Annotation")
        require_length(spacing)
        if spacing.points < 0:
            raise ValueError("Pipeline spacing must be non-negative")
        object.__setattr__(self, "stages", tuple(stages))
        object.__setattr__(self, "spacing", spacing)
        object.__setattr__(self, "annotations", tuple(annotations))
        object.__setattr__(self, "connector_style", connector_style)

    def body(self, context: Context) -> View:
        """Arrange stages horizontally and connect adjacent stage anchors."""
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

        content: View = HStack(*keyed_stages, spacing=self.spacing)
        connectors = tuple(
            Connector(
                Anchor(start, RelativePoint.right),
                Anchor(end, RelativePoint.left),
                style=self.connector_style,
            )
            for start, end in zip(keys, keys[1:])
        )
        return Annotated(content, *connectors, *self.annotations)
