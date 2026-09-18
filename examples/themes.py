from __future__ import annotations

from deckkit.themes import ClarityTheme
from deckkit.units import pt
from deckkit.views import Context, Rectangle, View, VStack, ZStack
from deckkit.views.semantic import BeforeAfter, SemanticView


class EditorialTheme(ClarityTheme):
    """An example structural recipe; editorial design is not a core theme flag."""

    def render_semantic(self, component: SemanticView, context: Context) -> View | None:
        if isinstance(component, BeforeAfter):
            comparison = ZStack(
                Rectangle().foreground_style("surface"),
                VStack(
                    component.before.foreground_style("muted"),
                    component.after.font("title").foreground_style("accent"),
                    spacing=pt(32),
                ).padding(pt(28)),
            )
            return VStack(
                component.title.font("title"),
                comparison,
                component.takeaway,
                spacing=pt(32),
            )
        return super().render_semantic(component, context)
