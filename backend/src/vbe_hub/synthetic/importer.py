"""Import canonical synthetic artifacts through the persistence adapters."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from vbe_hub.adapters.persistence.repositories import (
    SqlAlchemyEvaluationRepository,
    SqlAlchemyRawRecordRepository,
)
from vbe_hub.domain.records import EvaluationLabel, Provenance, RawRecord, SourceKind


@dataclass(frozen=True, slots=True)
class ImportResult:
    created: int
    skipped: int


def _read_gold(path: Path) -> dict[str, dict[str, Any]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    return {label["record_id"]: label for label in document["labels"]}


async def import_dataset(
    session: AsyncSession, records_path: Path, gold_path: Path
) -> ImportResult:
    """Import records and labels idempotently in the caller's transaction."""

    labels = _read_gold(gold_path)
    raw_repository = SqlAlchemyRawRecordRepository(session)
    evaluation_repository = SqlAlchemyEvaluationRepository(session)
    created = 0
    skipped = 0

    for line in records_path.read_text(encoding="utf-8").splitlines():
        data = json.loads(line)
        published_at = datetime.fromisoformat(data["published_at"])
        generated = RawRecord.create(
            source_kind=SourceKind(data["source_kind"]),
            source_name=data["source_name"],
            external_id=data.get("external_id"),
            published_at=published_at,
            title=data.get("title"),
            body=data["body"],
            source_url=data.get("source_url"),
            language=data["language"],
            original_payload=data["payload"],
        )
        record = replace(
            generated,
            id=UUID(data["id"]),
            created_at=published_at,
            updated_at=published_at,
        )
        label = labels[str(record.id)]
        provenance_data = data["provenance"]
        result = await raw_repository.add(
            record,
            Provenance(
                adapter_name="synthetic-importer",
                adapter_version="1.0.0",
                generator_name=provenance_data["generator"],
                generator_version=provenance_data["version"],
                seed=provenance_data["seed"],
                scenario_id=label["scenario_id"],
                collected_at=published_at,
            ),
        )
        if not result.created:
            skipped += 1
            continue
        created += 1
        if label["gold_event_id"] is not None:
            await evaluation_repository.add(
                EvaluationLabel(
                    raw_record_id=record.id,
                    gold_event_id=label["gold_event_id"],
                )
            )

    return ImportResult(created=created, skipped=skipped)
