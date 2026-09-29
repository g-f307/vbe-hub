from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from vbe_hub.application.ai import ProviderError, StructuredExtractor
from vbe_hub.evaluation.decisions import derive_field_decisions
from vbe_hub.evaluation.metrics import EvaluationCase
from vbe_hub.evaluation.protocol import ExperimentConfig
from vbe_hub.evaluation.report import build_report
from vbe_hub.evaluation.runner import EvaluationInput, extract_predictions

_ASSETS = Path(__file__).with_name("assets")


async def run_evaluation(
    *,
    split: str,
    extractor: StructuredExtractor,
    provider: str,
    model: str,
    output_directory: Path,
    input_usd_per_million: float | None = None,
    output_usd_per_million: float | None = None,
) -> dict[str, Any]:
    definition = _read_json(_ASSETS / "experiment-v1.json")
    inputs_path = _ASSETS / f"{split}-inputs.json"
    gold_path = _ASSETS / f"{split}-gold.json"
    raw_inputs = _read_json(inputs_path)
    gold_document = _read_json(gold_path)
    records = [EvaluationInput(**item) for item in raw_inputs]
    gold_by_id = {item["record_id"]: item["fields"] for item in gold_document["labels"]}
    if set(gold_by_id) != {record.record_id for record in records}:
        raise ValueError("input and gold identifiers must match exactly")

    dataset_digest = hashlib.sha256(inputs_path.read_bytes() + gold_path.read_bytes()).hexdigest()
    config = ExperimentConfig(
        dataset_version=definition["dataset_version"],
        dataset_sha256=dataset_digest,
        split=split,
        seed=definition["seed"],
        provider=provider,
        model=model,
        prompt_version=definition["prompt_version"],
        schema_version=definition["schema_version"],
        normalizer_version=definition["normalizer_version"],
    )

    successes = []
    failures: list[dict[str, str]] = []
    for record in records:
        try:
            successes.extend(
                await extract_predictions(
                    [record], extractor=extractor, prompt_version=config.prompt_version
                )
            )
        except ProviderError as error:
            failures.append(
                {"record_id": record.record_id, "kind": "schema/operational", "code": error.code}
            )

    predictions = {item.record_id: _flatten(item.technical_sheet) for item in successes}
    cases = [
        EvaluationCase(
            record.record_id, gold_by_id[record.record_id], predictions.get(record.record_id, {})
        )
        for record in records
    ]
    latencies = [item.metadata.duration_ms for item in successes]
    input_units = sum(item.metadata.input_units or 0 for item in successes)
    output_units = sum(item.metadata.output_units or 0 for item in successes)
    execution = {
        "attempted": len(records),
        "succeeded": len(successes),
        "failed": len(failures),
        "failure_rate": round(len(failures) / len(records), 6),
        "failures": failures,
        "cache_hits": sum(int(item.metadata.cache_hit) for item in successes),
        "latency_ms_p50": _percentile(latencies, 0.50),
        "latency_ms_p95": _percentile(latencies, 0.95),
        "input_units": input_units,
        "output_units": output_units,
        "estimated_cost_usd": _cost(
            input_units, output_units, input_usd_per_million, output_usd_per_million
        ),
    }
    report = build_report(
        experiment={
            **config.model_dump(),
            "identity": config.identity,
            "targets": definition["targets"],
        },
        cases=cases,
        field_kinds=definition["field_kinds"],
        execution=execution,
    )
    report["field_decisions"] = derive_field_decisions(
        fields=report["fields"],
        critical_fields=definition["critical_fields"],
        targets=definition["targets"],
        operational_failure_rate=execution["failure_rate"],
    )
    _write_reports(report, output_directory)
    return report


def assert_splits_are_disjoint() -> None:
    calibration = {item["record_id"] for item in _read_json(_ASSETS / "calibration-inputs.json")}
    evaluation = {item["record_id"] for item in _read_json(_ASSETS / "evaluation-inputs.json")}
    if calibration & evaluation:
        raise ValueError("calibration and evaluation splits must not overlap")


def _flatten(sheet: Any, prefix: str = "") -> dict[str, Any]:
    value = sheet.model_dump(mode="json") if hasattr(sheet, "model_dump") else dict(sheet)
    flattened: dict[str, Any] = {}
    for key, item in value.items():
        name = f"{prefix}.{key}" if prefix else key
        if isinstance(item, dict):
            flattened.update(_flatten(item, name))
        else:
            flattened[name] = item
    return flattened


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _percentile(values: list[int], percentile: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * percentile) - 1)]


def _cost(
    input_units: int,
    output_units: int,
    input_price: float | None,
    output_price: float | None,
) -> float | None:
    if input_price is None or output_price is None:
        return None
    return round((input_units * input_price + output_units * output_price) / 1_000_000, 8)


def _write_reports(report: dict[str, Any], output_directory: Path) -> None:
    output_directory.mkdir(parents=True, exist_ok=True)
    stem = f"technical-sheet-{report['experiment']['split']}-{report['experiment']['identity']}"
    (output_directory / f"{stem}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with (output_directory / f"{stem}.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["field", *next(iter(report["fields"].values()))]
        )
        writer.writeheader()
        for field, metrics in report["fields"].items():
            writer.writerow({"field": field, **metrics})
    experiment = report["experiment"]
    execution = report["execution"]
    lines = [
        f"# Avaliação da ficha técnica — {report['experiment']['split']}",
        "",
        f"- Execução: `{report['experiment']['identity']}`",
        f"- Provider/modelo: `{experiment['provider']}` / `{experiment['model']}`",
        f"- Registros: {report['execution']['attempted']}",
        f"- Falhas operacionais: {report['execution']['failed']}",
        f"- Latência p50/p95: {execution['latency_ms_p50']} / {execution['latency_ms_p95']} ms",
        f"- Custo estimado: {report['execution']['estimated_cost_usd']}",
        "",
        "| Campo | Cobertura | Acurácia | Alucinação | Omissão | F1 | MAE |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for field, metrics in report["fields"].items():
        lines.append(
            f"| {field} | {_fmt(metrics['coverage'])} | {_fmt(metrics['accuracy'])} | "
            f"{_fmt(metrics['hallucination_rate'])} | {_fmt(metrics['omission_rate'])} | "
            f"{_fmt(metrics['f1'])} | {_fmt(metrics['mean_absolute_error'])} |"
        )
    (output_directory / f"{stem}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _fmt(value: Any) -> str:
    return "—" if value is None else str(value)
