from __future__ import annotations

from abc import ABC, abstractmethod

from ..context import Context
from ..expanded_views import ExpandedMetadata, ExpandedPrimitive
from .view import View


class PrimitiveView(View, ABC):
    """A rendering leaf that resolves to a typed expanded view."""

    @abstractmethod
    def expand(self, context: Context, metadata: ExpandedMetadata) -> ExpandedPrimitive:
        """Resolve this leaf into rendering properties and a layout policy."""
        raise NotImplementedError
