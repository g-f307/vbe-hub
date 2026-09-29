import json
from pathlib import Path

from vbe_hub.synthetic.validator import (
    ValidationIssue,
    ValidationReport,
    validation_exit_code,
    write_validation_report,
)


def test_writes_machine_readable_success_report(tmp_path: Path) -> None:
    report = ValidationReport(issues=(), coverage={"records": 12, "scenarios": 12})
    output = tmp_path / "report.json"

    write_validation_report(report, output)

    document = json.loads(output.read_text())
    assert document == {
        "coverage": {"records": 12, "scenarios": 12},
        "issue_count": 0,
        "issues": [],
        "status": "valid",
    }
    assert validation_exit_code(report) == 0


def test_failure_report_identifies_rule_file_and_record_without_input_content(
    tmp_path: Path,
) -> None:
    report = ValidationReport(
        issues=(
            ValidationIssue(
                rule="privacy.personal_identifier",
                file="records.jsonl",
                message="content matches a prohibited pattern",
                record_id="record-001",
            ),
        ),
        coverage={"records": 1, "scenarios": 0},
    )
    output = tmp_path / "report.json"

    write_validation_report(report, output)

    document = json.loads(output.read_text())
    assert document["status"] == "invalid"
    assert document["issue_count"] == 1
    assert document["issues"][0] == {
        "file": "records.jsonl",
        "message": "content matches a prohibited pattern",
        "record_id": "record-001",
        "rule": "privacy.personal_identifier",
    }
    assert validation_exit_code(report) == 1
