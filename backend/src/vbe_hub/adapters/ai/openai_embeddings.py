from __future__ import annotations

import math
import time
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from typing import Any, Protocol

from vbe_hub.application.ai import (
    AIExecutionMetadata,
    EmbeddingRequest,
    EmbeddingResult,
    ExecutionStatus,
    ProviderError,
    ProviderErrorCode,
)


class OpenAIEmbeddingsResource(Protocol):
    async def create(self, **kwargs: Any) -> Any: ...


class OpenAIEmbeddingProvider:
    def __init__(
        self,
        *,
        embeddings: OpenAIEmbeddingsResource,
        model: str,
        timeout_seconds: float,
        max_input_chars: int,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
        monotonic_values: Iterator[float] | None = None,
    ) -> None:
        if not model.strip():
            raise ValueError("model must not be empty")
        if timeout_seconds <= 0 or max_input_chars <= 0:
            raise ValueError("OpenAI embedding limits must be positive")
        self._embeddings = embeddings
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._max_input_chars = max_input_chars
        self._now = now
        self._monotonic = iter(monotonic_values) if monotonic_values is not None else None

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        started_at = self._now()
        started = self._read_monotonic()
        if len(request.text) > self._max_input_chars:
            raise self._error(
                ProviderErrorCode.PERMANENT_FAILURE,
                "Embedding input exceeds the configured OpenAI limit.",
                False,
                started_at,
                started,
            )
        try:
            response = await self._embeddings.create(
                model=self._model,
                input=request.text,
                dimensions=request.expected_dimensions,
                timeout=self._timeout_seconds,
                encoding_format="float",
            )
        except Exception as error:
            code, retryable = _classify(error)
            raise self._error(
                code,
                "OpenAI embedding request failed.",
                retryable,
                started_at,
                started,
            ) from None
        try:
            vector = tuple(float(value) for value in response.data[0].embedding)
            if len(vector) != request.expected_dimensions or not all(
                math.isfinite(value) for value in vector
            ):
                raise ValueError
        except (AttributeError, IndexError, TypeError, ValueError):
            raise self._error(
                ProviderErrorCode.INVALID_RESPONSE,
                "OpenAI returned an invalid embedding response.",
                False,
                started_at,
                started,
            ) from None
        usage = getattr(response, "usage", None)
        input_units = getattr(usage, "prompt_tokens", None)
        return EmbeddingResult(
            request=request,
            vector=vector,
            dimensions=len(vector),
            metadata=AIExecutionMetadata(
                provider="openai",
                model=self._model,
                contract_version="embedding-v1",
                prompt_version=None,
                started_at=started_at,
                duration_ms=self._duration(started),
                status=ExecutionStatus.SUCCEEDED,
                input_units=input_units,
                output_units=0,
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
                provider="openai",
                model=self._model,
                contract_version="embedding-v1",
                prompt_version=None,
                started_at=started_at,
                duration_ms=self._duration(started),
                status=ExecutionStatus.FAILED,
                error_code=code,
                retryable=retryable,
            ),
        )

    def _read_monotonic(self) -> float:
        return next(self._monotonic) if self._monotonic is not None else time.monotonic()

    def _duration(self, started: float) -> int:
        return max(0, round((self._read_monotonic() - started) * 1000))


def _classify(error: Exception) -> tuple[ProviderErrorCode, bool]:
    status = getattr(error, "status_code", None)
    if status in (401, 403):
        return ProviderErrorCode.AUTHENTICATION, False
    if status == 429:
        return ProviderErrorCode.RATE_LIMITED, True
    if isinstance(status, int) and status >= 500:
        return ProviderErrorCode.TEMPORARILY_UNAVAILABLE, True
    if isinstance(error, TimeoutError):
        return ProviderErrorCode.TIMEOUT, True
    return ProviderErrorCode.TEMPORARILY_UNAVAILABLE, True
