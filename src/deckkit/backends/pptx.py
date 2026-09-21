"""Static slides and native PowerPoint presentation builds."""

from __future__ import annotations

from io import BytesIO
from os import PathLike
from typing import Any

from ..animation import EffectKind
from ..compiler import CompiledDeck, CompiledSlide
from ..drawables import (
    Drawable,
    DrawableConnector,
    DrawableEllipse,
    DrawableGroup,
    DrawableImage,
    DrawableLine,
    DrawablePath,
    DrawableRectangle,
    DrawableRichText,
    DrawableText,
    PathClose,
    PathLine,
    PathMove,
)
from .pptx_animation import PptxBehaviorKind, PptxTrigger, plan_slide


def _color(value: str) -> Any:
    from pptx.dml.color import RGBColor

    return RGBColor.from_string(value[1:])  # type: ignore[no-untyped-call]


def _apply_stroke(
    line: Any, color: str, width: Any, dash: tuple[Any, ...] = ()
) -> None:
    from pptx.oxml.ns import qn
    from pptx.oxml.xmlchemy import OxmlElement
    from pptx.util import Pt

    line.color.rgb = _color(color)
    line.width = Pt(width.points)
    if not dash:
        return
    values = dash if len(dash) % 2 == 0 else dash + dash
    element = line._get_or_add_ln()
    for existing in tuple(element):
        if existing.tag in (qn("a:prstDash"), qn("a:custDash")):
            element.remove(existing)
    custom = OxmlElement("a:custDash")
    for index in range(0, len(values), 2):
        item = OxmlElement("a:ds")
        item.set("d", str(max(1, round(values[index].points / width.points * 100000))))
        item.set(
            "sp", str(max(1, round(values[index + 1].points / width.points * 100000)))
        )
        custom.append(item)
    element.append(custom)


