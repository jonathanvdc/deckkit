"""An immutable, ordered presentation of slides."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from typing import overload

from .views.slide import Slide


@dataclass(frozen=True, init=False)
class Deck(Sequence[Slide]):
    slides: tuple[Slide, ...]

    def __init__(self, slides: Iterable[Slide]) -> None:
        items = tuple(slides)
        if any(not isinstance(slide, Slide) for slide in items):
            raise TypeError("Deck entries must be Slide instances")
        object.__setattr__(self, "slides", items)

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
            return Deck(self.slides[index])
        return self.slides[index]
