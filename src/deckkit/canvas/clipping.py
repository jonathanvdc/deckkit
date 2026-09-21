"""Backend-independent rectangular clipping for Canvas drawables."""

from __future__ import annotations

from collections.abc import Callable
from math import cos, pi, sin
from typing import Literal

from ..drawables import (
    Bounds,
    Drawable,
    DrawableEllipse,
    DrawableGroup,
    DrawableLine,
    DrawablePath,
    DrawablePathCommand,
    DrawableRectangle,
    DrawableText,
    PathClose,
    PathCubic,
    PathLine,
    PathMove,
    PathQuadratic,
)
from ..geometry import Point
from ..units import Length, pt


def clip_drawable(node: Drawable, clip: Bounds) -> Drawable:
    if isinstance(node, DrawableRectangle):
        bounds = _intersection(node.content_bounds, clip)
        if bounds is None:
            return _empty(node)
        return DrawableRectangle(
            node.identity,
            bounds,
            node.metadata,
            bounds,
            node.color,
            min(node.corner_radius, bounds.width / 2, bounds.height / 2),
            node.stroke,
            node.stroke_width,
            node.dash,
            node.fill_opacity,
            node.stroke_opacity,
            node.line_cap,
            node.line_join,
        )
    if isinstance(node, DrawableLine):
        segment = _clip_segment(node.start, node.end, clip)
        if segment is None:
            return _empty(node)
        start, end = segment
        return DrawableLine(
            node.identity,
            _point_bounds((start, end)),
            node.metadata,
            start,
            end,
            node.color,
            node.width,
            node.dash,
            node.opacity,
            node.line_cap,
            node.line_join,
        )
    if isinstance(node, DrawableEllipse):
        if _contains(clip, node.content_bounds):
            return node
        if _intersection(node.content_bounds, clip) is None:
            return _empty(node)
        center = Point(
            node.content_bounds.x + node.content_bounds.width / 2,
            node.content_bounds.y + node.content_bounds.height / 2,
        )
        points = tuple(
            Point(
                center.x + node.content_bounds.width / 2 * cos(i * 2 * pi / 48),
                center.y + node.content_bounds.height / 2 * sin(i * 2 * pi / 48),
            )
            for i in range(48)
        )
        return _polygon_drawable(
            node,
            _clip_polygon(points, clip),
            node.fill,
            node.stroke,
            node.stroke_width,
            node.dash,
            node.fill_opacity,
            node.stroke_opacity,
            node.line_cap,
            node.line_join,
        )
    if isinstance(node, DrawablePath):
        points, closed = _flatten(node)
        if closed and node.fill is not None:
            return _polygon_drawable(
                node,
                _clip_polygon(points, clip),
                node.fill,
                node.stroke,
                node.stroke_width,
                node.dash,
                node.fill_opacity,
                node.stroke_opacity,
                node.line_cap,
                node.line_join,
            )
        commands: list[DrawablePathCommand] = []
        previous_end = None
        for start, end in zip(points, points[1:]):
            segment = _clip_segment(start, end, clip)
            if segment is None:
                previous_end = None
                continue
            clipped_start, clipped_end = segment
            if previous_end != clipped_start:
                commands.append(PathMove(clipped_start))
            commands.append(PathLine(clipped_end))
            previous_end = clipped_end
        if not commands:
            return _empty(node)
        bounds = _point_bounds(
            tuple(
                command.point
                for command in commands
                if isinstance(command, (PathMove, PathLine))
            )
        )
        return DrawablePath(
            node.identity,
            bounds,
            node.metadata,
            tuple(commands),
            None,
            node.stroke,
            node.stroke_width,
            node.dash,
            1.0,
            node.stroke_opacity,
            node.line_cap,
            node.line_join,
        )
    if isinstance(node, DrawableText):
        return node if _intersection(node.bounds, clip) is not None else _empty(node)
    return node


def _empty(node: Drawable) -> DrawableGroup:
    return DrawableGroup(node.identity, node.bounds, node.metadata, ())


def _intersection(first: Bounds, second: Bounds) -> Bounds | None:
    left = max(first.x, second.x)
    top = max(first.y, second.y)
    right = min(first.x + first.width, second.x + second.width)
    bottom = min(first.y + first.height, second.y + second.height)
    if right <= left or bottom <= top:
        return None
    return Bounds(left, top, right - left, bottom - top)


def _contains(outer: Bounds, inner: Bounds) -> bool:
    return (
        inner.x >= outer.x
        and inner.y >= outer.y
        and inner.x + inner.width <= outer.x + outer.width
        and inner.y + inner.height <= outer.y + outer.height
    )


