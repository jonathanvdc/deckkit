from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable

from ..identity import ViewIdentity
from ..layout import Layout
from ..units import Length, pt, require_length
from .layout_view import LayoutView
from .view import View


@dataclass(frozen=True, init=False)
class Stack(LayoutView, ABC):
    children: tuple[View | None, ...]
    spacing: Length

    @abstractmethod
    def _make_layout(self) -> Layout:
        raise NotImplementedError(type(self).__name__)

    def __init__(self, *children: View | None, spacing: Length = pt(16)) -> None:
        require_length(spacing)
        if spacing < pt(0):
            raise ValueError("Spacing must be nonnegative")
        # Preserve absent slots for structural identity.
        object.__setattr__(self, "spacing", spacing)
        super().__init__(*children)

    def resolve_layout(self, lookup: Callable[[str], ViewIdentity]) -> Layout:
        return self._make_layout()

    @property
    def _expanded_spacing(self) -> Length:
        return self.spacing
