"""API-first examples A–G; implemented subset except the clearly marked video sketch."""

from dataclasses import dataclass
from deckkit import *
from deckkit.views.semantic import BeforeAfter, Metric, Stage


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


class PipelineSlide(Slide):
    def body(self, context):
        step = context.state.get("step", 0)
        return VStack(
            Text("A simpler lowering pipeline").font("title"),
            Annotated(
                HStack(
                    Stage(Text("Parse"), "primary" if step == 0 else "muted").key(
                        "parse"
                    ),
                    Stage(Text("Optimize"), "primary" if step == 1 else "muted").key(
                        "opt"
                    ),
                    spacing=pt(32),
                ),
                Connector(
                    Anchor("parse", RelativePoint.trailing),
                    Anchor("opt", RelativePoint.leading),
                ),
            ),
            Text("Three passes disappear").key("annotation").transition("opacity")
            if step >= 2
            else None,
            spacing=pt(28),
        ).padding(pt(40))


@dataclass(frozen=True)
class Chart(CompositeView):
    """Placeholder composition, not a charting engine."""

    def body(self, context):
        return ZStack(
            Rectangle().foreground_style("surface"),
            Text("Compilation throughput").font("body"),
        ).frame(height=pt(230))


class ResultsSlide(Slide):
    def body(self, context):
        return VStack(
            Text("Compiler performance").font("title"),
            HStack(
                Chart().key("results").flex().animation("smooth").animation_boundary(),
                Metric(Text("2.7×"), Text("Throughput"))
                .key("throughput")
                .transition("opacity")
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
