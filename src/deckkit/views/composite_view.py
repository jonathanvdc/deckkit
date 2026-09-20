from __future__ import annotations

from abc import ABC, abstractmethod

from ..context import Context
from .view import View


class CompositeView(View, ABC):
    """A view described by composing other views."""

    def _resolve_body(self, context: Context) -> View:
        """Resolve the body used during expansion."""
        return self.body(context)

    @abstractmethod
    def body(self, context: Context) -> View:
        """Return this component's composition for the current context."""
        raise NotImplementedError
