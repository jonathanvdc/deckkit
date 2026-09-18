"""Static API contract checks, run by mypy rather than pytest."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Callable

from typing_extensions import assert_type

from deckkit import CompiledDeck, CompiledSlide, CompiledView, Compiler, Deck
from deckkit.animation import Animation, SlideTimeline
from deckkit.annotations import Anchor, Annotated, Connector
from deckkit.drawables import Drawable
from deckkit.geometry import RelativePoint
from deckkit.identity import ViewIdentity
from deckkit.layout import (
    Constraints,
    Layout,
    LayoutChild,
    LayoutContext,
    LayoutPlan,
    Placement,
)
from deckkit.themes import Theme
from deckkit.units import Length, cm, inch, pt
from deckkit.views import (
    CompositeView,
    Context,
    EnvironmentKey,
    HStack,
    LayoutView,
    Rectangle,
    Slide,
    Text,
    View,
)
from deckkit.views.semantic import Card, Metric, Pill, Pipeline, PipelineStage


class CustomLayout:
    def measure(
        self,
        constraints: Constraints,
        children: Sequence[LayoutChild],
        context: LayoutContext,
    ) -> LayoutPlan:
        child = children[0]
        plan = child.measure(constraints)
        return LayoutPlan(plan.width, plan.height, (Placement(child, plan),))


@dataclass(frozen=True, init=False)
class CustomLayoutView(LayoutView):
    policy: Layout

    def __init__(self, policy: Layout, *children: View | None) -> None:
        object.__setattr__(self, "policy", policy)
        super().__init__(*children)

    def resolve_layout(self, lookup: Callable[[str], ViewIdentity]) -> Layout:
        return self.policy


class CustomEnvironmentKey(EnvironmentKey[int]):
    @classmethod
    def default(cls) -> int:
        return 0


class CustomView(CompositeView):
    def body(self, context: Context) -> View:
        assert_type(context.environment.theme, Theme)
        return Text("Typed composition")


class CustomSlide(Slide):
    def timeline(self) -> SlideTimeline:
        return SlideTimeline.steps(2)

    def body(self, context: Context) -> View:
        return Text("Slide")


def check_api(compiler: Compiler) -> None:
    assert_type(compiler.environment.get(CustomEnvironmentKey), int)
    text = Text("Hello").font("title").padding().frame(width=pt(100)).key("title")
    assert_type(text, Text)
    assert_type(Text("Custom").environment(CustomEnvironmentKey, 1), Text)
    Text("Invalid").environment(CustomEnvironmentKey, "wrong")  # type: ignore[misc]
    assert_type(
        Metric(Text("2.7×"), Text("Throughput")).animation(Animation.smooth()),
        Metric,
    )
    assert_type(Pill(HStack(Text("New"), Text("label"))), Pill)
    assert_type(Card(HStack(Text("Heading"), Text("content"))), Card)
    assert_type(
        Pipeline(PipelineStage(Text("Parse")), PipelineStage(Text("Optimize"))),
        Pipeline,
    )
    assert_type(
        Pipeline(PipelineStage(Text("Parse"))).padding(pt(4)),
        Pipeline,
    )
    assert_type(CustomView().padding(), CustomView)
    assert_type(
        Annotated(
            Rectangle().key("box"),
            Connector(
                Anchor("box", RelativePoint.leading),
                Anchor("box", RelativePoint.trailing),
            ),
        ),
        Annotated,
    )
    policy: Layout = CustomLayout()
    result = compiler.compile_view(CustomLayoutView(policy, text, None))
    assert_type(result, CompiledView)
    assert_type(result.drawable, Drawable)
    assert_type(
        compiler.compile_slide(CustomSlide()),
        CompiledSlide,
    )
    deck = Deck([CustomSlide()], theme=compiler.environment.theme)
    assert_type(deck.compile(), CompiledDeck)
    deck.write_pptx("typed.pptx")
    Deck([CustomSlide()])  # type: ignore[call-arg]


def check_lengths() -> None:
    assert_type(inch(1) + cm(2.54), Length)
    assert_type(pt(12) * 2, Length)
    assert_type(pt(12) / 2, Length)
    assert_type(inch(1) / pt(12), float)
    assert_type(Constraints(inch(1), cm(2.54)).max_width, Length)
    # These expected failures guard against accidentally widening the API.
    Text("Bare floats are invalid").padding(16)  # type: ignore[arg-type]
    pt(12) + 3  # type: ignore[operator]
    pt(12) * pt(2)  # type: ignore[operator]
