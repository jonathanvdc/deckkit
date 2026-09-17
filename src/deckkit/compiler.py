from __future__ import annotations

from dataclasses import dataclass

from .deck import Deck
from .drawables import Drawable
from .fonts import FontResolver, SystemFontResolver
from .layout import LayoutEngine
from .measurement import PillowMeasurer, TextMeasurer
from .reconcile import Change, reconcile, with_geometry
from .theme import Theme
from .units import Length, pt, require_length
from .view_expansion import ExpandedView, expand_view
from .views import Context, Environment, State, View


@dataclass(frozen=True)
class CompiledView:
    """One view evaluated for one state, environment and canvas.

    The resolved tree preserves logical identity/properties for reconciliation;
    the layout contains measured text and concrete geometry for export. Both
    artifacts come from the same evaluation. This is not an animation or a
    backend document, and it does not retain the source state or environment.
    """

    expanded_tree: ExpandedView
    drawable: Drawable


@dataclass(frozen=True)
class CompiledDeck:
    """Ordered compiled slide views, ready for layout export."""

    slides: tuple[CompiledView, ...]

    @property
    def drawables(self) -> tuple[Drawable, ...]:
        return tuple(slide.drawable for slide in self.slides)


class Compiler:
    def __init__(
        self,
        theme: Theme,
        *,
        width: Length = pt(960),
        height: Length = pt(540),
        measurer: TextMeasurer | None = None,
        font_resolver: FontResolver | None = None,
    ) -> None:
        require_length(width)
        require_length(height)
        self.environment = Environment(theme)
        self.width, self.height = width, height
        self.measurer = measurer if measurer is not None else PillowMeasurer()
        self.layout_engine = LayoutEngine()
        self.font_resolver = (
            font_resolver if font_resolver is not None else SystemFontResolver()
        )

    def compile_view(self, view: View, state: State | None = None) -> CompiledView:
        expanded_tree = expand_view(
            view,
            Context(state if state is not None else State(), self.environment),
            self.measurer,
            self.font_resolver,
        )
        return CompiledView(
            expanded_tree,
            self.layout_engine.layout_view(expanded_tree, self.width, self.height),
        )

    def compile_deck(self, deck: Deck, state: State | None = None) -> CompiledDeck:
        """Compile slides in order with this compiler's theme and canvas.

        The supplied state snapshot is shared; deck position is not a state source.
        Each slide retains its own identity/key scope.
        """
        return CompiledDeck(tuple(self.compile_view(slide, state) for slide in deck))

    def changes(self, before: CompiledView, after: CompiledView) -> tuple[Change, ...]:
        return with_geometry(
            reconcile(before.expanded_tree, after.expanded_tree),
            before.drawable,
            after.drawable,
        )
