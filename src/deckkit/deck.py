"""An immutable, ordered presentation of slides."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from os import PathLike
from typing import TYPE_CHECKING, overload

from .theme import Theme
from .units import Length, pt, require_length
from .views.slide import Slide

if TYPE_CHECKING:
    from .compiler import CompiledDeck
    from .context import State
    from .fonts import FontResolver
    from .measurement import TextMeasurer


@dataclass(frozen=True, init=False)
class Deck(Sequence[Slide]):
    slides: tuple[Slide, ...]
    theme: Theme
    width: Length
    height: Length

    def __init__(
        self,
        slides: Iterable[Slide],
        *,
        theme: Theme,
        width: Length = pt(960),
        height: Length = pt(540),
    ) -> None:
        items = tuple(slides)
        if any(not isinstance(slide, Slide) for slide in items):
            raise TypeError("Deck entries must be Slide instances")
        if not isinstance(theme, Theme):
            raise TypeError("Deck theme must be a Theme")
        require_length(width)
        require_length(height)
        if width.points <= 0 or height.points <= 0:
            raise ValueError("Deck dimensions must be positive")
        object.__setattr__(self, "slides", items)
        object.__setattr__(self, "theme", theme)
        object.__setattr__(self, "width", width)
        object.__setattr__(self, "height", height)

    def __len__(self) -> int:
        return len(self.slides)

    def __iter__(self) -> Iterator[Slide]:
        return iter(self.slides)

    @overload
    def __getitem__(self, index: int) -> Slide: ...
    @overload
    def __getitem__(self, index: slice) -> Deck: ...

    def __getitem__(self, index: int | slice) -> Slide | Deck:
        if isinstance(index, slice):
            return Deck(
                self.slides[index],
                theme=self.theme,
                width=self.width,
                height=self.height,
            )
        return self.slides[index]

    def compile(
        self,
        state: State | None = None,
        *,
        measurer: TextMeasurer | None = None,
        font_resolver: FontResolver | None = None,
    ) -> CompiledDeck:
        """Compile this deck using its theme and canvas configuration."""
        from .compiler import Compiler

        return Compiler(
            self.theme,
            width=self.width,
            height=self.height,
            measurer=measurer,
            font_resolver=font_resolver,
        ).compile_deck(self, state)

    def write_pptx(
        self,
        path: str | PathLike[str],
        state: State | None = None,
        *,
        measurer: TextMeasurer | None = None,
        font_resolver: FontResolver | None = None,
    ) -> None:
        """Compile and write this deck as a PowerPoint presentation."""
        from .backends import pptx

        pptx.render(
            self.compile(
                state,
                measurer=measurer,
                font_resolver=font_resolver,
            ),
            path,
        )
