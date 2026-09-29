from datetime import UTC, datetime
from math import nan
from uuid import UUID

import pytest

from vbe_hub.application.ai import (
    AIExecutionMetadata,
    EmbeddingRequest,
    EmbeddingResult,
    ExecutionStatus,
    FieldEvidence,
    ProviderError,
    ProviderErrorCode,
    RelationKind,
    RelationResult,
)

STARTED_AT = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)


def successful_metadata() -> AIExecutionMetadata:
    return AIExecutionMetadata(
        provider="fake",
        model="deterministic-v1",
        contract_version="1.0",
        prompt_version="extract-v1",
        started_at=STARTED_AT,
        duration_ms=12,
        status=ExecutionStatus.SUCCEEDED,
        input_units=30,
        output_units=8,
        cache_hit=False,
    )


def test_metadata_rejects_naive_time_and_negative_measurements() -> None:
    with pytest.raises(ValueError, match="started_at"):
        AIExecutionMetadata(
            provider="fake",
            model="v1",
            contract_version="1.0",
            prompt_version=None,
            started_at=datetime(2026, 9, 29),
            duration_ms=1,
            status=ExecutionStatus.SUCCEEDED,
        )

    with pytest.raises(ValueError, match="non-negative"):
        AIExecutionMetadata(
            provider="fake",
            model="v1",
            contract_version="1.0",
            prompt_version=None,
            started_at=STARTED_AT,
            duration_ms=-1,
            status=ExecutionStatus.SUCCEEDED,
        )


def test_embedding_result_requires_finite_vector_with_declared_dimension() -> None:
    request = EmbeddingRequest(
        stable_id=UUID("00000000-0000-0000-0000-000000000007"),
        input_hash="a" * 64,
        text="Febre e manchas vermelhas no bairro.",
        expected_dimensions=3,
    )

    result = EmbeddingResult(
        request=request,
        vector=(0.1, 0.2, 0.3),
        dimensions=3,
        metadata=successful_metadata(),
    )

    assert result.dimensions == len(result.vector)

    with pytest.raises(ValueError, match="dimensions"):
        EmbeddingResult(
            request=request,
            vector=(0.1, 0.2),
            dimensions=3,
            metadata=successful_metadata(),
        )
    with pytest.raises(ValueError, match="finite"):
        EmbeddingResult(
            request=request,
            vector=(0.1, nan, 0.3),
            dimensions=3,
            metadata=successful_metadata(),
        )


def test_relation_result_validates_confidence_and_bounded_justification() -> None:
    result = RelationResult(
        relation=RelationKind.CORROBORATES,
        justification="Sintomas, local e período são compatíveis.",
        confidence=0.87,
        metadata=successful_metadata(),
    )

    assert result.relation is RelationKind.CORROBORATES

    with pytest.raises(ValueError, match="confidence"):
        RelationResult(
            relation=RelationKind.UNRELATED,
            justification="Sem compatibilidade.",
            confidence=1.1,
            metadata=successful_metadata(),
        )
    with pytest.raises(ValueError, match="justification"):
        RelationResult(
            relation=RelationKind.UNRELATED,
            justification="x" * 501,
            confidence=0.1,
            metadata=successful_metadata(),
        )


def test_evidence_requires_a_non_empty_source_excerpt() -> None:
    with pytest.raises(ValueError, match="excerpt"):
        FieldEvidence(field="symptoms", excerpt="   ")


def test_provider_error_exposes_only_a_sanitized_message() -> None:
    error = ProviderError(
        code=ProviderErrorCode.RATE_LIMITED,
        message="Limite temporário do provedor.",
        retryable=True,
    )

    assert str(error) == "Limite temporário do provedor."
    assert error.retryable is True
    assert not hasattr(error, "raw_response")


def test_failed_metadata_requires_an_error_classification() -> None:
    with pytest.raises(ValueError, match="error_code"):
        AIExecutionMetadata(
            provider="fake",
            model="v1",
            contract_version="1.0",
            prompt_version=None,
            started_at=STARTED_AT,
            duration_ms=10,
            status=ExecutionStatus.FAILED,
        )

    metadata = AIExecutionMetadata(
        provider="fake",
        model="v1",
        contract_version="1.0",
        prompt_version=None,
        started_at=STARTED_AT,
        duration_ms=10,
        status=ExecutionStatus.FAILED,
        error_code=ProviderErrorCode.TIMEOUT,
        retryable=True,
    )

    assert metadata.error_code is ProviderErrorCode.TIMEOUT
    assert metadata.retryable is True
