from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from deckkit import CompiledDeck, Compiler
from deckkit.animation import Animation, FallbackPolicy, Transition
from deckkit.backends import pptx, svg
from deckkit.drawables import DrawableText
from deckkit.expanded_views import ExpandedLayout, ExpandedView
from deckkit.fonts import FileFontResolver, Font
from deckkit.layout import LayoutOverflow
from deckkit.layouts import OverlayLayout, StackLayout
from deckkit.measurement import PillowMeasurer
from deckkit.themes import ClarityTheme
from deckkit.units import pt
from deckkit.views import HStack, Image, Rectangle, State, Text, VStack
from examples.api_sketch import (
    CodeSlide,
    ComparisonSlide,
    MetricsSlide,
    PipelineSlide,
    ResultsSlide,
)
from examples.themes import EditorialTheme


def test_package_root_only_exposes_compilation_entry_points():
    import deckkit

    assert deckkit.__all__ == [
        "CompiledDeck",
        "CompiledSlide",
        "CompiledView",
        "Compiler",
        "Deck",
    ]
    assert not hasattr(deckkit, "ExpandedComponent")
    assert not hasattr(deckkit, "Text")
    assert not hasattr(deckkit, "ClarityTheme")


def test_code_example_compiles(compiler):
    compiled = compiler.compile_view(CodeSlide())
    assert any(node.identity.endswith("Code") for node in compiled.expanded_tree.walk())


def keyed(root, key):
    return next(n for n in root.walk() if f"key:{key}:" in n.identity)


def test_theme_changes_structure(font):
    source = ComparisonSlide()
    a = Compiler(
        ClarityTheme(),
        font_resolver=FileFontResolver({Font("Aptos"): font, Font("Aptos Mono"): font}),
    ).compile_view(source)
    b = Compiler(
        EditorialTheme(),
        font_resolver=FileFontResolver({Font("Aptos"): font, Font("Aptos Mono"): font}),
    ).compile_view(source)
    assert any(
        isinstance(n, ExpandedLayout)
        and isinstance(n.layout, StackLayout)
        and n.layout.axis == "horizontal"
        for n in a.expanded_tree.walk()
    )
    assert any(
        isinstance(n, ExpandedLayout) and isinstance(n.layout, OverlayLayout)
        for n in b.expanded_tree.walk()
    )
    assert all(isinstance(n, ExpandedView) for n in b.expanded_tree.walk())
    assert "BeforeAfter" not in Path("src/deckkit/backends/svg.py").read_text()


def test_real_wrapping(font):

    font = FileFontResolver({Font("Test Font"): font}).resolve(Font("Test Font"))
    m = PillowMeasurer()
    wide = m.measure(
        "Compiler performance improves with fewer intermediate passes",
        font,
        pt(20),
        pt(600),
        1.1,
    )
    narrow = m.measure(
        "Compiler performance improves with fewer intermediate passes",
        font,
        pt(20),
        pt(150),
        1.1,
    )
    assert narrow.height > wide.height
    assert (
        m.measure("WWW", font, pt(20), pt(600), 1.1).width
        > m.measure("iii", font, pt(20), pt(600), 1.1).width
    )


def test_fixed_intrinsic_flex(compiler):
    result = compiler.compile_view(
        HStack(
            Rectangle().frame(width=pt(100), height=pt(20)),
            Text("Hello"),
            Rectangle().flex(),
            Rectangle().flex(2),
            spacing=pt(10),
        )
    )
    a, b, c, d = result.drawable.children[0].children
    assert a.bounds.width == pt(100)
    assert b.bounds.width > pt(0)
    assert d.bounds.width.points == pytest.approx(2 * c.bounds.width.points)
    assert (d.bounds.x + d.bounds.width).points == pytest.approx(960)
    assert result.expanded_tree.spacing == pt(10)


def test_overflow(compiler):
    with pytest.raises(LayoutOverflow) as error:
        compiler.compile_view(
            Text("This cannot fit").frame(width=pt(30), height=pt(10))
        )
    assert error.value.required[0] > error.value.available[0]
    assert "Shorten content" in str(error.value)


def test_state_and_insertion(compiler):
    a = compiler.compile_view(PipelineSlide(), State(step=0))
    b = compiler.compile_view(PipelineSlide(), State(step=2))
    parse = keyed(a.expanded_tree, "parse")
    assert parse.identity == keyed(b.expanded_tree, "parse").identity
    changes = compiler.changes(a, b)
    assert any(c.identity == parse.identity and c.kind == "properties" for c in changes)
    assert not any(
        c.identity == parse.identity and c.kind in ("insert", "remove") for c in changes
    )
    assert any(
        "key:annotation:" in c.identity
        and c.kind == "insert"
        and c.transition == Transition.fade()
        for c in changes
    )
    reverse = compiler.changes(b, a)
    assert any("key:annotation:" in c.identity and c.kind == "remove" for c in reverse)


