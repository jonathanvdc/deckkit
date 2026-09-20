# Prototype design

Status: experimental. Examples establish the vocabulary; compatibility is not promised.

## Compiler boundaries

`views/`: author values, immutable modifier records, state snapshots and environment.
`view_expansion.py`: recursively evaluate composite bodies; preserve component nodes and semantic properties.
`measurement.py`: injectable text measurement using FreeType through Pillow and direct HarfBuzz bindings.
`layout.py`: layout protocol, measured plans, child proposal cache, validation and scene assembly.
`layouts.py`: stack, overlay, frame, padding and intrinsic leaf policies using `Length` values normalized to points (72 per inch).
`drawables/`: concrete bounds, measured text lines and retained component ancestry.
`reconcile.py`: reconcile logical nodes before layout; enrich changes with scene geometry afterward.
`backends/`: consume the same scene; SVG first, optional static PPTX.
`views/semantic/`, `theme.py`: ordinary composition and structural recipes, with no backend imports.

## Decisions to test

A View is a short-lived description, never the persistent instance. Identity belongs to
its occurrence in a compiled slide. Composite nodes survive expansion as groups. User
composites use frozen dataclasses; modifiers return a copied value with an ordered tuple
of modifier records. Order is meaningful (padding then frame differs from frame then
padding). No mutation of reusable view values occurs during compilation.

`body(context)` takes state/environment explicitly. This sacrifices exact SwiftUI syntax
for discoverability, isolated tests and safe concurrent compilation. State is an immutable
mapping snapshot with arbitrary source names, not a slide index. There is no reactive
scheduler yet. A video clock can supply `media_time` without advancing `step`.

Unkeyed identity uses parent identity + child slot + fully qualified view type. Explicit
keys are slide-global in this prototype: they allow movement between parents and are
validated for uniqueness. This deliberately differs from React's sibling-scoped keys.
Reordering/conditional siblings need keys. Changing type with the same key replaces the
component. Keyed movement records parent changes; geometry captures sibling reordering.
Theme recipe internals have structural identity; a theme change may replace those
internals while retaining the semantic component. This is a deliberate lifecycle boundary.

Semantic values survive as composite properties; concrete font/color resolution happens
during expansion. Drawable nodes retain identity, kind, parentage, animation/transition,
and boundary metadata. The smallest change record contains property changes, insertion,
removal, reparenting and old/new bounds. Animation decorates persistent changes;
transition decorates insertion/removal. A boundary stops animation and transition
inheritance from its ancestors without suppressing child reconciliation; a boundary's own
animation becomes the scope for its descendants. Specialized chart transitions remain a
future pass.

Measurement caches immutable requests including text, font file, size and available width.
A concrete font file selects weight/style (no synthetic bold). Line spacing is explicit.
Pillow supplies FreeType vertical metrics; uharfbuzz supplies shaped glyph advances. The first line breaker
is whitespace-based with explicit newlines and a hard diagnostic for an unbreakable word.
Unicode line breaking, bidi paragraph layout, font fallback and exact PowerPoint parity
remain open. SVG and PPTX receive prebroken lines; installed fonts still affect glyph
rendering. Production needs pinned redistributable fonts and PowerPoint visual tests.

Layout intentionally supports intrinsic sizing, fixed frames and weighted flex allocation,
with stacks and overlay. Padding/frame order is preserved. Flex children split remaining
space after intrinsic/fixed siblings; text does not implicitly become compressible.
Overflow fails with identity, available/required size and a suggested correction.
Grid, Fraction, MinMax, baseline alignment and responsive recipes can wait.

Image assets are captured during compilation with intrinsic dimensions; contain and cover
are renderer-independent fit choices. The scene is self-contained. Explicit state
sequences compile to a backend-neutral animation program. PPTX lowers its initial native
subset to union-scene shapes and a PresentationML timing tree; static SVG
continues to export selected states. Unsupported effects fail by default and have explicit
crossfade or discrete fallback policies. Rasterization is not a fallback.

## Research and open questions

React associates state with position/type and uses keys to control identity:
https://react.dev/learn/preserving-and-resetting-state
Pillow exposes FreeType advance lengths, font metrics and RAQM shaping:
https://pillow.readthedocs.io/en/stable/reference/ImageFont.html
HarfBuzz bindings expose shaped glyph advances:
https://uharfbuzz.readthedocs.io/reference.html