def _add_node(slide: Any, node: Drawable, *, name: str | None = None) -> Any:
    from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
    from pptx.enum.text import MSO_AUTO_SIZE
    from pptx.oxml.xmlchemy import OxmlElement
    from pptx.util import Pt

    if isinstance(
        node,
        (
            DrawableText,
            DrawableRichText,
            DrawableRectangle,
            DrawableEllipse,
            DrawableImage,
        ),
    ):
        b = node.content_bounds
        x, y, w, h = b.x.points, b.y.points, b.width.points, b.height.points
    if isinstance(node, DrawableRectangle):
        radius = node.corner_radius.points
        shape = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE if radius > 0 else MSO_SHAPE.RECTANGLE,
            Pt(x),
            Pt(y),
            Pt(w),
            Pt(h),
        )
        if radius > 0:
            # DrawingML expresses this adjustment as a fraction of the shape's
            # shorter side; Deckkit's public value is an absolute length.
            shape.adjustments[0] = radius / min(w, h)
        shape.fill.solid()
        shape.fill.fore_color.rgb = _color(node.color)
        shape.line.fill.background()
        if node.stroke is not None:
            _apply_stroke(shape.line, node.stroke, node.stroke_width, node.dash)
    elif isinstance(node, DrawableEllipse):
        shape = slide.shapes.add_shape(MSO_SHAPE.OVAL, Pt(x), Pt(y), Pt(w), Pt(h))
        if node.fill is None:
            shape.fill.background()
        else:
            shape.fill.solid()
            shape.fill.fore_color.rgb = _color(node.fill)
        if node.stroke is None:
            shape.line.fill.background()
        else:
            _apply_stroke(shape.line, node.stroke, node.stroke_width, node.dash)
    elif isinstance(node, DrawableRichText):
        for child in node.children:
            if isinstance(child, DrawableRectangle):
                _add_node(slide, child)
        shape = slide.shapes.add_textbox(Pt(x), Pt(y), Pt(max(w, 1)), Pt(h))
        tf = shape.text_frame
        tf.clear()
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        tf.word_wrap = False
        tf.auto_size = MSO_AUTO_SIZE.NONE
        for line_index, visual_line in enumerate(node.metrics.lines):
            paragraph = tf.paragraphs[0] if line_index == 0 else tf.add_paragraph()
            paragraph.space_before = paragraph.space_after = Pt(0)
            paragraph.line_spacing = Pt(visual_line.height.points)
            for measured_run in visual_line.runs:
                run = paragraph.add_run()
                run.text = measured_run.text
                run.font.name = measured_run.font.family
                run.font.size = Pt(measured_run.font_size.points)
                run.font.bold = measured_run.font.bold
                run.font.italic = measured_run.font.italic
                run.font.color.rgb = _color(measured_run.color)
    elif isinstance(node, DrawableText):
        m = node.metrics
        shape = slide.shapes.add_textbox(Pt(x), Pt(y), Pt(max(w, 1)), Pt(h))
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
            paragraph.font.color.rgb = _color(node.color)
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
    elif isinstance(node, DrawableConnector):
        shape = slide.shapes.add_connector(
            MSO_CONNECTOR.STRAIGHT,
            Pt(node.start.x.points),
            Pt(node.start.y.points),
            Pt(node.end.x.points),
            Pt(node.end.y.points),
        )
        shape.line.color.rgb = _color(node.color)
        if node.start_cap == "arrow" or node.end_cap == "arrow":
            line = shape.line._get_or_add_ln()
            if node.start_cap == "arrow":
                start = OxmlElement("a:headEnd")
                start.set("type", "triangle")
                line.append(start)
            if node.end_cap == "arrow":
                end = OxmlElement("a:tailEnd")
                end.set("type", "triangle")
                line.append(end)
    elif isinstance(node, DrawableLine):
        shape = slide.shapes.add_connector(
            MSO_CONNECTOR.STRAIGHT,
            Pt(node.start.x.points),
            Pt(node.start.y.points),
            Pt(node.end.x.points),
            Pt(node.end.y.points),
        )
        _apply_stroke(shape.line, node.color, node.width, node.dash)
    elif isinstance(node, DrawablePath):
        points = [
            command.point
            for command in node.commands
            if isinstance(command, (PathMove, PathLine))
        ]
        if not points:
            return None
        builder = slide.shapes.build_freeform(
            points[0].x.points,
            points[0].y.points,
            scale=12700,
        )
        builder.add_line_segments(
            [(point.x.points, point.y.points) for point in points[1:]],
            close=any(isinstance(command, PathClose) for command in node.commands),
        )
        shape = builder.convert_to_shape()
        if node.fill is None:
            shape.fill.background()
        else:
            shape.fill.solid()
            shape.fill.fore_color.rgb = _color(node.fill)
        if node.stroke is None:
            shape.line.fill.background()
        else:
            _apply_stroke(shape.line, node.stroke, node.stroke_width, node.dash)
    elif isinstance(node, DrawableGroup):
        return None
    else:
        raise TypeError(f"PPTX cannot render {type(node).__name__}")
    shape.name = name or node.identity
    return shape


def _new_presentation(width: float, height: float) -> Any:
    from pptx import Presentation
    from pptx.util import Pt

    prs = Presentation()
    prs.slide_width, prs.slide_height = Pt(width), Pt(height)
    return prs


def render(deck: CompiledDeck, path: str | PathLike[str]) -> None:
    """Render static and animated logical slides through one PPTX path."""
    if not deck.slides:
        raise ValueError("At least one slide is required")
    first = deck.slides[0].initial.drawable
    prs = _new_presentation(first.bounds.width.points, first.bounds.height.points)
    for compiled_slide in deck.slides:
        layout = compiled_slide.initial.drawable
        if (layout.bounds.width, layout.bounds.height) != (
            first.bounds.width,
            first.bounds.height,
        ):
            raise ValueError("PPTX slides must share a canvas size")
        _render_slide(prs, compiled_slide)
    prs.save(str(path))


def _leaf_index(root: Drawable) -> dict[str, Drawable]:
    return {
        node.identity: node
        for node in _pptx_nodes(root)
        if isinstance(node, DrawableRichText) or not node.children
    }


def _pptx_nodes(root: Drawable) -> list[Drawable]:
    """Flatten a drawable tree while keeping rich text atomic for PowerPoint."""
    result = [root]
    if not isinstance(root, DrawableRichText):
        for child in root.children:
            result.extend(_pptx_nodes(child))
    return result


