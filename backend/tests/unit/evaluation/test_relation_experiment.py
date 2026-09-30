import asyncio
import csv
from datetime import UTC, datetime

from vbe_hub.application.ai import (
    AIExecutionMetadata,
    ExecutionStatus,
    RelationKind,
    RelationResult,
)
from vbe_hub.application.correlation.candidates import CandidatePolicy, GeographicLevel
from vbe_hub.evaluation.correlation_pipeline import CorrelationPrediction
from vbe_hub.evaluation.relation_dataset import build_relation_dataset
from vbe_hub.evaluation.relation_experiment import (
    _build_provider_case_rows,
    _evidence_level,
    _operational_failure_rate,
    _predict_with_concurrency,
    _shuffled_pairs,
    _write_case_report,
)


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


def test_operational_failure_rate_uses_only_provider_attempts() -> None:
    assert _operational_failure_rate(failures=28, provider_attempts=44) == 0.636364
    assert _operational_failure_rate(failures=0, provider_attempts=0) == 0.0


def test_pair_order_is_seeded_and_preserves_every_input() -> None:
    dataset = build_relation_dataset(split="evaluation", cases_per_relation=1, seed=4040)

    first = _shuffled_pairs(dataset.inputs, seed=4040)
    repeated = _shuffled_pairs(dataset.inputs, seed=4040)
    another_seed = _shuffled_pairs(dataset.inputs, seed=4041)

    def pair_ids(pairs):
        return [(item.left_id, item.right_id) for item in pairs]

    assert pair_ids(first) == pair_ids(repeated)
    assert pair_ids(first) != pair_ids(another_seed)
    assert set(pair_ids(first)) == set(pair_ids(dataset.inputs))


def test_evidence_is_exploratory_below_expanded_sample() -> None:
    exploratory = build_relation_dataset(split="evaluation", cases_per_relation=10, seed=4040)
    expanded = build_relation_dataset(split="evaluation", cases_per_relation=50, seed=4040)

    assert _evidence_level(exploratory) == "exploratory"
    assert _evidence_level(expanded) == "expanded"


def test_provider_case_report_is_local_and_auditable(tmp_path) -> None:
    dataset = build_relation_dataset(split="evaluation", cases_per_relation=1, seed=4040)
    pair = dataset.inputs[0]
    gold = {(str(item.left_id), str(item.right_id)): item.relation for item in dataset.gold}
    predictions = [
        CorrelationPrediction(
            left_id=str(pair.left_id),
            right_id=str(pair.right_id),
            selected=True,
            predicted_relation=gold[(str(pair.left_id), str(pair.right_id))],
            exclusion_reason=None,
            failure_code=None,
            operation=None,
            sent_to_provider=True,
            confidence=0.91,
            justification="Os relatos descrevem o mesmo sinal no mesmo período.",
        ),
        CorrelationPrediction(
            left_id=str(dataset.inputs[1].left_id),
            right_id=str(dataset.inputs[1].right_id),
            selected=False,
            predicted_relation=None,
            exclusion_reason="geographic_mismatch",
            failure_code=None,
            operation=None,
        ),
    ]

    rows = _build_provider_case_rows(dataset, predictions, gold, run=1)

    assert len(rows) == 1
    assert rows[0] == {
        "run": 1,
        "left_id": str(pair.left_id),
        "right_id": str(pair.right_id),
        "gold_relation": gold[(str(pair.left_id), str(pair.right_id))],
        "predicted_relation": gold[(str(pair.left_id), str(pair.right_id))],
        "confidence": 0.91,
        "failure_code": None,
        "justification": "Os relatos descrevem o mesmo sinal no mesmo período.",
        "left_summary": pair.left["source_summary"],
        "right_summary": pair.right["source_summary"],
    }

    report_path = _write_case_report(rows, tmp_path, "relation-evaluation-test")
    with report_path.open(encoding="utf-8", newline="") as handle:
        written = list(csv.DictReader(handle))
    assert len(written) == 1
    assert written[0]["confidence"] == "0.91"
    assert written[0]["justification"] == rows[0]["justification"]
