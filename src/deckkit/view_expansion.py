"""Expand author views into an identity-preserving hierarchy ready for layout."""

from __future__ import annotations

from dataclasses import fields, is_dataclass, replace
from typing import Any
from urllib.parse import quote

from .expanded_views import (
    ExpandedComponent,
    ExpandedLayout,
    ExpandedMetadata,
    ExpandedView,
)
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
    keys: set[str] = set()

    def visit(
        value: View,
        parent: str,
        slot: str | int,
        context: Context,
        depth: int = 0,
    ) -> ExpandedView:
        if depth > 100:
            raise ValueError("Composite body recursion exceeds 100 levels")
        mods: dict[str, Any] = dict(value._modifiers)
        typename = type(value).__module__ + "." + type(value).__qualname__
        if "key" in mods:
            key = mods["key"]
            if key in keys:
                raise ValueError(f"Duplicate slide key: {key!r}")
            keys.add(key)
            identity = f"key:{quote(key, safe='')}:{typename}"
        else:
            identity = f"{parent}/{slot}:{typename}"
        environment = context.environment
        for modifier in value._modifiers:
            if modifier[0] == "environment":
                key, setting = modifier[1]
                environment = environment.setting(key, setting)
        local_context = replace(context, environment=environment)
        animation = mods.get("animation")
        transition = mods.get("transition")
        boundary = mods.get("boundary", False)
        metadata = ExpandedMetadata(
            identity, value._modifiers, animation, transition, boundary
        )
        expanded: ExpandedView
        if isinstance(value, PrimitiveView):
            expanded = value.expand(local_context, metadata)
        elif isinstance(value, LayoutView):
            children = tuple(
                visit(c, identity, i, local_context, depth + 1)
                for i, c in enumerate(value.children)
                if c is not None
            )
            expanded = ExpandedLayout(
                metadata,
                value.layout,
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
                (visit(body, identity, "body", local_context, depth + 1),),
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

    return visit(view, "slide", 0, context)
