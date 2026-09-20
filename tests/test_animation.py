from dataclasses import dataclass, field
from zipfile import ZipFile

import pytest

from deckkit import CompiledDeck
from deckkit.animation import (
    AfterPrevious,
    Animation,
    EffectKind,
    FallbackPolicy,
    OnAdvance,
    SlideTimeline,
    TimelineStep,
    Transition,
)
from deckkit.backends.pptx_animation import (
    PptxBehaviorKind,
    PptxLoweringError,
    PptxTrigger,
    plan_slide,
)
from deckkit.units import pt
from deckkit.views import Rectangle, Slide, State, Text, VStack


@dataclass(frozen=True)
class ReflowExample(Slide):
    authored_timeline: SlideTimeline = field(default_factory=SlideTimeline.static)

    def timeline(self):
        return self.authored_timeline

    def body(self, context):
        return VStack(
            Text("A").key("a"),
            Text("B").key("b").transition(Transition.fade())
            if context.state.get("show_b", True)
            else None,
            Text("C").key("c"),
        ).animation(Animation.smooth())


@dataclass(frozen=True)
class UnanimatedReflowExample(Slide):
    authored_timeline: SlideTimeline = field(default_factory=SlideTimeline.static)

    def timeline(self):
        return self.authored_timeline

    def body(self, context):
        return VStack(
            Text("A").key("a"),
            Text("B").key("b") if context.state.get("show_b", True) else None,
            Text("C").key("c"),
        )


def test_string_animation_forms_are_rejected():
    with pytest.raises(TypeError, match="Animation"):
        Text("No legacy strings").animation("smooth")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="Transition"):
        Text("No legacy strings").transition("opacity")  # type: ignore[arg-type]


def test_zero_duration_animation_is_explicitly_discrete():
    animation = Animation.discrete(delay=0.25)
    assert animation.is_discrete
    assert animation.duration == 0
    assert animation.delay == 0.25
    assert TimelineStep(State()).animation == Animation.discrete()
    assert not Animation.smooth().is_discrete


def test_sequence_defaults_to_presenter_advance_and_compiles_reflow(compiler):
    sequence = compiler.compile_slide(
        ReflowExample(
            SlideTimeline.advance_through(State(show_b=True), State(show_b=False))
        )
    )
    build = sequence.animation.builds[0]
    assert isinstance(build.trigger, OnAdvance)
    assert any(
        e.kind is EffectKind.REMOVE and "key:b:" in e.identity for e in build.effects
    )
    move = next(
        e for e in build.effects if e.kind is EffectKind.MOVE and "key:c:" in e.identity
    )
    assert move.before is not None and move.after is not None
    assert (
        move.before.bounds.y < move.after.bounds.y
        or move.before.bounds.y > move.after.bounds.y
    )
    assert move.animation == Animation.smooth()

    pptx_plan = plan_slide(sequence)
    assert pptx_plan.builds[0].trigger is PptxTrigger.ON_CLICK
    assert any(
        b.kind is PptxBehaviorKind.FADE_OUT for b in pptx_plan.builds[0].behaviors
    )
    assert any(b.kind is PptxBehaviorKind.MOTION for b in pptx_plan.builds[0].behaviors)


def test_timed_build_lowers_to_after_previous(compiler):
    sequence = compiler.compile_slide(
        ReflowExample(
            SlideTimeline(
                State(show_b=True),
                (TimelineStep(State(show_b=False), trigger=AfterPrevious(delay=1.25)),),
            )
        ),
    )
    build = plan_slide(sequence).builds[0]
    assert build.trigger is PptxTrigger.AFTER_PREVIOUS
    assert build.delay_ms == 1250


def test_unanimated_reflow_is_explicitly_discrete(compiler):
    sequence = compiler.compile_slide(
        UnanimatedReflowExample(
            SlideTimeline.advance_through(State(show_b=True), State(show_b=False))
        )
    )
    plan = plan_slide(sequence)
    move = next(
        behavior
        for behavior in plan.builds[0].behaviors
        if "key:c:" in behavior.identity
    )
    assert move.kind is PptxBehaviorKind.DISCRETE


def test_pptx_sequence_contains_union_shapes_and_native_timing(compiler, tmp_path):
    from deckkit.backends import pptx

    sequence = compiler.compile_slide(
        ReflowExample(
            SlideTimeline.advance_through(State(show_b=True), State(show_b=False))
        )
    )
    output = tmp_path / "animated.pptx"
    pptx.render(CompiledDeck((sequence,)), output)

    with ZipFile(output) as archive:
        slide = archive.read("ppt/slides/slide1.xml").decode()
    assert "<p:timing>" in slide
    assert 'nodeType="clickEffect"' in slide
    assert '<p:animEffect transition="out" filter="fade">' in slide
    assert "<p:animMotion" in slide
    assert 'presetID="42" presetClass="path"' in slide
    assert 'pathEditMode="relative" ptsTypes=""' in slide
    assert "key:b:" in slide
    assert 'presetID="10" presetClass="exit" presetSubtype="0"' in slide
    assert 'evt="onPrev"' in slide and 'evt="onNext"' in slide
    assert "<p:bldLst><p:bldP" in slide


