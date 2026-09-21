from dataclasses import dataclass
from math import isfinite
from typing import Literal

from ..theme import ColorStyle, ForegroundColor
from ..units import Length, pt, require_length


@dataclass(frozen=True)
class Stroke:
    style: ColorStyle = ForegroundColor
    width: Length = pt(1)
    dash: tuple[Length, ...] = ()
    opacity: float = 1.0
    line_cap: Literal["butt", "round", "square"] = "butt"
    line_join: Literal["miter", "round", "bevel"] = "miter"

    def __post_init__(self) -> None:
        require_length(self.width)
        if self.width <= pt(0):
            raise ValueError("Stroke width must be positive")
        for segment in self.dash:
            require_length(segment)
            if segment <= pt(0):
                raise ValueError("Stroke dash lengths must be positive")
        if not isfinite(self.opacity) or not 0 <= self.opacity <= 1:
            raise ValueError("Canvas opacity must be between zero and one")
        if self.line_cap not in ("butt", "round", "square"):
            raise ValueError("Unknown Canvas stroke line cap")
        if self.line_join not in ("miter", "round", "bevel"):
            raise ValueError("Unknown Canvas stroke line join")
