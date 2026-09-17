"""Backend-independent author values. Modifier order is significant."""

from __future__ import annotations

from copy import copy
from typing import Any, Literal, Optional, TypeVar, Union

from typing_extensions import Self

from ..context import EnvironmentKey, FontRoleKey, ForegroundStyleKey
from ..units import Length, pt, require_length

T = TypeVar("T")

# Tagged tuples preserve the relationship between modifier names and payloads.
Modifier = Union[
    tuple[Literal["key", "animation", "transition"], str],
    tuple[Literal["environment"], tuple[type[EnvironmentKey[Any]], Any]],
    tuple[Literal["padding"], Length],
    tuple[Literal["flex"], float],
    tuple[Literal["frame"], tuple[Optional[Length], Optional[Length]]],
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

    def padding(self, amount: Length = pt(16)) -> Self:
        require_length(amount)
        return self._with(("padding", amount))

    def frame(
        self, *, width: Length | None = None, height: Length | None = None
    ) -> Self:
        for value in (width, height):
            if value is not None:
                require_length(value)
        return self._with(("frame", (width, height)))

    def flex(self, weight: float = 1) -> Self:
        if weight <= 0:
            raise ValueError("Flex weight must be positive")
        return self._with(("flex", float(weight)))

    def animation(self, name: str) -> Self:
        return self._with(("animation", name))

    def transition(self, name: str) -> Self:
        return self._with(("transition", name))

    def animation_boundary(self) -> Self:
        return self._with(("boundary", True))
