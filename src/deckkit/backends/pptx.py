"""Editable static slides. This backend never measures or evaluates author views."""

from __future__ import annotations

from collections.abc import Iterable
from io import BytesIO
from os import PathLike

from ..drawables import (
    Drawable,
    DrawableConnector,
    DrawableGroup,
    DrawableImage,
    DrawableRectangle,
    DrawableText,
)


def render(layouts: Iterable[Drawable], path: str | PathLike[str]) -> None:
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
    from pptx.enum.text import MSO_AUTO_SIZE
    from pptx.util import Pt

    def color(value: str) -> RGBColor:
        # python-pptx exposes this factory without a function annotation.
        return RGBColor.from_string(value[1:])  # type: ignore[no-untyped-call, no-any-return]

    layouts = tuple(layouts)
    if not layouts:
        raise ValueError("At least one layout is required")
    prs = Presentation()
    prs.slide_width, prs.slide_height = (
        Pt(layouts[0].bounds.width.points),
        Pt(layouts[0].bounds.height.points),
    )
    for layout in layouts:
        if (layout.bounds.width, layout.bounds.height) != (
            layouts[0].bounds.width,
            layouts[0].bounds.height,
        ):
            raise ValueError("PPTX slides must share a canvas size")
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        for node in layout.walk():
            if isinstance(node, (DrawableText, DrawableRectangle, DrawableImage)):
                b = node.content_bounds
                x, y, w, h = b.x.points, b.y.points, b.width.points, b.height.points
            if isinstance(node, DrawableRectangle):
                shape = slide.shapes.add_shape(
                    MSO_SHAPE.RECTANGLE, Pt(x), Pt(y), Pt(w), Pt(h)
                )
                shape.fill.solid()
                shape.fill.fore_color.rgb = color(node.color)
                shape.line.fill.background()
                shape.name = node.identity
            elif isinstance(node, DrawableText):
                m = node.metrics
                shape = slide.shapes.add_textbox(Pt(x), Pt(y), Pt(max(w, 1)), Pt(h))
                shape.name = node.identity
                tf = shape.text_frame
                tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
                tf.word_wrap = False
                tf.auto_size = MSO_AUTO_SIZE.NONE
                for i, line in enumerate(m.lines):
                    paragraph = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                    paragraph.text = line
                    paragraph.space_before = paragraph.space_after = Pt(0)
                    paragraph.line_spacing = Pt(m.line_height.points)
                    paragraph.font.name = node.font.family
                    paragraph.font.size = Pt(node.font_size.points)
                    paragraph.font.bold = node.font.bold
                    paragraph.font.italic = node.font.italic
                    paragraph.font.color.rgb = color(node.color)
            elif isinstance(node, DrawableImage):
                iw, ih = node.intrinsic_pixels
                if node.fit == "contain":
                    scale = min(w / iw, h / ih)
                    rw, rh = iw * scale, ih * scale
                    shape = slide.shapes.add_picture(
                        BytesIO(node.data),
                        Pt(x + (w - rw) / 2),
                        Pt(y + (h - rh) / 2),
                        Pt(rw),
                        Pt(rh),
                    )
                else:
                    shape = slide.shapes.add_picture(
                        BytesIO(node.data), Pt(x), Pt(y), Pt(w), Pt(h)
                    )
                    scale = max(w / iw, h / ih)
                    shape.crop_left = shape.crop_right = (1 - w / (iw * scale)) / 2
                    shape.crop_top = shape.crop_bottom = (1 - h / (ih * scale)) / 2
                shape.name = node.identity
            elif isinstance(node, DrawableConnector):
                shape = slide.shapes.add_connector(
                    MSO_CONNECTOR.STRAIGHT,
                    Pt(node.start.x.points),
                    Pt(node.start.y.points),
                    Pt(node.end.x.points),
                    Pt(node.end.y.points),
                )
                shape.name = node.identity
                shape.line.color.rgb = color(node.color)
                if node.start_cap == "arrow" or node.end_cap == "arrow":
                    from pptx.oxml.xmlchemy import OxmlElement

                    line = shape.line._get_or_add_ln()
                    if node.start_cap == "arrow":
                        start = OxmlElement("a:headEnd")
                        start.set("type", "triangle")
                        line.append(start)
                    if node.end_cap == "arrow":
                        end = OxmlElement("a:tailEnd")
                        end.set("type", "triangle")
                        line.append(end)
            elif not isinstance(node, DrawableGroup):
                raise TypeError(f"PPTX cannot render {type(node).__name__}")
    prs.save(str(path))
