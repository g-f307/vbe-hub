from datetime import UTC, datetime
from uuid import UUID

import pytest

from vbe_hub.application.ai import ProviderError, ProviderErrorCode, RelationKind
from vbe_hub.application.correlation.candidates import CandidatePolicy, GeographicLevel
from vbe_hub.application.correlation.precompute import (
    PreparedSignal,
    RelatedSignalPrecomputer,
)

NOW = datetime(2026, 11, 8, 12, tzinfo=UTC)
ANCHOR = UUID("00000000-0000-0000-0000-000000000001")
RELATED = UUID("00000000-0000-0000-0000-000000000002")
FAR = UUID("00000000-0000-0000-0000-000000000003")


def sheet(*, district: str = "Compensa", disease: str = "Dengue") -> dict[str, object]:
    return {
        "disease_or_condition": disease,
        "symptoms": ["febre", "dor no corpo"],
        "temporal": {"start": "2026-11-01", "end": None},
        "location": {
            "country": "Brasil",
            "state": "Amazonas",
            "municipality": "Manaus",
            "district": district,
        },
    }


class Source:
    async def anchor(self, signal_id):
        assert signal_id == ANCHOR
        return PreparedSignal(ANCHOR, ANCHOR, sheet(), 1.0)

    async def nearest(self, anchor, limit):
        assert anchor.signal_id == ANCHOR
        assert limit == 10
        return [
            PreparedSignal(RELATED, RELATED, sheet(), 0.95),
            PreparedSignal(FAR, FAR, sheet(district="Flores"), 0.99),
        ]


class Suggestions:
    def __init__(self):
        self.pending = []
        self.ready = []
        self.failed = []

    async def mark_pending(self, left, right, contract_version):
        self.pending.append((left, right, contract_version))

    async def mark_ready(self, left, right, contract_version, assessment_id):
        self.ready.append((left, right, contract_version, assessment_id))

    async def mark_failed(self, left, right, contract_version, error_code):
        self.failed.append((left, right, contract_version, error_code))


class Assessor:
    def __init__(self, *, error=None):
        self.error = error
        self.calls = []

    async def assess(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return type("Assessment", (), {"id": UUID(int=90), "relation": RelationKind.CORROBORATES})()


def service(*, assessor, suggestions):
    return RelatedSignalPrecomputer(
        source=Source(),
        suggestions=suggestions,
        assessor=assessor,
        policy=CandidatePolicy(
            max_temporal_gap_days=30,
            geographic_level=GeographicLevel.DISTRICT,
            minimum_semantic_score=0.70,
            minimum_total_score=0.70,
        ),
        neighbor_limit=10,
        candidate_limit=3,
        contract_version="related-signal-v1",
    )


async def test_only_prefiltered_candidates_reach_the_relation_model() -> None:
    suggestions = Suggestions()
    assessor = Assessor()

    result = await service(assessor=assessor, suggestions=suggestions).process(ANCHOR)

    assert result.considered == 2
    assert result.submitted == 1
    assert result.ready == 1
    assert [call["right_id"] for call in assessor.calls] == [RELATED]
    assert suggestions.pending == [(ANCHOR, RELATED, "related-signal-v1")]
    assert suggestions.ready == [(ANCHOR, RELATED, "related-signal-v1", UUID(int=90))]


async def test_provider_failure_marks_suggestion_failed_without_failing_signal() -> None:
    suggestions = Suggestions()
    assessor = Assessor(
        error=ProviderError(
            code=ProviderErrorCode.TIMEOUT,
            message="Relation provider timed out.",
            retryable=True,
        )
    )

    result = await service(assessor=assessor, suggestions=suggestions).process(ANCHOR)

    assert result.failed == 1
    assert suggestions.failed == [(ANCHOR, RELATED, "related-signal-v1", "timeout")]


async def test_precomputation_requires_bounded_candidate_limits() -> None:
    with pytest.raises(ValueError, match="candidate_limit"):
        RelatedSignalPrecomputer(
            source=Source(),
            suggestions=Suggestions(),
            assessor=Assessor(),
            policy=CandidatePolicy(30, GeographicLevel.DISTRICT, 0.7, 0.7),
            neighbor_limit=10,
            candidate_limit=0,
            contract_version="related-signal-v1",
        )
