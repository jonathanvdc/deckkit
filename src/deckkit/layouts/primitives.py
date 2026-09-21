from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ..canvas import CanvasContext, CanvasRenderer, CanvasSize, scene_from
from ..context import Environment
from ..layout import LayoutChild, LayoutContext, LayoutPlan, ProposedSize
from ..measurement import StyledTextLine, TextFlow, layout_styled_text
from ..units import Length, pt
from ._content import content


@dataclass(frozen=True)
class TextLayout:
    styled_lines: tuple[StyledTextLine, ...]
    flow: TextFlow = "wrapped"

    def measure(
        self,
        proposal: ProposedSize,
        children: Sequence[LayoutChild],
        context: LayoutContext,
    ) -> LayoutPlan:
        measured_text = layout_styled_text(
            context.measurer,
            context.font_resolver,
            self.styled_lines,
            proposal.width if proposal.width is not None else pt(1_000_000_000),
            self.flow,
        )
        return content(
            measured_text.width,
            measured_text.height,
            measured_text=measured_text,
            line_width=measured_text.width,
        )


@dataclass(frozen=True)
class ShapeLayout:
    def measure(
        self,
        proposal: ProposedSize,
        children: Sequence[LayoutChild],
        context: LayoutContext,
    ) -> LayoutPlan:
        return content(proposal.width or pt(0), proposal.height or pt(0))


@dataclass(frozen=True)
class CanvasLayout:
    renderer: CanvasRenderer
    environment: Environment

    def measure(
        self,
        proposal: ProposedSize,
        children: Sequence[LayoutChild],
        context: LayoutContext,
    ) -> LayoutPlan:
        width, height = proposal.width or pt(0), proposal.height or pt(0)
        canvas_context = CanvasContext(
            self.environment, context.measurer, context.font_resolver
        )
        scene = scene_from(self.renderer(canvas_context, CanvasSize(width, height)))
        return content(
            width,
            height,
            canvas_context=canvas_context,
            canvas_scene=scene,
        )


@dataclass(frozen=True)
class ImageLayout:
    width: Length
    height: Length
    fit: str = "contain"

    def measure(
        self,
        proposal: ProposedSize,
        children: Sequence[LayoutChild],
        context: LayoutContext,
    ) -> LayoutPlan:
        if (
            self.fit == "cover"
            and proposal.width is not None
            and proposal.height is not None
        ):
            return content(proposal.width, proposal.height)
        width_scale = proposal.width / self.width if proposal.width is not None else 1
        height_scale = (
            proposal.height / self.height if proposal.height is not None else 1
        )
        scale = min(width_scale, height_scale, 1)
        return content(
            self.width * scale,
            self.height * scale,
        )
