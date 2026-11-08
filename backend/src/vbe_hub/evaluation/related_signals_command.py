from __future__ import annotations

import argparse
import json
from pathlib import Path

from vbe_hub.evaluation.related_signals import run_recorded_evaluation


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate precomputed related signals")
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("/data/reports"))
    parser.add_argument("--commit", required=True)
    args = parser.parse_args()
    report = run_recorded_evaluation(args.capture, args.output, commit=args.commit)
    print(json.dumps({"identity": report["identity"], **report["decision"]}, indent=2))


if __name__ == "__main__":
    main()
