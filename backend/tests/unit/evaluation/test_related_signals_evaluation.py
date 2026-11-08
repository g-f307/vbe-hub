import json
from dataclasses import replace
from datetime import UTC, datetime

from vbe_hub.application.ai import (
    AIExecutionMetadata,
    ExecutionStatus,
    RelationKind,
    RelationResult,
)
from vbe_hub.evaluation.related_signals import (
    FailureProbe,
    RelatedEvaluationInput,
    StageSample,
    build_related_evaluation_report,
    run_recorded_evaluation,
    run_relation_quality_evaluation,
)


def evaluation_input() -> RelatedEvaluationInput:
    return RelatedEvaluationInput(
        mode="recorded",
        dataset_identity="related-signals-v1:abc123",
        dataset_size=20,
        positive_pairs=10,
        candidate_recall=1.0,
        macro_f1=0.8,
        samples=(
            StageSample(12, 110, 35, 18, 220, 8, 100, 20, False),
            StageSample(20, 140, 45, 25, 300, 10, 120, 30, False),
            StageSample(8, 0, 0, 12, 0, 7, 0, 0, True),
        ),
        failure_probes=(
            FailureProbe("timeout", "failed", True),
            FailureProbe("rate_limited", "failed", True),
            FailureProbe("quota_exhausted", "failed", False),
            FailureProbe("reprocessing", "ready", True),
            FailureProbe("backlog", "pending", True),
        ),
        cache_invalidated_after_prompt_change=True,
        input_usd_per_million=0.10,
        output_usd_per_million=0.50,
        commit="abc1234",
    )


def test_report_measures_each_stage_and_excludes_cache_hits_from_cost() -> None:
    report = build_related_evaluation_report(evaluation_input())

    assert report["latency_ms"] == {
        "queue": {"p50": 12, "p95": 20},
        "extraction": {"p50": 110, "p95": 140},
        "embedding": {"p50": 35, "p95": 45},
        "candidate_search": {"p50": 18, "p95": 25},
        "judgment": {"p50": 220, "p95": 300},
        "persisted_read": {"p50": 8, "p95": 10},
        "preparation_total": {"p50": 395, "p95": 530},
    }
    assert report["usage"] == {
        "provider_calls": 2,
        "cache_hits": 1,
        "input_tokens": 220,
        "output_tokens": 50,
        "estimated_cost_usd": 0.000047,
        "cost_per_signal_usd": 0.00000235,
    }


def test_report_translates_operational_result_without_claiming_health_validity() -> None:
    report = build_related_evaluation_report(evaluation_input())

    assert report["decision"]["status"] == "approve_with_caveats"
    assert report["evidence"]["level"] == "contract_fixture"
    assert report["decision"]["passed"] == {
        "ready_read_slo": True,
        "preparation_slo": True,
        "candidate_recall": True,
        "relation_quality": True,
        "failure_communication": True,
        "cache_invalidation": True,
    }
    assert report["health_summary"]["what_was_demonstrated"] == (
        "A aba pronta lê sugestões já armazenadas sem aguardar a IA."
    )
    assert report["health_summary"]["what_was_not_demonstrated"] == (
        "O teste não confirma surtos, diagnósticos nem eficácia epidemiológica."
    )


def test_missing_failure_probe_blocks_operational_approval() -> None:
    value = evaluation_input()
    report = build_related_evaluation_report(
        replace(value, failure_probes=value.failure_probes[:-1])
    )

    assert report["decision"]["status"] == "block"
    assert report["decision"]["passed"]["failure_communication"] is False


def test_recorded_command_writes_machine_and_health_facing_reports(tmp_path) -> None:
    source = tmp_path / "capture.json"
    source.write_text(
        json.dumps(
            {
                "mode": "recorded",
                "dataset_identity": "related-signals-v1:abc123",
                "dataset_size": 20,
                "positive_pairs": 10,
                "candidate_recall": 1.0,
                "macro_f1": 0.8,
                "samples": [
                    {
                        "queue_ms": 10,
                        "extraction_ms": 100,
                        "embedding_ms": 30,
                        "candidate_search_ms": 20,
                        "judgment_ms": 200,
                        "persisted_read_ms": 9,
                        "input_tokens": 100,
                        "output_tokens": 20,
                        "cache_hit": False,
                    }
                ],
                "failure_probes": [
                    {"scenario": name, "visible_status": status, "recoverable": True}
                    for name, status in {
                        "timeout": "failed",
                        "rate_limited": "failed",
                        "quota_exhausted": "failed",
                        "reprocessing": "ready",
                        "backlog": "pending",
                    }.items()
                ],
                "cache_invalidated_after_prompt_change": True,
                "input_usd_per_million": 0.1,
                "output_usd_per_million": 0.5,
            }
        ),
        encoding="utf-8",
    )

    report = run_recorded_evaluation(source, tmp_path, commit="abc1234")

    assert report["dataset"]["signals"] == 20
    assert (tmp_path / "related-signals-evaluation.json").exists()
    health = (tmp_path / "related-signals-evaluation-health.md").read_text(encoding="utf-8")
    assert "Leitura da aba pronta" in health
    assert "não confirma surtos" in health


class FixedJudge:
    async def judge(self, request):
        return RelationResult(
            relation=RelationKind.CORROBORATES,
            justification="Fontes compatíveis no mesmo local e período.",
            confidence=0.8,
            metadata=AIExecutionMetadata(
                provider="openai",
                model="test-model",
                contract_version="relation-v1",
                prompt_version=request.prompt_version,
                started_at=datetime(2026, 11, 8, tzinfo=UTC),
                duration_ms=100,
                status=ExecutionStatus.SUCCEEDED,
                input_units=50,
                output_units=10,
            ),
        )


async def test_live_quality_evaluation_records_provider_usage_and_sample_identity() -> None:
    result = await run_relation_quality_evaluation(
        judge=FixedJudge(),
        cases_per_relation=1,
        seed=4040,
        input_usd_per_million=0.1,
        output_usd_per_million=0.5,
    )

    assert result["dataset"] == {
        "identity": "relation-calibration-v3:seed-4040:cases-1",
        "pairs": 25,
        "gold_relations": 5,
        "scope": "synthetic technical evaluation",
    }
    assert result["operations"]["provider_calls"] == 4
    assert result["operations"]["input_tokens"] == 200
    assert result["operations"]["output_tokens"] == 40
    assert result["operations"]["estimated_cost_usd"] == 0.00004
    assert result["decision"] == {
        "status": "block",
        "passed": {
            "candidate_recall": True,
            "relation_quality": False,
            "provider_failures": True,
        },
    }
