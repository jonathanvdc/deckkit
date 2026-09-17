"""Lower backend-neutral builds into a PowerPoint-oriented animation plan."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..animation import (
    AfterPrevious,
    AnimationProgram,
    EffectInstance,
    EffectKind,
    FallbackPolicy,
    OnAdvance,
    TransitionEffect,
    WithPrevious,
)
from ..compiler import CompiledSlide
from ..drawables import Bounds


class PptxTrigger(str, Enum):
    ON_CLICK = "on-click"
    WITH_PREVIOUS = "with-previous"
    AFTER_PREVIOUS = "after-previous"


class PptxBehaviorKind(str, Enum):
    APPEAR = "appear"
    DISAPPEAR = "disappear"
    FADE_IN = "fade-in"
    FADE_OUT = "fade-out"
    MOTION = "motion"
    CROSSFADE = "crossfade"
    DISCRETE = "discrete"


@dataclass(frozen=True)
class PptxBehavior:
    identity: str
    kind: PptxBehaviorKind
    duration_ms: int
    delay_ms: int
    before: Bounds | None = None
    after: Bounds | None = None


@dataclass(frozen=True)
class PptxBuild:
    trigger: PptxTrigger
    delay_ms: int
    behaviors: tuple[PptxBehavior, ...]


@dataclass(frozen=True)
class PptxLoweringDiagnostic:
    identity: str
    message: str


@dataclass(frozen=True)
class PptxAnimationPlan:
    builds: tuple[PptxBuild, ...]
    diagnostics: tuple[PptxLoweringDiagnostic, ...] = ()


class PptxLoweringError(ValueError):
    pass


def _unsupported(
    effect: EffectInstance, message: str
) -> tuple[PptxBehaviorKind, PptxLoweringDiagnostic | None]:
    assert effect.animation is not None
    fallback = effect.animation.fallback
    if fallback is FallbackPolicy.ERROR:
        raise PptxLoweringError(f"{effect.identity}: {message}")
    if fallback is FallbackPolicy.DISCRETE:
        return PptxBehaviorKind.DISCRETE, None
    return PptxBehaviorKind.CROSSFADE, PptxLoweringDiagnostic(
        effect.identity, f"{message}; using a crossfade"
    )


def _trigger(value: object) -> tuple[PptxTrigger, int]:
    if isinstance(value, OnAdvance):
        return PptxTrigger.ON_CLICK, 0
    if isinstance(value, WithPrevious):
        return PptxTrigger.WITH_PREVIOUS, round(value.delay * 1000)
    if isinstance(value, AfterPrevious):
        return PptxTrigger.AFTER_PREVIOUS, round(value.delay * 1000)
    raise TypeError(f"Unsupported build trigger: {type(value).__name__}")


def _lower_effect(
    effect: EffectInstance,
) -> tuple[PptxBehavior, PptxLoweringDiagnostic | None]:
    before = effect.before.bounds if effect.before is not None else None
    after = effect.after.bounds if effect.after is not None else None
    animation = effect.animation
    transition = effect.transition
    timing = transition.animation if transition is not None else animation
    assert timing is not None
    duration = round(timing.duration * 1000)
    delay = round(timing.delay * 1000)
    diagnostic = None

    if effect.kind is EffectKind.INSERT:
        kind = (
            PptxBehaviorKind.FADE_IN
            if transition is not None and transition.insertion is TransitionEffect.FADE
            else PptxBehaviorKind.APPEAR
        )
    elif effect.kind is EffectKind.REMOVE:
        kind = (
            PptxBehaviorKind.FADE_OUT
            if transition is not None and transition.removal is TransitionEffect.FADE
            else PptxBehaviorKind.DISAPPEAR
        )
    elif effect.kind is EffectKind.MOVE and before is not None and after is not None:
        if animation.is_discrete:
            kind = PptxBehaviorKind.DISCRETE
        elif before.width == after.width and before.height == after.height:
            kind = PptxBehaviorKind.MOTION
        else:
            kind, diagnostic = _unsupported(
                effect, "PPTX cannot reliably reproduce this resize"
            )
    elif effect.kind is EffectKind.CHANGE:
        if animation.is_discrete:
            kind = PptxBehaviorKind.DISCRETE
        else:
            kind, diagnostic = _unsupported(effect, "Visual content changed")
    else:
        kind = PptxBehaviorKind.DISCRETE

    return PptxBehavior(
        effect.identity, kind, duration, delay, before, after
    ), diagnostic


def plan(program: AnimationProgram) -> PptxAnimationPlan:
    builds = []
    diagnostics = []
    for build in program.builds:
        trigger, trigger_delay = _trigger(build.trigger)
        behaviors = []
        for effect in build.effects:
            behavior, diagnostic = _lower_effect(effect)
            behaviors.append(behavior)
            if diagnostic is not None:
                diagnostics.append(diagnostic)
        builds.append(PptxBuild(trigger, trigger_delay, tuple(behaviors)))
    return PptxAnimationPlan(tuple(builds), tuple(diagnostics))


def plan_slide(slide: CompiledSlide) -> PptxAnimationPlan:
    return plan(slide.animation)
