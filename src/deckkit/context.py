from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Generic, TypeVar, cast

if TYPE_CHECKING:
    from .theme import Theme

T = TypeVar("T")


class EnvironmentKey(ABC, Generic[T]):
    """A typed, inheritable environment value with an owner-defined default."""

    @classmethod
    @abstractmethod
    def default(cls) -> T:
        raise NotImplementedError


class FontRoleKey(EnvironmentKey[str]):
    @classmethod
    def default(cls) -> str:
        return "body"


class ForegroundStyleKey(EnvironmentKey[str]):
    @classmethod
    def default(cls) -> str:
        return "primary"


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
    """Inherited values available while evaluating a view subtree."""

    theme: Theme
    _values: Mapping[type[EnvironmentKey[Any]], Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_values", MappingProxyType(dict(self._values)))

    def get(self, key: type[EnvironmentKey[T]]) -> T:
        if key in self._values:
            return cast(T, self._values[key])
        return key.default()

    def setting(self, key: type[EnvironmentKey[T]], value: T) -> Environment:
        return Environment(self.theme, {**self._values, key: value})


@dataclass(frozen=True)
class Context:
    state: State
    environment: Environment
