from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any

from .animation import (
    Animation,
    AnimationProgram,
    BuildProgram,
    EffectInstance,
    EffectKind,
    SlideTimeline,
    TimelineStep,
    Transition,
    VisualState,
)
from .deck import Deck
from .drawables import Drawable
from .expanded_views import ExpandedView
from .fonts import FontResolver, SystemFontResolver
from .layout import LayoutContext, LayoutEngine
from .measurement import PillowMeasurer, TextMeasurer
from .reconcile import Change, reconcile, with_geometry
from .theme import Theme
from .units import Length, pt, require_length
from .view_expansion import expand_view
from .views import Context, Environment, Slide, State, View


@dataclass(frozen=True)
class CompiledView:
    """One view evaluated for one state, environment and canvas.

    The resolved tree preserves logical identity/properties for reconciliation;
    the layout contains measured text and concrete geometry for export. Both
    artifacts come from the same evaluation. This is not an animation or a
    backend document, and it does not retain the source state or environment.
    """

    expanded_tree: ExpandedView
    drawable: Drawable


@dataclass(frozen=True)
class CompiledDeck:
    """Ordered logical slides, each with zero or more presentation steps."""

    slides: tuple[CompiledSlide, ...]

    @classmethod
    def from_views(cls, *views: CompiledView) -> CompiledDeck:
        """Package already-compiled single views as static logical slides."""
        return cls(
            tuple(CompiledSlide((view,), AnimationProgram(())) for view in views)
        )

    def expanding_steps(self) -> CompiledDeck:
        """Return a static deck containing every animation endpoint as a slide."""
        return CompiledDeck(
            tuple(page for slide in self.slides for page in slide.expanding_steps())
        )


@dataclass(frozen=True)
class CompiledSlide:
    """One logical slide compiled at every presentation-step boundary."""

    states: tuple[CompiledView, ...]
    animation: AnimationProgram

    def __post_init__(self) -> None:
        if not self.states:
            raise ValueError("A compiled slide requires an initial state")
        if len(self.states) != len(self.animation.builds) + 1:
            raise ValueError("Compiled slide states must match its animation steps")

    @property
    def initial(self) -> CompiledView:
        return self.states[0]

    @property
    def is_animated(self) -> bool:
        return bool(self.animation.builds)

    def expanding_steps(self) -> tuple[CompiledSlide, ...]:
        """Represent every endpoint as an independent static logical slide."""
        return tuple(
            CompiledSlide((state,), AnimationProgram(())) for state in self.states
        )


@dataclass(frozen=True)
class _AnimatedDrawable:
    drawable: Drawable
    animation: Animation
    transition: Transition | None


def _animation_index(
    root: Drawable, default: Animation
) -> dict[str, _AnimatedDrawable]:
    result: dict[str, _AnimatedDrawable] = {}

    def visit(
        node: Drawable,
        inherited_animation: Animation,
        inherited_transition: Transition | None,
    ) -> None:
        if node.metadata.animation_boundary:
            inherited_animation = Animation.discrete()
            inherited_transition = None
        animation = (
            node.metadata.animation
            if node.metadata.animation is not None
            else inherited_animation
        )
        transition = node.metadata.transition or inherited_transition
        if not node.children:
            result[node.identity] = _AnimatedDrawable(node, animation, transition)
        for child in node.children:
            visit(child, animation, transition)

    visit(root, default, None)
    return result


def _visual_properties(drawable: Drawable) -> tuple[tuple[str, Any], ...]:
    ignored = {"identity", "bounds", "content_bounds", "metadata", "children"}
    return tuple(
        (item.name, getattr(drawable, item.name))
        for item in fields(drawable)
        if item.name not in ignored
    )


def _compile_build(
    before: CompiledView, after: CompiledView, step: TimelineStep
) -> BuildProgram:
    old = _animation_index(before.drawable, step.animation)
    new = _animation_index(after.drawable, step.animation)
    effects: list[EffectInstance] = []
    for identity in sorted(old.keys() | new.keys()):
        a, b = old.get(identity), new.get(identity)
        if a is None:
            assert b is not None
            effects.append(
                EffectInstance(
                    identity,
                    EffectKind.INSERT,
                    None,
                    VisualState(b.drawable.bounds, b.drawable),
                    animation=b.animation,
                    transition=b.transition,
                )
            )
        elif b is None:
            effects.append(
                EffectInstance(
                    identity,
                    EffectKind.REMOVE,
                    VisualState(a.drawable.bounds, a.drawable),
                    None,
                    animation=a.animation,
                    transition=a.transition,
                )
            )
        else:
            if type(a.drawable) is not type(b.drawable) or _visual_properties(
                a.drawable
            ) != _visual_properties(b.drawable):
                effects.append(
                    EffectInstance(
                        identity,
                        EffectKind.CHANGE,
                        VisualState(a.drawable.bounds, a.drawable),
                        VisualState(b.drawable.bounds, b.drawable),
                        b.animation,
                    )
                )
            elif a.drawable.bounds != b.drawable.bounds:
                effects.append(
                    EffectInstance(
                        identity,
                        EffectKind.MOVE,
                        VisualState(a.drawable.bounds, a.drawable),
                        VisualState(b.drawable.bounds, b.drawable),
                        b.animation,
                    )
                )
    return BuildProgram(step.trigger, tuple(effects))


class Compiler:
    def __init__(
        self,
        theme: Theme,
        *,
        width: Length = pt(960),
        height: Length = pt(540),
        measurer: TextMeasurer | None = None,
        font_resolver: FontResolver | None = None,
    ) -> None:
        require_length(width)
        require_length(height)
        self.environment = Environment(theme)
        self.width, self.height = width, height
        self.measurer = measurer if measurer is not None else PillowMeasurer()
        self.font_resolver = (
            font_resolver if font_resolver is not None else SystemFontResolver()
        )
        self.layout_engine = LayoutEngine(
            LayoutContext(self.measurer, self.font_resolver)
        )

    def compile_view(self, view: View, state: State | None = None) -> CompiledView:
        expanded_tree = expand_view(
            view,
            Context(state if state is not None else State(), self.environment),
        )
        return CompiledView(
            expanded_tree,
            self.layout_engine.layout_view(expanded_tree, self.width, self.height),
        )

    def compile_slide(self, slide: Slide, state: State | None = None) -> CompiledSlide:
        """Compile a slide's initial state and all declared timeline steps."""
        if not isinstance(slide, Slide):
            raise TypeError("compile_slide() requires a Slide")
        shared = state if state is not None else State()
        timeline = slide.timeline()
        if not isinstance(timeline, SlideTimeline):
            raise TypeError("Slide.timeline() must return SlideTimeline")
        compiled = [self.compile_view(slide, shared.merging(timeline.initial))]
        programs = []
        for step in timeline.subsequent:
            following = self.compile_view(slide, shared.merging(step.state))
            programs.append(_compile_build(compiled[-1], following, step))
            compiled.append(following)
        return CompiledSlide(tuple(compiled), AnimationProgram(tuple(programs)))

    def compile_deck(self, deck: Deck, state: State | None = None) -> CompiledDeck:
        """Compile every slide timeline, overlaying it on optional shared state."""
        return CompiledDeck(tuple(self.compile_slide(slide, state) for slide in deck))

    def changes(self, before: CompiledView, after: CompiledView) -> tuple[Change, ...]:
        return with_geometry(
            reconcile(before.expanded_tree, after.expanded_tree),
            before.drawable,
            after.drawable,
        )
