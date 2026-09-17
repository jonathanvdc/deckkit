from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .theme import Theme


class State(Mapping[str, Any]):
    def __init__(self, **values: Any) -> None:
        self._values = MappingProxyType(values)

    def __getitem__(self, key: str) -> Any:
        return self._values[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)


@dataclass(frozen=True)
class Environment:
    theme: Theme


@dataclass(frozen=True)
class Context:
    state: State
    environment: Environment
