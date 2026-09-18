"""Deck compilation entry points.

Author-facing building blocks live in focused namespaces: ``deckkit.views``,
``deckkit.views.semantic``, and ``deckkit.themes``. Lower-level extension
contracts likewise remain in their defining modules instead of being mirrored
at the package root.
"""

from .compiler import CompiledDeck, CompiledSlide, CompiledView, Compiler
from .deck import Deck

__all__ = ["CompiledDeck", "CompiledSlide", "CompiledView", "Compiler", "Deck"]