def _place_shape_in_state_z_order(
    slide: Any,
    shape: Any,
    identity: str,
    state: Drawable,
    shape_ids: dict[tuple[str, int], int],
) -> None:
    """Place an added animation version below later leaves in its state.

    PowerPoint uses document order as z-order. Replacement shapes are created
    after the initial-state shapes, so leaving them appended can put an opaque
    replacement background above unchanged foreground content.
    """
    order = [
        node.identity
        for node in _pptx_nodes(state)
        if isinstance(node, DrawableRichText) or not node.children
    ]
    try:
        following = set(order[order.index(identity) + 1 :])
    except ValueError:
        return
    following_shape_ids = {
        shape_id
        for (candidate_identity, _), shape_id in shape_ids.items()
        if candidate_identity in following
    }
    for candidate in slide.shapes:
        if candidate.shape_id in following_shape_ids:
            candidate._element.addprevious(shape._element)
            return


def _element(name: str, **attributes: object) -> Any:
    from pptx.oxml.xmlchemy import OxmlElement

    result = OxmlElement(name)
    for key, value in attributes.items():
        result.set(key.rstrip("_"), str(value))
    return result


def _common_behavior(
    parent: Any,
    node_id: int,
    duration: int,
    shape_id: int,
    *,
    delay: int | None = None,
    hold: bool = True,
) -> int:
    behavior = _element("p:cBhvr")
    parent.append(behavior)
    attributes: dict[str, object] = {"id": node_id, "dur": max(duration, 1)}
    if hold:
        attributes["fill"] = "hold"
    time_node = _element("p:cTn", **attributes)
    if delay is not None:
        conditions = _element("p:stCondLst")
        conditions.append(_element("p:cond", delay=delay))
        time_node.append(conditions)
    behavior.append(time_node)
    target = _element("p:tgtEl")
    target.append(_element("p:spTgt", spid=shape_id))
    behavior.append(target)
    return node_id + 1


def _set_visibility(
    shape_id: int, node_id: int, visible: bool, *, delay: int = 0
) -> tuple[Any, int]:
    result = _element("p:set")
    node_id = _common_behavior(result, node_id, 1, shape_id, delay=delay)
    behavior = result.find(
        "{http://schemas.openxmlformats.org/presentationml/2006/main}cBhvr"
    )
    names = _element("p:attrNameLst")
    name = _element("p:attrName")
    name.text = "style.visibility"
    names.append(name)
    behavior.append(names)
    destination = _element("p:to")
    destination.append(_element("p:strVal", val=("visible" if visible else "hidden")))
    result.append(destination)
    return result, node_id


def _effect_elements(
    kind: PptxBehaviorKind,
    shape_id: int,
    node_id: int,
    duration: int,
    dx: float = 0,
    dy: float = 0,
) -> tuple[list[Any], int]:
    if kind is PptxBehaviorKind.MOTION:
        result = _element(
            "p:animMotion",
            origin="layout",
            path=f"M 0 0 L {dx:g} {dy:g} E",
            pathEditMode="relative",
            ptsTypes="",
        )
        node_id = _common_behavior(result, node_id, duration, shape_id)
        behavior = result.find(
            "{http://schemas.openxmlformats.org/presentationml/2006/main}cBhvr"
        )
        names = _element("p:attrNameLst")
        for value in ("ppt_x", "ppt_y"):
            item = _element("p:attrName")
            item.text = value
            names.append(item)
        behavior.append(names)
        return [result], node_id
    if kind is PptxBehaviorKind.APPEAR:
        result, node_id = _set_visibility(shape_id, node_id, True)
        return [result], node_id
    if kind is PptxBehaviorKind.DISAPPEAR:
        result, node_id = _set_visibility(shape_id, node_id, False)
        return [result], node_id
    transition = "out" if kind is PptxBehaviorKind.FADE_OUT else "in"
    result = _element("p:animEffect", transition=transition, filter="fade")
    node_id = _common_behavior(result, node_id, duration, shape_id, hold=False)
    if kind is PptxBehaviorKind.FADE_IN:
        visibility, node_id = _set_visibility(shape_id, node_id, True)
        return [visibility, result], node_id
    visibility, node_id = _set_visibility(
        shape_id, node_id, False, delay=max(duration - 1, 0)
    )
    return [result, visibility], node_id


