from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
from pathlib import Path
from random import Random

from google import genai
from google.genai import types

from vbe_hub.adapters.ai.gemini_relations import GeminiRelationJudge
from vbe_hub.adapters.ai.google_genai_client import GoogleGenAIClient
from vbe_hub.application.correlation.candidates import CandidatePolicy, GeographicLevel
from vbe_hub.evaluation.correlation_pipeline import (
    CorrelationPrediction,
    evaluate_predictions,
    predict_relation_pairs,
)
from vbe_hub.evaluation.correlation_protocol import CorrelationExperimentConfig
from vbe_hub.evaluation.correlation_report import build_correlation_report
from vbe_hub.evaluation.relation_dataset import RelationDataset, build_relation_dataset
from vbe_hub.infrastructure.settings import Settings

PROMPT_VERSION = "relate-v2.1"
_TARGETS = {
    "candidate_recall": 0.90,
    "pair_reduction": 0.80,
    "macro_f1": 0.75,
    "operational_failure_rate": 0.05,
}


async def run_relation_experiment(
    *,
    settings: Settings,
    split: str,
    cases_per_relation: int,
    seed: int,
    repetitions: int,
    provider_concurrency: int,
    commit: str,
    output_directory: Path,
) -> dict:
    if split not in {"calibration", "evaluation"}:
        raise ValueError("split must be calibration or evaluation")
    if repetitions < 1:
        raise ValueError("repetitions must be positive")
    if not 1 <= provider_concurrency <= 8:
        raise ValueError("provider_concurrency must be between 1 and 8")
    if settings.gemini_api_key is None or not settings.gemini_api_key.get_secret_value().strip():
        raise SystemExit("GEMINI_API_KEY is required for the relation experiment.")

    dataset = build_relation_dataset(split=split, cases_per_relation=cases_per_relation, seed=seed)
    input_bytes, gold_bytes = _serialized_partitions(dataset)
    policy = CandidatePolicy(14, GeographicLevel.MUNICIPALITY, 0.65, 0.65)
    config = CorrelationExperimentConfig(
        dataset_version=f"relation-{split}-v3",
        dataset_sha256=hashlib.sha256(input_bytes + gold_bytes).hexdigest(),
        split=split,
        seed=seed,
        commit=commit,
        normalizer_version="not-applicable-precomputed-sheets",
        extraction_model="synthetic-technical-sheets-v3",
        embedding_model="synthetic-frozen-semantic-scores-v3",
        representation_version="relation-pair-v3",
        relation_model=settings.gemini_model,
        relation_prompt_version=PROMPT_VERSION,
        max_neighbors=5,
        provider_concurrency=provider_concurrency,
        provider_max_attempts=settings.gemini_max_attempts,
        repetitions=repetitions,
        processing_order="seeded-shuffle-v1",
        temporal_window_days=policy.max_temporal_gap_days,
        geographic_level=policy.geographic_level.value,
        minimum_semantic_score=policy.minimum_semantic_score,
        minimum_total_score=policy.minimum_total_score,
    )
    gold = {(str(item.left_id), str(item.right_id)): item.relation for item in dataset.gold}
    reports = []
    provider_case_rows: list[dict] = []
    root_client = genai.Client(
        api_key=settings.gemini_api_key.get_secret_value(),
        http_options=types.HttpOptions(
            api_version="v1",
            retry_options=types.HttpRetryOptions(attempts=settings.gemini_max_attempts),
        ),
    )
    async with root_client.aio as async_client:
        for run in range(1, repetitions + 1):
            judge = GeminiRelationJudge(
                client=GoogleGenAIClient(models=async_client.models, model=settings.gemini_model),
                model=settings.gemini_model,
                timeout_seconds=settings.gemini_timeout_seconds,
                max_input_chars=settings.gemini_max_input_chars,
            )
            predictions = await _predict_with_concurrency(
                dataset,
                order_seed=seed + run - 1,
                judge=judge,
                policy=policy,
                concurrency=provider_concurrency,
                relation_prompt_version=PROMPT_VERSION,
                input_usd_per_million=settings.gemini_input_usd_per_million,
                output_usd_per_million=settings.gemini_output_usd_per_million,
            )
            metrics = evaluate_predictions(predictions, gold_relations=gold)
            provider_attempts = sum(item.sent_to_provider for item in predictions)
            provider_case_rows.extend(
                _build_provider_case_rows(dataset, predictions, gold, run=run)
            )
            reports.append(
                {
                    **build_correlation_report(config=config, metrics=metrics),
                    "macro_f1_ci95": _bootstrap_macro_f1(predictions, gold, seed),
                    "provider_attempts": provider_attempts,
                }
            )

    result = _experiment_result(config, dataset, reports)
    _write_report(result, output_directory, provider_case_rows)
    return result


