import json
from datetime import datetime
from pathlib import Path

from vbe_hub.domain.records import RawRecord, SourceKind
from vbe_hub.normalization.service import NormalizationService


FIXTURES = Path(__file__).parents[2] / "fixtures"


def test_versioned_media_and_community_fixture_matches_normalized_contract() -> None:
    input_path = FIXTURES / "synthetic" / "v1" / "records.jsonl"
    expected_path = FIXTURES / "normalization" / "v1" / "expected.json"
    envelopes = [
        json.loads(line)
        for line in input_path.read_text(encoding="utf-8").splitlines()[:2]
    ]
    records = [
        RawRecord.create(
            source_kind=SourceKind(envelope["source_kind"]),
            source_name=envelope["source_name"],
            external_id=envelope["external_id"],
            published_at=datetime.fromisoformat(envelope["published_at"]),
            title=envelope["title"],
            body=envelope["body"],
            source_url=envelope["source_url"],
            language=envelope["language"],
            original_payload=envelope["payload"],
        )
        for envelope in envelopes
    ]

    actual = [
        result.normalized_data for result in NormalizationService().normalize_batch(records)
    ]
    expected = json.loads(expected_path.read_text(encoding="utf-8"))

    assert actual == expected
