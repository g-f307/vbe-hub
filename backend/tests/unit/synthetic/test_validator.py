import json
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from vbe_hub.synthetic.validator import validate_dataset

FIXTURE = Path(__file__).parents[2] / "fixtures" / "synthetic" / "v1"


def _dataset_copy(tmp_path: Path) -> Path:
    target = tmp_path / "dataset"
    shutil.copytree(FIXTURE, target)
    return target


def _read_records(directory: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in (directory / "records.jsonl").read_text().splitlines()]


def _write_records(directory: Path, records: list[dict[str, Any]]) -> None:
    content = "".join(
        json.dumps(record, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
        for record in records
    )
    (directory / "records.jsonl").write_text(content)


def _mutate_record(directory: Path, mutation: Callable[[dict[str, Any]], None]) -> None:
    records = _read_records(directory)
    mutation(records[0])
    _write_records(directory, records)


def test_accepts_versioned_fixture_without_issues() -> None:
    report = validate_dataset(FIXTURE)

    assert report.valid is True
    assert report.issues == ()
    assert report.coverage["records"] == 12
    assert report.coverage["scenarios"] == 12


@pytest.mark.parametrize(
    "mutation,expected_rule",
    [
        (lambda record: record.pop("body"), "record.required"),
        (lambda record: record.__setitem__("source_kind", "social"), "record.source_kind"),
        (lambda record: record.__setitem__("published_at", "ontem"), "record.published_at"),
        (
            lambda record: record["payload"].__setitem__("gold_event_id", "event-secret"),
            "record.gold_leak",
        ),
        (
            lambda record: record.__setitem__("body", "Contato: pessoa@exemplo.com"),
            "privacy.personal_identifier",
        ),
    ],
)
def test_rejects_invalid_or_sensitive_pipeline_records(
    tmp_path: Path,
    mutation: Callable[[dict[str, Any]], None],
    expected_rule: str,
) -> None:
    dataset = _dataset_copy(tmp_path)
    _mutate_record(dataset, mutation)

    report = validate_dataset(dataset)

    assert report.valid is False
    assert expected_rule in {issue.rule for issue in report.issues}
    matching = next(issue for issue in report.issues if issue.rule == expected_rule)
    assert matching.file == "records.jsonl"
    assert matching.record_id is not None


def test_rejects_duplicate_record_identifier(tmp_path: Path) -> None:
    dataset = _dataset_copy(tmp_path)
    records = _read_records(dataset)
    records[1]["id"] = records[0]["id"]
    _write_records(dataset, records)

    report = validate_dataset(dataset)

    assert "record.id_unique" in {issue.rule for issue in report.issues}


def test_rejects_relation_to_unknown_record(tmp_path: Path) -> None:
    dataset = _dataset_copy(tmp_path)
    gold_path = dataset / "gold.json"
    gold = json.loads(gold_path.read_text())
    gold["relations"][0]["right_record_id"] = "00000000-0000-4000-8000-000000000000"
    gold_path.write_text(json.dumps(gold))

    report = validate_dataset(dataset)

    issue = next(issue for issue in report.issues if issue.rule == "relation.record_reference")
    assert issue.file == "gold.json"


def test_rejects_missing_gold_event_field(tmp_path: Path) -> None:
    dataset = _dataset_copy(tmp_path)
    gold_path = dataset / "gold.json"
    gold = json.loads(gold_path.read_text())
    gold["labels"][0].pop("gold_event_id")
    gold_path.write_text(json.dumps(gold))

    report = validate_dataset(dataset)

    assert "label.gold_event_id" in {issue.rule for issue in report.issues}


def test_rejects_manifest_count_and_hash_divergence(tmp_path: Path) -> None:
    dataset = _dataset_copy(tmp_path)
    manifest_path = dataset / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["counts"]["records"] = 999
    manifest["sha256"]["records.jsonl"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest))

    report = validate_dataset(dataset)

    rules = {issue.rule for issue in report.issues}
    assert "manifest.counts" in rules
    assert "manifest.sha256" in rules


def test_rejects_missing_required_scenario(tmp_path: Path) -> None:
    dataset = _dataset_copy(tmp_path)
    gold_path = dataset / "gold.json"
    gold = json.loads(gold_path.read_text())
    gold["labels"][0]["scenario_kind"] = gold["labels"][1]["scenario_kind"]
    gold_path.write_text(json.dumps(gold))

    report = validate_dataset(dataset)

    assert "coverage.scenarios" in {issue.rule for issue in report.issues}