async def _predict_with_concurrency(
    dataset,
    *,
    order_seed=None,
    judge,
    policy,
    concurrency,
    relation_prompt_version,
    input_usd_per_million,
    output_usd_per_million,
):
    semaphore = asyncio.Semaphore(concurrency)
    pairs = (
        _shuffled_pairs(dataset.inputs, seed=order_seed)
        if order_seed is not None
        else list(dataset.inputs)
    )

    async def predict_one(pair):
        async with semaphore:
            predictions = await predict_relation_pairs(
                (pair,),
                judge=judge,
                policy=policy,
                relation_prompt_version=relation_prompt_version,
                input_usd_per_million=input_usd_per_million,
                output_usd_per_million=output_usd_per_million,
            )
            return predictions[0]

    return list(await asyncio.gather(*(predict_one(pair) for pair in pairs)))


def _shuffled_pairs(pairs, *, seed: int):
    shuffled = list(pairs)
    Random(seed).shuffle(shuffled)
    return shuffled


def _serialized_partitions(dataset: RelationDataset) -> tuple[bytes, bytes]:
    inputs = {
        "dataset_version": f"relation-{dataset.split}-v3",
        "split": dataset.split,
        "seed": dataset.seed,
        "pairs": [item.to_dict() for item in dataset.inputs],
    }
    gold = {
        "dataset_version": f"relation-{dataset.split}-v3-gold",
        "relations": [
            {
                "left_id": str(item.left_id),
                "right_id": str(item.right_id),
                "relation": item.relation,
            }
            for item in dataset.gold
        ],
    }

    def canonical(value):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()

    return canonical(inputs), canonical(gold)


def _bootstrap_macro_f1(predictions, gold, seed: int, iterations: int = 500) -> dict:
    by_pair = {(item.left_id, item.right_id): item for item in predictions}
    targets = [by_pair[pair] for pair in gold]
    random = Random(seed)
    values = []
    for _ in range(iterations):
        sampled = [targets[random.randrange(len(targets))] for _ in targets]
        sampled_gold = {
            (item.left_id, item.right_id): gold[(item.left_id, item.right_id)] for item in sampled
        }
        values.append(
            evaluate_predictions(sampled, gold_relations=sampled_gold).classification.macro_f1
        )
    values.sort()
    return {
        "method": "paired nonparametric bootstrap over target relations",
        "iterations": iterations,
        "lower": values[int(iterations * 0.025)],
        "upper": values[min(iterations - 1, int(iterations * 0.975))],
    }


def _evidence_level(dataset: RelationDataset) -> str:
    return "expanded" if min(dataset.relation_counts.values()) >= 50 else "exploratory"


def _operational_failure_rate(*, failures: int, provider_attempts: int) -> float:
    return round(failures / provider_attempts, 6) if provider_attempts else 0.0


def _experiment_result(config, dataset, reports: list[dict]) -> dict:
    run_summaries = []
    for index, report in enumerate(reports, start=1):
        failures = report["classification"]["failures"]
        provider_attempts = report["provider_attempts"]
        failure_rate = _operational_failure_rate(
            failures=failures, provider_attempts=provider_attempts
        )
        run_summaries.append(
            {
                "run": index,
                "candidate_recall": report["candidates"]["recall"],
                "pair_reduction": report["candidates"]["pair_reduction"],
                "macro_f1": report["classification"]["macro_f1"],
                "operational_failure_rate": failure_rate,
                "provider_attempts": provider_attempts,
                "macro_f1_ci95": report["macro_f1_ci95"],
                "classification": report["classification"],
                "operations": report["operations"],
            }
        )
    passed = {
        name: all(
            run[name] >= target if name != "operational_failure_rate" else run[name] <= target
            for run in run_summaries
        )
        for name, target in _TARGETS.items()
    }
    return {
        "report_version": "relation-experiment-report-v4",
        "experiment": {**config.model_dump(), "identity": config.identity},
        "dataset": {
            "input_pairs": len(dataset.inputs),
            "gold_relations": len(dataset.gold),
            "distribution": dataset.relation_counts,
            "decoys_per_target": 4,
            "evidence_level": _evidence_level(dataset),
        },
        "runs": run_summaries,
        "decision": {
            "status": "approve_with_caveats" if all(passed.values()) else "block",
            "evidence_level": _evidence_level(dataset),
            "limitation": (
                "small synthetic sample; limited statistical generalization"
                if _evidence_level(dataset) == "exploratory"
                else None
            ),
            "targets": _TARGETS,
            "passed": passed,
            "scope": "technical synthetic validation; no clinical or epidemiological validity",
        },
    }


