from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from random import Random

from vbe_hub.application.correlation.signals import (
    ConsolidationPolicy,
    SignalConsolidationService,
)
from vbe_hub.evaluation.grouping_dataset import GroupingDataset, build_grouping_dataset
from vbe_hub.evaluation.grouping_metrics import (
    EvaluatedCluster,
    GroupingEvaluationInput,
    GroupingMetrics,
    evaluate_grouping,
)

_TARGETS = {
    "pairwise_f1": 0.95,
    "b_cubed_f1": 0.95,
    "purity": 0.95,
    "inverse_purity": 0.95,
    "merge_rate": 0.05,
    "split_rate": 0.05,
}


def run_grouping_experiment(
    *,
    split: str,
    event_count: int,
    seed: int,
    commit: str,
    bootstrap_iterations: int = 500,
) -> dict:
    if bootstrap_iterations < 1:
        raise ValueError("bootstrap_iterations must be positive")
    dataset = build_grouping_dataset(split=split, event_count=event_count, seed=seed)
    inputs_bytes = _canonical(dataset.inputs.to_dict())
    gold_bytes = _canonical(dataset.gold.to_dict())
    config = {
        "dataset_version": dataset.inputs.dataset_version,
        "input_sha256": hashlib.sha256(inputs_bytes).hexdigest(),
        "gold_sha256": hashlib.sha256(gold_bytes).hexdigest(),
        "split": split,
        "seed": seed,
        "commit": commit,
        "consolidation_policy": "signal-consolidation-v1",
        "review_policy": "synthetic-review-v1",
        "evaluator_version": "grouping-evaluator-v1",
        "bootstrap_iterations": bootstrap_iterations,
        "targets": _TARGETS,
    }
    identity = hashlib.sha256(_canonical(config)).hexdigest()[:16]
    automatic = _consolidate(dataset, reviewed=False)
    reviewed = _consolidate(dataset, reviewed=True)
    automatic_metrics = evaluate_grouping(
        GroupingEvaluationInput(dataset.gold.event_by_record, automatic)
    )
    reviewed_metrics = evaluate_grouping(
        GroupingEvaluationInput(dataset.gold.event_by_record, reviewed)
    )
    automatic_summary = _summary(
        automatic_metrics,
        event_count=event_count,
        intervals=_bootstrap(
            dataset.gold.event_by_record,
            automatic,
            seed=seed,
            iterations=bootstrap_iterations,
        ),
    )
    reviewed_summary = _summary(
        reviewed_metrics,
        event_count=event_count,
        intervals=_bootstrap(
            dataset.gold.event_by_record,
            reviewed,
            seed=seed + 1,
            iterations=bootstrap_iterations,
        ),
    )
    passed = {
        "pairwise_f1": automatic_metrics.pairwise.f1 >= _TARGETS["pairwise_f1"],
        "b_cubed_f1": automatic_metrics.b_cubed.f1 >= _TARGETS["b_cubed_f1"],
        "purity": automatic_metrics.purity >= _TARGETS["purity"],
        "inverse_purity": automatic_metrics.inverse_purity
        >= _TARGETS["inverse_purity"],
        "merge_rate": automatic_summary["merges"]["rate"] <= _TARGETS["merge_rate"],
        "split_rate": automatic_summary["splits"]["rate"] <= _TARGETS["split_rate"],
    }
    return {
        "report_version": "grouping-experiment-report-v1",
        "experiment": {**config, "identity": identity},
        "dataset": {
            "events": event_count,
            "records": len(dataset.inputs.records),
            "automatic_relations": len(dataset.inputs.automatic_relations),
            "reviewed_relations": len(dataset.inputs.reviewed_relations),
            "scenario_distribution": dataset.inputs.scenario_counts,
            "splits_disjoint_by_design": True,
        },
        "automatic": automatic_summary,
        "reviewed": reviewed_summary,
        "by_scenario": _by_scenario(dataset, automatic, reviewed),
        "review": {
            "decisions": len(dataset.inputs.reviews),
            "actions": dict(
                sorted(
                    {
                        action: sum(item.action == action for item in dataset.inputs.reviews)
                        for action in {item.action for item in dataset.inputs.reviews}
                    }.items()
                )
            ),
            "items": [item.to_dict() for item in dataset.inputs.reviews],
        },
        "operations": {
            "provider_calls": 0,
            "cache_hits": 0,
            "failures": 0,
            "latency_ms": {"p50": 0, "p95": 0},
            "input_units": 0,
            "output_units": 0,
            "estimated_cost_usd": 0.0,
        },
        "decision": {
            "status": "approve_with_caveats" if all(passed.values()) else "block",
            "targets": _TARGETS,
            "passed": passed,
            "evidence_level": "expanded_synthetic",
            "limitation": (
                "synthetic frozen relation inputs; validates grouping, not clinical or "
                "epidemiological performance"
            ),
            "scope": "technical synthetic grouping validation",
        },
    }


