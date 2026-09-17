"""Expand author views into an identity-preserving hierarchy ready for layout."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, fields, is_dataclass
from io import BytesIO
from pathlib import Path
from types import MappingProxyType
from typing import Any
from urllib.parse import quote

from PIL import Image as PILImage

from .fonts import FontResolver, SystemFontResolver
from .layout import Layout
from .layouts import (
    FrameLayout,
    ImageLayout,
    PaddingLayout,
    PassthroughLayout,
    ShapeLayout,
    TextLayout,
)
from .measurement import PillowMeasurer, TextMeasurer
from .units import inch
from .views import (
    CompositeView,
    Context,
    Image,
    LayoutView,
    Modifier,
    PrimitiveView,
    Rectangle,
    Stack,
    Text,
    View,
)


@dataclass(frozen=True)
class ExpandedView:
    """One occurrence in an expanded view hierarchy, before layout.

    Composite bodies have been evaluated and semantic styles/fonts selected.
    Identity, properties, modifier order and component ancestry are retained;
    layout policies describe how to measure this occurrence. Concrete bounds
    belong to the later Drawable representation.
    """

    identity: str
    kind: str
    props: Mapping[str, Any]
    modifiers: tuple[Modifier, ...]
    children: tuple[ExpandedView, ...]
    layout: Layout

    def walk(self) -> Iterator[ExpandedView]:
        yield self
        for child in self.children:
            yield from child.walk()


def expand_view(
    view: View,
    context: Context,
    measurer: TextMeasurer | None = None,
    font_resolver: FontResolver | None = None,
) -> ExpandedView:
    """Expand composite bodies, select theme styles and attach layout policies."""
    measurer = measurer if measurer is not None else PillowMeasurer()
    font_resolver = font_resolver if font_resolver is not None else SystemFontResolver()
    keys: set[str] = set()

    def visit(
        value: View,
        parent: str,
        slot: str | int,
        inherited: Mapping[str, str],
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
        style = dict(inherited)
        style.update({k: mods[k] for k in ("font", "color") if k in mods})
        theme = context.environment.theme
        props: dict[str, Any] = {
            "animation": mods.get("animation"),
            "transition": mods.get("transition"),
            "boundary": mods.get("boundary", False),
        }
        children: tuple[ExpandedView, ...] = ()
        policy: Layout
        if isinstance(value, Text):
            kind = "text"
            typography = theme.text_style(style["font"])
            props.update(
                text=value.text,
                font=font_resolver.resolve(typography.font),
                requested_font=typography.font,
                font_size=typography.size,
                color=theme.color(style["color"]),
                line_spacing=typography.line_spacing,
            )
            policy = TextLayout(
                value.text,
                props["font"],
                props["font_size"],
                props["line_spacing"],
                measurer,
            )
        elif isinstance(value, Rectangle):
            policy = ShapeLayout()
            kind = "rectangle"
            props["color"] = theme.color(style["color"])
        elif isinstance(value, Image):
            kind = "image"
            data = Path(value.source).read_bytes()
            with PILImage.open(BytesIO(data)) as image:
                width, height = image.size
                mime = PILImage.MIME[image.format or ""]
            props.update(data=data, intrinsic=(width, height), mime=mime, fit=value.fit)
            policy = ImageLayout(inch(width / value.dpi), inch(height / value.dpi))
        elif isinstance(value, LayoutView):
            kind = value.layout_kind
            policy = value.layout
            if isinstance(value, Stack):
                props["spacing"] = value.spacing
            children = tuple(
                visit(c, identity, i, style, depth + 1)
                for i, c in enumerate(value.children)
                if c is not None
            )
        elif isinstance(value, CompositeView):
            policy = PassthroughLayout()
            kind = "component"
            props["component_type"] = typename
            if is_dataclass(value):
                props["semantic"] = tuple(
                    (f.name, getattr(value, f.name)) for f in fields(value)
                )
            body = value.body(context)
            if not isinstance(body, View):
                raise TypeError(f"{typename}.body() must return a View")
            children = (visit(body, identity, "body", style, depth + 1),)
        elif isinstance(value, PrimitiveView):
            raise TypeError(
                f"Unsupported primitive view: {typename}; add resolver and backend support"
            )
        else:
            raise TypeError(
                f"Unsupported view type: {typename}; inherit CompositeView for body-based composition or use LayoutView"
            )
        for modifier in value._modifiers:
            if modifier[0] == "padding":
                policy = PaddingLayout(policy, modifier[1])
            elif modifier[0] == "frame":
                policy = FrameLayout(policy, *modifier[1])
        return ExpandedView(
            identity, kind, MappingProxyType(props), value._modifiers, children, policy
        )

    return visit(view, "slide", 0, {"font": "body", "color": "primary"})
