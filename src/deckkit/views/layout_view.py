from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable

from ..identity import ViewIdentity
from ..layout import Layout
from ..units import Length
from .view import View


@dataclass(frozen=True, init=False)
class LayoutView(View, ABC):
    """Base class for views whose children are arranged by a layout policy."""

    children: tuple[View | None, ...]

    def __init__(self, *children: View | None) -> None:
        object.__setattr__(self, "children", tuple(children))

    @abstractmethod
    def resolve_layout(self, lookup: Callable[[str], ViewIdentity]) -> Layout:
        """Return the policy used to arrange this occurrence's children."""
        raise NotImplementedError

    @property
    def _expanded_spacing(self) -> Length | None:
        """Spacing metadata retained for logical reconciliation, when applicable."""
        return None
