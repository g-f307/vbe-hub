"""Canonical files and integrity manifest for synthetic datasets."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from vbe_hub.synthetic.models import GeneratorConfig, SyntheticDataset


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
    ).encode()


def _atomic_write(path: Path, content: bytes) -> None:
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_bytes(content)
    temporary.replace(path)


def _config_dict(config: GeneratorConfig) -> dict[str, Any]:
    return {
        "allowed_locations": list(config.allowed_locations),
        "end_date": config.end_date.isoformat(),
        "event_count": config.event_count,
        "languages": list(config.languages),
        "media_ratio": config.media_ratio,
        "missing_field_rate": config.missing_field_rate,
        "noise_level": config.noise_level,
        "relation_distribution": {
            relation.value: weight
            for relation, weight in sorted(
                config.relation_distribution.items(), key=lambda item: item[0].value
            )
        },
        "scenario_kinds": [scenario.value for scenario in config.scenario_kinds],
        "seed": config.seed,
        "start_date": config.start_date.isoformat(),
        "total_records": config.total_records,
    }


def write_dataset(
    dataset: SyntheticDataset, config: GeneratorConfig, output_directory: Path
) -> None:
    """Write records, gold data and a deterministic manifest to separate files."""

    output_directory.mkdir(parents=True, exist_ok=True)
    records_content = b"".join(_json_bytes(record.to_dict()) for record in dataset.records)
    gold_content = _json_bytes(
        {
            "labels": [
                {
                    "gold_event_id": label.gold_event_id,
                    "record_id": label.record_id,
                    "scenario_id": label.scenario_id,
                    "scenario_kind": label.scenario_kind.value,
                }
                for label in dataset.labels
            ],
            "relations": [
                {
                    "left_record_id": relation.left_record_id,
                    "relation": relation.relation.value,
                    "right_record_id": relation.right_record_id,
                }
                for relation in dataset.relations
            ],
        }
    )
    source_counts = Counter(record.source_kind for record in dataset.records)
    scenario_counts = Counter(label.scenario_kind.value for label in dataset.labels)
    relation_counts = Counter(relation.relation.value for relation in dataset.relations)
    manifest_content = _json_bytes(
        {
            "config": _config_dict(config),
            "counts": {
                "community": source_counts["community"],
                "labels": len(dataset.labels),
                "media": source_counts["media"],
                "records": len(dataset.records),
                "relations": len(dataset.relations),
            },
            "generator": "vbe-hub",
            "generator_version": config.generator_version,
            "relation_counts": dict(sorted(relation_counts.items())),
            "scenario_counts": dict(sorted(scenario_counts.items())),
            "seed": config.seed,
            "sha256": {
                "gold.json": hashlib.sha256(gold_content).hexdigest(),
                "records.jsonl": hashlib.sha256(records_content).hexdigest(),
            },
        }
    )
    _atomic_write(output_directory / "records.jsonl", records_content)
    _atomic_write(output_directory / "gold.json", gold_content)
    _atomic_write(output_directory / "manifest.json", manifest_content)
