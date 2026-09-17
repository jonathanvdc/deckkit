"""Typed occurrence identities and lexical key scopes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Union
from urllib.parse import quote


@dataclass(frozen=True)
class RootSegment:
    name: str


@dataclass(frozen=True)
class StructuralSegment:
    slot: str | int
    view_type: type[Any]


@dataclass(frozen=True)
class KeySegment:
    key: str
    view_type: type[Any]


IdentitySegment = Union[RootSegment, StructuralSegment, KeySegment]


@dataclass(frozen=True)
class ViewIdentity:
    segments: tuple[IdentitySegment, ...]

    @classmethod
    def root(cls, name: str) -> ViewIdentity:
        return cls((RootSegment(name),))

    def child(self, slot: str | int, view_type: type[Any]) -> ViewIdentity:
        return ViewIdentity((*self.segments, StructuralSegment(slot, view_type)))

    def keyed(self, key: str, view_type: type[Any]) -> ViewIdentity:
        return ViewIdentity((*self.segments, KeySegment(key, view_type)))

    def __str__(self) -> str:
        parts: list[str] = []
        for segment in self.segments:
            if isinstance(segment, RootSegment):
                parts.append(segment.name)
                continue
            typename = (
                segment.view_type.__module__ + "." + segment.view_type.__qualname__
            )
            if isinstance(segment, StructuralSegment):
                parts.append(f"{segment.slot}:{typename}")
            else:
                keyed = f"key:{quote(segment.key, safe='')}:{typename}"
                if len(parts) == 1 and isinstance(self.segments[0], RootSegment):
                    parts[0] = keyed
                else:
                    parts.append(keyed)
        return "/".join(parts)


@dataclass(frozen=True)
class KeyScope:
    owner: ViewIdentity


@dataclass(frozen=True)
class ScopedKey:
    scope: KeyScope
    key: str
