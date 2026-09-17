from __future__ import annotations

from dataclasses import dataclass

from .primitive_view import PrimitiveView


@dataclass(frozen=True)
class Rectangle(PrimitiveView):
    pass
