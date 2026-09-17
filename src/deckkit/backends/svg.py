from __future__ import annotations

from base64 import b64encode
from xml.etree.ElementTree import Element, SubElement, tostring

from ..drawables import (
    Drawable,
    DrawableGroup,
    DrawableImage,
    DrawableRectangle,
    DrawableText,
)


def render(layout: Drawable) -> str:
    root = Element(
        "svg",
        xmlns="http://www.w3.org/2000/svg",
        width=f"{layout.bounds.width.points:g}pt",
        height=f"{layout.bounds.height.points:g}pt",
        viewBox=f"0 0 {layout.bounds.width.points:g} {layout.bounds.height.points:g}",
    )
    SubElement(root, "rect", width="100%", height="100%", fill="white")

    def visit(node: Drawable, parent: Element) -> None:
        group = SubElement(parent, "g", id=node.identity)
        if isinstance(node, (DrawableText, DrawableRectangle, DrawableImage)):
            b = node.content_bounds
            x, y, w, h = b.x.points, b.y.points, b.width.points, b.height.points
        if isinstance(node, DrawableRectangle):
            SubElement(
                group,
                "rect",
                x=str(x),
                y=str(y),
                width=str(w),
                height=str(h),
                fill=node.color,
            )
        elif isinstance(node, DrawableText):
            m = node.metrics
            for i, line in enumerate(m.lines):
                SubElement(
                    group,
                    "text",
                    x=str(x),
                    y=str(y + m.ascent.points + i * m.line_height.points),
                    fill=node.color,
                    attrib={
                        "font-family": node.font.family,
                        "font-size": str(node.font_size.points),
                        "font-weight": "bold" if node.font.bold else "normal",
                        "font-style": "italic" if node.font.italic else "normal",
                    },
                ).text = line
        elif isinstance(node, DrawableImage):
            SubElement(
                group,
                "image",
                x=str(x),
                y=str(y),
                width=str(w),
                height=str(h),
                href=f"data:{node.mime};base64,{b64encode(node.data).decode()}",
                preserveAspectRatio="xMidYMid meet"
                if node.fit == "contain"
                else "xMidYMid slice",
            )
        elif not isinstance(node, DrawableGroup):
            raise TypeError(f"SVG cannot render {type(node).__name__}")
        for child in node.children:
            visit(child, group)

    visit(layout, root)
    return tostring(root, encoding="unicode")
