import pytest

from deckkit.backends import svg
from deckkit.canvas import Rect
from deckkit.charts import (
    Axis,
    BandScaleSpec,
    BarMark,
    Chart,
    ChartContent,
    CompositeChartContent,
    DomainContribution,
    LinearScaleSpec,
    OrdinalScaleSpec,
    PointMark,
    nice_ticks,
    value,
)
from deckkit.drawables import Bounds, DrawableEllipse, DrawableRectangle
from deckkit.theme import Color
from deckkit.units import pt


class SampleContent(ChartContent):
    def __init__(self, key: str):
        self.key = key

    def domain_contributions(self):
        return (DomainContribution.quantitative("x", (1, 2)),)

    def lower(self, context):
        return (Rect(Bounds(pt(0), pt(0), pt(1), pt(1)), key=self.key),)


def test_linear_scale_infers_expands_and_reverses_domains():
    scale = LinearScaleSpec(include_zero=True).resolve((2, 6), (pt(100), pt(0)))

    assert scale.domain == (0, 6)
    assert scale(0) == pt(100)
    assert scale(3) == pt(50)
    assert scale(6) == pt(0)
    assert LinearScaleSpec().infer_domain((4, 4)) == (3.8, 4.2)


def test_linear_scale_expands_to_nice_domain_and_plans_round_ticks():
    scale = LinearScaleSpec().resolve((18, 54), (pt(0), pt(100)))

    assert scale.domain == (10, 60)
    assert nice_ticks(scale.domain) == (10, 20, 30, 40, 50, 60)
    assert nice_ticks((6.2, 16.8)) == (8, 10, 12, 14, 16)


def test_linear_scale_rejects_invalid_values_and_domains():
    with pytest.raises(ValueError, match="ordered"):
        LinearScaleSpec(domain=(2, 1)).infer_domain(())
    with pytest.raises(ValueError, match="finite"):
        LinearScaleSpec().infer_domain((float("nan"),))


def test_band_scale_preserves_order_and_applies_padding():
    scale = BandScaleSpec[str](padding_inner=0.2, padding_outer=0.1).resolve(
        ("b", "a", "b", "c"), (pt(0), pt(300))
    )

    assert scale.domain == ("b", "a", "c")
    assert scale.step == pt(100)
    assert scale.bandwidth == pt(80)
    assert scale("b") == pt(10)
    assert scale.center("a") == pt(150)
    with pytest.raises(KeyError):
        scale("missing")


def test_ordinal_scale_cycles_outputs_over_inferred_domain():
    scale = OrdinalScaleSpec[str, str](("red", "blue")).resolve(("a", "b", "c"))

    assert scale("a") == "red"
    assert scale("b") == "blue"
    assert scale("c") == "red"


def test_chart_content_composes_domains_and_canvas_elements():
    content = CompositeChartContent(SampleContent("a"), SampleContent("b"))

    assert [item.values for item in content.domain_contributions()] == [(1, 2), (1, 2)]


def test_value_encoding_extracts_typed_values():
    encoding = value("Amount", lambda row: row["amount"])

    assert encoding({"amount": 42}) == 42
    assert encoding.label == "Amount"


def test_chart_resolves_scales_in_final_frame_and_clips_content(compiler):
    observed = []

    class RecordingContent(ChartContent):
        def domain_contributions(self):
            return (
                DomainContribution.categorical("x", ("a", "b")),
                DomainContribution.quantitative("y", (10, 20)),
            )

        def lower(self, context):
            observed.append(context)
            return (Rect(context.plot_bounds, key="plot"),)

    compiled = compiler.compile_view(
        Chart(RecordingContent(), x_axis=None, y_axis=None).frame(
            width=pt(200), height=pt(100)
        )
    )

    context = observed[-1]
    assert context.plot_bounds == Bounds(pt(12), pt(12), pt(176), pt(76))
    assert context.x_scale.domain == ("a", "b")
    assert context.y_scale.domain == (10, 20)
    assert any(node.identity.endswith("key:plot") for node in compiled.drawable.walk())


def test_chart_rejects_mixed_domain_kinds(compiler):
    class MixedContent(ChartContent):
        def domain_contributions(self):
            return (
                DomainContribution.categorical("x", ("a",)),
                DomainContribution.quantitative("x", (1,)),
            )

        def lower(self, context):
            return ()

    with pytest.raises(ValueError, match="mixes"):
        compiler.compile_view(
            Chart(MixedContent()).frame(width=pt(100), height=pt(100))
        )


