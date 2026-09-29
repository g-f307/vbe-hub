from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from vbe_hub.adapters.persistence.models import EvaluationLabelModel, RawRecordModel
from vbe_hub.synthetic.artifacts import write_dataset
from vbe_hub.synthetic.generator import generate_dataset
from vbe_hub.synthetic.importer import import_dataset
from vbe_hub.synthetic.models import GeneratorConfig


@pytest.mark.integration
async def test_imports_dataset_and_reprocessing_is_idempotent(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    config = GeneratorConfig(total_records=24)
    output = tmp_path / "dataset"
    dataset = generate_dataset(config)
    write_dataset(dataset, config, output)

    first = await import_dataset(db_session, output / "records.jsonl", output / "gold.json")
    await db_session.commit()
    second = await import_dataset(db_session, output / "records.jsonl", output / "gold.json")
    await db_session.commit()

    record_ids = [UUID(record.id) for record in dataset.records]
    labeled_ids = [
        UUID(label.record_id) for label in dataset.labels if label.gold_event_id is not None
    ]
    record_count = await db_session.scalar(
        select(func.count()).select_from(RawRecordModel).where(RawRecordModel.id.in_(record_ids))
    )
    label_count = await db_session.scalar(
        select(func.count())
        .select_from(EvaluationLabelModel)
        .where(EvaluationLabelModel.raw_record_id.in_(labeled_ids))
    )
    assert first.created == 24
    assert first.skipped == 0
    assert second.created == 0
    assert second.skipped == 24
    assert record_count == 24
    assert label_count == 22
