import hashlib
import json
from collections.abc import Mapping
from datetime import datetime

from vbe_hub.application.ai import (
    AIExecutionMetadata,
    EmbeddingRequest,
    EmbeddingResult,
    ExecutionStatus,
    FieldEvidence,
    ProviderError,
    ProviderErrorCode,
    RelationKind,
    RelationRequest,
    RelationResult,
    StructuredExtractionRequest,
    StructuredExtractionResult,
)


class FakeStructuredExtractor:
    def __init__(
        self,
        *,
        started_at: datetime,
        failures: Mapping[str, ProviderError] | None = None,
    ) -> None:
        self._started_at = started_at
        self._failures = dict(failures or {})

    async def extract(self, request: StructuredExtractionRequest) -> StructuredExtractionResult:
        if failure := self._failures.get(request.input_hash):
            raise _failure_with_metadata(
                failure,
                started_at=self._started_at,
                model="deterministic-extractor-v1",
                prompt_version=request.prompt_version,
            )
        source_text = str(request.normalized_data.get("text", ""))
        excerpt = source_text[:200] or "No textual evidence supplied."
        return StructuredExtractionResult(
            technical_sheet={
                "record_id": str(request.record_id),
                "summary": excerpt,
                "source_input_hash": request.input_hash,
            },
            evidence=(FieldEvidence(field="summary", excerpt=excerpt),),
            metadata=_metadata(
                started_at=self._started_at,
                model="deterministic-extractor-v1",
                prompt_version=request.prompt_version,
            ),
        )


class FakeEmbeddingProvider:
    def __init__(self, *, dimensions: int, started_at: datetime) -> None:
        if dimensions <= 0:
            raise ValueError("dimensions must be positive")
        self._dimensions = dimensions
        self._started_at = started_at

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        if request.expected_dimensions != self._dimensions:
            raise ProviderError(
                code=ProviderErrorCode.INVALID_RESPONSE,
                message="Embedding dimensions do not match the configured contract.",
                retryable=False,
                metadata=AIExecutionMetadata(
                    provider="fake",
                    model="deterministic-embedding-v1",
                    contract_version="1.0",
                    prompt_version=None,
                    started_at=self._started_at,
                    duration_ms=0,
                    status=ExecutionStatus.FAILED,
                    error_code=ProviderErrorCode.INVALID_RESPONSE,
                    retryable=False,
                ),
            )
        vector = tuple(_deterministic_vector(request.input_hash, self._dimensions))
        return EmbeddingResult(
            request=request,
            vector=vector,
            dimensions=self._dimensions,
            metadata=_metadata(
                started_at=self._started_at,
                model="deterministic-embedding-v1",
                prompt_version=None,
            ),
        )


class FakeRelationJudge:
    def __init__(
        self,
        *,
        started_at: datetime,
        failures: Mapping[str, ProviderError] | None = None,
    ) -> None:
        self._started_at = started_at
        self._failures = dict(failures or {})

    async def judge(self, request: RelationRequest) -> RelationResult:
        key = _relation_key(request)
        if failure := self._failures.get(key):
            raise _failure_with_metadata(
                failure,
                started_at=self._started_at,
                model="deterministic-relation-v1",
                prompt_version=request.prompt_version,
            )
        choices = tuple(RelationKind)
        digest = hashlib.sha256(key.encode()).digest()
        relation = choices[digest[0] % len(choices)]
        confidence = round(digest[1] / 255, 4)
        return RelationResult(
            relation=relation,
            justification="Deterministic fake suggestion for contract testing.",
            confidence=confidence,
            metadata=_metadata(
                started_at=self._started_at,
                model="deterministic-relation-v1",
                prompt_version=request.prompt_version,
            ),
        )


def _metadata(
    *, started_at: datetime, model: str, prompt_version: str | None
) -> AIExecutionMetadata:
    return AIExecutionMetadata(
        provider="fake",
        model=model,
        contract_version="1.0",
        prompt_version=prompt_version,
        started_at=started_at,
        duration_ms=0,
        status=ExecutionStatus.SUCCEEDED,
        input_units=0,
        output_units=0,
        cache_hit=False,
    )


def _failure_with_metadata(
    failure: ProviderError,
    *,
    started_at: datetime,
    model: str,
    prompt_version: str | None,
) -> ProviderError:
    return ProviderError(
        code=failure.code,
        message=str(failure),
        retryable=failure.retryable,
        metadata=AIExecutionMetadata(
            provider="fake",
            model=model,
            contract_version="1.0",
            prompt_version=prompt_version,
            started_at=started_at,
            duration_ms=0,
            status=ExecutionStatus.FAILED,
            error_code=failure.code,
            retryable=failure.retryable,
        ),
    )


def _deterministic_vector(input_hash: str, dimensions: int):
    for index in range(dimensions):
        digest = hashlib.sha256(f"{input_hash}:{index}".encode()).digest()
        yield round((int.from_bytes(digest[:4], "big") / (2**32 - 1)) * 2 - 1, 8)


def _relation_key(request: RelationRequest) -> str:
    return json.dumps(
        {
            "left": request.left,
            "left_id": str(request.left_id),
            "right": request.right,
            "right_id": str(request.right_id),
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
