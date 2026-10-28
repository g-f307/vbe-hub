"""Compose the auditable evidence of the integrated synthetic PoC experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.request import urlopen

from vbe_hub.evaluation.grouping_experiment import run_grouping_experiment

_CRITICAL_KINDS = ("technical_sheet", "relation")


def build_integrated_report(
    *,
    manifest: dict[str, Any],
    validation: dict[str, Any],
    operational: dict[str, Any],
    grouping: dict[str, Any],
    commit: str,
) -> dict[str, Any]:
    """Combine current reproducibility checks and frozen quality evidence.

    The result intentionally does not imply that every item came from one live provider run.
    """

    if validation.get("status") != "valid" or validation.get("issue_count") != 0:
        raise ValueError("synthetic validation must be valid and have no issues")
    if operational.get("dataset", {}).get("kind") != "synthetic":
        raise ValueError("operational evidence must describe a synthetic dataset")
    if operational.get("classification") != "technical_operational":
        raise ValueError("operational evidence has an unexpected classification")

    evaluations = {
        item["kind"]: item
        for item in operational.get("evaluations", [])
        if item.get("kind") in _CRITICAL_KINDS
    }
    missing = sorted(set(_CRITICAL_KINDS).difference(evaluations))
    if missing:
        raise ValueError(f"required frozen evaluations are missing: {', '.join(missing)}")

    passed = {
        "dataset_integrity": True,
        "operational_reproduction": operational.get("operational_status") == "ok",
        "technical_sheet": evaluations["technical_sheet"].get("status")
        == "approve_with_caveats",
        "relation": evaluations["relation"].get("status") == "approve_with_caveats",
        "grouping": grouping.get("decision", {}).get("status") == "approve_with_caveats",
    }
    config = {
        "commit": commit,
        "manifest_sha256": _hash(manifest),
        "validation_sha256": _hash(validation),
        "grouping_identity": grouping.get("experiment", {}).get("identity"),
        "dataset_seed": manifest.get("seed"),
        "dataset_generator_version": manifest.get("generator_version"),
    }
    identity = _hash(config)[:16]
    evidence = {
        "dataset": {
            "provenance": "current_reproduction",
            "generator": manifest.get("generator"),
            "generator_version": manifest.get("generator_version"),
            "seed": manifest.get("seed"),
            "config": manifest.get("config", {}),
            "counts": manifest.get("counts", {}),
            "sha256": manifest.get("sha256", {}),
            "validation_status": validation["status"],
            "validation_issue_count": validation["issue_count"],
        },
        "operation": {
            "provenance": "current_reproduction",
            "status": operational.get("operational_status"),
            "dataset": operational.get("dataset"),
            "pipeline": operational.get("pipeline", {}),
            "reconciliation": operational.get("reconciliation", []),
        },
        "technical_sheet": _frozen_evidence(evaluations["technical_sheet"]),
        "relation": _frozen_evidence(evaluations["relation"]),
        "grouping": {
            "provenance": "current_reproduction",
            "identity": grouping.get("experiment", {}).get("identity"),
            "dataset": grouping.get("dataset", {}),
            "automatic": grouping.get("automatic", {}),
            "reviewed": grouping.get("reviewed", {}),
            "operations": grouping.get("operations", {}),
            "decision": grouping.get("decision", {}),
        },
    }
    return {
        "report_version": "integrated-experiment-report-v1",
        "classification": "technical_synthetic_validation",
        "experiment": {
            **config,
            "identity": identity,
            "provider_calls_this_run": 0,
            "provider_evidence_reused": True,
        },
        "evidence": evidence,
        "decision": {
            "status": "approve_with_caveats" if all(passed.values()) else "block",
            "passed": passed,
            "interpretation": (
                "technical evidence for the synthetic proof of concept; the final public-health "
                "decision always belongs to a surveillance professional"
            ),
        },
        "limitations": {
            "single_end_to_end_live_run": False,
            "clinical_validity": False,
            "epidemiological_validity": False,
            "real_eios_or_guardioes_data": False,
            "note": (
                "Compositional evidence: current deterministic reproduction plus frozen official "
                "provider runs; stages must not be interpreted as one live end-to-end execution."
            ),
        },
    }


def write_integrated_report(report: dict[str, Any], output: Path) -> tuple[Path, Path]:
    output.mkdir(parents=True, exist_ok=True)
    stem = f"integrated-{report['experiment']['identity']}"
    json_path = output / f"{stem}.json"
    markdown_path = output / f"{stem}.md"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(_markdown(report), encoding="utf-8")
    return json_path, markdown_path


def _frozen_evidence(evaluation: dict[str, Any]) -> dict[str, Any]:
    return {
        "provenance": "frozen_official_run",
        "identity": evaluation.get("identity"),
        "dataset_version": evaluation.get("dataset_version"),
        "evaluated_on": evaluation.get("evaluated_on"),
        "status": evaluation.get("status"),
        "evidence_level": evaluation.get("evidence_level"),
        "artifact": evaluation.get("artifact"),
        "metrics": evaluation.get("metrics", {}),
        "limitation": evaluation.get("limitation"),
        "scope": evaluation.get("scope"),
    }


def _hash(value: Any) -> str:
    content = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()


def _markdown(report: dict[str, Any]) -> str:
    blocked = report["decision"]["status"] == "block"
    result = "bloqueado" if blocked else "aprovado com ressalvas"
    passed = report["decision"]["passed"]
    stage_labels = {
        "dataset_integrity": "Integridade dos dados sintéticos",
        "operational_reproduction": "Reprodução operacional",
        "technical_sheet": "Extração da ficha técnica",
        "relation": "Correlação entre relatos",
        "grouping": "Agrupamento e revisão humana",
    }
    rows = [
        f"| {stage_labels[key]} | {'Atendeu' if value else 'Não atendeu'} |"
        for key, value in passed.items()
    ]
    return "\n".join(
        [
            "# Experimento integrado da PoC",
            "",
            f"- Identidade: `{report['experiment']['identity']}`",
            f"- Commit: `{report['experiment']['commit']}`",
            f"- Resultado geral: {result}",
            "- Chamadas ao provedor nesta repetição: 0",
            "",
            "## O que foi verificado",
            "",
            "| Etapa | Resultado |",
            "| --- | --- |",
            *rows,
            "",
            "## Como interpretar",
            "",
            "O sistema conseguiu repetir a geração e a verificação dos dados, expor o estado "
            "operacional e reorganizar os relatos sintéticos em sinais com revisão humana. O "
            "resultado geral permanece bloqueado se qualquer etapa crítica não atingir sua meta.",
            "",
            "Para economizar a cota gratuita, esta repetição não chamou o Gemini: ela reutilizou "
            "as rodadas oficiais congeladas de extração e correlação, identificadas no JSON.",
            "",
            "Esta não foi uma única execução ponta a ponta com provedor ao vivo. É uma composição "
            "auditável de uma reprodução determinística atual e evidências oficiais anteriores. "
            "Não demonstra validade clínica ou epidemiológica e não substitui a decisão do "
            "profissional de vigilância.",
            "",
        ]
    )


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object in {path}")
    return value


def _fetch_json(url: str) -> dict[str, Any]:
    with urlopen(url, timeout=10) as response:  # noqa: S310 - fixed internal URL in Compose
        value = json.load(response)
    if not isinstance(value, dict):
        raise ValueError("operational endpoint did not return a JSON object")
    return value


def _main() -> None:
    parser = argparse.ArgumentParser(description="Run the integrated synthetic PoC experiment")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--validation", type=Path, required=True)
    parser.add_argument("--metrics-url", default="http://api:8000/metrics/summary")
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output", type=Path, default=Path("/data/reports"))
    args = parser.parse_args()
    grouping = run_grouping_experiment(
        split="evaluation",
        event_count=60,
        seed=5170,
        commit=args.commit,
        bootstrap_iterations=500,
    )
    report = build_integrated_report(
        manifest=_read_json(args.manifest),
        validation=_read_json(args.validation),
        operational=_fetch_json(args.metrics_url),
        grouping=grouping,
        commit=args.commit,
    )
    json_path, markdown_path = write_integrated_report(report, args.output)
    print(
        json.dumps(
            {
                "identity": report["experiment"]["identity"],
                "status": report["decision"]["status"],
                "passed": report["decision"]["passed"],
                "json": str(json_path),
                "summary": str(markdown_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    _main()