def _build_provider_case_rows(
    dataset: RelationDataset,
    predictions: list[CorrelationPrediction],
    gold_relations: dict[tuple[str, str], str],
    *,
    run: int,
) -> list[dict]:
    inputs = {(str(item.left_id), str(item.right_id)): item for item in dataset.inputs}
    rows = []
    for prediction in predictions:
        if not prediction.sent_to_provider:
            continue
        pair_key = (prediction.left_id, prediction.right_id)
        pair = inputs[pair_key]
        rows.append(
            {
                "run": run,
                "left_id": prediction.left_id,
                "right_id": prediction.right_id,
                "gold_relation": gold_relations.get(pair_key, "unrelated"),
                "predicted_relation": prediction.predicted_relation,
                "confidence": prediction.confidence,
                "failure_code": prediction.failure_code,
                "justification": prediction.justification,
                "left_summary": pair.left["source_summary"],
                "right_summary": pair.right["source_summary"],
            }
        )
    return rows


def _write_case_report(rows: list[dict], output_directory: Path, stem: str) -> Path:
    path = output_directory / f"{stem}-provider-cases.csv"
    fieldnames = [
        "run",
        "left_id",
        "right_id",
        "gold_relation",
        "predicted_relation",
        "confidence",
        "failure_code",
        "justification",
        "left_summary",
        "right_summary",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


def _write_report(
    report: dict, output_directory: Path, provider_case_rows: list[dict]
) -> None:
    output_directory.mkdir(parents=True, exist_ok=True)
    stem = f"relation-{report['experiment']['split']}-{report['experiment']['identity']}"
    _write_case_report(provider_case_rows, output_directory, stem)
    (output_directory / f"{stem}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Experimento de relações v3",
        "",
        f"- Identidade: `{report['experiment']['identity']}`",
        f"- Split: `{report['experiment']['split']}`",
        f"- Decisão: `{report['decision']['status']}`",
        f"- Nível da evidência: `{report['decision']['evidence_level']}`",
        f"- Relações gold: {report['dataset']['gold_relations']}",
        "",
        "| Rodada | Recall candidatos | Redução | Macro-F1 | Chamadas provider "
        "| Falhas | IC95% Macro-F1 |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for run in report["runs"]:
        interval = run["macro_f1_ci95"]
        lines.append(
            f"| {run['run']} | {run['candidate_recall']} | {run['pair_reduction']} | "
            f"{run['macro_f1']} | {run['provider_attempts']} | "
            f"{run['operational_failure_rate']} | "
            f"[{interval['lower']}, {interval['upper']}] |"
        )
    lines.extend(["", "Validação técnica sintética; não confirma evento nem validade clínica."])
    (output_directory / f"{stem}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


async def _main() -> None:
    parser = argparse.ArgumentParser(description="Run relate-v2 calibration or evaluation")
    parser.add_argument("--split", choices=("calibration", "evaluation"), required=True)
    parser.add_argument("--cases-per-relation", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output", type=Path, default=Path("/data/reports"))
    args = parser.parse_args()
    report = await run_relation_experiment(
        settings=Settings(),
        split=args.split,
        cases_per_relation=args.cases_per_relation,
        seed=args.seed,
        repetitions=args.repetitions,
        provider_concurrency=args.concurrency,
        commit=args.commit,
        output_directory=args.output,
    )
    print(
        json.dumps({"identity": report["experiment"]["identity"], **report["decision"]}, indent=2)
    )


if __name__ == "__main__":
    asyncio.run(_main())
