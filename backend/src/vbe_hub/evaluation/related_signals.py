from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from math import ceil
from pathlib import Path
from typing import Any

from vbe_hub.application.ai import RelationJudge
from vbe_hub.application.correlation.candidates import CandidatePolicy, GeographicLevel
from vbe_hub.evaluation.correlation_pipeline import (
    evaluate_predictions,
    predict_relation_pairs,
)
from vbe_hub.evaluation.relation_dataset import build_relation_dataset

_REQUIRED_FAILURE_PROBES = {
    "backlog": "pending",
    "timeout": "failed",
    "rate_limited": "failed",
    "quota_exhausted": "failed",
    "reprocessing": "ready",
}

_TARGETS = {
    "ready_read_p95_ms": 500,
    "preparation_p95_ms": 60_000,
    "candidate_recall": 0.90,
    "macro_f1": 0.75,
}


@dataclass(frozen=True, slots=True)
class StageSample:
    queue_ms: int
    extraction_ms: int
    embedding_ms: int
    candidate_search_ms: int
    judgment_ms: int
    persisted_read_ms: int
    input_tokens: int
    output_tokens: int
    cache_hit: bool

    def __post_init__(self) -> None:
        if any(value < 0 for value in asdict(self).values() if isinstance(value, int)):
            raise ValueError("stage measurements must be non-negative")


@dataclass(frozen=True, slots=True)
class FailureProbe:
    scenario: str
    visible_status: str
    recoverable: bool


@dataclass(frozen=True, slots=True)
class RelatedEvaluationInput:
    mode: str
    dataset_identity: str
    dataset_size: int
    positive_pairs: int
    candidate_recall: float
    macro_f1: float
    samples: tuple[StageSample, ...]
    failure_probes: tuple[FailureProbe, ...]
    cache_invalidated_after_prompt_change: bool
    input_usd_per_million: float
    output_usd_per_million: float
    commit: str


def build_related_evaluation_report(value: RelatedEvaluationInput) -> dict:
    if value.mode not in {"recorded", "live"}:
        raise ValueError("mode must be recorded or live")
    if value.dataset_size <= 0 or not value.samples:
        raise ValueError("evaluation requires a non-empty identified sample")

    stages = {
        "queue": [sample.queue_ms for sample in value.samples],
        "extraction": [sample.extraction_ms for sample in value.samples],
        "embedding": [sample.embedding_ms for sample in value.samples],
        "candidate_search": [sample.candidate_search_ms for sample in value.samples],
        "judgment": [sample.judgment_ms for sample in value.samples],
        "persisted_read": [sample.persisted_read_ms for sample in value.samples],
        "preparation_total": [
            sample.queue_ms
            + sample.extraction_ms
            + sample.embedding_ms
            + sample.candidate_search_ms
            + sample.judgment_ms
            for sample in value.samples
        ],
    }
    latency = {
        name: {"p50": _percentile(samples, 0.50), "p95": _percentile(samples, 0.95)}
        for name, samples in stages.items()
    }
    paid = [sample for sample in value.samples if not sample.cache_hit]
    input_tokens = sum(sample.input_tokens for sample in paid)
    output_tokens = sum(sample.output_tokens for sample in paid)
    cost = round(
        (
            input_tokens * value.input_usd_per_million
            + output_tokens * value.output_usd_per_million
        )
        / 1_000_000,
        8,
    )
    probes = {probe.scenario: probe.visible_status for probe in value.failure_probes}
    failure_communication = all(
        probes.get(scenario) == expected
        for scenario, expected in _REQUIRED_FAILURE_PROBES.items()
    )
    passed = {
        "ready_read_slo": latency["persisted_read"]["p95"] <= _TARGETS["ready_read_p95_ms"],
        "preparation_slo": latency["preparation_total"]["p95"]
        <= _TARGETS["preparation_p95_ms"],
        "candidate_recall": value.candidate_recall >= _TARGETS["candidate_recall"],
        "relation_quality": value.macro_f1 >= _TARGETS["macro_f1"],
        "failure_communication": failure_communication,
        "cache_invalidation": value.cache_invalidated_after_prompt_change,
    }
    canonical = json.dumps(asdict(value), sort_keys=True, separators=(",", ":"))
    identity = hashlib.sha256(canonical.encode()).hexdigest()[:16]
    status = "block" if not all(passed.values()) else (
        "approve" if value.mode == "live" else "approve_with_caveats"
    )
    return {
        "report_version": "related-signals-evaluation-v1",
        "identity": identity,
        "mode": value.mode,
        "commit": value.commit,
        "dataset": {
            "identity": value.dataset_identity,
            "signals": value.dataset_size,
            "positive_pairs": value.positive_pairs,
            "scope": "synthetic technical evaluation",
        },
        "evidence": {
            "level": "live" if value.mode == "live" else "contract_fixture",
            "limitation": (
                "Recorded values validate calculations and report contracts; "
                "they are not measurements of a live provider."
                if value.mode == "recorded"
                else "Live technical measurement on synthetic data."
            ),
        },
        "targets": _TARGETS,
        "latency_ms": latency,
        "quality": {
            "candidate_recall": value.candidate_recall,
            "macro_f1": value.macro_f1,
        },
        "usage": {
            "provider_calls": len(paid),
            "cache_hits": len(value.samples) - len(paid),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "estimated_cost_usd": cost,
            "cost_per_signal_usd": round(cost / value.dataset_size, 10),
        },
        "failure_probes": [asdict(probe) for probe in value.failure_probes],
        "cache": {
            "invalidated_after_prompt_change": value.cache_invalidated_after_prompt_change
        },
        "decision": {"status": status, "passed": passed},
        "health_summary": {
            "what_was_demonstrated": (
                "A aba pronta lê sugestões já armazenadas sem aguardar a IA."
            ),
            "what_failures_mean": (
                "Pendente indica processamento; falha informa indisponibilidade "
                "sem decidir pelo analista."
            ),
            "what_was_not_demonstrated": (
                "O teste não confirma surtos, diagnósticos nem eficácia epidemiológica."
            ),
        },
    }