def _preset(kind: PptxBehaviorKind) -> tuple[int | None, str | None]:
    if kind is PptxBehaviorKind.MOTION:
        # PowerPoint classifies native motion effects separately from generic
        # behaviors. Without the path preset metadata, clients can retain the
        # timing row but ignore the animMotion payload during playback.
        return 42, "path"
    if kind in (PptxBehaviorKind.FADE_IN, PptxBehaviorKind.FADE_OUT):
        return 10, "exit" if kind is PptxBehaviorKind.FADE_OUT else "entr"
    if kind in (PptxBehaviorKind.APPEAR, PptxBehaviorKind.DISAPPEAR):
        return 1, "exit" if kind is PptxBehaviorKind.DISAPPEAR else "entr"
    return None, None


def _append_timing(
    slide: Any,
    compiled_slide: CompiledSlide,
    shape_ids: dict[tuple[str, int], int],
) -> None:
    plan = plan_slide(compiled_slide)
    timing = _element("p:timing")
    timing_list = _element("p:tnLst")
    timing.append(timing_list)
    root = _element("p:par")
    timing_list.append(root)
    root_time = _element(
        "p:cTn", id=1, dur="indefinite", restart="never", nodeType="tmRoot"
    )
    root.append(root_time)
    root_children = _element("p:childTnLst")
    root_time.append(root_children)
    sequence_node = _element("p:seq", concurrent=1, nextAc="seek")
    root_children.append(sequence_node)
    sequence_time = _element("p:cTn", id=2, dur="indefinite", nodeType="mainSeq")
    sequence_node.append(sequence_time)
    builds_element = _element("p:childTnLst")
    sequence_time.append(builds_element)

    node_id = 3
    active_version = {identity: 0 for identity, version in shape_ids if version == 0}
    for build_index, (source, lowered) in enumerate(
        zip(compiled_slide.animation.builds, plan.builds), start=1
    ):
        build_par = _element("p:par")
        build_time = _element("p:cTn", id=node_id, fill="hold")
        node_id += 1
        build_par.append(build_time)
        conditions = _element("p:stCondLst")
        conditions.append(
            _element(
                "p:cond",
                delay=(
                    "indefinite"
                    if lowered.trigger is PptxTrigger.ON_CLICK
                    else lowered.delay_ms
                ),
            )
        )
        build_time.append(conditions)
        build_children = _element("p:childTnLst")
        build_time.append(build_children)
        synchronized = _element("p:par")
        build_children.append(synchronized)
        synchronized_time = _element("p:cTn", id=node_id, fill="hold")
        node_id += 1
        synchronized.append(synchronized_time)
        synchronized_conditions = _element("p:stCondLst")
        synchronized_conditions.append(_element("p:cond", delay=0))
        synchronized_time.append(synchronized_conditions)
        effects_element = _element("p:childTnLst")
        synchronized_time.append(effects_element)
        effect_number = 0

        for effect, behavior in zip(source.effects, lowered.behaviors):
            targets: list[tuple[PptxBehaviorKind, int]] = []
            current = active_version.get(effect.identity, 0)
            if behavior.kind is PptxBehaviorKind.CROSSFADE:
                targets.append((PptxBehaviorKind.FADE_OUT, current))
                targets.append((PptxBehaviorKind.FADE_IN, build_index))
                active_version[effect.identity] = build_index
            elif (
                behavior.kind is PptxBehaviorKind.DISCRETE
                and effect.kind is EffectKind.CHANGE
            ):
                targets.append((PptxBehaviorKind.DISAPPEAR, current))
                targets.append((PptxBehaviorKind.APPEAR, build_index))
                active_version[effect.identity] = build_index
            elif (
                behavior.kind is PptxBehaviorKind.DISCRETE
                and effect.kind is EffectKind.MOVE
            ):
                assert behavior.before is not None and behavior.after is not None
                if (behavior.before.width, behavior.before.height) != (
                    behavior.after.width,
                    behavior.after.height,
                ):
                    targets.append((PptxBehaviorKind.DISAPPEAR, current))
                    targets.append((PptxBehaviorKind.APPEAR, build_index))
                    active_version[effect.identity] = build_index
                else:
                    targets.append((PptxBehaviorKind.MOTION, current))
            else:
                if effect.kind is EffectKind.INSERT:
                    current = build_index
                    active_version[effect.identity] = current
                targets.append((behavior.kind, current))
            for target_kind, version in targets:
                shape_id = shape_ids[(effect.identity, version)]
                dx = dy = 0.0
                if behavior.before is not None and behavior.after is not None:
                    width = compiled_slide.initial.drawable.bounds.width.points
                    height = compiled_slide.initial.drawable.bounds.height.points
                    dx = (behavior.after.x - behavior.before.x).points / width
                    dy = (behavior.after.y - behavior.before.y).points / height
                preset_id, preset_class = _preset(target_kind)
                effect_attributes: dict[str, object] = {
                    "id": node_id,
                    "fill": "hold",
                    "grpId": 0,
                    "nodeType": (
                        (
                            "clickEffect"
                            if lowered.trigger is PptxTrigger.ON_CLICK
                            else (
                                "withEffect"
                                if lowered.trigger is PptxTrigger.WITH_PREVIOUS
                                else "afterEffect"
                            )
                        )
                        if effect_number == 0
                        else "withEffect"
                    ),
                }
                if preset_id is not None:
                    effect_attributes.update(
                        presetID=preset_id,
                        presetClass=preset_class,
                        presetSubtype=0,
                    )
                effect_number += 1
                effect_par = _element("p:par")
                effect_time = _element("p:cTn", **effect_attributes)
                node_id += 1
                effect_par.append(effect_time)
                effect_conditions = _element("p:stCondLst")
                effect_conditions.append(_element("p:cond", delay=behavior.delay_ms))
                effect_time.append(effect_conditions)
                behavior_list = _element("p:childTnLst")
                effect_time.append(behavior_list)
                elements, node_id = _effect_elements(
                    target_kind,
                    shape_id,
                    node_id,
                    behavior.duration_ms,
                    dx,
                    dy,
                )
                for element in elements:
                    behavior_list.append(element)
                effects_element.append(effect_par)
        builds_element.append(build_par)
    for name, event in (("p:prevCondLst", "onPrev"), ("p:nextCondLst", "onNext")):
        navigation = _element(name)
        condition = _element("p:cond", evt=event, delay=0)
        target = _element("p:tgtEl")
        target.append(_element("p:sldTgt"))
        condition.append(target)
        navigation.append(condition)
        sequence_node.append(navigation)
    power_point_builds = _element("p:bldLst")
    for shape_id in sorted(set(shape_ids.values())):
        power_point_builds.append(_element("p:bldP", spid=shape_id, grpId=0))
    timing.append(power_point_builds)
    slide._element.append(timing)


