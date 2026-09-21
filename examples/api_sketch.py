"""API-first examples A–G; implemented subset except the clearly marked video sketch."""

from dataclasses import dataclass

from deckkit.animation import Animation, FallbackPolicy, SlideTimeline, Transition
from deckkit.annotations import Anchor, Connector, Label
from deckkit.canvas import (
    CanvasContext,
    CanvasScene,
    CanvasSize,
    Ellipse,
    Line,
    LineTo,
    MoveTo,
    Path,
    Rect,
    Stroke,
)
from deckkit.drawables import Bounds
from deckkit.geometry import Point, RelativePoint
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
    Canvas,
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
                PipelineStage(Text("Parse"))
                .style(
                    foreground=context.environment[
                        PrimaryColor if step == 0 else MutedColor
                    ]
                )
                .key("parse"),
                PipelineStage(Text("Optimize"))
                .style(
                    foreground=context.environment[
                        PrimaryColor if step == 1 else MutedColor
                    ]
                )
                .key("opt"),
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


def _canvas_demo(context: CanvasContext, size: CanvasSize) -> CanvasScene:
    """Draw a responsive miniature chart using Canvas-local coordinates."""
    left, top, right, bottom = pt(36), pt(20), pt(20), pt(30)
    plot_width = size.width - left - right
    plot_height = size.height - top - bottom
    baseline = top + plot_height
    values = (0.42, 0.68, 0.91, 0.74)
    slot = plot_width / len(values)
    bar_width = slot * 0.55

    elements = [
        Rect(Bounds(pt(0), pt(0), size.width, size.height), fill=SurfaceColor),
    ]
    for index in range(1, 5):
        y = top + plot_height * (index / 5)
        elements.append(
            Line(
                Point(left, y),
                Point(left + plot_width, y),
                Stroke(MutedColor, pt(1), (pt(3), pt(4))),
            )
        )
    elements.extend(
        (
            Line(
                Point(left, top),
                Point(left, baseline),
                Stroke(PrimaryColor, pt(2)),
            ),
            Line(
                Point(left, baseline),
                Point(left + plot_width, baseline),
                Stroke(PrimaryColor, pt(2)),
            ),
        )
    )

    points = []
    for index, value in enumerate(values):
        x = left + slot * index + (slot - bar_width) / 2
        height = plot_height * value
        y = baseline - height
        center = Point(x + bar_width / 2, y)
        points.append(center)
        elements.append(
            Rect(
                Bounds(x, y, bar_width, height),
                fill=AccentColor,
                corner_radius=pt(5),
                key=f"bar:{index}",
            )
        )

    elements.append(
        Path(
            (MoveTo(points[0]), *(LineTo(point) for point in points[1:])),
            stroke=Stroke(PrimaryColor, pt(3)),
            key="trend",
        )
    )
    elements.extend(
        Ellipse(
            Bounds(point.x - pt(4), point.y - pt(4), pt(8), pt(8)),
            fill=PrimaryColor,
            stroke=Stroke(SurfaceColor, pt(2)),
            key=f"point:{index}",
        )
        for index, point in enumerate(points)
    )
    return CanvasScene(*elements)


class CanvasSlide(TitleAndContentSlide):
    @property
    def title(self):
        return Text("Size-dependent native drawing")

    def content(self, context):
        return VStack(
            Canvas(_canvas_demo).frame(width=pt(760), height=pt(270)),
            Text("Bars, grid lines, points, and the trend path remain native shapes.")
            .font(CaptionTextStyle)
            .foreground_style(MutedColor),
            spacing=pt(18),
        )


# G: future API sketch, intentionally not an implemented media runtime:
# Video("demo.mp4", time=context.state["demo_clock"]).key("demo")
# State(step=1, demo_clock=4.25) and State(step=1, demo_clock=4.50)
# are distinct snapshots with the same presenter step.
