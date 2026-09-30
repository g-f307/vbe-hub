from datetime import UTC, datetime
from uuid import UUID

from vbe_hub.application.ai import (
    AIExecutionMetadata,
    EmbeddingResult,
    ExecutionStatus,
    RelationKind,
    RelationResult,
)
from vbe_hub.application.correlation.candidates import CandidatePolicy, GeographicLevel
from vbe_hub.evaluation.correlation_pipeline import (
    CorrelationEvaluationRecord,
    evaluate_predictions,
    predict_correlations,
    predict_relation_pairs,
)
from vbe_hub.evaluation.relation_dataset import RelationPairInput


class Embeddings:
    async def embed(self, request):
        return EmbeddingResult(
            request=request,
            vector=(1.0, *([0.0] * 767)),
            dimensions=768,
            metadata=metadata("embedding-v1"),
        )


class Judge:
    async def judge(self, request):
        assert "gold_relation" not in request.left
        assert "gold_relation" not in request.right
        return RelationResult(
            relation=RelationKind.CORROBORATES,
            justification="Fontes sintéticas independentes descrevem o mesmo evento.",
            confidence=0.9,
            metadata=metadata("relation-v1"),
        )


def metadata(model: str) -> AIExecutionMetadata:
    return AIExecutionMetadata(
        provider="fake",
        model=model,
        contract_version="test-v1",
        prompt_version="relate-v1" if model == "relation-v1" else None,
        started_at=datetime(2026, 9, 30, tzinfo=UTC),
        duration_ms=12,
        status=ExecutionStatus.SUCCEEDED,
        input_units=10,
        output_units=2,
    )


def record(identifier: int, *, cases: int) -> CorrelationEvaluationRecord:
    return CorrelationEvaluationRecord(
        record_id=UUID(f"00000000-0000-0000-0000-{identifier:012d}"),
        technical_sheet={
            "disease_or_condition": "Sarampo",
            "symptoms": ["febre", "manchas vermelhas"],
            "estimated_cases": cases,
            "temporal": {"start": "2026-03-10", "end": None},
            "location": {
                "country": "Brasil",
                "state": "Amazonas",
                "municipality": "Manaus",
            },
        },
    )


async def test_pipeline_predicts_without_gold_and_evaluator_applies_it_afterward() -> None:
    records = [record(1, cases=4), record(2, cases=8)]
    policy = CandidatePolicy(14, GeographicLevel.MUNICIPALITY, 0.7, 0.65)

    predictions = await predict_correlations(
        records, embedding_provider=Embeddings(), judge=Judge(), policy=policy
    )
    metrics = evaluate_predictions(
        predictions,
        gold_relations={(str(records[0].record_id), str(records[1].record_id)): "corroborates"},
    )

    assert predictions[0].predicted_relation == "corroborates"
    assert metrics.candidates.recall == 1.0
    assert metrics.classification.by_class["corroborates"]["f1"] == 1.0
    assert metrics.operations.provider_calls == 1


async def test_pipeline_uses_duplicate_rule_without_counting_a_provider_call() -> None:
    first = record(1, cases=4)
    second = record(2, cases=4)

    predictions = await predict_correlations(
        [first, second],
        embedding_provider=Embeddings(),
        judge=Judge(),
        policy=CandidatePolicy(14, GeographicLevel.MUNICIPALITY, 0.7, 0.65),
    )
    metrics = evaluate_predictions(
        predictions,
        gold_relations={(str(first.record_id), str(second.record_id)): "duplicate"},
    )

    assert predictions[0].predicted_relation == "duplicate"
    assert metrics.operations.provider_calls == 0


async def test_pair_pipeline_applies_selection_without_exposing_gold() -> None:
    left, right = record(1, cases=4), record(2, cases=8)
    excluded = record(3, cases=8)
    excluded.technical_sheet["location"]["municipality"] = "Tefé"
    pairs = [
        RelationPairInput(
            left.record_id, right.record_id, 0.9, left.technical_sheet, right.technical_sheet
        ),
        RelationPairInput(
            left.record_id,
            excluded.record_id,
            0.95,
            left.technical_sheet,
            excluded.technical_sheet,
        ),
    ]

    predictions = await predict_relation_pairs(
        pairs,
        judge=Judge(),
        policy=CandidatePolicy(14, GeographicLevel.MUNICIPALITY, 0.7, 0.65),
        relation_prompt_version="relate-v2",
    )

    assert predictions[0].predicted_relation == "corroborates"
    assert predictions[1].selected is False
    assert predictions[1].exclusion_reason == "geographic_conflict:municipality"
