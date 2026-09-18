from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import pytest

from deckkit.backends import pptx, svg
from deckkit.identity import ViewIdentity
from deckkit.layout import (
    Constraints,
    Layout,
    LayoutContext,
    LayoutEngine,
    LayoutOverflow,
    LayoutPlan,
    Placement,
)
from deckkit.layouts import StackLayout
from deckkit.units import Length, pt
from deckkit.view_expansion import expand_view
from deckkit.views import Context, LayoutView, Rectangle, State, Text, View


@dataclass(frozen=True, init=False)
class CustomLayoutView(LayoutView):
    layout: Layout

    def __init__(self, layout: Layout, *children: View | None) -> None:
        object.__setattr__(self, "layout", layout)
        super().__init__(*children)

    def resolve_layout(self, lookup: Callable[[str], ViewIdentity]) -> Layout:
        return self.layout


@dataclass(frozen=True)
class DiagonalLayout:
    """A user policy with no layout, node-kind or backend knowledge."""

    inset: Length = field(default_factory=lambda: pt(12))

    def measure(self, constraints, children, context):
        placements = []
        width = height = pt(0)
        for i, child in enumerate(children):
            offset = i * self.inset
            plan = child.measure(
                Constraints(
                    constraints.max_width - offset, constraints.max_height - offset
                )
            )
            # Identical proposals return the already measured plan.
            assert plan is child.measure(
                Constraints(
                    constraints.max_width - offset, constraints.max_height - offset
                )
            )
            placements.append(Placement(child, plan, offset, offset))
            width = max(width, offset + plan.width)
            height = max(height, offset + plan.height)
        return LayoutPlan(width, height, tuple(placements))


def test_custom_layout_through_both_backends(compiler, tmp_path):
    from pptx import Presentation

    view = CustomLayoutView(
        DiagonalLayout(),
        Rectangle().frame(width=pt(30), height=pt(20)).key("box"),
        Text("Custom layout").key("label"),
    ).padding(pt(10))
    result = compiler.compile_view(view)
    first, second = result.drawable.children[0].children
    assert (first.bounds.x, first.bounds.y) == (pt(10), pt(10))
    assert (second.bounds.x, second.bounds.y) == (pt(22), pt(22))
    assert "Custom layout" in svg.render(result.drawable)
    target = tmp_path / "custom.pptx"
    from deckkit import CompiledDeck

    pptx.render(CompiledDeck.from_views(result), target)
    assert len(Presentation(target).slides[0].shapes) == 2


def test_placement_does_not_remeasure(compiler):
    class CountingMeasurer:
        calls = 0

        def measure(self, *args):
            self.calls += 1
            return compiler.measurer.measure(*args)

    measurer = CountingMeasurer()
    view = CustomLayoutView(DiagonalLayout(), Text("Once"))
    tree = expand_view(view, Context(State(), compiler.environment))
    assert measurer.calls == 0
    context = LayoutContext(measurer, compiler.font_resolver)
    LayoutEngine(context).layout_view(tree)
    assert measurer.calls == 1
    # Cache belongs to this compilation, not mutable global layout state.
    LayoutEngine(context).layout_view(tree)
    assert measurer.calls == 2


def test_vertical_flex_allocation(compiler):
    view = CustomLayoutView(
        StackLayout("vertical", pt(10)),
        Rectangle().frame(width=pt(30), height=pt(50)),
        Rectangle().flex(),
        Rectangle().flex(2),
    )
    layout = compiler.compile_view(view).drawable
    fixed, one, two = layout.children[0].children
    assert fixed.bounds.height == pt(50)
    assert two.bounds.height.points == pytest.approx(one.bounds.height.points * 2)
    assert (two.bounds.y + two.bounds.height).points == pytest.approx(
        layout.bounds.height.points
    )


def test_bad_custom_placement_is_diagnosed(compiler):
    class BadLayout:
        def measure(self, c, children, context):
            plan = children[0].measure(c)
            return LayoutPlan(
                plan.width, plan.height, (Placement(children[0], plan, pt(20), pt(0)),)
            )

    with pytest.raises(LayoutOverflow) as error:
        compiler.compile_view(CustomLayoutView(BadLayout(), Text("Outside")))
    assert error.value.identity.endswith("test_layout_policies.CustomLayoutView")


def test_modifier_overflow_has_component_identity(compiler):
    with pytest.raises(LayoutOverflow) as error:
        compiler.compile_view(
            Text("No space").key("title").frame(width=pt(1)).padding(pt(5))
        )
    assert "key:title:" in error.value.identity
