# deckkit

Experimental declarative Python presentation framework. Author composed views, compile
constrained layout into a scene, then export that scene to SVG or editable static PowerPoint.

```python
from deckkit import Compiler, ClarityTheme, Font
from examples.api_sketch import MetricsSlide
from deckkit.backends import pptx

compiler = Compiler(ClarityTheme.from_font(Font("Aptos")))
result = compiler.compile_view(MetricsSlide())
pptx.render([result.drawable], "metrics.pptx")
```

## Run the prototype

Python 3.9+ and a TrueType/OpenType font file are required. HarfBuzz shapes text and Pillow supplies FreeType metrics. Fonts are not bundled.

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[pptx,dev]'
python -m examples.render --font Aptos
pytest
mypy
```

On macOS, `/System/Library/Fonts/Helvetica.ttc` is an example font path. Tests also
recognize DejaVu Sans on Linux and Arial on Windows; override with `DECKKIT_FONT`.

The example deck and supplementary previews demonstrate composition, two structural theme recipes,
changing emphasis, insertion and layout-driven resizing. Outputs are in `output/`.
PPTX uses editable native text, rectangles and images. Each state is a separate slide;
animation/transition intent is recorded in `changes.json`, not lowered into PPTX timing.

Start with [API examples](examples/api_sketch.py) and [design decisions](docs/design.md).
The public API is provisional. State snapshots accept independent named inputs. Modifiers
copy values; order matters. Explicit keys are slide-global and must be unique.

Current limits: whitespace wrapping, named fonts per typography role, no font fallback,
no automatic text shrinking, no Grid/media runtime, no native animation lowering, and
no PowerPoint grouping yet. Geometry is shared by both backends, but font rendering
and baseline placement still require validation in PowerPoint. Text is editable and
prewrapped; fonts are not embedded. Image payloads are stored in the resolved scene.

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


## Physical units

Distances require immutable `Length` values; bare floats are no longer accepted.

```python
from deckkit import Text, Rectangle, Compiler, pt, inch, cm

heading = Text("Compiler performance").padding(pt(16))
box = Rectangle().frame(width=inch(3), height=cm(2))
compiler = Compiler(theme, width=inch(13 + 1/3), height=inch(7.5))
```

`pt(72)`, `inch(1)` and `cm(2.54)` describe the same length. Lengths support addition,
subtraction, comparisons and scalar multiplication/division. Dividing two lengths
returns a dimensionless ratio. There is no implicit conversion to float; `.points`
is the explicit conversion for measurement/export integrations. Nonfinite lengths
are rejected; flexible allocation remains a separate layout concept.

Constraints, placement plans, scene bounds, font sizes and measured text metrics all
retain `Length`. Flex weights and line-spacing multipliers remain floats. Custom
layout policies use `pt(0)` for a zero distance and `pt(...)` for tolerances.

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
from deckkit import HStack, Text
from deckkit.views.semantic import BeforeAfter, Metric, Stage

comparison = BeforeAfter(
    title=Text("A simpler pipeline"),
    before=Stage(HStack(Text("Parse"), Text("Lower"))),
    after=Stage(Text("Parse")),
    takeaway=Metric(Text("3"), Text("Passes removed")),
)
```

All semantic components inherit `SemanticView`. Its `body(context)` asks
`theme.render_semantic(component, context)` for a view. Returning `None` selects
`component.default_body(context)`. Themes can override built-in or application-defined
semantic types through this single hook. Recipes remain ordinary view composition.
`Metric.value`, `Metric.label`, `Stage.label`, and every `BeforeAfter` content slot
require views; wrap strings in `Text(...)`. Style tokens such as `Stage.emphasis`
remain strings. Explicit child styles override inherited recipe styles.

View implementations live in `views/`, one file per view, with semantic components
under `views/semantic/`. State and environment types live in `context.py`. Top-level
imports and `deckkit.semantic` remain convenient re-exports.

## View categories

`View` supplies modifiers and identity without a `body` method. Use
`CompositeView` for application-defined compositions and implement its abstract
`body(context) -> View`. `Slide` and `SemanticView` are composite views; semantic
components implement `default_body` because their shared `body` handles theme recipes.

`Text`, `Image` and `Rectangle` inherit `PrimitiveView`. `LayoutView` holds children
and a layout policy; all stacks inherit that contract. Neither category has a body.
New primitive subclasses require explicit compiler/backend support. Unsupported
view types produce a diagnostic instead of implicitly invoking a body method.


## Typography and example themes

