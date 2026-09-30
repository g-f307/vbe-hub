from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
from uuid import UUID

from google import genai
from google.genai import types

from vbe_hub.adapters.ai.gemini_embeddings import GoogleGenAIEmbeddingProvider
from vbe_hub.adapters.ai.gemini_relations import GeminiRelationJudge
from vbe_hub.adapters.ai.google_genai_client import GoogleGenAIClient
from vbe_hub.application.ai.embeddings import REPRESENTATION_VERSION
from vbe_hub.application.correlation.candidates import CandidatePolicy, GeographicLevel
from vbe_hub.application.correlation.relations import RELATION_PROMPT_VERSION
from vbe_hub.evaluation.correlation_pipeline import (
    CorrelationEvaluationRecord,
    evaluate_predictions,
    predict_correlations,
)
from vbe_hub.evaluation.correlation_protocol import CorrelationExperimentConfig
from vbe_hub.evaluation.correlation_report import build_correlation_report
from vbe_hub.infrastructure.settings import Settings

_ASSETS = Path(__file__).with_name("assets")
_INPUTS = _ASSETS / "correlation-evaluation-inputs.json"
_GOLD = _ASSETS / "correlation-evaluation-gold.json"
_TARGETS = {
    "candidate_recall": 0.90,
    "pair_reduction": 0.80,
    "macro_f1": 0.75,
    "operational_failure_rate": 0.05,
}


async def run_reserved_evaluation(
    *, settings: Settings, commit: str, output_directory: Path
) -> dict:
    if settings.gemini_api_key is None or not settings.gemini_api_key.get_secret_value().strip():
        raise SystemExit("GEMINI_API_KEY is required for the reserved correlation evaluation.")
    input_bytes = _INPUTS.read_bytes()
    document = json.loads(input_bytes)
    records = [
        CorrelationEvaluationRecord(UUID(item["record_id"]), item["technical_sheet"])
        for item in document["records"]
    ]
    policy = CandidatePolicy(14, GeographicLevel.MUNICIPALITY, 0.65, 0.65)
    root_client = genai.Client(
        api_key=settings.gemini_api_key.get_secret_value(),
        http_options=types.HttpOptions(
            api_version="v1", retry_options=types.HttpRetryOptions(attempts=1)
        ),
    )
    async with root_client.aio as async_client:
        predictions = await predict_correlations(
            records,
            embedding_provider=GoogleGenAIEmbeddingProvider(
                models=async_client.models,
                model=settings.gemini_embedding_model,
                timeout_seconds=settings.gemini_timeout_seconds,
                max_input_chars=settings.gemini_max_input_chars,
            ),
            judge=GeminiRelationJudge(
                client=GoogleGenAIClient(models=async_client.models, model=settings.gemini_model),
                model=settings.gemini_model,
                timeout_seconds=settings.gemini_timeout_seconds,
                max_input_chars=settings.gemini_max_input_chars,
            ),
            policy=policy,
            input_usd_per_million=settings.gemini_input_usd_per_million,
            output_usd_per_million=settings.gemini_output_usd_per_million,
        )

    gold_bytes = _GOLD.read_bytes()
    gold_document = json.loads(gold_bytes)
    gold_relations = {
        (item["left_id"], item["right_id"]): item["relation"]
        for item in gold_document["relations"]
    }
    metrics = evaluate_predictions(predictions, gold_relations=gold_relations)
    config = CorrelationExperimentConfig(
        dataset_version=document["dataset_version"],
        dataset_sha256=hashlib.sha256(input_bytes + gold_bytes).hexdigest(),
        split="evaluation",
        seed=document["seed"],
        commit=commit,
        normalizer_version="not-applicable-precomputed-sheets",
        extraction_model="reserved-technical-sheets-v1",
        embedding_model=settings.gemini_embedding_model,
        representation_version=REPRESENTATION_VERSION,
        relation_model=settings.gemini_model,
        relation_prompt_version=RELATION_PROMPT_VERSION,
        max_neighbors=len(records) - 1,
        temporal_window_days=policy.max_temporal_gap_days,
        geographic_level=policy.geographic_level.value,
        minimum_semantic_score=policy.minimum_semantic_score,
        minimum_total_score=policy.minimum_total_score,
    )
    report = build_correlation_report(config=config, metrics=metrics)
    selected = metrics.candidates.selected_pairs
    failure_rate = round(metrics.classification.failures / selected, 6) if selected else 0.0
    passed = {
        "candidate_recall": (metrics.candidates.recall or 0.0) >= _TARGETS["candidate_recall"],
        "pair_reduction": metrics.candidates.pair_reduction >= _TARGETS["pair_reduction"],
        "macro_f1": metrics.classification.macro_f1 >= _TARGETS["macro_f1"],
        "operational_failure_rate": failure_rate <= _TARGETS["operational_failure_rate"],
    }
    report["decision"] = {
        "status": "approve_with_caveats" if all(passed.values()) else "block",
        "targets": _TARGETS,
        "observed_operational_failure_rate": failure_rate,
        "passed": passed,
        "limitations": [
            "Reserved set contains 10 synthetic technical sheets and is not clinically "
            "representative.",
            "The run evaluates candidate selection and relation classification, not "
            "extraction quality.",
        ],
    }
    _write_report(report, output_directory)
    return report


def _write_report(report: dict, output_directory: Path) -> None:
    output_directory.mkdir(parents=True, exist_ok=True)
    stem = f"correlation-evaluation-{report['experiment']['identity']}"
    (output_directory / f"{stem}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    candidate, classification, decision = (
        report["candidates"], report["classification"], report["decision"]
    )
    lines = [
        "# Resultado reservado da correlação",
        "",
        f"- Execução: `{report['experiment']['identity']}`",
        f"- Commit: `{report['experiment']['commit']}`",
        f"- Decisão: `{decision['status']}`",
        f"- Recall de candidatos: {candidate['recall']}",
        f"- Redução de pares: {candidate['pair_reduction']}",
        f"- Macro-F1: {classification['macro_f1']}",
        f"- Falhas operacionais: {decision['observed_operational_failure_rate']}",
        "",
        "A decisão é técnica e não confirma evento epidemiológico nem validade clínica.",
    ]
    (output_directory / f"{stem}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


async def _main() -> None:
    parser = argparse.ArgumentParser(description="Run the reserved correlation evaluation")
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output", type=Path, default=Path("/data/reports"))
    args = parser.parse_args()
    report = await run_reserved_evaluation(
        settings=Settings(), commit=args.commit, output_directory=args.output
    )
    summary = {"identity": report["experiment"]["identity"], **report["decision"]}
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    asyncio.run(_main())
