import argparse
import json
from pathlib import Path

from vbe_hub.evaluation.correlation_metrics import (
    CorrelationCase,
    OperationalSample,
    evaluate_correlation,
)
from vbe_hub.evaluation.correlation_protocol import CorrelationExperimentConfig
from vbe_hub.evaluation.correlation_report import build_correlation_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the correlation funnel")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    document = json.loads(args.input.read_text(encoding="utf-8"))
    config = CorrelationExperimentConfig.model_validate(document["experiment"])
    cases = [CorrelationCase(**item) for item in document["cases"]]
    samples = [OperationalSample(**item) for item in document.get("operations", [])]
    metrics = evaluate_correlation(
        cases,
        theoretical_pairs=document["theoretical_pairs"],
        operational_samples=samples,
    )
    report = build_correlation_report(config=config, metrics=metrics)
    args.output.mkdir(parents=True, exist_ok=True)
    stem = f"correlation-{config.split}-{config.identity}"
    (args.output / f"{stem}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.output / f"{stem}.md").write_text(_markdown(report), encoding="utf-8")


def _markdown(report: dict) -> str:
    experiment, candidates = report["experiment"], report["candidates"]
    classification, operations = report["classification"], report["operations"]
    lines = [
        f"# Avaliação da correlação — {experiment['split']}",
        "",
        f"- Execução: `{experiment['identity']}`",
        f"- Commit: `{experiment['commit']}`",
        f"- Recall de candidatos: {candidates['recall']}",
        f"- Redução de pares: {candidates['pair_reduction']}",
        f"- Macro-F1: {classification['macro_f1']}",
        f"- Micro-F1: {classification['micro_f1']}",
        f"- Falhas: {classification['failures']}",
        f"- Chamadas/cache hits: {operations['provider_calls']} / {operations['cache_hits']}",
        f"- Latência p50/p95: {operations['latency_ms_p50']} / {operations['latency_ms_p95']} ms",
        f"- Custo estimado: {operations['estimated_cost_usd']}",
        "",
        "## Métricas por classe",
        "",
        "| Classe | Precisão | Revocação | F1 |",
        "| --- | ---: | ---: | ---: |",
    ]
    for relation, metrics in classification["by_class"].items():
        lines.append(
            f"| {relation} | {metrics['precision']} | {metrics['recall']} | {metrics['f1']} |"
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
