from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .primitive_view import PrimitiveView


@dataclass(frozen=True)
class Image(PrimitiveView):
    source: str
    fit: Literal["contain", "cover"] = "contain"
    dpi: float = 96

    def __post_init__(self) -> None:
        from math import isfinite

        if not isfinite(self.dpi) or self.dpi <= 0:
            raise ValueError("Image DPI must be finite and positive")
        if self.fit not in ("contain", "cover"):
            raise ValueError("Image fit must be contain or cover")