def _clip_segment(start: Point, end: Point, clip: Bounds) -> tuple[Point, Point] | None:
    x0, y0 = start.x.points, start.y.points
    dx, dy = end.x.points - x0, end.y.points - y0
    minimum, maximum = 0.0, 1.0
    for p, q in (
        (-dx, x0 - clip.x.points),
        (dx, clip.x.points + clip.width.points - x0),
        (-dy, y0 - clip.y.points),
        (dy, clip.y.points + clip.height.points - y0),
    ):
        if p == 0:
            if q < 0:
                return None
            continue
        ratio = q / p
        if p < 0:
            minimum = max(minimum, ratio)
        else:
            maximum = min(maximum, ratio)
        if minimum > maximum:
            return None
    return (
        Point(pt(x0 + minimum * dx), pt(y0 + minimum * dy)),
        Point(pt(x0 + maximum * dx), pt(y0 + maximum * dy)),
    )


def _flatten(node: DrawablePath) -> tuple[tuple[Point, ...], bool]:
    result = []
    current = None
    start = None
    closed = False
    for command in node.commands:
        if isinstance(command, PathMove):
            current = start = command.point
            result.append(current)
        elif isinstance(command, PathLine) and current is not None:
            current = command.point
            result.append(current)
        elif isinstance(command, PathQuadratic) and current is not None:
            origin = current
            for index in range(1, 17):
                amount = index / 16
                inverse = 1 - amount
                result.append(
                    Point(
                        origin.x * (inverse * inverse)
                        + command.control.x * (2 * inverse * amount)
                        + command.end.x * (amount * amount),
                        origin.y * (inverse * inverse)
                        + command.control.y * (2 * inverse * amount)
                        + command.end.y * (amount * amount),
                    )
                )
            current = command.end
        elif isinstance(command, PathCubic) and current is not None:
            origin = current
            for index in range(1, 17):
                amount = index / 16
                inverse = 1 - amount
                result.append(
                    Point(
                        origin.x * (inverse**3)
                        + command.control1.x * (3 * inverse * inverse * amount)
                        + command.control2.x * (3 * inverse * amount * amount)
                        + command.end.x * (amount**3),
                        origin.y * (inverse**3)
                        + command.control1.y * (3 * inverse * inverse * amount)
                        + command.control2.y * (3 * inverse * amount * amount)
                        + command.end.y * (amount**3),
                    )
                )
            current = command.end
        elif isinstance(command, PathClose) and start is not None:
            result.append(start)
            current = start
            closed = True
    return tuple(result), closed


def _clip_polygon(points: tuple[Point, ...], clip: Bounds) -> tuple[Point, ...]:
    result = list(points)
    edges: tuple[
        tuple[Callable[[Point], bool], Callable[[Point, Point], Point]], ...
    ] = (
        (lambda p: p.x >= clip.x, lambda a, b: _vertical(a, b, clip.x)),
        (
            lambda p: p.x <= clip.x + clip.width,
            lambda a, b: _vertical(a, b, clip.x + clip.width),
        ),
        (lambda p: p.y >= clip.y, lambda a, b: _horizontal(a, b, clip.y)),
        (
            lambda p: p.y <= clip.y + clip.height,
            lambda a, b: _horizontal(a, b, clip.y + clip.height),
        ),
    )
    for inside, intersection in edges:
        source, result = result, []
        if not source:
            break
        previous = source[-1]
        for current in source:
            if inside(current):
                if not inside(previous):
                    result.append(intersection(previous, current))
                result.append(current)
            elif inside(previous):
                result.append(intersection(previous, current))
            previous = current
    return tuple(result)


def _vertical(start: Point, end: Point, x: Length) -> Point:
    amount = (x - start.x) / (end.x - start.x)
    return Point(x, start.y + (end.y - start.y) * amount)


def _horizontal(start: Point, end: Point, y: Length) -> Point:
    amount = (y - start.y) / (end.y - start.y)
    return Point(start.x + (end.x - start.x) * amount, y)


def _polygon_drawable(
    node: Drawable,
    points: tuple[Point, ...],
    fill: str | None,
    stroke: str | None,
    stroke_width: Length,
    dash: tuple[Length, ...],
    fill_opacity: float,
    stroke_opacity: float,
    line_cap: Literal["butt", "round", "square"],
    line_join: Literal["miter", "round", "bevel"],
) -> Drawable:
    if len(points) < 3:
        return _empty(node)
    commands: tuple[DrawablePathCommand, ...] = (
        PathMove(points[0]),
        *(PathLine(point) for point in points[1:]),
        PathClose(),
    )
    return DrawablePath(
        node.identity,
        _point_bounds(points),
        node.metadata,
        commands,
        fill,
        stroke,
        stroke_width,
        dash,
        fill_opacity,
        stroke_opacity,
        line_cap,
        line_join,
    )


def _point_bounds(points: tuple[Point, ...]) -> Bounds:
    left = min(point.x for point in points)
    top = min(point.y for point in points)
    right = max(point.x for point in points)
    bottom = max(point.y for point in points)
    return Bounds(left, top, right - left, bottom - top)
