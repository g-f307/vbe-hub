import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol
from uuid import UUID

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _require_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must include timezone information")


def _require_sha256(value: str) -> None:
    if not _SHA256_PATTERN.fullmatch(value):
        raise ValueError("input_hash must be a lowercase SHA-256 hexadecimal digest")


class ExecutionStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ProviderErrorCode(StrEnum):
    CONFIGURATION = "configuration"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    INVALID_RESPONSE = "invalid_response"
    TEMPORARILY_UNAVAILABLE = "temporarily_unavailable"
    PERMANENT_FAILURE = "permanent_failure"


class RelationKind(StrEnum):
    DUPLICATE = "duplicate"
    CORROBORATES = "corroborates"
    UPDATES = "updates"
    RELATED_CONTEXT = "related_context"
    UNRELATED = "unrelated"


@dataclass(frozen=True, slots=True)
class AIExecutionMetadata:
    provider: str
    model: str
    contract_version: str
    prompt_version: str | None
    started_at: datetime
    duration_ms: int
    status: ExecutionStatus
    input_units: int | None = None
    output_units: int | None = None
    cache_hit: bool = False
    error_code: ProviderErrorCode | None = None
    retryable: bool | None = None

    def __post_init__(self) -> None:
        _require_aware(self.started_at, "started_at")
        measurements = (self.duration_ms, self.input_units, self.output_units)
        if any(value is not None and value < 0 for value in measurements):
            raise ValueError("execution measurements must be non-negative")
        if not self.provider.strip() or not self.model.strip() or not self.contract_version.strip():
            raise ValueError("provider, model and contract_version must not be empty")
        if self.status is ExecutionStatus.FAILED and self.error_code is None:
            raise ValueError("failed execution metadata requires an error_code")
        if self.status is ExecutionStatus.FAILED and self.retryable is None:
            raise ValueError("failed execution metadata requires retryable classification")
        if self.status is ExecutionStatus.SUCCEEDED and (
            self.error_code is not None or self.retryable is not None
        ):
            raise ValueError("succeeded execution metadata cannot contain an error classification")


class ProviderError(Exception):
    """Provider-neutral failure safe to expose beyond an adapter boundary."""

    def __init__(
        self,
        *,
        code: ProviderErrorCode,
        message: str,
        retryable: bool,
        metadata: AIExecutionMetadata | None = None,
    ) -> None:
        sanitized_message = message.strip()
        if not sanitized_message:
            raise ValueError("provider error message must not be empty")
        super().__init__(sanitized_message)
        self.code = code
        self.retryable = retryable
        self.metadata = metadata


@dataclass(frozen=True, slots=True)
class FieldEvidence:
    field: str
    excerpt: str

    def __post_init__(self) -> None:
        if not self.field.strip():
            raise ValueError("evidence field must not be empty")
        if not self.excerpt.strip():
            raise ValueError("evidence excerpt must not be empty")


@dataclass(frozen=True, slots=True)
class StructuredExtractionRequest:
    record_id: UUID
    input_hash: str
    normalized_data: Mapping[str, Any]
    schema_version: str
    prompt_version: str
    trace_id: str

    def __post_init__(self) -> None:
        _require_sha256(self.input_hash)
        if not self.schema_version.strip() or not self.prompt_version.strip():
            raise ValueError("schema_version and prompt_version must not be empty")
        if not self.trace_id.strip():
            raise ValueError("trace_id must not be empty")


@dataclass(frozen=True, slots=True)
class StructuredExtractionResult:
    technical_sheet: Mapping[str, Any]
    evidence: tuple[FieldEvidence, ...]
    metadata: AIExecutionMetadata

    def __post_init__(self) -> None:
        if self.metadata.status is not ExecutionStatus.SUCCEEDED:
            raise ValueError("a structured extraction result must have succeeded metadata")


@dataclass(frozen=True, slots=True)
class EmbeddingRequest:
    stable_id: UUID
    input_hash: str
    text: str
    expected_dimensions: int

    def __post_init__(self) -> None:
        _require_sha256(self.input_hash)
        if not self.text.strip():
            raise ValueError("embedding text must not be empty")
        if self.expected_dimensions <= 0:
            raise ValueError("expected_dimensions must be positive")


@dataclass(frozen=True, slots=True)
class EmbeddingResult:
    request: EmbeddingRequest
    vector: tuple[float, ...]
    dimensions: int
    metadata: AIExecutionMetadata

    def __post_init__(self) -> None:
        if self.dimensions != len(self.vector):
            raise ValueError("declared dimensions must match the vector length")
        if self.dimensions != self.request.expected_dimensions:
            raise ValueError("result dimensions must match the request")
        if not all(math.isfinite(value) for value in self.vector):
            raise ValueError("embedding values must be finite")
        if self.metadata.status is not ExecutionStatus.SUCCEEDED:
            raise ValueError("an embedding result must have succeeded metadata")


@dataclass(frozen=True, slots=True)
class RelationRequest:
    left_id: UUID
    right_id: UUID
    left: Mapping[str, Any]
    right: Mapping[str, Any]
    prompt_version: str
    trace_id: str

    def __post_init__(self) -> None:
        if self.left_id == self.right_id:
            raise ValueError("relation candidates must be different records")
        if not self.prompt_version.strip() or not self.trace_id.strip():
            raise ValueError("prompt_version and trace_id must not be empty")


@dataclass(frozen=True, slots=True)
class RelationResult:
    relation: RelationKind
    justification: str
    confidence: float
    metadata: AIExecutionMetadata

    def __post_init__(self) -> None:
        if not self.justification.strip() or len(self.justification) > 500:
            raise ValueError("justification must contain between 1 and 500 characters")
        if not math.isfinite(self.confidence) or not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be finite and between 0 and 1")
        if self.metadata.status is not ExecutionStatus.SUCCEEDED:
            raise ValueError("a relation result must have succeeded metadata")


class StructuredExtractor(Protocol):
    async def extract(self, request: StructuredExtractionRequest) -> StructuredExtractionResult: ...


class EmbeddingProvider(Protocol):
    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult: ...


class RelationJudge(Protocol):
    async def judge(self, request: RelationRequest) -> RelationResult: ...
