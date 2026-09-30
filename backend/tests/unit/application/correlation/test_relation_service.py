from datetime import UTC, datetime
from uuid import UUID

import pytest

from vbe_hub.application.ai import (
    AIExecutionMetadata,
    ExecutionStatus,
    ProviderError,
    ProviderErrorCode,
    RelationKind,
    RelationRequest,
    RelationResult,
)
from vbe_hub.application.correlation.relations import (
    RELATION_RULES_VERSION,
    RelationAssessmentService,
    RelationMethod,
)

NOW = datetime(2026, 9, 30, 12, tzinfo=UTC)
LEFT = UUID("00000000-0000-0000-0000-000000000012")
RIGHT = UUID("00000000-0000-0000-0000-000000000013")


def sheet(*, cases: int = 5, start: str = "2026-03-10") -> dict[str, object]:
    return {
        "disease_or_condition": "Sarampo",
        "symptoms": ["febre", "manchas vermelhas"],
        "estimated_cases": cases,
        "temporal": {"start": start, "end": None},
        "location": {"country": "Brasil", "state": "Amazonas", "municipality": "Manaus"},
    }


class Repository:
    def __init__(self) -> None:
        self.records = {}

    async def get(self, cache_key):
        return self.records.get(cache_key)

    async def save(self, record):
        self.records[record.cache_key] = record


class Judge:
    def __init__(self, result=None, error=None) -> None:
        self.result = result
        self.error = error
        self.calls = 0
        self.request = None

    async def judge(self, request: RelationRequest) -> RelationResult:
        self.calls += 1
        self.request = request
        if self.error:
            raise self.error
        return self.result


def metadata(status=ExecutionStatus.SUCCEEDED) -> AIExecutionMetadata:
    return AIExecutionMetadata(
        provider="fake",
        model="relation-v1",
        contract_version="relation-v1",
        prompt_version="relate-v1",
        started_at=NOW,
        duration_ms=10,
        status=status,
        error_code=ProviderErrorCode.TIMEOUT if status is ExecutionStatus.FAILED else None,
        retryable=True if status is ExecutionStatus.FAILED else None,
    )


async def test_identical_sheets_use_deterministic_duplicate_rule() -> None:
    judge = Judge()
    service = RelationAssessmentService(judge=judge, repository=Repository(), now=lambda: NOW)

    record = await service.assess(left_id=LEFT, right_id=RIGHT, left=sheet(), right=sheet())

    assert record.relation is RelationKind.DUPLICATE
    assert record.method is RelationMethod.RULE
    assert record.rules_version == RELATION_RULES_VERSION
    assert judge.calls == 0


async def test_ambiguous_pair_uses_judge_and_preserves_update_direction() -> None:
    judge = Judge(
        RelationResult(
            relation=RelationKind.UPDATES,
            justification="Registro posterior atualiza a magnitude.",
            confidence=0.88,
            metadata=metadata(),
        )
    )
    service = RelationAssessmentService(judge=judge, repository=Repository(), now=lambda: NOW)

    record = await service.assess(
        left_id=LEFT,
        right_id=RIGHT,
        left=sheet(),
        right=sheet(cases=9, start="2026-03-12"),
    )

    assert record.method is RelationMethod.PROVIDER
    assert record.relation is RelationKind.UPDATES
    assert record.updating_record_id == RIGHT


async def test_provider_failure_is_saved_without_positive_relation() -> None:
    repository = Repository()
    judge = Judge(
        error=ProviderError(
            code=ProviderErrorCode.TIMEOUT,
            message="Relation provider timed out.",
            retryable=True,
            metadata=metadata(ExecutionStatus.FAILED),
        )
    )
    service = RelationAssessmentService(judge=judge, repository=repository, now=lambda: NOW)

    with pytest.raises(ProviderError, match="timed out"):
        await service.assess(left_id=LEFT, right_id=RIGHT, left=sheet(), right=sheet(cases=8))

    saved = next(iter(repository.records.values()))
    assert saved.relation is None
    assert saved.sanitized_error == "Relation provider timed out."


async def test_reversed_pair_uses_same_cache_entry() -> None:
    repository = Repository()
    judge = Judge(
        RelationResult(
            relation=RelationKind.CORROBORATES,
            justification="Fontes independentes convergem.",
            confidence=0.9,
            metadata=metadata(),
        )
    )
    service = RelationAssessmentService(judge=judge, repository=repository, now=lambda: NOW)

    first = await service.assess(left_id=LEFT, right_id=RIGHT, left=sheet(), right=sheet(cases=8))
    second = await service.assess(left_id=RIGHT, right_id=LEFT, left=sheet(cases=8), right=sheet())

    assert first.id == second.id
    assert judge.calls == 1


async def test_prompt_versions_use_distinct_cache_entries() -> None:
    repository = Repository()
    judge = Judge(
        RelationResult(
            relation=RelationKind.CORROBORATES,
            justification="Fontes independentes convergem.",
            confidence=0.9,
            metadata=metadata(),
        )
    )
    v1 = RelationAssessmentService(
        judge=judge, repository=repository, relation_prompt_version="relate-v1", now=lambda: NOW
    )
    v2 = RelationAssessmentService(
        judge=judge, repository=repository, relation_prompt_version="relate-v2", now=lambda: NOW
    )

    first = await v1.assess(left_id=LEFT, right_id=RIGHT, left=sheet(), right=sheet(cases=8))
    second = await v2.assess(left_id=LEFT, right_id=RIGHT, left=sheet(), right=sheet(cases=8))

    assert first.cache_key != second.cache_key
    assert judge.calls == 2
    assert judge.request.prompt_version == "relate-v2"
