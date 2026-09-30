from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
from random import Random

from google import genai
from google.genai import types

from vbe_hub.adapters.ai.gemini_relations import GeminiRelationJudge
from vbe_hub.adapters.ai.google_genai_client import GoogleGenAIClient
from vbe_hub.application.correlation.candidates import CandidatePolicy, GeographicLevel
from vbe_hub.evaluation.correlation_pipeline import evaluate_predictions, predict_relation_pairs
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
        temporal_window_days=policy.max_temporal_gap_days,
        geographic_level=policy.geographic_level.value,
        minimum_semantic_score=policy.minimum_semantic_score,
        minimum_total_score=policy.minimum_total_score,
    )
    gold = {(str(item.left_id), str(item.right_id)): item.relation for item in dataset.gold}
    reports = []
    root_client = genai.Client(
        api_key=settings.gemini_api_key.get_secret_value(),
        http_options=types.HttpOptions(
            api_version="v1", retry_options=types.HttpRetryOptions(attempts=1)
        ),
    )
    async with root_client.aio as async_client:
        for _ in range(repetitions):
            judge = GeminiRelationJudge(
                client=GoogleGenAIClient(models=async_client.models, model=settings.gemini_model),
                model=settings.gemini_model,
                timeout_seconds=settings.gemini_timeout_seconds,
                max_input_chars=settings.gemini_max_input_chars,
            )
            predictions = await _predict_with_concurrency(
                dataset,
                judge=judge,
                policy=policy,
                concurrency=provider_concurrency,
                relation_prompt_version=PROMPT_VERSION,
                input_usd_per_million=settings.gemini_input_usd_per_million,
                output_usd_per_million=settings.gemini_output_usd_per_million,
            )
            metrics = evaluate_predictions(predictions, gold_relations=gold)
            reports.append(
                {
                    **build_correlation_report(config=config, metrics=metrics),
                    "macro_f1_ci95": _bootstrap_macro_f1(predictions, gold, seed),
                }
            )

    result = _experiment_result(config, dataset, reports)
    _write_report(result, output_directory)
    return result


async def _predict_with_concurrency(
    dataset,
    *,
    judge,
    policy,
    concurrency,
    relation_prompt_version,
    input_usd_per_million,
    output_usd_per_million,
):
    semaphore = asyncio.Semaphore(concurrency)

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

    return list(await asyncio.gather(*(predict_one(pair) for pair in dataset.inputs)))


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


def _experiment_result(config, dataset, reports: list[dict]) -> dict:
    run_summaries = []
    for index, report in enumerate(reports, start=1):
        selected = report["candidates"]["selected_pairs"]
        failures = report["classification"]["failures"]
        failure_rate = round(failures / selected, 6) if selected else 0.0
        run_summaries.append(
            {
                "run": index,
                "candidate_recall": report["candidates"]["recall"],
                "pair_reduction": report["candidates"]["pair_reduction"],
                "macro_f1": report["classification"]["macro_f1"],
                "operational_failure_rate": failure_rate,
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
        "report_version": "relation-experiment-report-v3",
        "experiment": {**config.model_dump(), "identity": config.identity},
        "dataset": {
            "input_pairs": len(dataset.inputs),
            "gold_relations": len(dataset.gold),
            "distribution": dataset.relation_counts,
            "decoys_per_target": 4,
        },
        "runs": run_summaries,
        "decision": {
            "status": "approve_with_caveats" if all(passed.values()) else "block",
            "targets": _TARGETS,
            "passed": passed,
            "scope": "technical synthetic validation; no clinical or epidemiological validity",
        },
    }


def _write_report(report: dict, output_directory: Path) -> None:
    output_directory.mkdir(parents=True, exist_ok=True)
    stem = f"relation-{report['experiment']['split']}-{report['experiment']['identity']}"
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
        f"- Relações gold: {report['dataset']['gold_relations']}",
        "",
        "| Rodada | Recall candidatos | Redução | Macro-F1 | Falhas | IC95% Macro-F1 |",
        "| ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for run in report["runs"]:
        interval = run["macro_f1_ci95"]
        lines.append(
            f"| {run['run']} | {run['candidate_recall']} | {run['pair_reduction']} | "
            f"{run['macro_f1']} | {run['operational_failure_rate']} | "
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
