"""Logical reconciliation first; geometry enrichment is a separate pass."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields
from typing import Any, Literal, TypeVar

from .drawables import Bounds, Drawable
from .expanded_views import ExpandedView


@dataclass(frozen=True)
class Change:
    identity: str
    kind: Literal["insert", "remove", "properties", "reparent", "bounds"]
    before: Mapping[str, Any] | Bounds | str | None = None
    after: Mapping[str, Any] | Bounds | str | None = None
    animation: str | None = None
    transition: str | None = None


TreeT = TypeVar("TreeT", ExpandedView, Drawable)


def _properties(node: ExpandedView) -> dict[str, Any]:
    tracked = {
        item.name: getattr(node.metadata, item.name)
        for item in fields(node.metadata)
        if item.metadata.get("tracked", False)
    }
    tracked.update(
        {
            item.name: getattr(node, item.name)
            for item in fields(node)
            if item.metadata.get("tracked", False)
        }
    )
    return tracked


def _index(root: TreeT) -> tuple[dict[str, TreeT], dict[str, str | None]]:
    nodes: dict[str, TreeT] = {}
    parents: dict[str, str | None] = {}

    def visit(node: TreeT, parent: str | None) -> None:
        nodes[node.identity] = node
        parents[node.identity] = parent
        for ch in node.children:
            visit(ch, node.identity)

    visit(root, None)
    return nodes, parents


def reconcile(before: ExpandedView, after: ExpandedView) -> tuple[Change, ...]:
    old, op = _index(before)
    new, np = _index(after)
    changes = []
    for key in sorted(old.keys() | new.keys()):
        a, b = old.get(key), new.get(key)
        if a is None:
            assert b is not None
            changes.append(
                Change(
                    key,
                    "insert",
                    after=_properties(b),
                    transition=b.transition,
                )
            )
        elif b is None:
            changes.append(
                Change(
                    key,
                    "remove",
                    before=_properties(a),
                    transition=a.transition,
                )
            )
        else:
            if (
                type(a) is not type(b)
                or _properties(a) != _properties(b)
                or a.modifiers != b.modifiers
            ):
                changes.append(
                    Change(
                        key,
                        "properties",
                        _properties(a),
                        _properties(b),
                        b.animation,
                    )
                )
            if op[key] != np[key]:
                changes.append(Change(key, "reparent", op[key], np[key]))
    return tuple(changes)


def with_geometry(
    changes: Sequence[Change], before: Drawable, after: Drawable
) -> tuple[Change, ...]:
    old, _ = _index(before)
    new, _ = _index(after)
    result = list(changes)
    for key in sorted(old.keys() & new.keys()):
        if old[key].bounds != new[key].bounds:
            result.append(
                Change(
                    key,
                    "bounds",
                    old[key].bounds,
                    new[key].bounds,
                    new[key].metadata.animation,
                )
            )
    return tuple(result)
