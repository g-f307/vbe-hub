import asyncio
import hashlib
import json
import time
from collections.abc import Awaitable, Callable, Iterator, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from pydantic import ValidationError

from vbe_hub.application.ai import (
    AIExecutionMetadata,
    ExecutionStatus,
    FieldEvidence,
    ProviderError,
    ProviderErrorCode,
    StructuredExtractionRequest,
    StructuredExtractionResult,
)
from vbe_hub.application.ai.technical_sheet import (
    SCHEMA_VERSION,
    TechnicalSheet,
    validate_grounded_sheet,
)

_ASSETS = Path(__file__).parents[2] / "application" / "ai" / "assets"
PROMPT_VERSION = "extract-v2"


@dataclass(frozen=True, slots=True)
class GeminiClientRequest:
    contents: str
    response_schema: Mapping[str, Any]
    timeout_seconds: float
    max_output_tokens: int
    temperature: float = 0.0
    tools: tuple[()] = ()


@dataclass(frozen=True, slots=True)
class GeminiClientResponse:
    payload: dict[str, Any]
    input_tokens: int | None
    output_tokens: int | None


class GeminiClient(Protocol):
    async def generate(self, request: GeminiClientRequest) -> GeminiClientResponse: ...


class GeminiTransportError(Exception):
    def __init__(self, *, status_code: int | None, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code


class GeminiStructuredExtractor:
    def __init__(
        self,
        *,
        client: GeminiClient,
        model: str,
        timeout_seconds: float,
        max_attempts: int,
        max_input_chars: int,
        max_output_tokens: int,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
        monotonic_values: Iterator[float] | None = None,
    ) -> None:
        if not model.strip():
            raise ValueError("model must not be empty")
        if timeout_seconds <= 0 or max_attempts <= 0:
            raise ValueError("timeout_seconds and max_attempts must be positive")
        if max_input_chars <= 0 or max_output_tokens <= 0:
            raise ValueError("input and output limits must be positive")
        self._client = client
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._max_attempts = max_attempts
        self._max_input_chars = max_input_chars
        self._max_output_tokens = max_output_tokens
        self._sleep = sleep
        self._now = now
        self._monotonic = iter(monotonic_values) if monotonic_values is not None else None

    async def extract(self, request: StructuredExtractionRequest) -> StructuredExtractionResult:
        source_content = json.dumps(request.normalized_data, ensure_ascii=False, sort_keys=True)
        started_at = self._now()
        started_monotonic = self._read_monotonic()
        if request.prompt_version != PROMPT_VERSION or request.schema_version != SCHEMA_VERSION:
            raise self._provider_error(
                code=ProviderErrorCode.CONFIGURATION,
                message="Gemini extractor does not support the requested contract versions.",
                retryable=False,
                request=request,
                started_at=started_at,
                started_monotonic=started_monotonic,
            )
        if len(source_content) > self._max_input_chars:
            raise self._provider_error(
                code=ProviderErrorCode.PERMANENT_FAILURE,
                message="Normalized input exceeds the configured Gemini limit.",
                retryable=False,
                request=request,
                started_at=started_at,
                started_monotonic=started_monotonic,
            )

        client_request = GeminiClientRequest(
            contents=self._build_contents(request, source_content),
            response_schema=TechnicalSheet.model_json_schema(),
            timeout_seconds=self._timeout_seconds,
            max_output_tokens=self._max_output_tokens,
        )
        response: GeminiClientResponse | None = None
        sheet: TechnicalSheet | None = None
        total_input_units = 0
        total_output_units = 0
        for attempt in range(1, self._max_attempts + 1):
            try:
                response = await self._client.generate(client_request)
                total_input_units += response.input_tokens or 0
                total_output_units += response.output_tokens or 0
            except GeminiTransportError as error:
                code, retryable = _classify_transport_error(error.status_code)
                if retryable and attempt < self._max_attempts:
                    await self._sleep(0.25 * (2 ** (attempt - 1)))
                    continue
                raise self._provider_error(
                    code=code,
                    message=_public_error_message(code),
                    retryable=retryable,
                    request=request,
                    started_at=started_at,
                    started_monotonic=started_monotonic,
                ) from None
            try:
                sheet = validate_grounded_sheet(response.payload, source_text=source_content)
                break
            except (ValidationError, ValueError, TypeError):
                if attempt < self._max_attempts:
                    await self._sleep(0.25 * (2 ** (attempt - 1)))
                    continue
                raise self._provider_error(
                    code=ProviderErrorCode.INVALID_RESPONSE,
                    message="Gemini returned an invalid structured response.",
                    retryable=False,
                    request=request,
                    started_at=started_at,
                    started_monotonic=started_monotonic,
                    input_units=total_input_units,
                    output_units=total_output_units,
                ) from None

        if response is None or sheet is None:
            raise RuntimeError("Gemini extraction finished without a response")

        return StructuredExtractionResult(
            technical_sheet=sheet.model_dump(mode="json"),
            evidence=tuple(
                FieldEvidence(field=item.field, excerpt=item.excerpt) for item in sheet.evidence
            ),
            metadata=AIExecutionMetadata(
                provider="gemini",
                model=self._model,
                contract_version=request.schema_version,
                prompt_version=request.prompt_version,
                started_at=started_at,
                duration_ms=self._duration_ms(started_monotonic),
                status=ExecutionStatus.SUCCEEDED,
                input_units=total_input_units,
                output_units=total_output_units,
            ),
        )

    def _build_contents(self, request: StructuredExtractionRequest, source_content: str) -> str:
        instructions = (
            (_ASSETS / f"{request.prompt_version}.prompt.txt").read_text(encoding="utf-8").strip()
        )
        delimiter = hashlib.sha256(request.trace_id.encode()).hexdigest()[:16]
        return (
            f"{instructions}\n\n"
            f"UNTRUSTED_RECORD_START_{delimiter}\n{source_content}\n"
            f"UNTRUSTED_RECORD_END_{delimiter}\n"
            "Return only the JSON object matching the supplied response schema."
        )

    def _provider_error(
        self,
        *,
        code: ProviderErrorCode,
        message: str,
        retryable: bool,
        request: StructuredExtractionRequest,
        started_at: datetime,
        started_monotonic: float,
        input_units: int | None = None,
        output_units: int | None = None,
    ) -> ProviderError:
        return ProviderError(
            code=code,
            message=message,
            retryable=retryable,
            metadata=AIExecutionMetadata(
                provider="gemini",
                model=self._model,
                contract_version=request.schema_version,
                prompt_version=request.prompt_version,
                started_at=started_at,
                input_units=input_units,
                output_units=output_units,
                duration_ms=self._duration_ms(started_monotonic),
                status=ExecutionStatus.FAILED,
                error_code=code,
                retryable=retryable,
            ),
        )

    def _read_monotonic(self) -> float:
        if self._monotonic is not None:
            return next(self._monotonic)
        return time.monotonic()

    def _duration_ms(self, started: float) -> int:
        return round((self._read_monotonic() - started) * 1_000)


def _classify_transport_error(status_code: int | None) -> tuple[ProviderErrorCode, bool]:
    if status_code == 408:
        return ProviderErrorCode.TIMEOUT, True
    if status_code == 429:
        return ProviderErrorCode.RATE_LIMITED, True
    if status_code == 422:
        return ProviderErrorCode.INVALID_RESPONSE, False
    if status_code is None or status_code >= 500:
        return ProviderErrorCode.TEMPORARILY_UNAVAILABLE, True
    return ProviderErrorCode.PERMANENT_FAILURE, False


def _public_error_message(code: ProviderErrorCode) -> str:
    messages = {
        ProviderErrorCode.TIMEOUT: "Gemini request timed out.",
        ProviderErrorCode.RATE_LIMITED: "Gemini rate limit was reached.",
        ProviderErrorCode.TEMPORARILY_UNAVAILABLE: "Gemini is temporarily unavailable.",
        ProviderErrorCode.INVALID_RESPONSE: "Gemini returned an invalid structured response.",
        ProviderErrorCode.PERMANENT_FAILURE: "Gemini rejected the request.",
    }
    return messages[code]
