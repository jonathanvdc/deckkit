"""Run with: python -m examples.render."""

import argparse
from pathlib import Path

from deckkit import Deck
from deckkit.fonts import FileFontResolver, Font
from deckkit.themes import ClarityTheme

from .api_sketch import (
    CanvasSlide,
    CodeSlide,
    ComparisonSlide,
    MetricsSlide,
    PipelineSlide,
    ResultsSlide,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", default="output/prototype.pptx")
    parser.add_argument(
        "--font",
        type=Path,
        help="Font file to use for the Aptos and Aptos Mono example aliases",
    )
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    deck = Deck(
        [
            MetricsSlide(),
            ComparisonSlide(),
            CodeSlide(),
            PipelineSlide(),
            ResultsSlide(),
            CanvasSlide(),
        ],
        theme=ClarityTheme(),
    )
    resolver = (
        FileFontResolver(
            {
                Font("Aptos"): str(args.font),
                Font("Aptos Mono"): str(args.font),
            }
        )
        if args.font is not None
        else None
    )
    deck.write_pptx(output, font_resolver=resolver)
    print(f"Wrote {len(deck)} slides to {output}")


if __name__ == "__main__":
    main()
