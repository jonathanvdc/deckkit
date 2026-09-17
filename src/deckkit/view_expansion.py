"""Expand author views into an identity-preserving hierarchy ready for layout."""

from __future__ import annotations

from dataclasses import fields, is_dataclass, replace
from typing import Any

from .expanded_views import (
    ExpandedComponent,
    ExpandedLayout,
    ExpandedMetadata,
    ExpandedView,
)
from .identity import KeyScope, ScopedKey, ViewIdentity
from .layouts import FrameLayout, PaddingLayout, PassthroughLayout
from .views import (
    CompositeView,
    Context,
    LayoutView,
    PrimitiveView,
    Stack,
    View,
)


def expand_view(
    view: View,
    context: Context,
) -> ExpandedView:
    """Expand composite bodies, select theme styles and attach layout policies."""
    keys: dict[ScopedKey, ViewIdentity] = {}

    def visit(
        value: View,
        parent: ViewIdentity,
        slot: str | int,
        context: Context,
        key_scope: KeyScope,
        depth: int = 0,
    ) -> ExpandedView:
        if depth > 100:
            raise ValueError("Composite body recursion exceeds 100 levels")
        mods: dict[str, Any] = dict(value._modifiers)
        view_type = type(value)
        typename = view_type.__module__ + "." + view_type.__qualname__
        key: str | None = None
        if "key" in mods:
            key = mods["key"]
            reference = ScopedKey(key_scope, key)
            if reference in keys:
                raise ValueError(f"Duplicate key {key!r} in scope {key_scope.owner}")
            identity = key_scope.owner.keyed(key, view_type)
            keys[reference] = identity
        else:
            identity = parent.child(slot, view_type)
        environment = context.environment
        for modifier in value._modifiers:
            if modifier[0] == "environment":
                environment_key, setting = modifier[1]
                environment = environment.setting(environment_key, setting)
        local_context = replace(context, environment=environment)
        animation = mods.get("animation")
        transition = mods.get("transition")
        boundary = mods.get("boundary", False)
        metadata = ExpandedMetadata(
            identity,
            key,
            key_scope,
            value._modifiers,
            animation,
            transition,
            boundary,
        )
        expanded: ExpandedView
        if isinstance(value, PrimitiveView):
            expanded = value.expand(local_context, metadata)
        elif isinstance(value, LayoutView):
            children = tuple(
                visit(c, identity, i, local_context, key_scope, depth + 1)
                for i, c in enumerate(value.children)
                if c is not None
            )

            def resolve_key(key: str) -> ViewIdentity:
                try:
                    return keys[ScopedKey(key_scope, key)]
                except KeyError:
                    raise ValueError(
                        f"Unknown key {key!r} in annotation scope {key_scope.owner}"
                    ) from None

            expanded = ExpandedLayout(
                metadata,
                value.resolve_layout(resolve_key),
                children,
                value.spacing if isinstance(value, Stack) else None,
            )
        elif isinstance(value, CompositeView):
            semantic = ()
            if is_dataclass(value):
                semantic = tuple(
                    (f.name, getattr(value, f.name)) for f in fields(value)
                )
            body = value.body(local_context)
            if not isinstance(body, View):
                raise TypeError(f"{typename}.body() must return a View")
            expanded = ExpandedComponent(
                metadata,
                PassthroughLayout(),
                (
                    visit(
                        body,
                        identity,
                        "body",
                        local_context,
                        KeyScope(identity),
                        depth + 1,
                    ),
                ),
                typename,
                semantic,
            )
        else:
            raise TypeError(
                f"Unsupported view type: {typename}; inherit CompositeView for body-based composition or use LayoutView"
            )
        for modifier in value._modifiers:
            if modifier[0] == "padding":
                expanded = replace(
                    expanded, layout=PaddingLayout(expanded.layout, modifier[1])
                )
            elif modifier[0] == "frame":
                expanded = replace(
                    expanded, layout=FrameLayout(expanded.layout, *modifier[1])
                )
        return expanded

    root = ViewIdentity.root("slide")
    return visit(view, root, 0, context, KeyScope(root))
