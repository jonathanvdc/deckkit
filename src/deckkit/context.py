from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, TypeVar

from .tokens import DesignToken, TokenAssignment, TokenResolver

if TYPE_CHECKING:
    from .theme import Theme

T = TypeVar("T")


class State(Mapping[str, Any]):
    def __init__(self, **values: Any) -> None:
        self._values = MappingProxyType(values)

    def __getitem__(self, key: str) -> Any:
        return self._values[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)

    def merging(self, overrides: State) -> State:
        """Return a snapshot in which slide-local values override shared values."""
        return State(**{**self._values, **overrides._values})


@dataclass(frozen=True)
class Environment:
    """The active inherited design-token resolution scope."""

    theme: Theme
    _tokens: TokenResolver | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._tokens is None:
            object.__setattr__(self, "_tokens", self.theme.token_resolver())

    def __getitem__(self, token: DesignToken[T]) -> T:
        """Resolve a design token against this inherited scope."""
        assert self._tokens is not None
        return self._tokens[token]

    def get(self, token: DesignToken[T]) -> T:
        """Resolve a design token using method-call syntax."""
        return self[token]

    def with_token(
        self, token: DesignToken[T], assignment: TokenAssignment[T]
    ) -> Environment:
        """Return a child scope with one token override."""
        assert self._tokens is not None
        return Environment(self.theme, self._tokens.with_token(token, assignment))

    def with_tokens(
        self, overrides: Mapping[DesignToken[Any], TokenAssignment[Any]]
    ) -> Environment:
        """Return a child scope with a group of token overrides."""
        assert self._tokens is not None
        return Environment(self.theme, self._tokens.with_tokens(overrides))


@dataclass(frozen=True)
class Context:
    state: State
    environment: Environment