The next design review should focus on global keys versus scoped keys plus a separate
matched-geometry ID; automatic text compression versus explicit flex; environment
subtree overrides; and whether modifier records should become public typed values.
Do not add a reactive runtime scheduler or generic constraint solver. Presentation builds
are explicit state snapshots, with `OnAdvance`, `WithPrevious`, and `AfterPrevious`
providing the scheduling vocabulary required by PPTX and a future HTML player.

## Publication gate

The working distribution name is unverified. Before PyPI: select license and name,
exercise the API on real decks, define supported Python/font platforms, add CI and
wheel/sdist install checks, document font redistribution, and settle versioning policy.
No credentials or publication are required for this prototype.


## Extending layout

`Layout.measure(constraints, children)` returns a `LayoutPlan` with its size and
`Placement(child, measured_plan, x, y)` records. Children expose identity, flex weight
and cached measurement, without exposing view types. A `LayoutView` subclass returns
its policy from `resolve_layout`; both exporters treat it as an ordinary grouping node.
Policies are immutable descriptions by convention.

Resolution attaches policies to nodes and composes modifier wrappers in source order.
Text policies receive the compiler's measurement service. The engine has no node-kind
switch: it invokes policies, checks sizes and child containment, then walks stored plans
to produce scene nodes. Padding and frames do not add logical identities. Renderers
continue to consume only the resulting scene.

Measurements are cached per child and constraint proposal for one scene compilation.
Placement does not measure again. Overlay may need two distinct proposals: intrinsic
measurement determines its extent, then an exact allocation expands the background.
This is intentional; caching removes duplicate proposals, not necessary negotiation.
Custom policies must use the supplied children and return finite, nonnegative sizes
and placements within their own bounds. Layout overflow retains the owning identity.


## Physical units

Author APIs and compiler geometry carry immutable `Length` values. `pt`, `inch` and
`cm` normalize at construction; explicit `.points` conversion occurs at the font
engine and renderer boundaries. Length/length division produces a scalar; weights,
line-spacing multipliers and image DPI are dimensionless numeric inputs. Arbitrary
length×length arithmetic is deliberately unsupported. Infinite lengths are rejected;
future unbounded proposals or fill rules should be explicit allocation types.

Image intrinsic size uses declared DPI (96 by default), ignoring embedded metadata.
SVG uses physical `pt` dimensions with a point-coordinate viewBox. The existing
example PPTX geometry remains unchanged after migrating literal points to `pt(...)`.


## Semantic composition convention

Each semantic view inherits `SemanticView` and defines `body(context)`.
Composite expansion asks `Theme.render_semantic(component, context)` first;
`None` delegates to the authored body. There is no renderer-side semantic dispatch.
All presentation content slots are views (including metric values/labels and stage
labels); emphasis and similar design tokens remain scalar properties. Theme recipes
must compose the supplied views, preserving their keys and modifiers. The editorial
recipe now measures content intrinsically rather than imposing a fixed text-sized
height. Layout overflow remains explicit when content exceeds the canvas.

Slide structure uses the same nested semantic composition. `SlideWithMargins`
emits `SlideMargins`, and `TitleAndContentSlide` places a `TitleAndContent` node
inside it. A theme can therefore replace the margin and title-layout recipes
independently instead of replacing the entire slide for either concern.

The module reorganization changes fully qualified structural identities. These are
compiler-local identities, not a version-stable serialized interchange format.

## Explicit view categories

Only `CompositeView` declares the abstract `body(context)` contract. `View` owns
modifiers and identity, `PrimitiveView` marks directly supported leaves, and
`LayoutView` is the abstract category for policy-laid-out children. Custom layout
views and stacks inherit `LayoutView`; stacks
construct their policy through an abstract `_make_layout` method. The resolver
expands only composites and validates that their bodies return views. Existing
custom `class X(View)` compositions must migrate to `class X(CompositeView)`.


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
Each `CompiledSlide` retains those roots at its initial and step boundaries. A
`CompiledDeck` can expand those boundaries into static logical slides without consulting
a backend. The synthetic root's
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
