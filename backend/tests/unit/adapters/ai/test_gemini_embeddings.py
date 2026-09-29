from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest

from vbe_hub.adapters.ai.gemini_embeddings import GoogleGenAIEmbeddingProvider
from vbe_hub.application.ai import EmbeddingRequest, ProviderError, ProviderErrorCode

NOW = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)


class StubModels:
    def __init__(self, *, response: object = None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.calls: list[dict[str, object]] = []

    async def embed_content(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.response


def request(*, dimensions: int = 3) -> EmbeddingRequest:
    return EmbeddingRequest(
        stable_id=UUID("00000000-0000-0000-0000-000000000010"),
        input_hash="a" * 64,
        text="doenca_agravo: Sarampo\nmunicipio: Manaus",
        expected_dimensions=dimensions,
    )


async def test_provider_requests_document_embedding_with_pinned_dimensions() -> None:
    models = StubModels(
        response=SimpleNamespace(
            embeddings=[SimpleNamespace(values=[0.1, 0.2, 0.3])],
            metadata=SimpleNamespace(billable_character_count=44),
        )
    )
    provider = GoogleGenAIEmbeddingProvider(
        models=models,
        model="gemini-embedding-2",
        timeout_seconds=7,
        max_input_chars=1_000,
        now=lambda: NOW,
        monotonic_values=iter([1.0, 1.025]),
    )

    result = await provider.embed(request())

    assert result.vector == (0.1, 0.2, 0.3)
    assert result.metadata.model == "gemini-embedding-2"
    assert result.metadata.duration_ms == 25
    call = models.calls[0]
    assert call["model"] == "gemini-embedding-2"
    assert call["contents"] == request().text
    assert call["config"].output_dimensionality == 3
    assert call["config"].task_type == "RETRIEVAL_DOCUMENT"
    assert call["config"].http_options.timeout == 7_000
    assert call["config"].http_options.retry_options.attempts == 1


async def test_provider_rejects_vector_with_unexpected_dimensions() -> None:
    models = StubModels(response=SimpleNamespace(embeddings=[SimpleNamespace(values=[0.1])]))
    provider = GoogleGenAIEmbeddingProvider(
        models=models,
        model="gemini-embedding-2",
        timeout_seconds=7,
        max_input_chars=1_000,
        now=lambda: NOW,
    )

    with pytest.raises(ProviderError) as captured:
        await provider.embed(request())

    assert captured.value.code is ProviderErrorCode.INVALID_RESPONSE
    assert str(captured.value) == "Gemini returned an invalid embedding response."


async def test_provider_rejects_non_finite_vector_as_invalid_response() -> None:
    models = StubModels(
        response=SimpleNamespace(embeddings=[SimpleNamespace(values=[0.1, float("nan"), 0.3])])
    )
    provider = GoogleGenAIEmbeddingProvider(
        models=models,
        model="gemini-embedding-2",
        timeout_seconds=7,
        max_input_chars=1_000,
        now=lambda: NOW,
        monotonic_values=iter([1.0, 1.01]),
    )

    with pytest.raises(ProviderError) as captured:
        await provider.embed(request())

    assert captured.value.code is ProviderErrorCode.INVALID_RESPONSE


async def test_provider_does_not_expose_sdk_error_details() -> None:
    models = StubModels(error=RuntimeError("secret provider payload"))
    provider = GoogleGenAIEmbeddingProvider(
        models=models,
        model="gemini-embedding-2",
        timeout_seconds=7,
        max_input_chars=1_000,
        now=lambda: NOW,
    )

    with pytest.raises(ProviderError) as captured:
        await provider.embed(request())

    assert captured.value.code is ProviderErrorCode.TEMPORARILY_UNAVAILABLE
    assert "secret" not in str(captured.value)
