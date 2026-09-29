from datetime import UTC, datetime
from uuid import UUID

import pytest

from vbe_hub.application.ai import (
    AIExecutionMetadata,
    ExecutionStatus,
    ProviderError,
    ProviderErrorCode,
    StructuredExtractionRequest,
    StructuredExtractionResult,
)
from vbe_hub.application.ai.extraction import (
    ExtractionRecord,
    StructuredExtractionService,
    build_extraction_cache_key,
)

NOW = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)
RECORD_ID = UUID("00000000-0000-0000-0000-000000000008")


class InMemoryExtractionRepository:
    def __init__(self) -> None:
        self.records: dict[str, ExtractionRecord] = {}

    async def get_succeeded(self, cache_key: str) -> ExtractionRecord | None:
        record = self.records.get(cache_key)
        if record is None or record.metadata.status is not ExecutionStatus.SUCCEEDED:
            return None
        return record

    async def save(self, record: ExtractionRecord) -> None:
        self.records[record.cache_key] = record


class CountingExtractor:
    def __init__(
        self, result: StructuredExtractionResult | None = None, error: ProviderError | None = None
    ) -> None:
        self.result = result
        self.error = error
        self.calls = 0

    async def extract(self, request: StructuredExtractionRequest) -> StructuredExtractionResult:
        self.calls += 1
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result


def request(
    *, prompt_version: str = "extract-v1", schema_version: str = "technical-sheet-v1"
) -> StructuredExtractionRequest:
    return StructuredExtractionRequest(
        record_id=RECORD_ID,
        input_hash="8" * 64,
        normalized_data={"text": "Relato sintético sem evidência suficiente."},
        schema_version=schema_version,
        prompt_version=prompt_version,
        trace_id="trace-8",
    )


def successful_result() -> StructuredExtractionResult:
    return StructuredExtractionResult(
        technical_sheet={"record_nature": None, "evidence": []},
        evidence=(),
        metadata=AIExecutionMetadata(
            provider="gemini",
            model="gemini-test-model",
            contract_version="technical-sheet-v1",
            prompt_version="extract-v1",
            started_at=NOW,
            duration_ms=100,
            status=ExecutionStatus.SUCCEEDED,
            input_units=20,
            output_units=10,
        ),
    )


async def test_second_execution_uses_cache_without_calling_provider_again() -> None:
    repository = InMemoryExtractionRepository()
    extractor = CountingExtractor(result=successful_result())
    service = StructuredExtractionService(
        extractor=extractor,
        repository=repository,
        provider="gemini",
        model="gemini-test-model",
        now=lambda: NOW,
    )

    first = await service.extract(request())
    second = await service.extract(request())

    assert extractor.calls == 1
    assert first.metadata.cache_hit is False
    assert second.metadata.cache_hit is True
    assert second.technical_sheet == first.technical_sheet
    assert len(repository.records) == 1


def test_cache_key_changes_with_every_relevant_version() -> None:
    base = build_extraction_cache_key(
        input_hash="8" * 64,
        provider="gemini",
        model="model-a",
        prompt_version="prompt-a",
        schema_version="schema-a",
    )

    variants = {
        build_extraction_cache_key(
            input_hash="9" * 64,
            provider="gemini",
            model="model-a",
            prompt_version="prompt-a",
            schema_version="schema-a",
        ),
        build_extraction_cache_key(
            input_hash="8" * 64,
            provider="fake",
            model="model-a",
            prompt_version="prompt-a",
            schema_version="schema-a",
        ),
        build_extraction_cache_key(
            input_hash="8" * 64,
            provider="gemini",
            model="model-b",
            prompt_version="prompt-a",
            schema_version="schema-a",
        ),
        build_extraction_cache_key(
            input_hash="8" * 64,
            provider="gemini",
            model="model-a",
            prompt_version="prompt-b",
            schema_version="schema-a",
        ),
        build_extraction_cache_key(
            input_hash="8" * 64,
            provider="gemini",
            model="model-a",
            prompt_version="prompt-a",
            schema_version="schema-b",
        ),
    }

    assert len(base) == 64
    assert base not in variants
    assert len(variants) == 5


async def test_failure_is_saved_with_sanitized_metadata_and_re_raised() -> None:
    metadata = AIExecutionMetadata(
        provider="gemini",
        model="gemini-test-model",
        contract_version="technical-sheet-v1",
        prompt_version="extract-v1",
        started_at=NOW,
        duration_ms=250,
        status=ExecutionStatus.FAILED,
        error_code=ProviderErrorCode.TIMEOUT,
        retryable=True,
    )
    extractor = CountingExtractor(
        error=ProviderError(
            code=ProviderErrorCode.TIMEOUT,
            message="Gemini request timed out.",
            retryable=True,
            metadata=metadata,
        )
    )
    repository = InMemoryExtractionRepository()
    service = StructuredExtractionService(
        extractor=extractor,
        repository=repository,
        provider="gemini",
        model="gemini-test-model",
        now=lambda: NOW,
    )

    with pytest.raises(ProviderError, match="timed out"):
        await service.extract(request())

    saved = next(iter(repository.records.values()))
    assert saved.technical_sheet is None
    assert saved.sanitized_error == "Gemini request timed out."
    assert saved.metadata.error_code is ProviderErrorCode.TIMEOUT
    assert not hasattr(saved, "raw_response")
