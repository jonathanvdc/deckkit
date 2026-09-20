"""Typed, computed design tokens and immutable resolution scopes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Generic, TypeVar, cast

T = TypeVar("T")


class TokenError(ValueError):
    """Base class for design-token resolution errors."""


class MissingTokenError(TokenError):
    """Raised when a token has neither an override nor a default."""


class TokenDependencyCycle(TokenError):
    """Raised when computed token defaults contain a dependency cycle."""


class DesignToken(Generic[T]):
    """A typed design value with an optional computed default.

    Tokens intentionally use object identity rather than their display names as keys.
    This lets applications and extension packages define tokens without coordinating a
    global registry or risking name collisions.
    """

    def __init__(
        self,
        name: str,
        default: Callable[[TokenResolver], T] | None = None,
        *,
        value_type: type[Any] | tuple[type[Any], ...] | None = None,
        validate: Callable[[T], None] | None = None,
    ) -> None:
        if not name:
            raise ValueError("A design token requires a non-empty name")
        self.name = name
        self._default = default
        self._value_type = value_type
        self._validate = validate

    def __repr__(self) -> str:
        return f"DesignToken({self.name!r})"

    def compute_default(self, values: TokenResolver) -> T:
        if self._default is None:
            raise MissingTokenError(
                f"No value or default for design token {self.name!r}"
            )
        return self._default(values)

    def validate(self, value: T) -> None:
        if self._value_type is not None and not isinstance(value, self._value_type):
            expected = (
                self._value_type.__name__
                if isinstance(self._value_type, type)
                else " or ".join(item.__name__ for item in self._value_type)
            )
            raise TypeError(
                f"Design token {self.name!r} requires {expected}, "
                f"not {type(value).__name__}"
            )
        if self._validate is not None:
            self._validate(value)

    def set(self, value: T) -> Value[T]:
        return Value(value)

    def alias(self, target: DesignToken[T]) -> Alias[T]:
        return Alias(target)

    def derive(self, transform: Callable[[T], T]) -> Transform[T]:
        """Transform this token's inherited value in a child scope."""
        return Transform(lambda values: transform(values.inherited(self)))

    def transform(self, compute: Callable[[TokenResolver], T]) -> Transform[T]:
        """Compute an override from the complete active token scope."""
        return Transform(compute)


class TokenAssignment(ABC, Generic[T]):
    """An explicit instruction for assigning a value to a design token."""

    @abstractmethod
    def resolve(self, values: TokenResolver) -> T:
        """Resolve this assignment against the active token scope."""
        raise NotImplementedError


@dataclass(frozen=True)
class Value(TokenAssignment[T]):
    value: T

    def resolve(self, values: TokenResolver) -> T:
        return self.value


@dataclass(frozen=True)
class Alias(TokenAssignment[T]):
    target: DesignToken[T]

    def resolve(self, values: TokenResolver) -> T:
        return values[self.target]


@dataclass(frozen=True)
class Transform(TokenAssignment[T]):
    """Compute a token value from the complete active resolution scope."""

    compute: Callable[[TokenResolver], T]

    def resolve(self, values: TokenResolver) -> T:
        return self.compute(values)


class TokenResolver:
    """Resolve tokens within one immutable, inherited override scope."""

    def __init__(
        self,
        overrides: Mapping[DesignToken[Any], TokenAssignment[Any]] | None = None,
        *,
        parent: TokenResolver | None = None,
    ) -> None:
        if overrides is not None:
            if not all(isinstance(token, DesignToken) for token in overrides):
                raise TypeError("Token assignment keys must be DesignToken instances")
            if not all(
                isinstance(assignment, TokenAssignment)
                for assignment in overrides.values()
            ):
                raise TypeError(
                    "Token assignment values must be Value, Alias, or Transform"
                )
        self._overrides = dict(overrides or {})
        self._parent = parent
        self._cache: dict[DesignToken[Any], Any] = {}
        self._resolving: list[DesignToken[Any]] = []
        self._assigning: list[tuple[DesignToken[Any], TokenResolver]] = []

    def get(self, token: DesignToken[T]) -> T:
        if not isinstance(token, DesignToken):
            raise TypeError("TokenResolver keys must be DesignToken instances")
        if token in self._cache:
            return cast(T, self._cache[token])
        if token in self._resolving:
            start = self._resolving.index(token)
            cycle = self._resolving[start:] + [token]
            names = " -> ".join(item.name for item in cycle)
            raise TokenDependencyCycle(f"Design token dependency cycle: {names}")

        self._resolving.append(token)
        try:
            override, owner = self._nearest_override(token)
            if override is not None:
                assert owner is not None
                self._assigning.append((token, owner))
                try:
                    value = override.resolve(self)
                finally:
                    self._assigning.pop()
            else:
                # Defaults always run against the active scope, so a child override of
                # a dependency recomputes every downstream token in that scope.
                value = token.compute_default(self)
            token.validate(cast(Any, value))
            self._cache[token] = value
            return cast(T, value)
        finally:
            self._resolving.pop()

    def __getitem__(self, token: DesignToken[T]) -> T:
        return self.get(token)

    def with_tokens(
        self, overrides: Mapping[DesignToken[Any], TokenAssignment[Any]]
    ) -> TokenResolver:
        """Return a child scope with a group of token overrides."""
        return TokenResolver(overrides, parent=self)

    def with_token(
        self, token: DesignToken[T], assignment: TokenAssignment[T]
    ) -> TokenResolver:
        """Return a child scope with one token override."""
        return self.with_tokens({token: assignment})

    def inherited(self, token: DesignToken[T]) -> T:
        """Resolve a token while skipping its currently evaluated assignment."""
        for active_token, owner in reversed(self._assigning):
            if active_token is token:
                return self._value_without_override(token, owner)
        raise TokenError(
            f"Design token {token.name!r} has no active assignment to inherit from"
        )

    def _nearest_override(
        self, token: DesignToken[Any]
    ) -> tuple[TokenAssignment[Any] | None, TokenResolver | None]:
        scope: TokenResolver | None = self
        while scope is not None:
            if token in scope._overrides:
                return scope._overrides[token], scope
            scope = scope._parent
        return None, None

    def _value_without_override(
        self, token: DesignToken[T], skipped: TokenResolver
    ) -> T:
        """Resolve against this scope while ignoring one transform layer."""
        scope: TokenResolver | None = self
        while scope is not None:
            if scope is skipped:
                scope = scope._parent
                continue
            if token in scope._overrides:
                override = scope._overrides[token]
                self._assigning.append((token, scope))
                try:
                    return cast(T, override.resolve(self))
                finally:
                    self._assigning.pop()
            scope = scope._parent
        return token.compute_default(self)
