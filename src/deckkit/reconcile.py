"""Logical reconciliation first; geometry enrichment is a separate pass."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal, TypeVar

from .drawables import Bounds, Drawable
from .view_expansion import ExpandedView


@dataclass(frozen=True)
class Change:
    identity: str
    kind: Literal["insert", "remove", "properties", "reparent", "bounds"]
    before: Mapping[str, Any] | Bounds | str | None = None
    after: Mapping[str, Any] | Bounds | str | None = None
    animation: str | None = None
    transition: str | None = None


TreeT = TypeVar("TreeT", ExpandedView, Drawable)


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
                    after=dict(b.props),
                    transition=b.props.get("transition"),
                )
            )
        elif b is None:
            changes.append(
                Change(
                    key,
                    "remove",
                    before=dict(a.props),
                    transition=a.props.get("transition"),
                )
            )
        else:
            if a.props != b.props or a.modifiers != b.modifiers:
                changes.append(
                    Change(
                        key,
                        "properties",
                        dict(a.props),
                        dict(b.props),
                        b.props.get("animation"),
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
