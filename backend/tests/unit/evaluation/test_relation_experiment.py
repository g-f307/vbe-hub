import asyncio
from datetime import UTC, datetime

from vbe_hub.application.ai import (
    AIExecutionMetadata,
    ExecutionStatus,
    RelationKind,
    RelationResult,
)
from vbe_hub.application.correlation.candidates import CandidatePolicy, GeographicLevel
from vbe_hub.evaluation.relation_dataset import build_relation_dataset
from vbe_hub.evaluation.relation_experiment import _predict_with_concurrency


class ConcurrentJudge:
    def __init__(self) -> None:
        self.active = 0
        self.maximum = 0

    async def judge(self, request):
        self.active += 1
        self.maximum = max(self.maximum, self.active)
        await asyncio.sleep(0.01)
        self.active -= 1
        return RelationResult(
            relation=RelationKind.UNRELATED,
            justification="Resposta sintética para teste de concorrência.",
            confidence=0.8,
            metadata=AIExecutionMetadata(
                provider="fake",
                model="fake-relation",
                contract_version="relation-v1",
                prompt_version=request.prompt_version,
                started_at=datetime(2026, 9, 30, tzinfo=UTC),
                duration_ms=10,
                status=ExecutionStatus.SUCCEEDED,
            ),
        )


async def test_relation_experiment_limits_and_uses_configured_concurrency() -> None:
    dataset = build_relation_dataset(split="calibration", cases_per_relation=1, seed=3040)
    judge = ConcurrentJudge()

    predictions = await _predict_with_concurrency(
        dataset,
        judge=judge,
        policy=CandidatePolicy(14, GeographicLevel.MUNICIPALITY, 0.65, 0.65),
        concurrency=2,
        relation_prompt_version="relate-v2.1",
        input_usd_per_million=None,
        output_usd_per_million=None,
    )

    assert len(predictions) == len(dataset.inputs)
    assert judge.maximum == 2