def write_grouping_report(report: dict, output_directory: Path) -> tuple[Path, Path, Path]:
    output_directory.mkdir(parents=True, exist_ok=True)
    stem = f"grouping-{report['experiment']['split']}-{report['experiment']['identity']}"
    json_path = output_directory / f"{stem}.json"
    markdown_path = output_directory / f"{stem}.md"
    errors_path = output_directory / f"{stem}-errors.csv"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(_markdown(report), encoding="utf-8")
    _write_errors(report, errors_path)
    return json_path, markdown_path, errors_path


def _consolidate(dataset: GroupingDataset, *, reviewed: bool) -> tuple[EvaluatedCluster, ...]:
    relations = (
        dataset.inputs.reviewed_relations if reviewed else dataset.inputs.automatic_relations
    )
    result = SignalConsolidationService(
        ConsolidationPolicy(version="signal-consolidation-v1")
    ).consolidate(records=dataset.inputs.records, relations=relations)
    return tuple(
        EvaluatedCluster(
            cluster_id=str(signal.id),
            core_record_ids=tuple(str(item) for item in signal.core_record_ids),
            context_record_ids=tuple(str(item) for item in signal.context_record_ids),
            relation_ids=tuple(str(item) for item in signal.relation_ids),
        )
        for signal in result.signals
    )


def _summary(metrics: GroupingMetrics, *, event_count: int, intervals: dict) -> dict:
    merge_items = [asdict(item) for item in metrics.merges]
    split_items = [asdict(item) for item in metrics.splits]
    return {
        "pairwise": asdict(metrics.pairwise),
        "b_cubed": asdict(metrics.b_cubed),
        "purity": metrics.purity,
        "inverse_purity": metrics.inverse_purity,
        "merges": {
            "count": len(merge_items),
            "rate": round(len(merge_items) / event_count, 6),
            "items": merge_items,
        },
        "splits": {
            "count": len(split_items),
            "rate": round(len(split_items) / event_count, 6),
            "items": split_items,
        },
        "lost_record_ids": list(metrics.lost_record_ids),
        "spurious_record_ids": list(metrics.spurious_record_ids),
        "spurious_cluster_ids": list(metrics.spurious_cluster_ids),
        "failure_counts": dict(metrics.failure_counts),
        "cluster_size_distribution": {
            str(key): value for key, value in metrics.cluster_size_distribution.items()
        },
        "confidence_intervals_95": intervals,
    }


def _by_scenario(
    dataset: GroupingDataset,
    automatic: tuple[EvaluatedCluster, ...],
    reviewed: tuple[EvaluatedCluster, ...],
) -> dict:
    result = {}
    for scenario in sorted(dataset.inputs.scenario_counts):
        event_ids = {
            event_id
            for event_id, item_scenario in dataset.gold.scenario_by_event.items()
            if item_scenario == scenario
        }
        gold = {
            record_id: event_id
            for record_id, event_id in dataset.gold.event_by_record.items()
            if event_id in event_ids
        }
        automatic_metrics = evaluate_grouping(
            GroupingEvaluationInput(gold, _restrict_clusters(automatic, set(gold)))
        )
        reviewed_metrics = evaluate_grouping(
            GroupingEvaluationInput(gold, _restrict_clusters(reviewed, set(gold)))
        )
        result[scenario] = {
            "events": len(event_ids),
            "records": len(gold),
            "automatic": {
                "pairwise_f1": automatic_metrics.pairwise.f1,
                "b_cubed_f1": automatic_metrics.b_cubed.f1,
                "merges": len(automatic_metrics.merges),
                "splits": len(automatic_metrics.splits),
            },
            "reviewed": {
                "pairwise_f1": reviewed_metrics.pairwise.f1,
                "b_cubed_f1": reviewed_metrics.b_cubed.f1,
                "merges": len(reviewed_metrics.merges),
                "splits": len(reviewed_metrics.splits),
            },
        }
    return result


