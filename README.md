# deckkit

Experimental declarative Python presentation framework. Author composed views, compile
constrained layout into a scene, then export that scene to SVG or PowerPoint.

```python
from deckkit import Deck
from deckkit.fonts import Font
from deckkit.themes import ClarityTheme
from examples.api_sketch import MetricsSlide

deck = Deck(
    [MetricsSlide()],
    theme=ClarityTheme(),
)
deck.write_pptx("metrics.pptx")
```

## Run the prototype

Python 3.9+ and a TrueType/OpenType font file are required. HarfBuzz shapes text and Pillow supplies FreeType metrics. Fonts are not bundled.

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[pptx,dev]'
python -m examples.render
pytest
mypy
```

On macOS, `/System/Library/Fonts/Helvetica.ttc` is an example font path. Tests also
recognize DejaVu Sans on Linux and Arial on Windows; override with `DECKKIT_FONT`.

The example deck demonstrates composition, changing emphasis, insertion and
layout-driven resizing. It writes `output/prototype.pptx`.
PPTX uses native text, rectangles and images. Explicit state sequences compile
to native PowerPoint build timing; static SVG continues to represent one selected state.

Start with [API examples](examples/api_sketch.py) and [design decisions](docs/design.md).
The public API is provisional. State snapshots accept independent named inputs. Modifiers
copy values; order matters. Explicit keys are slide-global and must be unique.

Current limits: whitespace wrapping, named fonts per typography role, no font fallback,
no automatic text shrinking, no Grid/media runtime, a deliberately small native animation
subset, and no PowerPoint grouping yet. Geometry is shared by both backends, but font rendering
and baseline placement still require validation in PowerPoint. Text is prewrapped;
fonts are not embedded. Image payloads are stored in the resolved scene.

PyPI packaging is scaffolded, but nothing has been published. The distribution name,
license and compatibility policy remain decisions for the project owner.


## Type annotations

The package ships a `py.typed` marker. `mypy` checks the library in strict mode and
runs static public-API contract checks in `tests/typing`. Fluent modifiers preserve
the concrete view type, including custom subclasses. Layout policies and text
measurers use protocols; compiled trees, scenes, changes and traversal are typed.

Application state and extensible property mappings intentionally accept arbitrary
values. Built-in modifier payloads use a tagged union. HarfBuzz's missing typing
metadata is isolated with a module-specific override; python-pptx's untyped color
factory has a single local exception. Core type errors are not suppressed globally.


## Presentation builds

Animation uses typed values and explicit state boundaries stored on each slide. Steps
default to presenter advance; timed steps use `AfterPrevious` or `WithPrevious`.

```python
from deckkit import Deck
from deckkit.animation import SlideTimeline
from deckkit.views import Slide


class PipelineSlide(Slide):
    def timeline(self):
        return SlideTimeline.steps(3)

    def body(self, context):
        return pipeline_for(context.state["step"])


compiled = compiler.compile_deck(
    Deck([PipelineSlide()], theme=compiler.environment.theme)
)
pptx.render(compiled, "animated.pptx")
```

`SlideTimeline.steps(3)` creates `State(step=0)` through `State(step=2)`, advancing
on each presenter click. `SlideTimeline.advance_through(...)` accepts arbitrary state snapshots.
For custom timing or per-step animation, construct `SlideTimeline(initial, subsequent)` with
explicit `TimelineStep` values. Static slides inherit the default one-state timeline.

Views opt into layout animation and insertion/removal transitions with typed modifiers:

```python
VStack(
    Text("Optional").key("optional").transition(Transition.fade())
    if context.state.get("show", True)
    else None,
    Text("Persistent").key("persistent"),
).animation(Animation.smooth())
```

The shared animation program retains identities, endpoint geometry, triggers, effects,
and shape lifetimes without depending on PresentationML. PPTX currently lowers appear,
disappear, fade, positional reflow, presenter advance, and timed builds. Unsupported
content changes fail by default. Authors can explicitly request a crossfade or discrete
fallback. Rasterization is not a fallback.


## Physical units

Distances require immutable `Length` values; bare floats are no longer accepted.

```python
from deckkit import Deck
from deckkit.fonts import Font
from deckkit.themes import ClarityTheme
from deckkit.units import cm, inch, pt
from deckkit.views import Rectangle, Text

