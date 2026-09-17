"""Static API contract checks, run by mypy rather than pytest."""

from collections.abc import Sequence

from typing_extensions import assert_type

from deckkit import (
    Anchor,
    Annotated,
    CompiledView,
    Compiler,
    CompositeView,
    Connector,
    Context,
    EnvironmentKey,
    Layout,
    LayoutChild,
    LayoutContext,
    LayoutPlan,
    LayoutView,
    Length,
    Placement,
    Rectangle,
    RelativePoint,
    Text,
    Theme,
    View,
    cm,
    inch,
    pt,
)
from deckkit.layout import Constraints
from deckkit.drawables import Drawable
from deckkit.views.semantic import Metric


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


class CustomEnvironmentKey(EnvironmentKey[int]):
    @classmethod
    def default(cls) -> int:
        return 0


class CustomView(CompositeView):
    def body(self, context: Context) -> View:
        assert_type(context.environment.theme, Theme)
        return Text("Typed composition")


def check_api(compiler: Compiler) -> None:
    assert_type(compiler.environment.get(CustomEnvironmentKey), int)
    text = Text("Hello").font("title").padding().frame(width=pt(100)).key("title")
    assert_type(text, Text)
    assert_type(Text("Custom").environment(CustomEnvironmentKey, 1), Text)
    Text("Invalid").environment(CustomEnvironmentKey, "wrong")  # type: ignore[misc]
    assert_type(Metric(Text("2.7×"), Text("Throughput")).animation("smooth"), Metric)
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
    result = compiler.compile_view(LayoutView(policy, text, None))
    assert_type(result, CompiledView)
    assert_type(result.drawable, Drawable)


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
