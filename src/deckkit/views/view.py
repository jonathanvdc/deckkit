"""Backend-independent author values. Modifier order is significant."""

from __future__ import annotations

from copy import copy
from typing import Literal, Optional, Union

from typing_extensions import Self

from ..units import Length, pt, require_length

# Tagged tuples preserve the relationship between modifier names and payloads.
Modifier = Union[
    tuple[Literal["key", "font", "color", "animation", "transition"], str],
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

    def font(self, role: str) -> Self:
        return self._with(("font", role))

    def foreground_style(self, style: str) -> Self:
        return self._with(("color", style))

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