def test_pptx_discrete_resize_replaces_shape(compiler, tmp_path):
    from deckkit.backends import pptx

    @dataclass(frozen=True)
    class ResizingSlide(Slide):
        def timeline(self):
            return SlideTimeline.advance_through(State(width=100), State(width=200))

        def body(self, context):
            return (
                Rectangle()
                .key("box")
                .frame(width=pt(context.state["width"]), height=pt(40))
                .animation(Animation.smooth(fallback=FallbackPolicy.DISCRETE))
            )

    compiled = compiler.compile_slide(ResizingSlide())
    output = tmp_path / "resizing.pptx"
    pptx.render(CompiledDeck((compiled,)), output)

    with ZipFile(output) as archive:
        slide = archive.read("ppt/slides/slide1.xml").decode()
    assert "key:box:" in slide
    assert "#build-1" in slide
    assert "<p:animScale>" not in slide
    assert slide.count('presetID="1"') == 2
    assert 'filter="fade"' not in slide


def test_results_slide_resizes_chart_discretely(compiler):
    from deckkit.drawables import DrawableRectangle, DrawableText
    from examples.api_sketch import ResultsSlide

    compiled = compiler.compile_slide(ResultsSlide())
    planned = plan_slide(compiled)
    pairs = tuple(
        zip(compiled.animation.builds[0].effects, planned.builds[0].behaviors)
    )

    chart_rectangle = next(
        behavior
        for effect, behavior in pairs
        if effect.before is not None
        and isinstance(effect.before.drawable, DrawableRectangle)
    )
    chart_label = next(
        behavior
        for effect, behavior in pairs
        if effect.before is not None
        and isinstance(effect.before.drawable, DrawableText)
    )
    assert chart_rectangle.kind is PptxBehaviorKind.DISCRETE
    assert chart_label.kind is PptxBehaviorKind.MOTION
    assert not planned.diagnostics


def test_pptx_replacement_background_stays_below_unchanged_label(compiler, tmp_path):
    from lxml import etree

    from deckkit.backends import pptx
    from examples.api_sketch import ResultsSlide

    compiled = compiler.compile_slide(ResultsSlide())
    output = tmp_path / "results.pptx"
    pptx.render(CompiledDeck((compiled,)), output)

    with ZipFile(output) as archive:
        root = etree.fromstring(archive.read("ppt/slides/slide1.xml"))

    namespaces = {
        "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
        "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    }
    shapes = root.xpath("./p:cSld/p:spTree/p:sp", namespaces=namespaces)
    replacement_index = next(
        index
        for index, shape in enumerate(shapes)
        if "#build-1"
        in shape.xpath("string(p:nvSpPr/p:cNvPr/@name)", namespaces=namespaces)
        and not shape.xpath(".//a:t", namespaces=namespaces)
    )
    label_index = next(
        index
        for index, shape in enumerate(shapes)
        if shape.xpath("string(.//a:t)", namespaces=namespaces)
        == "Compilation throughput"
    )
    assert replacement_index < label_index


def test_animation_boundary_stops_ancestor_animation(compiler):
    @dataclass(frozen=True)
    class BoundaryExample(Slide):
        def timeline(self):
            return SlideTimeline.advance_through(
                State(show_b=True), State(show_b=False)
            )

        def body(self, context):
            return VStack(
                VStack(
                    Text("B").key("b") if context.state.get("show_b", True) else None,
                    Text("C").key("c"),
                ).animation_boundary()
            ).animation(Animation.smooth())

    sequence = compiler.compile_slide(BoundaryExample())
    move = next(
        e for e in sequence.animation.builds[0].effects if "key:c:" in e.identity
    )
    assert move.animation == Animation.discrete()


def test_default_fallback_rejects_unsupported_content_change(compiler):
    @dataclass(frozen=True)
    class ChangingText(Slide):
        def timeline(self):
            return SlideTimeline.advance_through(
                State(text="Before"), State(text="After")
            )

        def body(self, context):
            return Text(context.state["text"]).key("text").animation(Animation.smooth())

    sequence = compiler.compile_slide(ChangingText())
    try:
        plan_slide(sequence)
    except PptxLoweringError as error:
        assert "Visual content changed" in str(error)
    else:
        raise AssertionError("unsupported content change should fail")
