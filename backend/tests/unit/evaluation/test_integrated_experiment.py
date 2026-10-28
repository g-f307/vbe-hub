import json
from pathlib import Path

import pytest

from vbe_hub.evaluation.integrated_experiment import (
    build_integrated_report,
    write_integrated_report,
)


def _manifest() -> dict:
    return {
        "generator": "vbe-hub",
        "generator_version": "1.0.0",
        "seed": 307,
        "config": {"total_records": 120, "event_count": 12},
        "counts": {"records": 120, "labels": 120, "relations": 108},
        "sha256": {"records.jsonl": "a" * 64, "gold.json": "b" * 64},
    }


def _validation() -> dict:
    return {"status": "valid", "issue_count": 0, "issues": [], "coverage": {}}


def _operational() -> dict:
    return {
        "contract_version": "metrics-summary-v1",
        "classification": "technical_operational",
        "operational_status": "ok",
        "dataset": {
            "kind": "synthetic",
            "status": "single",
            "sources": [
                {"generator": "vbe-hub", "version": "1.0.0", "seed": 307, "records": 120}
            ],
        },
        "pipeline": {
            "raw_records": {"value": 120, "status": "available", "origin": "raw_records"},
            "normalized_records": {
                "value": 6,
                "status": "available",
                "origin": "normalized_records",
            },
        },
        "reconciliation": [],
        "evaluations": [
            {
                "identity": "extract-1",
                "classification": "synthetic_evaluation",
                "kind": "technical_sheet",
                "dataset_version": "technical-sheet-eval-v1",
                "evaluated_on": "2026-09-29",
                "status": "block",
                "evidence_level": "exploratory",
                "artifact": "docs/technical-sheet-baseline-2026-09-29.md",
                "metrics": {"operational_failure_rate": 0.25},
                "limitation": "small synthetic sample",
                "scope": "technical synthetic extraction validation",
            },
            {
                "identity": "relation-1",
                "classification": "synthetic_evaluation",
                "kind": "relation",
                "dataset_version": "relation-evaluation-v3",
                "evaluated_on": "2026-09-30",
                "status": "approve_with_caveats",
                "evidence_level": "exploratory",
                "artifact": "docs/correlation-evaluation.md",
                "metrics": {"macro_f1": 1.0, "provider_calls": 44},
                "limitation": "small synthetic sample",
                "scope": "technical synthetic relation validation",
            },
        ],
    }


def _grouping() -> dict:
    return {
        "report_version": "grouping-experiment-report-v1",
        "experiment": {
            "identity": "group-1",
            "dataset_version": "grouping-evaluation-v2",
            "commit": "abc1234",
            "seed": 5170,
            "input_sha256": "c" * 64,
            "gold_sha256": "d" * 64,
        },
        "dataset": {"events": 60, "records": 270},
        "automatic": {"pairwise": {"f1": 0.98}, "merges": {"count": 1}},
        "reviewed": {"pairwise": {"f1": 1.0}, "merges": {"count": 0}},
        "operations": {"provider_calls": 0, "estimated_cost_usd": 0.0},
        "decision": {
            "status": "approve_with_caveats",
            "evidence_level": "expanded_synthetic",
            "limitation": "synthetic frozen relation inputs",
            "scope": "technical synthetic grouping validation",
        },
    }


def test_integrated_report_blocks_when_a_critical_stage_is_blocked() -> None:
    report = build_integrated_report(
        manifest=_manifest(),
        validation=_validation(),
        operational=_operational(),
        grouping=_grouping(),
        commit="abc1234",
    )

    assert report["report_version"] == "integrated-experiment-report-v1"
    assert report["decision"]["status"] == "block"
    assert report["decision"]["passed"] == {
        "dataset_integrity": True,
        "operational_reproduction": True,
        "technical_sheet": False,
        "relation": True,
        "grouping": True,
    }
    assert report["evidence"]["technical_sheet"]["provenance"] == "frozen_official_run"
    assert report["evidence"]["grouping"]["provenance"] == "current_reproduction"
    assert report["limitations"]["single_end_to_end_live_run"] is False
    assert report["experiment"]["provider_calls_this_run"] == 0


def test_integrated_report_rejects_invalid_or_non_synthetic_inputs() -> None:
    invalid = _validation()
    invalid["status"] = "invalid"
    with pytest.raises(ValueError, match="synthetic validation"):
        build_integrated_report(
            manifest=_manifest(),
            validation=invalid,
            operational=_operational(),
            grouping=_grouping(),
            commit="abc1234",
        )

    operational = _operational()
    operational["dataset"]["kind"] = "real"
    with pytest.raises(ValueError, match="synthetic dataset"):
        build_integrated_report(
            manifest=_manifest(),
            validation=_validation(),
            operational=operational,
            grouping=_grouping(),
            commit="abc1234",
        )


def test_integrated_report_writes_sanitized_json_and_plain_language_summary(
    tmp_path: Path,
) -> None:
    report = build_integrated_report(
        manifest=_manifest(),
        validation=_validation(),
        operational=_operational(),
        grouping=_grouping(),
        commit="abc1234",
    )

    json_path, markdown_path = write_integrated_report(report, tmp_path)

    persisted = json.loads(json_path.read_text(encoding="utf-8"))
    summary = markdown_path.read_text(encoding="utf-8")
    assert persisted["experiment"]["identity"] == report["experiment"]["identity"]
    assert "Resultado geral: bloqueado" in summary
    assert "não foi uma única execução ponta a ponta" in summary
    assert "chave" not in json_path.read_text(encoding="utf-8").lower()
