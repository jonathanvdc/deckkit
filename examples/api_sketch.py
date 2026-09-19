"""API-first examples A–G; implemented subset except the clearly marked video sketch."""

from dataclasses import dataclass

from deckkit.animation import Animation, FallbackPolicy, SlideTimeline, Transition
from deckkit.annotations import Anchor, Connector, Label
from deckkit.geometry import RelativePoint
from deckkit.units import pt
from deckkit.views import (
    Code,
    CompositeView,
    HStack,
    Rectangle,
    Slide,
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


class MetricsSlide(Slide):
    def body(self, context):
        return VStack(
            Text("Compiler performance").font("title"),
            HStack(
                Metric(Text("2.7×"), Text("Throughput")),
                Metric(Text("−38%"), Text("Compile time")),
                Metric(Text("−22%"), Text("Memory")),
                spacing=pt(32),
            ),
            spacing=pt(36),
        ).padding(pt(40))


class ComparisonSlide(Slide):
    def body(self, context):
        return BeforeAfter(
            Text("A simpler lowering pipeline"),
            Text("Parse · Lower · Optimize"),
            Text("Parse · Optimize"),
            Text("Three intermediate passes disappear."),
        ).padding(pt(40))


class CodeSlide(Slide):
    def body(self, context):
        return VStack(
            Text("Language-aware code styling").font("title"),
            CodeBlock(
                Code.highlight(
                    "def optimize(module):\n"
                    '    passes = ["lower", "simplify"]\n'
                    "    return run(module, passes)",
                    language="python",
                )
            ).frame(width=pt(760)),
            Text("Token scopes resolve through the active theme.")
            .font("caption")
            .foreground_style("muted"),
            spacing=pt(28),
        ).padding(pt(40))


class PipelineSlide(Slide):
    def timeline(self):
        return SlideTimeline.steps(3)

    def body(self, context):
        step = context.state.get("step", 0)
        return VStack(
            Text("A simpler lowering pipeline").font("title"),
            Pipeline(
                PipelineStage(Text("Parse"), "primary" if step == 0 else "muted").key(
                    "parse"
                ),
                PipelineStage(
                    Text("Optimize"), "primary" if step == 1 else "muted"
                ).key("opt"),
                annotations=(
                    Connector(
                        Anchor("opt", RelativePoint.bottom),
                        Anchor("result-label", RelativePoint.top),
                        end_cap="none",
                        style="accent",
                    ),
                    Label(
                        Anchor("opt", RelativePoint.bottom, offset_y=pt(24)),
                        Text("Final IR").key("result-label").foreground_style("accent"),
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
        ).padding(pt(40))


@dataclass(frozen=True)
class Chart(CompositeView):
    """Placeholder composition, not a charting engine."""

    def body(self, context):
        return ZStack(
            Rectangle(corner_radius=pt(16)).foreground_style("surface"),
            Text("Compilation throughput").font("body"),
        ).frame(height=pt(230))


class ResultsSlide(Slide):
    def timeline(self):
        return SlideTimeline.steps(2)

    def body(self, context):
        return VStack(
            Text("Compiler performance").font("title"),
            HStack(
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
            ),
            spacing=pt(32),
        ).padding(pt(40))


# G: future API sketch, intentionally not an implemented media runtime:
# Video("demo.mp4", time=context.state["demo_clock"]).key("demo")
# State(step=1, demo_clock=4.25) and State(step=1, demo_clock=4.50)
# are distinct snapshots with the same presenter step.