Core `Theme` has no editorial flag or built-in structural recipe. The example
`examples.themes.EditorialTheme` subclasses it and overrides `render_semantic`.

`ClarityTheme.typography` maps role names to immutable `TextStyle(font, size,
line_spacing=1.1)` values. Each role can request a different family, regular/bold weight and italic face. `ClarityTheme.from_font(Font("Aptos"))` is a convenience that
initializes all built-in roles with one face; it also works on theme subclasses.
For example:

```python
from deckkit import ClarityTheme, TextStyle, Font, pt

roles = dict(ClarityTheme.from_font(Font("Aptos")).typography)
roles["title"] = TextStyle(Font("Aptos Display", weight="bold"), pt(36))
roles["metric"] = TextStyle(Font("Aptos"), pt(48), line_spacing=1.2)
theme = ClarityTheme(roles)
```

`.font("title")` selects the complete typography role; descendant overrides still
win. Missing roles produce an actionable error. The example runner accepts
`--title-font` and `--metric-font` alongside its required `--font`.


## Font resolution

Typography describes named requests: `Font("Aptos", weight="bold", italic=False)`.
The default `SystemFontResolver` searches standard macOS, Windows or Linux font
folders for a matching family and face. It does not download fonts, synthesize styles,
or silently substitute another family. This prototype supports regular/bold and
italic/oblique static faces; variable-axis selection and platform-specific application
font registries are not yet supported. Missing fonts produce `FontNotFoundError`.

Explicit files are a resolver configuration, not a second typography representation:

```python
from deckkit import Compiler, ClarityTheme, Font, FileFontResolver, FontFile

body = Font("Aptos")
resolver = FileFontResolver({body: FontFile("/fonts/Aptos.ttf", index=0)})
compiler = Compiler(ClarityTheme.from_font(body), font_resolver=resolver)
```

A string file path is also accepted as a mapping value. `FontFile` adds an explicit
face index for collections. Mapping keys can be aliases; exports use the loaded
face's actual family/style so they match measurement. Both the request and resolved
face survive in the scene. HarfBuzz and FreeType use the same file and collection
index. Font files are not embedded in SVG or PPTX; viewing machines need the fonts.
The example CLI's `--font`, `--title-font` and `--metric-font` now take family names.


## Theme contract and Clarity

`Theme` is an abstract design-system interface: subclasses implement `color(role)`
and `text_style(role)`. It owns no palette, typography mapping or scale. Its optional
`render_semantic` hook returns `None` by default, letting components use their own
composition; this is fallback behavior, not a design recipe.

The bundled `ClarityTheme` (`deckkit.themes.clarity`) supplies the original blue/teal
palette and title/body/caption/metric scale. Use `ClarityTheme.from_font(Font("Aptos"))`
or pass a typography mapping to `ClarityTheme(...)`. The editorial example inherits
from Clarity. Applications can instead implement `Theme` directly without adopting
Clarity's tokens or storage model.


## Decks

`Deck` is an immutable sequence of `Slide` instances, constructed from an iterable.
It supports iteration, indexing and slicing (which returns another deck).

```python
from deckkit import Deck

deck = Deck([MetricsSlide(), ComparisonSlide()])
compiled = compiler.compile_deck(deck)
pptx.render(compiled.drawables, "presentation.pptx")
```

`CompiledDeck.slides` retains each slide's logical tree and scene for reconciliation;
`.drawables` feeds exporters directly. `compile_deck(deck, state=...)` shares the supplied
snapshot across slides without treating slide position as a state source. Keys remain
scoped per slide. Empty decks compile to an empty result; PPTX export still requires
at least one scene.

The example runner now exports a four-slide deck to `prototype.pptx`. Additional
SVG previews demonstrate theme changes and state transitions separately from the
main deck. It does not remove older files from an existing output directory.


## Compiled results

`Compiler.compile_view(view, state=None)` returns `CompiledView`, pairing
`expanded_tree` (logical reconciliation) with `layout` (geometry and export) from
one evaluation under the compiler's environment and canvas. It works for both
slides and ordinary views. It represents one selected state, not an animation or
backend document, and does not store the source state/environment.

`Compiler.compile_deck(deck, state=None)` returns `CompiledDeck`. Its `slides` are
ordered `CompiledView` results; `scenes` provides their scenes for export. There
is no separate compiled-slide type. These names replace `Compilation`,
`DeckCompilation`, `.tree` and `Compiler.compile()` in the prototype API.


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
`CompiledDeck.drawables` provides those roots in slide order. The synthetic root's
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