heading = Text("Compiler performance").padding(pt(16))
box = Rectangle().frame(width=inch(3), height=cm(2))
deck = Deck(
    [],
    theme=ClarityTheme(),
    width=inch(13 + 1 / 3),
    height=inch(7.5),
)
```

`pt(72)`, `inch(1)` and `cm(2.54)` describe the same length. Lengths support addition,
subtraction, comparisons and scalar multiplication/division. Dividing two lengths
returns a dimensionless ratio. There is no implicit conversion to float; `.points`
is the explicit conversion for measurement/export integrations. Nonfinite lengths
are rejected; flexible allocation remains a separate layout concept.

Concrete proposals, placement plans, scene bounds, font sizes and measured text
metrics all retain `Length`. Flex weights and line-spacing multipliers remain floats.
Custom layout policies receive `ProposedSize`; either dimension can be `None` to ask
for the child's ideal size. Proposals are advisory: layouts may return a different size
and may place children outside their own bounds, including at negative offsets. Drawing
is not implicitly clipped.

Frames and padding are structural views, so modifier order is visible in layout:

```python
from deckkit.geometry import RelativePoint
from deckkit.views import EdgeSet, Text, unbounded

title = (
    Text("Compiler performance")
    .frame(
        min_width=pt(240),
        ideal_width=pt(480),
        max_width=unbounded,
        alignment=RelativePoint.left,
    )
    .padding(pt(16), edges=EdgeSet.horizontal)
)
```

Exact `width` and `height` values create fixed frames. Flexible frames accept minimum,
ideal and maximum dimensions; `unbounded` consumes a concrete size proposed by the
parent and falls back to the ideal child size for an unspecified proposal. Because
frame and padding return wrapper views, their result type is `View`, and reversing
their order changes which wrapper is outermost. Like SwiftUI, a frame does not clip
or reject an oversized child; it aligns that child relative to the reported frame.

Images use 96 DPI for intrinsic physical size by default. `Image(path, dpi=192)`
explicitly changes that conversion; embedded DPI metadata is ignored to keep layout
predictable. Pixel dimensions remain integers. Explicit frames and contain/cover
still determine the rendered image fit.

SVG declares physical dimensions in `pt` and uses numerical points in its `viewBox`.
PPTX converts points into EMUs only during export. Change JSON represents lengths as
objects with a `points` field.


## Semantic content and theme recipes

Semantic content slots accept views, including nested composites:

```python
from deckkit.views import HStack, Text, VStack
from deckkit.views.semantic import (
    BeforeAfter,
    Card,
    Metric,
    Pill,
    Pipeline,
    PipelineStage,
)

pipeline = Pipeline(
    PipelineStage(Text("Parse")),
    PipelineStage(Text("Lower")),
    PipelineStage(Text("Optimize")),
)

status = Pill(Text("READY"))
summary = Card(VStack(Text("Heading"), Text("Supporting content")))

comparison = BeforeAfter(
    title=Text("A simpler pipeline"),
    before=PipelineStage(HStack(Text("Parse"), Text("Lower"))),
    after=PipelineStage(Text("Parse")),
    takeaway=Metric(Text("3"), Text("Passes removed")),
)
```

All semantic components inherit `SemanticView`. Its `body(context)` asks
`theme.render_semantic(component, context)` for a view. Returning `None` selects
`component.default_body(context)`. Themes can override built-in or application-defined
semantic types through this single hook. Recipes remain ordinary view composition.
`Metric.value`, `Metric.label`, `Pill.content`, `Card.content`, `PipelineStage.label`, and every
`BeforeAfter` content slot require views; wrap strings in `Text(...)`. A `Pill` can
therefore contain text or richer composed content. Style tokens such as
`PipelineStage.emphasis` remain strings. Explicit child styles override inherited
recipe styles.

`Pipeline` lays out its stages horizontally and connects each adjacent pair. Additional
`Label` or `Connector` values remain ordinary annotations passed through its
`annotations` argument.

View implementations live in `views/`, one file per view, with semantic components
under `views/semantic/`. Import authoring types from `deckkit.views`, semantic
components from `deckkit.views.semantic`, and theme contracts and implementations
from `deckkit.themes`. The package root is reserved for deck compilation entry points.

## View categories

`View` supplies modifiers and identity without a `body` method. Use
`CompositeView` for application-defined compositions and implement its abstract
`body(context) -> View`. `Slide` and `SemanticView` are composite views; semantic
components implement `default_body` because their shared `body` handles theme recipes.

`Text`, `Image` and `Rectangle` inherit `PrimitiveView`. `LayoutView` is the abstract
category for views that arrange children with a layout policy; stacks and custom
layout views inherit that contract. Neither category has a body.
New primitive subclasses require explicit compiler/backend support. Unsupported
view types produce a diagnostic instead of implicitly invoking a body method.


## Typography and example themes

Core `Theme` has no editorial flag or built-in structural recipe. The example
`examples.themes.EditorialTheme` subclasses it and overrides `render_semantic`.

`ClarityTheme()` is a complete theme with an Aptos-based title/body/caption/metric
scale. Font choices are part of the theme rather than constructor configuration.
Customize them through ordinary subclassing:

```python
from deckkit.fonts import Font
from deckkit.themes import ClarityTheme, TextStyle


