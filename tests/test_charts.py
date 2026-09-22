import pytest

from deckkit.charts import BandScaleSpec, LinearScaleSpec, OrdinalScaleSpec
from deckkit.units import pt


def test_linear_scale_infers_expands_and_reverses_domains():
    scale = LinearScaleSpec(include_zero=True).resolve((2, 6), (pt(100), pt(0)))

    assert scale.domain == (0, 6)
    assert scale(0) == pt(100)
    assert scale(3) == pt(50)
    assert scale(6) == pt(0)
    assert LinearScaleSpec().infer_domain((4, 4)) == (3.8, 4.2)


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
