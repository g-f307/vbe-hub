import math
import time
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from typing import Any, Protocol

from google.genai import types

from vbe_hub.application.ai import (
    AIExecutionMetadata,
    EmbeddingRequest,
    EmbeddingResult,
    ExecutionStatus,
    ProviderError,
    ProviderErrorCode,
)


class AsyncEmbeddingModels(Protocol):
    async def embed_content(self, **kwargs: Any) -> Any: ...


class GoogleGenAIEmbeddingProvider:
    def __init__(
        self,
        *,
        models: AsyncEmbeddingModels,
        model: str,
        timeout_seconds: float,
        max_input_chars: int,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
        monotonic_values: Iterator[float] | None = None,
    ) -> None:
        if not model.strip():
            raise ValueError("model must not be empty")
        if timeout_seconds <= 0 or max_input_chars <= 0:
            raise ValueError("timeout and input limit must be positive")
        self._models = models
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._max_input_chars = max_input_chars
        self._now = now
        self._monotonic = iter(monotonic_values) if monotonic_values is not None else None

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        started_at, started = self._now(), self._read_monotonic()
        if len(request.text) > self._max_input_chars:
            raise self._error(
                ProviderErrorCode.PERMANENT_FAILURE,
                "Embedding input exceeds the configured Gemini limit.",
                False,
                started_at,
                started,
            )
        config = types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=request.expected_dimensions,
            http_options=types.HttpOptions(
                timeout=round(self._timeout_seconds * 1_000),
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )
        try:
            response = await self._models.embed_content(
                model=self._model, contents=request.text, config=config
            )
        except Exception:
            raise self._error(
                ProviderErrorCode.TEMPORARILY_UNAVAILABLE,
                "Gemini embedding service is temporarily unavailable.",
                True,
                started_at,
                started,
            ) from None
        embeddings = getattr(response, "embeddings", None)
        values = (
            getattr(embeddings[0], "values", None) if embeddings and len(embeddings) == 1 else None
        )
        if not isinstance(values, list) or len(values) != request.expected_dimensions:
            raise self._error(
                ProviderErrorCode.INVALID_RESPONSE,
                "Gemini returned an invalid embedding response.",
                False,
                started_at,
                started,
            )
        try:
            vector = tuple(float(value) for value in values)
        except (TypeError, ValueError):
            raise self._error(
                ProviderErrorCode.INVALID_RESPONSE,
                "Gemini returned an invalid embedding response.",
                False,
                started_at,
                started,
            ) from None
        if not all(math.isfinite(value) for value in vector):
            raise self._error(
                ProviderErrorCode.INVALID_RESPONSE,
                "Gemini returned an invalid embedding response.",
                False,
                started_at,
                started,
            )
        return EmbeddingResult(
            request=request,
            vector=vector,
            dimensions=len(vector),
            metadata=AIExecutionMetadata(
                provider="gemini",
                model=self._model,
                contract_version="embedding-text-v1",
                prompt_version=None,
                started_at=started_at,
                duration_ms=self._duration_ms(started),
                status=ExecutionStatus.SUCCEEDED,
                input_units=getattr(
                    getattr(response, "metadata", None), "billable_character_count", None
                ),
            ),
        )

    def _error(
        self,
        code: ProviderErrorCode,
        message: str,
        retryable: bool,
        started_at: datetime,
        started: float,
    ) -> ProviderError:
        return ProviderError(
            code=code,
            message=message,
            retryable=retryable,
            metadata=AIExecutionMetadata(
                provider="gemini",
                model=self._model,
                contract_version="embedding-text-v1",
                prompt_version=None,
                started_at=started_at,
                duration_ms=self._duration_ms(started),
                status=ExecutionStatus.FAILED,
                error_code=code,
                retryable=retryable,
            ),
        )

    def _read_monotonic(self) -> float:
        return next(self._monotonic) if self._monotonic is not None else time.monotonic()

    def _duration_ms(self, started: float) -> int:
        return round((self._read_monotonic() - started) * 1_000)