def test_geometry_and_boundary(compiler):
    a = compiler.compile_view(ResultsSlide(), State(step=0))
    b = compiler.compile_view(ResultsSlide(), State(step=1))
    chart = keyed(a.drawable.children[0], "results")
    assert chart.metadata.animation_boundary
    change = next(
        c
        for c in compiler.changes(a, b)
        if c.identity == chart.identity and c.kind == "bounds"
    )
    assert change.before.width > change.after.width
    assert change.animation == Animation.smooth(fallback=FallbackPolicy.DISCRETE)


def test_reparent_and_duplicate_key(compiler):
    a = compiler.compile_view(VStack(HStack(Text("A").key("a")), HStack()))
    b = compiler.compile_view(VStack(HStack(), HStack(Text("A").key("a"))))
    assert any(c.kind == "reparent" for c in compiler.changes(a, b))
    with pytest.raises(ValueError, match="Duplicate"):
        compiler.compile_view(HStack(Text("A").key("a"), Text("B").key("a")))


def test_type_change_replaces_identity(compiler):
    a = compiler.compile_view(Text("A").key("a"))
    b = compiler.compile_view(Rectangle().key("a"))
    assert {c.kind for c in compiler.changes(a, b)} == {"insert", "remove"}


def test_modifiers_copy_and_preserve_order(compiler):
    text = Text("Hi")
    padded = text.padding(pt(10))
    assert not text._modifiers
    a = compiler.compile_view(padded.frame(width=pt(100))).drawable.children[0]
    b = compiler.compile_view(
        text.frame(width=pt(100)).padding(pt(10))
    ).drawable.children[0]
    assert a.bounds.width == pt(100)
    assert b.bounds.width == pt(120)


def test_both_backends_same_scene(compiler, tmp_path):
    from pptx import Presentation

    result = compiler.compile_view(MetricsSlide())
    layout = result.drawable
    ET.fromstring(svg.render(layout))
    output = tmp_path / "metrics.pptx"
    pptx.render(CompiledDeck.from_views(result), output)
    deck = Presentation(output)
    assert len(deck.slides) == 1
    texts = [s.text for s in deck.slides[0].shapes if s.has_text_frame]
    assert "Compiler performance" in texts
    assert "2.7×" in texts
    title = next(
        s
        for s in deck.slides[0].shapes
        if s.has_text_frame and s.text == "Compiler performance"
    )
    node = next(
        n
        for n in layout.children[0].walk()
        if isinstance(n, DrawableText) and n.text == "Compiler performance"
    )
    assert title.left / 12700 == pytest.approx(node.bounds.x.points)


@pytest.mark.parametrize("fit", ["contain", "cover"])
def test_image_and_editable_shape(compiler, tmp_path, fit):
    from PIL import Image as PILImage
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE_TYPE

    asset = tmp_path / "asset.png"
    PILImage.new("RGB", (80, 40), "red").save(asset)
    result = compiler.compile_view(
        HStack(
            Image(str(asset), fit).frame(width=pt(100), height=pt(100)),
            Rectangle().frame(width=pt(50), height=pt(50)),
        )
    )
    layout = result.drawable
    assert "data:image/png;base64" in svg.render(layout)
    output = tmp_path / "image.pptx"
    pptx.render(CompiledDeck.from_views(result), output)
    shapes = Presentation(output).slides[0].shapes
    assert shapes[0].shape_type == MSO_SHAPE_TYPE.PICTURE
    assert shapes[1].shape_type == MSO_SHAPE_TYPE.AUTO_SHAPE
    if fit == "cover":
        assert shapes[0].crop_left == pytest.approx(0.25)


def test_core_has_no_backend_imports():
    for name in (
        "annotations",
        "geometry",
        "identity",
        "views",
        "semantic",
        "theme",
        "layout",
        "layouts",
        "view_expansion",
        "drawables",
        "reconcile",
    ):
        path = Path(f"src/deckkit/{name}")
        sources = path.rglob("*.py") if path.is_dir() else [path.with_suffix(".py")]
        source = "\n".join(p.read_text() for p in sources)
        assert "from pptx" not in source and "import pptx" not in source


def test_state_sources_are_independent(compiler):
    a = compiler.compile_view(PipelineSlide(), State(step=0, media_time=1.2))
    b = compiler.compile_view(PipelineSlide(), State(step=0, media_time=1.3))
    assert compiler.changes(a, b) == ()
