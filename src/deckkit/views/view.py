"""Backend-independent author values. Modifier order is significant."""

from __future__ import annotations

from copy import copy
from typing import TYPE_CHECKING, Any, Literal, TypeVar, Union

from typing_extensions import Self

from ..animation import Animation, Transition
from ..context import EnvironmentKey, FontRoleKey, ForegroundStyleKey
from ..units import Length, pt

if TYPE_CHECKING:
    from ..geometry import RelativePoint
    from .modifier_views import EdgeSet, FrameMaximum

T = TypeVar("T")

# Tagged tuples preserve the relationship between modifier names and payloads.
Modifier = Union[
    tuple[Literal["key"], str],
    tuple[Literal["animation"], Animation],
    tuple[Literal["transition"], Transition],
    tuple[Literal["environment"], tuple[type[EnvironmentKey[Any]], Any]],
    tuple[Literal["flex"], float],
    tuple[Literal["boundary"], bool],
]


class View:
    _modifiers: tuple[Modifier, ...] = ()

    def _with(self, modifier: Modifier) -> Self:
        result = copy(self)
        object.__setattr__(result, "_modifiers", self._modifiers + (modifier,))
        return result

    def key(self, value: str | int) -> Self:
        return self._with(("key", str(value)))

    def environment(self, key: type[EnvironmentKey[T]], value: T) -> Self:
        return self._with(("environment", (key, value)))

    def font(self, role: str) -> Self:
        return self.environment(FontRoleKey, role)

    def foreground_style(self, style: str) -> Self:
        return self.environment(ForegroundStyleKey, style)

    @property
    def _layout_flex(self) -> float:
        return next((m[1] for m in reversed(self._modifiers) if m[0] == "flex"), 0.0)

    def padding(self, amount: Length = pt(16), *, edges: EdgeSet | None = None) -> View:
        from .modifier_views import EdgeSet, Padding

        return Padding(self, amount, EdgeSet.all if edges is None else edges)

    def frame(
        self,
        *,
        width: Length | None = None,
        height: Length | None = None,
        min_width: Length | None = None,
        ideal_width: Length | None = None,
        max_width: FrameMaximum | None = None,
        min_height: Length | None = None,
        ideal_height: Length | None = None,
        max_height: FrameMaximum | None = None,
        alignment: RelativePoint | None = None,
    ) -> View:
        from ..geometry import RelativePoint
        from .modifier_views import Frame, FrameSpec

        return Frame(
            self,
            FrameSpec(
                width,
                height,
                min_width,
                ideal_width,
                max_width,
                min_height,
                ideal_height,
                max_height,
                RelativePoint.center if alignment is None else alignment,
            ),
        )

    def flex(self, weight: float = 1) -> Self:
        if weight <= 0:
            raise ValueError("Flex weight must be positive")
        return self._with(("flex", float(weight)))

    def animation(self, animation: Animation) -> Self:
        if not isinstance(animation, Animation):
            raise TypeError("animation() requires an Animation value")
        return self._with(("animation", animation))

    def transition(self, transition: Transition) -> Self:
        if not isinstance(transition, Transition):
            raise TypeError("transition() requires a Transition value")
        return self._with(("transition", transition))

    def animation_boundary(self) -> Self:
        return self._with(("boundary", True))
