from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def derive_field_decisions(
    *,
    fields: Mapping[str, Mapping[str, Any]],
    critical_fields: list[str],
    targets: Mapping[str, float],
) -> dict[str, str]:
    decisions: dict[str, str] = {}
    critical = set(critical_fields)
    for name, metrics in fields.items():
        if name == "symptoms":
            f1 = metrics.get("f1")
            decisions[name] = (
                "direct"
                if f1 is not None and f1 >= targets["symptoms_f1_min"]
                else "reduced_weight"
            )
            continue
        if name not in critical:
            decisions[name] = "evidence_only"
            continue
        hallucination = metrics.get("hallucination_rate") or 0.0
        omission = metrics.get("omission_rate") or 0.0
        hallucination_max = targets["critical_field_hallucination_rate_max"]
        omission_max = targets["critical_field_omission_rate_max"]
        if hallucination <= hallucination_max and omission <= omission_max:
            decisions[name] = "direct"
        elif hallucination > hallucination_max * 2 or omission > omission_max * 2:
            decisions[name] = "evidence_only"
        else:
            decisions[name] = "reduced_weight"
    return decisions