def test_chart_axes_measure_labels_and_lower_outside_plot_clip(compiler):
    observed = []

    class AxisContent(ChartContent):
        def domain_contributions(self):
            return (
                DomainContribution.categorical("x", ("First", "Second")),
                DomainContribution.quantitative("y", (0, 100)),
            )

        def lower(self, context):
            observed.append(context)
            return ()

    compiled = compiler.compile_view(
        Chart(AxisContent(), x_axis=Axis(title="Category"), y_axis=Axis()).frame(
            width=pt(240), height=pt(140)
        )
    )
    markup = svg.render(compiled.drawable)

    assert observed[-1].plot_bounds.x > pt(12)
    assert observed[-1].plot_bounds.height < pt(116)
    assert "First" in markup
    assert "Category" in markup
    assert 'font-size="14.0"' in markup


def test_point_mark_lowers_styled_points_with_stable_keys(compiler):
    data = (
        {"id": "a", "x": 1, "y": 4},
        {"id": "b", "x": 2, "y": 7},
    )
    mark = PointMark(
        data,
        x=value("X", lambda row: row["x"]),
        y=value("Revenue", lambda row: row["y"]),
        fill=lambda row: Color("#ff0000") if row["id"] == "a" else Color("#0000ff"),
        radius=lambda row: pt(4 if row["id"] == "a" else 3),
        key=lambda row: row["id"],
    )
    compiled = compiler.compile_view(
        Chart(mark, x_axis=None, y_axis=None).frame(width=pt(200), height=pt(100))
    )
    points = [
        node for node in compiled.drawable.walk() if isinstance(node, DrawableEllipse)
    ]

    assert [point.fill for point in points] == ["#FF0000", "#0000FF"]
    assert points[0].bounds.width == pt(8)
    assert points[0].identity.endswith("key:series:Revenue/datum:a")
    assert points[1].identity.endswith("key:series:Revenue/datum:b")


def test_point_mark_insets_scale_range_for_rendered_radius(compiler):
    observed = []

    class ObservedPointMark(PointMark):
        def lower(self, context):
            observed.append(context)
            return super().lower(context)

    mark = ObservedPointMark(
        ({"x": 0, "y": 0}, {"x": 10, "y": 10}),
        x=value("X", lambda row: row["x"]),
        y=value("Y", lambda row: row["y"]),
        radius=pt(6),
    )
    compiled = compiler.compile_view(
        Chart(
            mark,
            x_scale=LinearScaleSpec(domain=(0, 10)),
            y_scale=LinearScaleSpec(domain=(0, 10)),
            x_axis=None,
            y_axis=None,
        ).frame(width=pt(100), height=pt(100))
    )

    points = [
        node for node in compiled.drawable.walk() if isinstance(node, DrawableEllipse)
    ]
    assert len(points) == 2
    assert observed[-1].x_scale(0) == observed[-1].plot_bounds.x + pt(6)


@pytest.mark.parametrize(
    ("orientation", "expected_count"),
    (("vertical", 2), ("horizontal", 2)),
)
def test_bar_mark_lowers_vertical_and_horizontal_bars(
    compiler, orientation, expected_count
):
    data = (
        {"name": "A", "amount": 4},
        {"name": "B", "amount": 7},
    )
    if orientation == "vertical":
        mark = BarMark(
            data,
            x=value("Name", lambda row: row["name"]),
            y=value("Amount", lambda row: row["amount"]),
            key=lambda row: row["name"],
        )
    else:
        mark = BarMark(
            data,
            x=value("Amount", lambda row: row["amount"]),
            y=value("Name", lambda row: row["name"]),
            orientation="horizontal",
            key=lambda row: row["name"],
        )
    compiled = compiler.compile_view(
        Chart(mark, x_axis=None, y_axis=None).frame(width=pt(200), height=pt(100))
    )
    bars = [
        node for node in compiled.drawable.walk() if isinstance(node, DrawableRectangle)
    ]

    assert len(bars) == expected_count
    assert all(bar.bounds.width > pt(0) and bar.bounds.height > pt(0) for bar in bars)
    assert bars[0].identity.endswith("key:series:Amount/datum:A")