def _restrict_clusters(
    clusters: tuple[EvaluatedCluster, ...], record_ids: set[str]
) -> tuple[EvaluatedCluster, ...]:
    return tuple(
        EvaluatedCluster(
            cluster_id=item.cluster_id,
            core_record_ids=tuple(value for value in item.core_record_ids if value in record_ids),
            relation_ids=item.relation_ids,
        )
        for item in clusters
        if set(item.core_record_ids).intersection(record_ids)
    )


def _bootstrap(
    gold: dict[str, str],
    clusters: tuple[EvaluatedCluster, ...],
    *,
    seed: int,
    iterations: int,
) -> dict:
    predicted = {
        record_id: cluster.cluster_id
        for cluster in clusters
        for record_id in cluster.core_record_ids
    }
    records = sorted(gold)
    random = Random(seed)
    pairwise_values = []
    b_cubed_values = []
    for _ in range(iterations):
        sampled_gold: dict[str, str] = {}
        sampled_clusters: dict[str, list[str]] = {}
        for index in range(len(records)):
            original = records[random.randrange(len(records))]
            sampled = f"sample-{index}"
            sampled_gold[sampled] = gold[original]
            if original in predicted:
                sampled_clusters.setdefault(predicted[original], []).append(sampled)
        metrics = evaluate_grouping(
            GroupingEvaluationInput(
                sampled_gold,
                tuple(
                    EvaluatedCluster(cluster_id, tuple(members))
                    for cluster_id, members in sorted(sampled_clusters.items())
                ),
            )
        )
        pairwise_values.append(metrics.pairwise.f1)
        b_cubed_values.append(metrics.b_cubed.f1)
    return {
        "method": "nonparametric bootstrap over synthetic records",
        "iterations": iterations,
        "pairwise_f1": _interval(pairwise_values),
        "b_cubed_f1": _interval(b_cubed_values),
    }


def _interval(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)
    count = len(ordered)
    return {
        "lower": ordered[int(count * 0.025)],
        "upper": ordered[min(count - 1, int(count * 0.975))],
    }


def _canonical(value: dict) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode()


def _markdown(report: dict) -> str:
    return "\n".join(
        [
            "# Avaliação de agrupamentos sintéticos",
            "",
            f"- Identidade: `{report['experiment']['identity']}`",
            f"- Split: `{report['experiment']['split']}`",
            f"- Decisão: `{report['decision']['status']}`",
            f"- Eventos: {report['dataset']['events']}",
            f"- Registros: {report['dataset']['records']}",
            "",
            "| Resultado | Pairwise F1 | B-cubed F1 | Pureza | Cobertura | Merges | Splits |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
            _metric_row("Automático", report["automatic"]),
            _metric_row("Após revisão", report["reviewed"]),
            "",
            "Validação técnica com dados e relações sintéticas congeladas; não demonstra validade ",
            "clínica, epidemiológica nem desempenho sobre fontes reais.",
            "",
        ]
    )


def _metric_row(label: str, result: dict) -> str:
    return (
        f"| {label} | {result['pairwise']['f1']} | {result['b_cubed']['f1']} | "
        f"{result['purity']} | {result['inverse_purity']} | "
        f"{result['merges']['count']} | {result['splits']['count']} |"
    )


def _write_errors(report: dict, path: Path) -> None:
    rows = []
    for result_name in ("automatic", "reviewed"):
        for kind in ("merges", "splits"):
            for item in report[result_name][kind]["items"]:
                rows.append(
                    {
                        "result": result_name,
                        "error_type": kind[:-1],
                        "entity_id": item.get("cluster_id") or item.get("gold_event_id"),
                        "record_ids": ";".join(item.get("record_ids", ())),
                        "relation_ids": ";".join(item.get("relation_ids", ())),
                        "details": json.dumps(item, ensure_ascii=False, sort_keys=True),
                    }
                )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=(
                "result",
                "error_type",
                "entity_id",
                "record_ids",
                "relation_ids",
                "details",
            ),
        )
        writer.writeheader()
        writer.writerows(rows)


def _main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate synthetic signal grouping")
    parser.add_argument("--split", choices=("calibration", "evaluation"), required=True)
    parser.add_argument("--event-count", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--bootstrap-iterations", type=int, default=500)
    parser.add_argument("--output", type=Path, default=Path("/data/reports"))
    args = parser.parse_args()
    report = run_grouping_experiment(
        split=args.split,
        event_count=args.event_count,
        seed=args.seed,
        commit=args.commit,
        bootstrap_iterations=args.bootstrap_iterations,
    )
    write_grouping_report(report, args.output)
    print(
        json.dumps(
            {"identity": report["experiment"]["identity"], **report["decision"]},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    _main()
