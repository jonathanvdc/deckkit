from __future__ import annotations

from base64 import b64encode
from xml.etree.ElementTree import Element, SubElement, tostring

from ..drawables import (
    Drawable,
    DrawableConnector,
    DrawableGroup,
    DrawableImage,
    DrawableRectangle,
    DrawableRichText,
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

    marker_count = 0

    def visit(node: Drawable, parent: Element) -> None:
        nonlocal marker_count
        group = SubElement(parent, "g", id=node.identity)
        if isinstance(node, (DrawableText, DrawableRectangle, DrawableImage)):
            b = node.content_bounds
            x, y, w, h = b.x.points, b.y.points, b.width.points, b.height.points
        if isinstance(node, DrawableRectangle):
            attributes = {
                "x": str(x),
                "y": str(y),
                "width": str(w),
                "height": str(h),
                "fill": node.color,
            }
            if node.corner_radius.points > 0:
                attributes["rx"] = attributes["ry"] = str(node.corner_radius.points)
            SubElement(group, "rect", attributes)
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
                        "{http://www.w3.org/XML/1998/namespace}space": "preserve",
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
        elif isinstance(node, DrawableConnector):
            attributes = {
                "x1": str(node.start.x.points),
                "y1": str(node.start.y.points),
                "x2": str(node.end.x.points),
                "y2": str(node.end.y.points),
                "stroke": node.color,
                "stroke-width": "2",
            }
            for cap, attribute, orient in (
                (node.start_cap, "marker-start", "auto-start-reverse"),
                (node.end_cap, "marker-end", "auto"),
            ):
                if cap == "arrow":
                    marker_count += 1
                    marker_id = f"deckkit-arrow-{marker_count}"
                    marker = SubElement(
                        group,
                        "marker",
                        id=marker_id,
                        markerWidth="6",
                        markerHeight="6",
                        refX="5",
                        refY="3",
                        orient=orient,
                        markerUnits="strokeWidth",
                    )
                    SubElement(marker, "path", d="M 0 0 L 6 3 L 0 6 z", fill=node.color)
                    attributes[attribute] = f"url(#{marker_id})"
            SubElement(group, "line", attributes)
        elif not isinstance(node, (DrawableGroup, DrawableRichText)):
            raise TypeError(f"SVG cannot render {type(node).__name__}")
        for child in node.children:
            visit(child, group)

    visit(layout, root)
    return tostring(root, encoding="unicode")
