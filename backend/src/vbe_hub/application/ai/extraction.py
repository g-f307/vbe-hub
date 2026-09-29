import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

from vbe_hub.application.ai.contracts import (
    AIExecutionMetadata,
    ExecutionStatus,
    FieldEvidence,
    ProviderError,
    ProviderErrorCode,
    StructuredExtractionRequest,
    StructuredExtractionResult,
    StructuredExtractor,
)


@dataclass(frozen=True, slots=True)
class ExtractionRecord:
    id: UUID
    normalized_record_id: UUID
    cache_key: str
    input_hash: str
    technical_sheet: Mapping[str, Any] | None
    evidence: tuple[FieldEvidence, ...]
    metadata: AIExecutionMetadata
    sanitized_error: str | None
    created_at: datetime


class ExtractionRepository(Protocol):
    async def get_succeeded(self, cache_key: str) -> ExtractionRecord | None: ...

    async def save(self, record: ExtractionRecord) -> None: ...


class StructuredExtractionService:
    def __init__(
        self,
        *,
        extractor: StructuredExtractor,
        repository: ExtractionRepository,
        provider: str,
        model: str,
        now=lambda: datetime.now(UTC),
    ) -> None:
        self._extractor = extractor
        self._repository = repository
        self._provider = provider
        self._model = model
        self._now = now

    async def extract(self, request: StructuredExtractionRequest) -> StructuredExtractionResult:
        cache_key = build_extraction_cache_key(
            input_hash=request.input_hash,
            provider=self._provider,
            model=self._model,
            prompt_version=request.prompt_version,
            schema_version=request.schema_version,
        )
        cached = await self._repository.get_succeeded(cache_key)
        if cached is not None:
            return StructuredExtractionResult(
                technical_sheet=cached.technical_sheet or {},
                evidence=cached.evidence,
                metadata=replace(
                    cached.metadata,
                    started_at=self._now(),
                    duration_ms=0,
                    input_units=0,
                    output_units=0,
                    cache_hit=True,
                ),
            )

        try:
            result = await self._extractor.extract(request)
        except ProviderError as error:
            metadata = error.metadata or AIExecutionMetadata(
                provider=self._provider,
                model=self._model,
                contract_version=request.schema_version,
                prompt_version=request.prompt_version,
                started_at=self._now(),
                duration_ms=0,
                status=ExecutionStatus.FAILED,
                error_code=error.code,
                retryable=error.retryable,
            )
            await self._repository.save(
                ExtractionRecord(
                    id=uuid4(),
                    normalized_record_id=request.record_id,
                    cache_key=cache_key,
                    input_hash=request.input_hash,
                    technical_sheet=None,
                    evidence=(),
                    metadata=metadata,
                    sanitized_error=str(error),
                    created_at=self._now(),
                )
            )
            raise

        if result.metadata.provider != self._provider or result.metadata.model != self._model:
            raise ProviderError(
                code=ProviderErrorCode.INVALID_RESPONSE,
                message="Extraction provider metadata does not match its configuration.",
                retryable=False,
            )
        await self._repository.save(
            ExtractionRecord(
                id=uuid4(),
                normalized_record_id=request.record_id,
                cache_key=cache_key,
                input_hash=request.input_hash,
                technical_sheet=result.technical_sheet,
                evidence=result.evidence,
                metadata=result.metadata,
                sanitized_error=None,
                created_at=self._now(),
            )
        )
        return result


def build_extraction_cache_key(
    *,
    input_hash: str,
    provider: str,
    model: str,
    prompt_version: str,
    schema_version: str,
) -> str:
    canonical = json.dumps(
        {
            "input_hash": input_hash,
            "model": model,
            "prompt_version": prompt_version,
            "provider": provider,
            "schema_version": schema_version,
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return hashlib.sha256(canonical).hexdigest()
