from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest

from vbe_hub.adapters.ai.openai_embeddings import OpenAIEmbeddingProvider
from vbe_hub.application.ai import EmbeddingRequest, ProviderError, ProviderErrorCode

NOW = datetime(2026, 11, 8, 12, tzinfo=UTC)


class EmbeddingsDouble:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.response


def request(*, text="doenca_agravo: Sarampo", dimensions=3):
    return EmbeddingRequest(
        stable_id=UUID(int=1),
        input_hash="a" * 64,
        text=text,
        expected_dimensions=dimensions,
    )


async def test_provider_requests_a_bounded_vector_and_records_usage() -> None:
    api = EmbeddingsDouble(
        SimpleNamespace(
            data=[SimpleNamespace(embedding=[0.1, 0.2, 0.3])],
            usage=SimpleNamespace(prompt_tokens=7, total_tokens=7),
        )
    )
    provider = OpenAIEmbeddingProvider(
        embeddings=api,
        model="text-embedding-3-small",
        timeout_seconds=8,
        max_input_chars=100,
        now=lambda: NOW,
        monotonic_values=iter([1.0, 1.025]),
    )

    result = await provider.embed(request())

    assert result.vector == (0.1, 0.2, 0.3)
    assert result.metadata.provider == "openai"
    assert result.metadata.input_units == 7
    assert result.metadata.duration_ms == 25
    assert api.calls == [
        {
            "model": "text-embedding-3-small",
            "input": "doenca_agravo: Sarampo",
            "dimensions": 3,
            "timeout": 8,
            "encoding_format": "float",
        }
    ]


async def test_provider_rejects_input_before_calling_api_when_size_limit_is_exceeded() -> None:
    api = EmbeddingsDouble()
    provider = OpenAIEmbeddingProvider(
        embeddings=api,
        model="text-embedding-3-small",
        timeout_seconds=8,
        max_input_chars=10,
        now=lambda: NOW,
    )

    with pytest.raises(ProviderError) as captured:
        await provider.embed(request())

    assert captured.value.code is ProviderErrorCode.PERMANENT_FAILURE
    assert api.calls == []


async def test_provider_rejects_invalid_vector_without_leaking_provider_details() -> None:
    api = EmbeddingsDouble(
        SimpleNamespace(
            data=[SimpleNamespace(embedding=[0.1, float("nan"), 0.3])],
            usage=None,
        )
    )
    provider = OpenAIEmbeddingProvider(
        embeddings=api,
        model="text-embedding-3-small",
        timeout_seconds=8,
        max_input_chars=100,
        now=lambda: NOW,
    )

    with pytest.raises(ProviderError) as captured:
        await provider.embed(request())

    assert captured.value.code is ProviderErrorCode.INVALID_RESPONSE
    assert "nan" not in str(captured.value).lower()
