from __future__ import annotations

from deckkit.themes import (
    AccentColor,
    ClarityTheme,
    MutedColor,
    SurfaceColor,
    TitleTextStyle,
    semantic_renderer,
)
from deckkit.units import pt
from deckkit.views import (
    Context,
    Rectangle,
    View,
    VStack,
    ZStack,
)
from deckkit.views.semantic import BeforeAfter
from deckkit.views.slides import SlideMargins, TitleAndContent


class EditorialTheme(ClarityTheme):
    """An example theme."""

    @semantic_renderer(SlideMargins)
    def render_slide_margins(self, component: SlideMargins, context: Context) -> View:
        return component.content.padding(pt(48))

    @semantic_renderer(TitleAndContent)
    def render_title_and_content(
        self, component: TitleAndContent, context: Context
    ) -> View:
        return VStack(
            component.title.font(TitleTextStyle),
            component.content,
            spacing=pt(40),
        )

    @semantic_renderer(BeforeAfter)
    def render_before_after(self, component: BeforeAfter, context: Context) -> View:
        comparison = ZStack(
            Rectangle().foreground_style(SurfaceColor),
            VStack(
                component.before.foreground_style(MutedColor),
                component.after.font(TitleTextStyle).foreground_style(AccentColor),
                spacing=pt(32),
            ).padding(pt(28)),
        )
        return VStack(comparison, component.takeaway, spacing=pt(32))
