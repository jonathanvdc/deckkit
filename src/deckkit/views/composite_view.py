from __future__ import annotations

from abc import ABC, abstractmethod

from ..context import Context
from .view import View


class CompositeView(View, ABC):
    """A view described by composing other views."""

    @abstractmethod
    def body(self, context: Context) -> View:
        """Return this component's composition for the current context."""
        raise NotImplementedError
