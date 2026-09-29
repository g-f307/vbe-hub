"""Command-line entry point for synthetic dataset operations."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from vbe_hub.infrastructure.settings import get_settings
from vbe_hub.synthetic.artifacts import write_dataset
from vbe_hub.synthetic.generator import generate_dataset
from vbe_hub.synthetic.importer import import_dataset
from vbe_hub.synthetic.models import GeneratorConfig
from vbe_hub.synthetic.validator import (
    validate_dataset,
    validation_exit_code,
    write_validation_report,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m vbe_hub.synthetic")
    subparsers = parser.add_subparsers(dest="command", required=True)
    generate = subparsers.add_parser("generate", help="generate canonical synthetic artifacts")
    generate.add_argument("--output", type=Path, required=True)
    generate.add_argument("--seed", type=int, default=307)
    generate.add_argument("--total-records", type=int, default=120)
    generate.add_argument("--media-ratio", type=float, default=0.6)
    generate.add_argument("--event-count", type=int, default=12)
    importer = subparsers.add_parser("import", help="import canonical artifacts into PostgreSQL")
    importer.add_argument("--records", type=Path, required=True)
    importer.add_argument("--gold", type=Path, required=True)
    validate = subparsers.add_parser("validate", help="validate canonical synthetic artifacts")
    validate.add_argument("--input", type=Path, required=True)
    validate.add_argument("--report", type=Path, required=True)
    return parser


async def _import(records: Path, gold: Path) -> None:
    settings = get_settings()
    engine = create_async_engine(settings.sqlalchemy_database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            result = await import_dataset(session, records, gold)
            await session.commit()
        print(f"created={result.created} skipped={result.skipped}")
    finally:
        await engine.dispose()


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
    elif args.command == "import":
        asyncio.run(_import(args.records, args.gold))
    elif args.command == "validate":
        report = validate_dataset(args.input)
        write_validation_report(report, args.report)
        print(
            f"status={'valid' if report.valid else 'invalid'} "
            f"records={report.coverage['records']} issues={len(report.issues)}"
        )
        for issue in report.issues:
            location = f" record={issue.record_id}" if issue.record_id else ""
            print(f"{issue.file}: {issue.rule}:{location} {issue.message}")
        raise SystemExit(validation_exit_code(report))


if __name__ == "__main__":
    main()