class BrandTheme(ClarityTheme):
    def text_style(self, role):
        style = super().text_style(role)
        return TextStyle(Font("Inter"), style.size, style.line_spacing)


theme = BrandTheme()
```

`.font("title")` selects the complete typography role; descendant overrides still
win. Missing roles produce an actionable error.

Text can also contain styled spans and logical lines. The compiler resolves theme
roles, measures runs, and wraps them within the proposed width; author code never
supplies text geometry. Span backgrounds cover the measured run, while a line
background covers every visual line produced by wrapping:

```python
from deckkit.views import Text, TextLine, TextSpan

source = Text(
    TextLine(
        TextSpan("def", foreground_style="accent"),
        TextSpan(" greet", background_style="#FFF2A8"),
        TextSpan("(name):"),
        background_style="surface",
    ),
    TextLine(TextSpan('    return f"Hello, {name}"')),
    flow="verbatim",
)
```

Use `flow="wrapped"` for ordinary wrapping across span boundaries and
`flow="verbatim"` to preserve spaces and logical lines without wrapping.

Use `Code` when spans represent language tokens rather than literal presentation.
Token scopes are open, hierarchical strings, so each language can use its own
vocabulary without extending a shared enum. Wrap it in the semantic `CodeBlock`
when it should appear on a padded surface:

```python
from deckkit.views import Code, CodeLine, CodeSpan
from deckkit.views.semantic import CodeBlock

source = CodeBlock(
    Code(
        CodeLine(
            CodeSpan("def", token="keyword.declaration"),
            CodeSpan(" greet", token="name.function"),
            CodeSpan("(name):", token="punctuation"),
        ),
        CodeLine('    return f"Hello, {name}"'),
        language="python",
    )
)
```

Themes map scopes to presentation roles with `CodeTokenStyle`. Styles cascade
from broad to specific—for example `keyword`, `keyword.declaration`,
`python.keyword`, then `python.keyword.declaration`. Manual span overrides take
precedence. `Code` preserves whitespace and lowers to the same rich-text model as
`Text`, which also provides a target representation for future automatic lexers.

Install the `highlight` extra to generate the same semantic model with Pygments:

```bash
pip install "deckkit[highlight]"
```

```python
source = CodeBlock(
    Code.highlight(
        'def greet(name):\n    return f"Hello, {name}"',
        language="python",
    )
)
```

Automatic highlighting only performs lexing. Pygments token types such as
`Token.Name.Function` become Deckkit scopes such as `name.function`; the active
Deckkit theme still controls their appearance. A custom `CodeHighlighter` can
produce `CodeLine` values for languages or parsers outside Pygments.


## Font resolution

Typography describes named requests: `Font("Aptos", weight="bold", italic=False)`.
The default `SystemFontResolver` searches standard macOS, Windows or Linux font
folders for a matching family and face. It does not download fonts, synthesize styles,
or silently substitute another family. This prototype supports regular/bold and
italic/oblique static faces; variable-axis selection and platform-specific application
font registries are not yet supported. Missing fonts produce `FontNotFoundError`.

Explicit files are a resolver configuration, not a second typography representation:

```python
from deckkit import Compiler
from deckkit.fonts import FileFontResolver, Font, FontFile
from deckkit.themes import ClarityTheme

