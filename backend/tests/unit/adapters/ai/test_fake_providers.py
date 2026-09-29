from datetime import UTC, datetime
from uuid import UUID

import pytest

from tests.contracts.ai import (
    assert_embedding_provider_contract,
    assert_relation_judge_contract,
    assert_structured_extractor_contract,
)
from vbe_hub.adapters.ai.fake import (
    FakeEmbeddingProvider,
    FakeRelationJudge,
    FakeStructuredExtractor,
)
from vbe_hub.application.ai import (
    EmbeddingProvider,
    EmbeddingRequest,
    ProviderError,
    ProviderErrorCode,
    RelationJudge,
    RelationKind,
    RelationRequest,
    StructuredExtractionRequest,
    StructuredExtractor,
)

NOW = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)
RECORD_ID = UUID("00000000-0000-0000-0000-000000000007")


def extraction_request(input_hash: str = "a" * 64) -> StructuredExtractionRequest:
    return StructuredExtractionRequest(
        record_id=RECORD_ID,
        input_hash=input_hash,
        normalized_data={"text": "Febre e manchas vermelhas no bairro."},
        schema_version="technical-sheet-v1",
        prompt_version="extract-v1",
        trace_id="trace-7",
    )


def test_fake_providers_satisfy_the_application_ports() -> None:
    extractor: StructuredExtractor = FakeStructuredExtractor(started_at=NOW)
    embedder: EmbeddingProvider = FakeEmbeddingProvider(dimensions=4, started_at=NOW)
    judge: RelationJudge = FakeRelationJudge(started_at=NOW)

    assert extractor is not None
    assert embedder is not None
    assert judge is not None


async def test_fake_extractor_is_deterministic_and_keeps_field_evidence() -> None:
    provider = FakeStructuredExtractor(started_at=NOW)
    request = extraction_request()

    await assert_structured_extractor_contract(provider, request)
    first = await provider.extract(request)

    assert first.technical_sheet["record_id"] == str(RECORD_ID)
    assert first.evidence[0].field == "summary"
    assert first.metadata.provider == "fake"
    assert first.metadata.prompt_version == request.prompt_version


async def test_fake_embedding_has_configurable_dimension_and_is_deterministic() -> None:
    provider = FakeEmbeddingProvider(dimensions=4, started_at=NOW)
    request = EmbeddingRequest(
        stable_id=RECORD_ID,
        input_hash="b" * 64,
        text="Possível surto de sarampo.",
        expected_dimensions=4,
    )

    await assert_embedding_provider_contract(provider, request)
    first = await provider.embed(request)

    assert first.dimensions == 4
    assert len(first.vector) == 4


async def test_fake_embedding_rejects_the_wrong_expected_dimension() -> None:
    provider = FakeEmbeddingProvider(dimensions=4, started_at=NOW)
    request = EmbeddingRequest(
        stable_id=RECORD_ID,
        input_hash="c" * 64,
        text="Texto",
        expected_dimensions=3,
    )

    with pytest.raises(ProviderError) as captured:
        await provider.embed(request)

    assert captured.value.code is ProviderErrorCode.INVALID_RESPONSE
    assert captured.value.retryable is False


async def test_fake_relation_judge_returns_a_suggestion_not_a_human_decision() -> None:
    provider = FakeRelationJudge(started_at=NOW)
    request = RelationRequest(
        left_id=RECORD_ID,
        right_id=UUID("00000000-0000-0000-0000-000000000008"),
        left={"location": "Cidade Nova", "symptom": "febre"},
        right={"location": "Cidade Nova", "symptom": "manchas"},
        prompt_version="relation-v1",
        trace_id="trace-relation-7",
    )

    result = await provider.judge(request)

    await assert_relation_judge_contract(provider, request)
    assert result.relation in RelationKind
    assert 0 <= result.confidence <= 1
    assert not hasattr(result, "confirmed")
    assert not hasattr(result, "priority")


async def test_fake_provider_simulates_sanitized_retryable_failures_by_hash() -> None:
    provider = FakeStructuredExtractor(
        started_at=NOW,
        failures={
            "f" * 64: ProviderError(
                code=ProviderErrorCode.TIMEOUT,
                message="Tempo limite excedido.",
                retryable=True,
            )
        },
    )

    with pytest.raises(ProviderError) as captured:
        await provider.extract(extraction_request("f" * 64))

    assert captured.value.code is ProviderErrorCode.TIMEOUT
    assert captured.value.retryable is True
    assert str(captured.value) == "Tempo limite excedido."
    assert captured.value.metadata is not None
    assert captured.value.metadata.status.value == "failed"
    assert captured.value.metadata.error_code is ProviderErrorCode.TIMEOUT
