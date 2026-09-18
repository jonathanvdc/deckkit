"""Run with: python -m examples.render."""

import argparse
from pathlib import Path

from deckkit import Deck
from deckkit.themes import ClarityTheme

from .api_sketch import ComparisonSlide, MetricsSlide, PipelineSlide, ResultsSlide


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", default="output/prototype.pptx")
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    deck = Deck(
        [
            MetricsSlide(),
            ComparisonSlide(),
            PipelineSlide(),
            ResultsSlide(),
        ],
        theme=ClarityTheme(),
    )
    deck.write_pptx(output)
    print(f"Wrote {len(deck)} slides to {output}")


if __name__ == "__main__":
    main()
