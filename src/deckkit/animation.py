"""Backend-independent presentation builds and animation intent."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from .context import State
    from .drawables import Bounds, Drawable


class Easing(str, Enum):
    LINEAR = "linear"
    EASE_IN = "ease-in"
    EASE_OUT = "ease-out"
    EASE_IN_OUT = "ease-in-out"


class FallbackPolicy(str, Enum):
    ERROR = "error"
    CROSSFADE = "crossfade"
    DISCRETE = "discrete"


@dataclass(frozen=True)
class Animation:
    duration: float = 0.4
    easing: Easing = Easing.EASE_IN_OUT
    delay: float = 0.0
    fallback: FallbackPolicy = FallbackPolicy.ERROR

    def __post_init__(self) -> None:
        if self.duration < 0 or self.delay < 0:
            raise ValueError("Animation duration and delay must be nonnegative")

    @property
    def is_discrete(self) -> bool:
        return self.duration == 0

    @classmethod
    def discrete(cls, *, delay: float = 0.0) -> Animation:
        return cls(
            duration=0,
            easing=Easing.LINEAR,
            delay=delay,
            fallback=FallbackPolicy.DISCRETE,
        )

    @classmethod
    def smooth(
        cls,
        duration: float = 0.4,
        *,
        delay: float = 0.0,
        fallback: FallbackPolicy = FallbackPolicy.ERROR,
    ) -> Animation:
        return cls(duration, Easing.EASE_IN_OUT, delay, fallback)

    @classmethod
    def linear(
        cls,
        duration: float = 0.4,
        *,
        delay: float = 0.0,
        fallback: FallbackPolicy = FallbackPolicy.ERROR,
    ) -> Animation:
        return cls(duration, Easing.LINEAR, delay, fallback)


class TransitionEffect(str, Enum):
    APPEAR = "appear"
    FADE = "fade"


@dataclass(frozen=True)
class Transition:
    insertion: TransitionEffect
    removal: TransitionEffect
    animation: Animation = field(default_factory=Animation.smooth)

    @classmethod
    def fade(cls, duration: float = 0.3) -> Transition:
        return cls(
            TransitionEffect.FADE,
            TransitionEffect.FADE,
            Animation(duration, Easing.EASE_IN_OUT, fallback=FallbackPolicy.CROSSFADE),
        )

    @classmethod
    def appear(cls) -> Transition:
        return cls(
            TransitionEffect.APPEAR,
            TransitionEffect.APPEAR,
            Animation.discrete(),
        )


@dataclass(frozen=True)
class OnAdvance:
    """Start a build when the presenter advances the presentation."""


@dataclass(frozen=True)
class WithPrevious:
    delay: float = 0.0

    def __post_init__(self) -> None:
        if self.delay < 0:
            raise ValueError("Trigger delay must be nonnegative")


@dataclass(frozen=True)
class AfterPrevious:
    delay: float = 0.0

    def __post_init__(self) -> None:
        if self.delay < 0:
            raise ValueError("Trigger delay must be nonnegative")


Trigger = Union[OnAdvance, WithPrevious, AfterPrevious]


@dataclass(frozen=True)
class TimelineStep:
    state: State
    trigger: Trigger = field(default_factory=OnAdvance)
    animation: Animation = field(default_factory=Animation.discrete)


@dataclass(frozen=True)
class SlideTimeline:
    initial: State
    subsequent: tuple[TimelineStep, ...] = ()

    def __post_init__(self) -> None:
        from .context import State

        if not isinstance(self.initial, State):
            raise TypeError("timeline initial value must be State")
        if any(not isinstance(step, TimelineStep) for step in self.subsequent):
            raise TypeError("timeline steps must be TimelineStep values")

    @classmethod
    def static(cls, state: State | None = None) -> SlideTimeline:
        """Create a timeline with one state and no presentation advances."""
        from .context import State

        if state is not None and not isinstance(state, State):
            raise TypeError("timeline state must be State")
        return cls(state if state is not None else State())

    @classmethod
    def advance_through(cls, initial: State, *states: State) -> SlideTimeline:
        """Advance through arbitrary state snapshots on successive presenter clicks."""
        from .context import State

        if not isinstance(initial, State) or any(
            not isinstance(state, State) for state in states
        ):
            raise TypeError("timeline values must be State values")
        return cls(initial, tuple(TimelineStep(state) for state in states))

    @classmethod
    def steps(cls, count: int) -> SlideTimeline:
        """Create ``count`` click-advanced states numbered ``step=0`` onward."""
        from .context import State

        if isinstance(count, bool) or not isinstance(count, int):
            raise TypeError("step count must be an integer")
        if count < 1:
            raise ValueError("step count must be at least one")
        return cls.advance_through(*(State(step=number) for number in range(count)))


class EffectKind(str, Enum):
    INSERT = "insert"
    REMOVE = "remove"
    MOVE = "move"
    CHANGE = "change"


@dataclass(frozen=True)
class VisualState:
    bounds: Bounds
    drawable: Drawable


@dataclass(frozen=True)
class EffectInstance:
    identity: str
    kind: EffectKind
    before: VisualState | None
    after: VisualState | None
    animation: Animation = field(default_factory=Animation.discrete)
    transition: Transition | None = None


@dataclass(frozen=True)
class BuildProgram:
    trigger: Trigger
    effects: tuple[EffectInstance, ...]


@dataclass(frozen=True)
class AnimationProgram:
    """Resolved builds independent of PPTX, HTML, or frame sampling."""

    builds: tuple[BuildProgram, ...]
