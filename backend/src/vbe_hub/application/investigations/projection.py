from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class TechnicalSheetProjection:
    technical_sheet: dict[str, Any]
    provenance: dict[str, list[str]]
    conflicts: list[dict[str, Any]]


def compose_technical_sheet(
    head_signal_id: UUID,
    head_sheet: dict[str, Any] | None,
    evidence_sheets: list[tuple[UUID, dict[str, Any] | None]],
) -> TechnicalSheetProjection:
    merged = deepcopy(head_sheet or {})
    provenance: dict[str, list[str]] = {}
    conflicts: list[dict[str, Any]] = []
    _record_provenance(merged, str(head_signal_id), provenance)
    for signal_id, sheet in evidence_sheets:
        if sheet:
            _merge(merged, sheet, str(signal_id), provenance, conflicts)
    return TechnicalSheetProjection(merged, provenance, conflicts)


def _record_provenance(
    value: dict[str, Any], signal_id: str, target: dict[str, list[str]], prefix: str = ""
) -> None:
    for key, item in value.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(item, dict):
            _record_provenance(item, signal_id, target, path)
        else:
            target[path] = [signal_id]


def _merge(
    target: dict[str, Any],
    incoming: dict[str, Any],
    signal_id: str,
    provenance: dict[str, list[str]],
    conflicts: list[dict[str, Any]],
    prefix: str = "",
) -> None:
    for key, incoming_value in incoming.items():
        path = f"{prefix}.{key}" if prefix else key
        if incoming_value in (None, "", [], {}):
            continue
        if key not in target or target[key] in (None, "", [], {}):
            target[key] = deepcopy(incoming_value)
            if isinstance(incoming_value, dict):
                _record_provenance(incoming_value, signal_id, provenance, path)
            else:
                provenance[path] = [signal_id]
            continue
        current = target[key]
        if isinstance(current, dict) and isinstance(incoming_value, dict):
            _merge(current, incoming_value, signal_id, provenance, conflicts, path)
        elif isinstance(current, list) and isinstance(incoming_value, list):
            additions = [item for item in incoming_value if item not in current]
            if additions:
                current.extend(deepcopy(additions))
                provenance.setdefault(path, []).append(signal_id)
        elif current != incoming_value:
            conflicts.append(
                {
                    "field": path,
                    "kept_value": deepcopy(current),
                    "alternative_value": deepcopy(incoming_value),
                    "source_signal_id": signal_id,
                }
            )
