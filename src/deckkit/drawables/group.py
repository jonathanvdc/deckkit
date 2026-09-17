from __future__ import annotations

from dataclasses import dataclass

from .drawable import Drawable


@dataclass(frozen=True)
class DrawableGroup(Drawable):
    children: tuple[Drawable, ...] = ()