def run_recorded_evaluation(source: Path, output: Path, *, commit: str) -> dict:
    payload = json.loads(source.read_text(encoding="utf-8"))
    value = RelatedEvaluationInput(
        mode=payload["mode"],
        dataset_identity=payload["dataset_identity"],
        dataset_size=payload["dataset_size"],
        positive_pairs=payload["positive_pairs"],
        candidate_recall=payload["candidate_recall"],
        macro_f1=payload["macro_f1"],
        samples=tuple(StageSample(**sample) for sample in payload["samples"]),
        failure_probes=tuple(
            FailureProbe(**probe) for probe in payload["failure_probes"]
        ),
        cache_invalidated_after_prompt_change=payload[
            "cache_invalidated_after_prompt_change"
        ],
        input_usd_per_million=payload["input_usd_per_million"],
        output_usd_per_million=payload["output_usd_per_million"],
        commit=commit,
    )
    report = build_related_evaluation_report(value)
    output.mkdir(parents=True, exist_ok=True)
    (output / "related-signals-evaluation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    latency = report["latency_ms"]
    usage = report["usage"]
    summary = report["health_summary"]
    lines = [
        "# Resultado dos sinais relacionados para a equipe de saúde",
        "",
        f"- Decisão técnica: `{report['decision']['status']}`.",
        f"- Amostra: {report['dataset']['signals']} sinais sintéticos identificados.",
        f"- Leitura da aba pronta (p95): {latency['persisted_read']['p95']} ms.",
        f"- Preparação após entrada do sinal (p95): {latency['preparation_total']['p95']} ms.",
        f"- Custo estimado do lote: US$ {usage['estimated_cost_usd']:.8f}.",
        "",
        f"**O que foi demonstrado:** {summary['what_was_demonstrated']}",
        "",
        f"**Como interpretar falhas:** {summary['what_failures_mean']}",
        "",
        f"**Limite da evidência:** {summary['what_was_not_demonstrated']}",
    ]
    (output / "related-signals-evaluation-health.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    return report


async def run_relation_quality_evaluation(
    *,
    judge: RelationJudge,
    cases_per_relation: int,
    seed: int,
    input_usd_per_million: float,
    output_usd_per_million: float,
) -> dict[str, Any]:
    dataset = build_relation_dataset(
        split="calibration", cases_per_relation=cases_per_relation, seed=seed
    )
    predictions = await predict_relation_pairs(
        dataset.inputs,
        judge=judge,
        policy=CandidatePolicy(14, GeographicLevel.MUNICIPALITY, 0.65, 0.65),
        relation_prompt_version="relate-v2.1",
        input_usd_per_million=input_usd_per_million,
        output_usd_per_million=output_usd_per_million,
    )
    gold = {(str(item.left_id), str(item.right_id)): item.relation for item in dataset.gold}
    metrics = evaluate_predictions(predictions, gold_relations=gold)
    passed = {
        "candidate_recall": metrics.candidates.recall >= _TARGETS["candidate_recall"],
        "relation_quality": metrics.classification.macro_f1 >= _TARGETS["macro_f1"],
        "provider_failures": metrics.classification.failures == 0,
    }
    return {
        "report_version": "related-signals-live-quality-v1",
        "dataset": {
            "identity": (
                f"relation-calibration-v3:seed-{seed}:cases-{cases_per_relation}"
            ),
            "pairs": len(dataset.inputs),
            "gold_relations": len(dataset.gold),
            "scope": "synthetic technical evaluation",
        },
        "quality": {
            "candidate_recall": metrics.candidates.recall,
            "macro_f1": metrics.classification.macro_f1,
            "failures": metrics.classification.failures,
            "failures_by_code": metrics.classification.failures_by_code,
        },
        "operations": {
            "provider_calls": metrics.operations.provider_calls,
            "cache_hits": metrics.operations.cache_hits,
            "latency_ms_p50": metrics.operations.latency_ms_p50,
            "latency_ms_p95": metrics.operations.latency_ms_p95,
            "input_tokens": metrics.operations.input_units,
            "output_tokens": metrics.operations.output_units,
            "estimated_cost_usd": metrics.operations.estimated_cost_usd,
        },
        "decision": {
            "status": "approve" if all(passed.values()) else "block",
            "passed": passed,
        },
        "limitation": (
            "small synthetic sample; no clinical or epidemiological validity"
        ),
    }


def _percentile(values: list[int], percentile: float) -> int:
    ordered = sorted(values)
    return ordered[max(0, ceil(len(ordered) * percentile) - 1)]