body = Font("Aptos")
resolver = FileFontResolver({body: FontFile("/fonts/Aptos.ttf", index=0)})
compiler = Compiler(ClarityTheme(), font_resolver=resolver)
```

A string file path is also accepted as a mapping value. `FontFile` adds an explicit
face index for collections. Mapping keys can be aliases; exports use the loaded
face's actual family/style so they match measurement. Both the request and resolved
face survive in the scene. HarfBuzz and FreeType use the same file and collection
index. Font files are not embedded in SVG or PPTX; viewing machines need the fonts.


## Theme contract and Clarity

`Theme` is an abstract design-system interface: subclasses implement `color(role)`
and `text_style(role)`. It owns no palette, typography mapping or scale. Its optional
`render_semantic` hook returns `None` by default, letting components use their own
composition; this is fallback behavior, not a design recipe.

The bundled `ClarityTheme` (`deckkit.themes.clarity`) supplies the original blue/teal
palette and an Aptos-based title/body/caption/metric scale. The editorial example
inherits from Clarity. Applications can subclass it to change the design or implement
`Theme` directly without adopting Clarity's tokens or storage model.


## Decks

`Deck` is an immutable sequence of `Slide` instances, constructed from an iterable.
It supports iteration, indexing and slicing (which returns another deck).

```python
from deckkit import Deck

deck = Deck(
    [MetricsSlide(), ComparisonSlide()],
    theme=compiler.environment.theme,
)
compiled = compiler.compile_deck(deck)
pptx.render(compiled, "presentation.pptx")
```

`CompiledDeck.slides` contains one `CompiledSlide` per authored slide. Each compiled slide
retains its initial scene, step endpoint scenes, and backend-neutral animation program.
`compile_deck(deck, state=...)` overlays slide timeline state on a shared snapshot without
treating slide position as a state source. Keys remain scoped per slide. Empty decks compile
to an empty result; PPTX export still requires at least one slide.

There is only one deck compilation and PPTX export path. To materialize builds as ordinary
static slides for a backend without animation support, call `compiled.expanding_steps()`
before export. SVG renders a selected endpoint such as `slide.initial.drawable` directly.

The example runner exports a five-slide deck to `output/prototype.pptx`. It does
not remove older files from an existing output directory.


## Compiled results

`Compiler.compile_view(view, state=None)` returns `CompiledView`, pairing
`expanded_tree` (logical reconciliation) with `layout` (geometry and export) from
one evaluation under the compiler's environment and canvas. It works for both
slides and ordinary views. It represents one selected state, not an animation or
backend document, and does not store the source state/environment.

`Compiler.compile_slide(slide, state=None)` returns `CompiledSlide`, containing an initial
`CompiledView`, one additional state per `TimelineStep`, and the resolved animation program.
`Compiler.compile_deck(deck, state=None)` returns an ordered `CompiledDeck` of those logical
slides. Static slides use the same representation with no steps. These names replace the
earlier separate sequence/static compilation paths.


The view-expansion stage is named explicitly: `view_expansion.expand_view()`
returns an `ExpandedView` hierarchy. This is the pre-layout representation, with
composite bodies evaluated, style/font requests resolved, stable identities and
layout policies attached. `CompiledView.expanded_tree` retains it for logical
reconciliation; `CompiledView.drawable` holds concrete geometry for export. The
former `resolve.py`, `resolve()`, `Node` and `resolved_tree` names are replaced.
Font resolution remains a separate, specifically named service.


The final rendering representation is a hierarchy of `Drawable` objects with no
outer wrapper. `CompiledView.drawable` is a canvas-sized root group at `(0, 0)`;
its first child retains the compiled content's own bounds and identity. Exporters
use the root bounds as canvas dimensions and traverse its children for drawing.
`CompiledSlide.states` provides those roots at each step boundary. The synthetic root's
reserved `canvas` identity is distinct from source-view identities and preserves
canvas geometry for comparisons without stretching the content to fill it.


Drawable implementations live one per module under `deckkit.drawables`:
`DrawableGroup`, `DrawableText`, `DrawableRectangle` and `DrawableImage`.
Their shared `Drawable` base carries identity, allocated bounds and typed
`DrawableMetadata` (animation, transition and animation boundary). Only groups
store children; leaves expose an empty child sequence for traversal.

Primitives expose explicit fields instead of `kind`/`props`. Their `content_bounds`
record the actual painting rectangle separately from padded/framed allocation.
Text includes measured lines and resolved font information; images include bytes,
MIME type, intrinsic pixel dimensions and fit. Exporters consume these types directly.
The expanded hierarchy and layout plans still use internal property mappings;
conversion to typed drawing primitives happens at placement.
