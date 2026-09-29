import hashlib
import json
from pathlib import Path

from vbe_hub.synthetic.artifacts import write_dataset
from vbe_hub.synthetic.generator import generate_dataset
from vbe_hub.synthetic.models import GeneratorConfig

FIXTURE = Path(__file__).parents[2] / "fixtures" / "synthetic" / "v1"


def _contents(directory: Path) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in sorted(directory.iterdir())}


def test_writes_byte_identical_artifacts_for_same_configuration(tmp_path: Path) -> None:
    config = GeneratorConfig(total_records=24)
    dataset = generate_dataset(config)
    first = tmp_path / "first"
    second = tmp_path / "second"

    write_dataset(dataset, config, first)
    write_dataset(dataset, config, second)

    assert _contents(first) == _contents(second)
    assert set(_contents(first)) == {"gold.json", "manifest.json", "records.jsonl"}


def test_manifest_reconciles_counts_and_hashes(tmp_path: Path) -> None:
    config = GeneratorConfig(total_records=24, media_ratio=0.5)
    output = tmp_path / "dataset"

    write_dataset(generate_dataset(config), config, output)

    manifest = json.loads((output / "manifest.json").read_text())
    records = (output / "records.jsonl").read_bytes()
    gold = (output / "gold.json").read_bytes()
    assert manifest["seed"] == config.seed
    assert manifest["generator_version"] == config.generator_version
    assert manifest["counts"] == {
        "community": 12,
        "labels": 24,
        "media": 12,
        "records": 24,
        "relations": 12,
    }
    assert manifest["sha256"]["records.jsonl"] == hashlib.sha256(records).hexdigest()
    assert manifest["sha256"]["gold.json"] == hashlib.sha256(gold).hexdigest()


def test_pipeline_jsonl_does_not_leak_evaluation_fields(tmp_path: Path) -> None:
    output = tmp_path / "dataset"
    write_dataset(generate_dataset(GeneratorConfig()), GeneratorConfig(), output)

    for line in (output / "records.jsonl").read_text().splitlines():
        record = json.loads(line)
        assert "scenario_id" not in record
        assert "gold_event_id" not in record
        assert "scenario_id" not in record["provenance"]


def test_versioned_fixture_matches_its_manifest_and_covers_all_scenarios() -> None:
    manifest = json.loads((FIXTURE / "manifest.json").read_text())
    records = (FIXTURE / "records.jsonl").read_bytes()
    gold_content = (FIXTURE / "gold.json").read_bytes()
    gold = json.loads(gold_content)

    assert manifest["counts"]["records"] == 12
    assert len(manifest["scenario_counts"]) == 12
    assert set(manifest["scenario_counts"].values()) == {1}
    assert manifest["sha256"]["records.jsonl"] == hashlib.sha256(records).hexdigest()
    assert manifest["sha256"]["gold.json"] == hashlib.sha256(gold_content).hexdigest()
    assert len(gold["labels"]) == 12
