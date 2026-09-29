"""Fail-closed validation for generated dataset artifacts."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

from vbe_hub.synthetic.artifacts import write_dataset
from vbe_hub.synthetic.generator import generate_dataset
from vbe_hub.synthetic.models import GeneratorConfig, RelationKind, ScenarioKind

_REQUIRED_RECORD_FIELDS = {
    "id",
    "source_kind",
    "source_name",
    "external_id",
    "published_at",
    "title",
    "body",
    "source_url",
    "language",
    "payload",
    "provenance",
}
_GOLD_KEYS = {"gold_event_id", "scenario_id", "scenario_kind"}
_FORBIDDEN_PERSONAL_KEYS = {
    "address",
    "cpf",
    "email",
    "exact_age",
    "name",
    "phone",
}
_PERSONAL_PATTERNS = (
    re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"),
    re.compile(r"(?:\+?55\s*)?(?:\(?\d{2}\)?\s*)?9?\d{4}[- ]?\d{4}"),
)
_MAX_ARTIFACT_BYTES = 100 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    rule: str
    file: str
    message: str
    record_id: str | None = None


@dataclass(frozen=True, slots=True)
class ValidationReport:
    issues: tuple[ValidationIssue, ...]
    coverage: dict[str, int]

    @property
    def valid(self) -> bool:
        return not self.issues


def validation_exit_code(report: ValidationReport) -> int:
    """Return the process status associated with a validation report."""

    return 0 if report.valid else 1


def write_validation_report(report: ValidationReport, output_path: Path) -> None:
    """Write a deterministic report without copying untrusted record content."""

    document = {
        "coverage": report.coverage,
        "issue_count": len(report.issues),
        "issues": [
            {
                "file": issue.file,
                "message": issue.message,
                "record_id": issue.record_id,
                "rule": issue.rule,
            }
            for issue in report.issues
        ],
        "status": "valid" if report.valid else "invalid",
    }
    content = (
        json.dumps(document, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(f"{output_path.suffix}.tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(output_path)


def _issue(
    issues: list[ValidationIssue],
    rule: str,
    file: str,
    message: str,
    record_id: str | None = None,
) -> None:
    issues.append(ValidationIssue(rule, file, message, record_id))


def _read_bytes(path: Path, issues: list[ValidationIssue]) -> bytes | None:
    try:
        size = path.stat().st_size
        if size > _MAX_ARTIFACT_BYTES:
            _issue(issues, "file.size", path.name, "artifact exceeds the 100 MiB limit")
            return None
        return path.read_bytes()
    except OSError:
        _issue(issues, "file.required", path.name, "required artifact is unavailable")
        return None


def _read_json(path: Path, issues: list[ValidationIssue]) -> tuple[Any, bytes | None]:
    content = _read_bytes(path, issues)
    if content is None:
        return None, None
    try:
        return json.loads(content), content
    except (UnicodeDecodeError, json.JSONDecodeError):
        _issue(issues, "file.json", path.name, "artifact is not valid UTF-8 JSON")
        return None, content


def _valid_uuid(value: Any) -> bool:
    try:
        UUID(value) if isinstance(value, str) else None
        return isinstance(value, str)
    except (ValueError, TypeError, AttributeError):
        return False


def _contains_forbidden_key(value: Any) -> bool:
    if isinstance(value, dict):
        if _FORBIDDEN_PERSONAL_KEYS.intersection(key.lower() for key in value):
            return True
        return any(_contains_forbidden_key(child) for child in value.values())
    if isinstance(value, list):
        return any(_contains_forbidden_key(child) for child in value)
    return False


def _validate_record(record: Any, issues: list[ValidationIssue], index: int) -> str | None:
    if not isinstance(record, dict):
        _issue(issues, "record.object", "records.jsonl", f"line {index} is not an object")
        return None
    record_id = record.get("id") if isinstance(record.get("id"), str) else f"line-{index}"
    missing = sorted(_REQUIRED_RECORD_FIELDS.difference(record))
    if missing:
        _issue(
            issues,
            "record.required",
            "records.jsonl",
            f"required fields are missing: {', '.join(missing)}",
            record_id,
        )
    if not _valid_uuid(record.get("id")):
        _issue(issues, "record.id", "records.jsonl", "id must be a UUID", record_id)
    if record.get("source_kind") not in {"media", "community"}:
        _issue(
            issues,
            "record.source_kind",
            "records.jsonl",
            "source_kind is outside the allowed enum",
            record_id,
        )
    try:
        published_at = datetime.fromisoformat(record.get("published_at", ""))
        if published_at.tzinfo is None or published_at.utcoffset() is None:
            raise ValueError
    except (TypeError, ValueError):
        _issue(
            issues,
            "record.published_at",
            "records.jsonl",
            "published_at must be an ISO 8601 timestamp with timezone",
            record_id,
        )
    parsed_url = urlparse(record.get("source_url", ""))
    if parsed_url.scheme != "https" or not (parsed_url.hostname or "").endswith(".invalid"):
        _issue(
            issues,
            "record.source_url",
            "records.jsonl",
            "source_url must use HTTPS on the reserved .invalid domain",
            record_id,
        )
    payload = record.get("payload")
    provenance = record.get("provenance")
    if not isinstance(payload, dict) or not isinstance(provenance, dict):
        _issue(
            issues,
            "record.object_fields",
            "records.jsonl",
            "payload and provenance must be objects",
            record_id,
        )
    elif _GOLD_KEYS.intersection(payload) or _GOLD_KEYS.intersection(provenance):
        _issue(
            issues,
            "record.gold_leak",
            "records.jsonl",
            "evaluation-only field is present in a pipeline record",
            record_id,
        )
    if record.get("source_kind") == "media" and not isinstance(record.get("title"), str):
        _issue(
            issues,
            "record.media_fields",
            "records.jsonl",
            "media records require a title",
            record_id,
        )
    community_fields = {"estimated_cases", "geographic_precision", "municipality", "symptoms"}
    if record.get("source_kind") == "community" and (
        not isinstance(payload, dict)
        or not community_fields.issubset(payload)
        or not isinstance(payload.get("symptoms"), list)
    ):
        _issue(
            issues,
            "record.community_fields",
            "records.jsonl",
            "community payload lacks required aggregate fields",
            record_id,
        )
    if _contains_forbidden_key(record):
        _issue(
            issues,
            "privacy.personal_identifier",
            "records.jsonl",
            "a prohibited personal-identifier field is present",
            record_id,
        )
    text = f"{record.get('title', '')} {record.get('body', '')}"
    if any(pattern.search(text) for pattern in _PERSONAL_PATTERNS):
        _issue(
            issues,
            "privacy.personal_identifier",
            "records.jsonl",
            "content matches a prohibited personal-identifier pattern",
            record_id,
        )
    return record.get("id") if _valid_uuid(record.get("id")) else None


def _read_records(path: Path, issues: list[ValidationIssue]) -> tuple[list[Any], bytes | None]:
    content = _read_bytes(path, issues)
    if content is None:
        return [], None
    records: list[Any] = []
    for index, line in enumerate(content.splitlines(), start=1):
        try:
            records.append(json.loads(line))
        except (UnicodeDecodeError, json.JSONDecodeError):
            _issue(issues, "file.jsonl", path.name, f"line {index} is not valid JSON")
    return records, content


def _validate_gold(
    gold: Any, record_ids: set[str], issues: list[ValidationIssue]
) -> tuple[Counter[str], set[str]]:
    scenarios: Counter[str] = Counter()
    if not isinstance(gold, dict) or not isinstance(gold.get("labels"), list):
        _issue(issues, "gold.structure", "gold.json", "labels must be an array")
        return scenarios, set()
    labels = gold["labels"]
    labeled_records: set[str] = set()
    gold_identifiers: set[str] = set()
    for index, label in enumerate(labels):
        if not isinstance(label, dict):
            _issue(issues, "label.object", "gold.json", f"label {index} is not an object")
            continue
        record_id = label.get("record_id")
        if record_id not in record_ids:
            _issue(
                issues,
                "label.record_reference",
                "gold.json",
                "label references an unknown record",
                record_id if isinstance(record_id, str) else None,
            )
        if record_id in labeled_records:
            _issue(
                issues,
                "label.record_unique",
                "gold.json",
                "record has multiple labels",
                record_id,
            )
        if isinstance(record_id, str):
            labeled_records.add(record_id)
        if "gold_event_id" not in label:
            _issue(
                issues,
                "label.gold_event_id",
                "gold.json",
                "gold_event_id field is required",
                record_id,
            )
        elif label["gold_event_id"] is not None and not isinstance(label["gold_event_id"], str):
            _issue(
                issues,
                "label.gold_event_id",
                "gold.json",
                "gold_event_id must be text or null",
                record_id,
            )
        elif isinstance(label["gold_event_id"], str):
            gold_identifiers.add(label["gold_event_id"])
        scenario = label.get("scenario_kind")
        if scenario not in {item.value for item in ScenarioKind}:
            _issue(issues, "label.scenario_kind", "gold.json", "unknown scenario kind", record_id)
        else:
            scenarios[scenario] += 1
        if (
            scenario == ScenarioKind.IRRELEVANT.value
            and label.get("gold_event_id") is not None
        ) or (
            scenario in {item.value for item in ScenarioKind if item is not ScenarioKind.IRRELEVANT}
            and label.get("gold_event_id") is None
        ):
            _issue(
                issues,
                "label.event_composition",
                "gold.json",
                "scenario and gold event association are inconsistent",
                record_id,
            )
        if isinstance(label.get("scenario_id"), str):
            gold_identifiers.add(label["scenario_id"])
        else:
            _issue(issues, "label.scenario_id", "gold.json", "scenario_id is required", record_id)
    if labeled_records != record_ids:
        _issue(issues, "label.coverage", "gold.json", "each record must have exactly one label")

    relations = gold.get("relations")
    if not isinstance(relations, list):
        _issue(issues, "relation.structure", "gold.json", "relations must be an array")
        return scenarios, gold_identifiers
    for relation in relations:
        if not isinstance(relation, dict):
            _issue(issues, "relation.object", "gold.json", "relation must be an object")
            continue
        if relation.get("relation") not in {item.value for item in RelationKind}:
            _issue(issues, "relation.kind", "gold.json", "unknown relation kind")
        for side in ("left_record_id", "right_record_id"):
            if relation.get(side) not in record_ids:
                _issue(
                    issues,
                    "relation.record_reference",
                    "gold.json",
                    f"{side} references an unknown record",
                    relation.get(side) if isinstance(relation.get(side), str) else None,
                )
    return scenarios, gold_identifiers


def _validate_manifest(
    manifest: Any,
    records: list[Any],
    gold: Any,
    records_content: bytes | None,
    gold_content: bytes | None,
    issues: list[ValidationIssue],
) -> None:
    if not isinstance(manifest, dict):
        _issue(issues, "manifest.structure", "manifest.json", "manifest must be an object")
        return
    source_counts = Counter(
        record.get("source_kind") for record in records if isinstance(record, dict)
    )
    labels = gold.get("labels", []) if isinstance(gold, dict) else []
    relations = gold.get("relations", []) if isinstance(gold, dict) else []
    expected_counts = {
        "community": source_counts["community"],
        "labels": len(labels),
        "media": source_counts["media"],
        "records": len(records),
        "relations": len(relations),
    }
    if manifest.get("counts") != expected_counts:
        _issue(issues, "manifest.counts", "manifest.json", "manifest counts do not reconcile")
    expected_hashes = {}
    if records_content is not None:
        expected_hashes["records.jsonl"] = hashlib.sha256(records_content).hexdigest()
    if gold_content is not None:
        expected_hashes["gold.json"] = hashlib.sha256(gold_content).hexdigest()
    if manifest.get("sha256") != expected_hashes:
        _issue(issues, "manifest.sha256", "manifest.json", "manifest hashes do not reconcile")
    scenario_counts = Counter(
        label.get("scenario_kind") for label in labels if isinstance(label, dict)
    )
    relation_counts = Counter(
        relation.get("relation") for relation in relations if isinstance(relation, dict)
    )
    if manifest.get("scenario_counts") != dict(sorted(scenario_counts.items())) or manifest.get(
        "relation_counts"
    ) != dict(sorted(relation_counts.items())):
        _issue(
            issues,
            "manifest.distributions",
            "manifest.json",
            "manifest distributions do not reconcile",
        )
    config = manifest.get("config")
    if isinstance(config, dict) and isinstance(config.get("media_ratio"), int | float):
        expected_media = round(len(records) * config["media_ratio"])
        if source_counts["media"] != expected_media:
            _issue(
                issues,
                "coverage.source_ratio",
                "manifest.json",
                "source counts do not match the configured media ratio",
            )


def _config_from_manifest(manifest: Any) -> GeneratorConfig | None:
    if not isinstance(manifest, dict) or not isinstance(manifest.get("config"), dict):
        return None
    config = manifest["config"]
    try:
        return GeneratorConfig(
            seed=config["seed"],
            total_records=config["total_records"],
            media_ratio=config["media_ratio"],
            event_count=config["event_count"],
            relation_distribution={
                RelationKind(relation): weight
                for relation, weight in config["relation_distribution"].items()
            },
            languages=tuple(config["languages"]),
            noise_level=config["noise_level"],
            missing_field_rate=config["missing_field_rate"],
            start_date=date.fromisoformat(config["start_date"]),
            end_date=date.fromisoformat(config["end_date"]),
            allowed_locations=tuple(config["allowed_locations"]),
            generator_version=manifest["generator_version"],
            scenario_kinds=tuple(ScenarioKind(item) for item in config["scenario_kinds"]),
        )
    except (KeyError, TypeError, ValueError):
        return None


def _validate_reproducibility(
    manifest: Any,
    records_content: bytes | None,
    gold_content: bytes | None,
    issues: list[ValidationIssue],
) -> None:
    config = _config_from_manifest(manifest)
    if config is None:
        _issue(
            issues,
            "manifest.config",
            "manifest.json",
            "generator configuration is incomplete or invalid",
        )
        return
    with TemporaryDirectory() as temporary:
        output = Path(temporary)
        write_dataset(generate_dataset(config), config, output)
        expected_records = (output / "records.jsonl").read_bytes()
        expected_gold = (output / "gold.json").read_bytes()
    if records_content != expected_records or gold_content != expected_gold:
        _issue(
            issues,
            "reproducibility.content",
            "manifest.json",
            "artifacts differ from a generation with the declared configuration",
        )


def _validate_gold_leaks(
    records: list[Any], gold_identifiers: set[str], issues: list[ValidationIssue]
) -> None:
    for record in records:
        if not isinstance(record, dict):
            continue
        serialized = json.dumps(record, ensure_ascii=False, sort_keys=True)
        if any(identifier in serialized for identifier in gold_identifiers):
            _issue(
                issues,
                "record.gold_identifier_leak",
                "records.jsonl",
                "pipeline content contains an evaluation identifier",
                record.get("id") if isinstance(record.get("id"), str) else None,
            )


def validate_dataset(directory: Path) -> ValidationReport:
    """Validate one artifact directory and return all safely reportable violations."""

    issues: list[ValidationIssue] = []
    records, records_content = _read_records(directory / "records.jsonl", issues)
    gold, gold_content = _read_json(directory / "gold.json", issues)
    manifest, _ = _read_json(directory / "manifest.json", issues)

    record_ids: list[str] = []
    for index, record in enumerate(records, start=1):
        record_id = _validate_record(record, issues, index)
        if record_id is not None:
            if record_id in record_ids:
                _issue(
                    issues,
                    "record.id_unique",
                    "records.jsonl",
                    "record id is duplicated",
                    record_id,
                )
            record_ids.append(record_id)
    scenarios, gold_identifiers = _validate_gold(gold, set(record_ids), issues)
    required_scenarios = {scenario.value for scenario in ScenarioKind}
    if set(scenarios) != required_scenarios:
        _issue(
            issues,
            "coverage.scenarios",
            "gold.json",
            "required scenario coverage is incomplete",
        )
    _validate_manifest(manifest, records, gold, records_content, gold_content, issues)
    _validate_gold_leaks(records, gold_identifiers, issues)
    _validate_reproducibility(manifest, records_content, gold_content, issues)
    return ValidationReport(
        issues=tuple(issues),
        coverage={
            "records": len(records),
            "scenarios": len(scenarios),
            "relations": len(gold.get("relations", [])) if isinstance(gold, dict) else 0,
        },
    )
