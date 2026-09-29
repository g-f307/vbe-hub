"""Command-line entry point for synthetic dataset operations."""

from __future__ import annotations

import argparse
from pathlib import Path

from vbe_hub.synthetic.artifacts import write_dataset
from vbe_hub.synthetic.generator import generate_dataset
from vbe_hub.synthetic.models import GeneratorConfig


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m vbe_hub.synthetic")
    subparsers = parser.add_subparsers(dest="command", required=True)
    generate = subparsers.add_parser("generate", help="generate canonical synthetic artifacts")
    generate.add_argument("--output", type=Path, required=True)
    generate.add_argument("--seed", type=int, default=307)
    generate.add_argument("--total-records", type=int, default=120)
    generate.add_argument("--media-ratio", type=float, default=0.6)
    generate.add_argument("--event-count", type=int, default=12)
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.command == "generate":
        config = GeneratorConfig(
            seed=args.seed,
            total_records=args.total_records,
            media_ratio=args.media_ratio,
            event_count=args.event_count,
        )
        write_dataset(generate_dataset(config), config, args.output)


if __name__ == "__main__":
    main()
