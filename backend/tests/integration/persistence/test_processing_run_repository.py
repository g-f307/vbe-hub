from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from vbe_hub.adapters.persistence.repositories import SqlAlchemyProcessingRunRepository
from vbe_hub.domain.records import ProcessingRun, ProcessingState


@pytest.mark.integration
async def test_inserts_and_recovers_processing_run(db_session: AsyncSession) -> None:
    repository = SqlAlchemyProcessingRunRepository(db_session)
    run = ProcessingRun(
        id=uuid4(),
        run_type="synthetic_import",
        state=ProcessingState.FAILED,
        started_at=datetime(2026, 9, 28, 12, tzinfo=UTC),
        finished_at=datetime(2026, 9, 28, 12, 5, tzinfo=UTC),
        component_versions={"importer": "1.0.0", "contract": "2026-09"},
        received_count=10,
        processed_count=8,
        skipped_count=1,
        failed_count=1,
        sanitized_error={"code": "partial_failure", "message": "Uma entrada inválida"},
    )

    await repository.add(run)
    await db_session.commit()

    assert await repository.get(run.id) == run
