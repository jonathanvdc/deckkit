"""Static API contract checks, run by mypy rather than pytest."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Callable, Optional

from typing_extensions import assert_type

from deckkit import CompiledDeck, CompiledSlide, CompiledView, Compiler, Deck
from deckkit.animation import Animation, SlideTimeline
from deckkit.annotations import Anchor, Annotated, Connector
from deckkit.drawables import Drawable
from deckkit.fonts import Font
from deckkit.geometry import RelativePoint
from deckkit.identity import ViewIdentity
from deckkit.layout import (
    Layout,
    LayoutChild,
    LayoutContext,
    LayoutPlan,
    Placement,
    ProposedSize,
)
from deckkit.themes import (
    AccentColor,
    BaseFont,
    CodeTokenStyle,
    DesignToken,
    Theme,
    TitleTextStyle,
)
from deckkit.units import Length, cm, inch, pt
from deckkit.views import (
    Code,
    CodeHighlighter,
    CodeLine,
    CodeSpan,
    CompositeView,
    Context,
    HStack,
    LayoutView,
    PygmentsHighlighter,
    Rectangle,
    Slide,
    Text,
    TextLine,
    TextSpan,
    View,
)
from deckkit.views.semantic import (
    Card,
    CodeBlock,
    Metric,
    Pill,
    Pipeline,
    PipelineStage,
)


class CustomLayout:
    def measure(
        self,
        constraints: ProposedSize,
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


CustomEnvironmentValue = DesignToken[int]("custom.environment-value", lambda values: 0)


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
    assert_type(compiler.environment[CustomEnvironmentValue], int)
    custom_spacing = DesignToken[Length]("custom.spacing", lambda values: pt(4))
    assert_type(compiler.environment[custom_spacing], Length)
    assert_type(compiler.environment[BaseFont], Font)
    text = (
        Text("Hello").font(TitleTextStyle).padding().frame(width=pt(100)).key("title")
    )
    assert_type(text, View)
    assert_type(Text("    code", flow="verbatim"), Text)
    assert_type(
        Text(
            TextLine(
                TextSpan("def", foreground_style=AccentColor),
                TextSpan(" greet(name):"),
            ),
            flow="verbatim",
        ),
        Text,
    )
    assert_type(
        Text("Custom").with_token(
            CustomEnvironmentValue, CustomEnvironmentValue.set(1)
        ),
        Text,
    )
    assert_type(
        Text("Themed").with_token(custom_spacing, custom_spacing.set(pt(8))), Text
    )
    Text("Invalid").with_token(
        CustomEnvironmentValue,
        CustomEnvironmentValue.set("wrong"),  # type: ignore[arg-type]
    )
    assert_type(
        Metric(Text("2.7×"), Text("Throughput")).animation(Animation.smooth()),
        Metric,
    )
    assert_type(Pill(HStack(Text("New"), Text("label"))), Pill)
    assert_type(Card(HStack(Text("Heading"), Text("content"))), Card)
    card = Card(Text("Content"))
    style = compiler.environment[Card.style_token]
    assert_type(style, Card.Style)
    assert_type(card.with_style(style), Card)
    assert_type(
        card.transform_style(lambda style: assert_type(style, Card.Style)), Card
    )
    pill_style = compiler.environment[Pill.style_token]
    card.with_style(pill_style)  # type: ignore[arg-type]
    assert_type(
        Code(
            CodeLine(
                CodeSpan("def", token="keyword.declaration"),
                " greet():",
            ),
            language="python",
        ),
        Code,
    )
    assert_type(CodeTokenStyle(foreground_style=AccentColor), CodeTokenStyle)
    assert_type(CodeBlock(Code("print('hello')")), CodeBlock)
    highlighter: CodeHighlighter = PygmentsHighlighter()
    assert_type(
        Code.highlight("def greet(): pass", language="python"),
        Code,
    )
    assert_type(
        Code.highlight("custom", language="custom", highlighter=highlighter),
        Code,
    )
    assert_type(
        Pipeline(PipelineStage(Text("Parse")), PipelineStage(Text("Optimize"))),
        Pipeline,
    )
    assert_type(
        Pipeline(PipelineStage(Text("Parse"))).padding(pt(4)),
        View,
    )
    assert_type(CustomView().padding(), View)
    assert_type(
        Annotated(
            Rectangle().key("box"),
            Connector(
                Anchor("box", RelativePoint.left),
                Anchor("box", RelativePoint.right),
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
    assert_type(ProposedSize(inch(1), cm(2.54)).width, Optional[Length])
    # These expected failures guard against accidentally widening the API.
    Text("Bare floats are invalid").padding(16)  # type: ignore[arg-type]
    pt(12) + 3  # type: ignore[operator]
    pt(12) * pt(2)  # type: ignore[operator]
