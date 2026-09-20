"""API-first examples A–G; implemented subset except the clearly marked video sketch."""

from dataclasses import dataclass

from deckkit.animation import Animation, FallbackPolicy, SlideTimeline, Transition
from deckkit.annotations import Anchor, Connector, Label
from deckkit.geometry import RelativePoint
from deckkit.themes import (
    AccentColor,
    BodyTextStyle,
    CaptionTextStyle,
    MutedColor,
    PrimaryColor,
    SurfaceColor,
)
from deckkit.units import pt
from deckkit.views import (
    Code,
    CompositeView,
    HStack,
    Rectangle,
    Text,
    VStack,
    ZStack,
)
from deckkit.views.semantic import (
    BeforeAfter,
    CodeBlock,
    Metric,
    Pipeline,
    PipelineStage,
)
from deckkit.views.slides import TitleAndContentSlide


class MetricsSlide(TitleAndContentSlide):
    @property
    def title(self):
        return Text("Compiler performance")

    def content(self, context):
        return HStack(
            Metric(Text("2.7×"), Text("Throughput")),
            Metric(Text("−38%"), Text("Compile time")),
            Metric(Text("−22%"), Text("Memory")),
            spacing=pt(32),
        )


class ComparisonSlide(TitleAndContentSlide):
    @property
    def title(self):
        return Text("A simpler lowering pipeline")

    def content(self, context):
        return BeforeAfter(
            Text("Parse · Lower · Optimize"),
            Text("Parse · Optimize"),
            Text("Three intermediate passes disappear."),
        )


class CodeSlide(TitleAndContentSlide):
    @property
    def title(self):
        return Text("Language-aware code styling")

    def content(self, context):
        return VStack(
            CodeBlock(
                Code.highlight(
                    "def optimize(module):\n"
                    '    passes = ["lower", "simplify"]\n'
                    "    return run(module, passes)",
                    language="python",
                )
            ).frame(width=pt(760)),
            Text("Token scopes resolve through the active theme.")
            .font(CaptionTextStyle)
            .foreground_style(MutedColor),
            spacing=pt(28),
        )


class PipelineSlide(TitleAndContentSlide):
    @property
    def title(self):
        return Text("A simpler lowering pipeline")

    def timeline(self):
        return SlideTimeline.steps(3)

    def content(self, context):
        step = context.state.get("step", 0)
        return VStack(
            Pipeline(
                PipelineStage(
                    Text("Parse"), PrimaryColor if step == 0 else MutedColor
                ).key("parse"),
                PipelineStage(
                    Text("Optimize"), PrimaryColor if step == 1 else MutedColor
                ).key("opt"),
                annotations=(
                    Connector(
                        Anchor("opt", RelativePoint.bottom),
                        Anchor("result-label", RelativePoint.top),
                        end_cap="none",
                        style=AccentColor,
                    ),
                    Label(
                        Anchor("opt", RelativePoint.bottom, offset_y=pt(24)),
                        Text("Final IR")
                        .key("result-label")
                        .foreground_style(AccentColor),
                        alignment=RelativePoint.center,
                    ),
                ),
            ),
            Text("Three passes disappear")
            .key("annotation")
            .transition(Transition.fade())
            if step >= 2
            else None,
            spacing=pt(28),
        )


@dataclass(frozen=True)
class Chart(CompositeView):
    """Placeholder composition, not a charting engine."""

    def body(self, context):
        return ZStack(
            Rectangle(corner_radius=pt(16)).foreground_style(SurfaceColor),
            Text("Compilation throughput").font(BodyTextStyle),
        ).frame(height=pt(230))


class ResultsSlide(TitleAndContentSlide):
    @property
    def title(self):
        return Text("Compiler performance")

    def timeline(self):
        return SlideTimeline.steps(2)

    def content(self, context):
        return HStack(
            Chart()
            .key("results")
            .flex()
            .animation(Animation.smooth(fallback=FallbackPolicy.DISCRETE))
            .animation_boundary(),
            Metric(Text("2.7×"), Text("Throughput"))
            .key("throughput")
            .transition(Transition.fade())
            if context.state.get("step", 0)
            else None,
            spacing=pt(24),
        )


# G: future API sketch, intentionally not an implemented media runtime:
# Video("demo.mp4", time=context.state["demo_clock"]).key("demo")
# State(step=1, demo_clock=4.25) and State(step=1, demo_clock=4.50)
# are distinct snapshots with the same presenter step.
