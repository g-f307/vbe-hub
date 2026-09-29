from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from vbe_hub.evaluation.metrics import EvaluationCase, FieldKind, evaluate_cases


def build_report(
    *,
    experiment: Mapping[str, Any],
    cases: list[EvaluationCase],
    field_kinds: Mapping[str, FieldKind],
    execution: Mapping[str, Any],
) -> dict[str, Any]:
    metrics = evaluate_cases(cases, field_kinds=field_kinds)
    return {
        "report_version": "technical-sheet-evaluation-report-v1",
        "experiment": dict(experiment),
        "execution": dict(execution),
        "fields": {name: value.to_dict() for name, value in sorted(metrics.fields.items())},
        "errors": [
            {"record_id": item.record_id, "field": item.field, "kind": item.kind}
            for item in sorted(
                metrics.errors, key=lambda value: (value.record_id, value.field, value.kind)
            )
        ],
    }
