"""Run with: python -m examples.render --font Aptos."""

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from deckkit import (
    ClarityTheme,
    CompiledDeck,
    Compiler,
    Deck,
    Font,
    TextStyle,
)
from deckkit.backends import pptx, svg

from .api_sketch import ComparisonSlide, MetricsSlide, PipelineSlide, ResultsSlide
from .themes import EditorialTheme


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--font", required=True, help="Installed font family, e.g. Aptos or Helvetica"
    )
    parser.add_argument("--output", default="output")
    parser.add_argument("--title-font", help="Optional title font family")
    parser.add_argument("--metric-font", help="Optional metric font family")
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    typography = dict(ClarityTheme.from_font(Font(args.font)).typography)
    for role in ("title", "metric"):
        family = getattr(args, f"{role}_font")
        if family is not None:
            typography[role] = TextStyle(Font(family), typography[role].size)
    compiler = Compiler(ClarityTheme(typography))

    deck = Deck(
        [
            MetricsSlide(),
            ComparisonSlide(),
            PipelineSlide(),
            ResultsSlide(),
        ]
    )
    compiled = compiler.compile_deck(deck)
    pptx.render(compiled, output / "prototype.pptx")
    for number, slide in enumerate(compiled.slides, start=1):
        (output / f"slide-{number}.svg").write_text(svg.render(slide.initial.drawable))

    # Independent demonstrations of theme recipes and presentation state.
    editorial = Compiler(EditorialTheme(typography)).compile_deck(deck[1:2])
    (output / "editorial.svg").write_text(
        svg.render(editorial.slides[0].initial.drawable)
    )
    pipeline = compiled.slides[2]
    for step, state in enumerate(pipeline.states):
        (output / f"pipeline-{step}.svg").write_text(svg.render(state.drawable))
    pptx.render(CompiledDeck((pipeline,)), output / "pipeline-animated.pptx")
    before, after = compiled.slides[3].states
    (output / "results-1.svg").write_text(svg.render(after.drawable))
    (output / "changes.json").write_text(
        json.dumps(
            [asdict(change) for change in compiler.changes(before, after)],
            indent=2,
            default=str,
        )
    )
    print(
        f"Wrote {len(deck)}-slide prototype.pptx, an animated pipeline, SVG previews and state examples to {output}"
    )


if __name__ == "__main__":
    main()