def _render_slide(prs: Any, compiled_slide: CompiledSlide) -> None:
    initial = compiled_slide.initial.drawable
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    if not compiled_slide.is_animated:
        for node in _pptx_nodes(initial):
            _add_node(slide, node)
        return
    shape_ids: dict[tuple[str, int], int] = {}
    for identity, node in _leaf_index(initial).items():
        shape = _add_node(slide, node)
        shape_ids[(identity, 0)] = shape.shape_id

    lowered = plan_slide(compiled_slide)
    for build_index, (build, planned) in enumerate(
        zip(compiled_slide.animation.builds, lowered.builds), start=1
    ):
        for effect, behavior in zip(build.effects, planned.behaviors):
            discrete_resize = (
                effect.kind is EffectKind.MOVE
                and behavior.kind is PptxBehaviorKind.DISCRETE
                and behavior.before is not None
                and behavior.after is not None
                and (behavior.before.width, behavior.before.height)
                != (behavior.after.width, behavior.after.height)
            )
            if (
                effect.kind in (EffectKind.INSERT, EffectKind.CHANGE)
                or (
                    effect.kind is EffectKind.MOVE
                    and behavior.kind is PptxBehaviorKind.CROSSFADE
                )
                or discrete_resize
            ):
                assert effect.after is not None
                shape = _add_node(
                    slide,
                    effect.after.drawable,
                    name=f"{effect.identity}#build-{build_index}",
                )
                shape_ids[(effect.identity, build_index)] = shape.shape_id
                _place_shape_in_state_z_order(
                    slide,
                    shape,
                    effect.identity,
                    compiled_slide.states[build_index].drawable,
                    shape_ids,
                )

    _append_timing(slide, compiled_slide, shape_ids)
