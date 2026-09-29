import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4


def _require_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must include timezone information")


def _utc_now() -> datetime:
    return datetime.now(UTC)


class SourceKind(StrEnum):
    MEDIA = "media"
    COMMUNITY = "community"


class ProcessingState(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class Provenance:
    adapter_name: str
    adapter_version: str
    collected_at: datetime
    generator_name: str | None = None
    generator_version: str | None = None
    seed: int | None = None
    scenario_id: str | None = None
    ingestion_run_id: UUID | None = None

    def __post_init__(self) -> None:
        _require_aware(self.collected_at, "collected_at")


@dataclass(frozen=True, slots=True)
class EvaluationLabel:
    raw_record_id: UUID
    gold_event_id: str


@dataclass(frozen=True, slots=True)
class RawRecord:
    id: UUID
    source_kind: SourceKind
    source_name: str
    external_id: str | None
    published_at: datetime
    title: str | None
    body: str
    source_url: str | None
    language: str
    original_payload: dict[str, Any]
    content_hash: str
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        _require_aware(self.published_at, "published_at")
        _require_aware(self.created_at, "created_at")
        _require_aware(self.updated_at, "updated_at")

    @classmethod
    def create(
        cls,
        *,
        source_kind: SourceKind,
        source_name: str,
        external_id: str | None,
        published_at: datetime,
        title: str | None,
        body: str,
        source_url: str | None,
        language: str,
        original_payload: dict[str, Any],
    ) -> "RawRecord":
        _require_aware(published_at, "published_at")
        canonical_content = json.dumps(
            {
                "body": body,
                "language": language,
                "original_payload": original_payload,
                "published_at": published_at.astimezone(UTC).isoformat(),
                "source_url": source_url,
                "title": title,
            },
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
        timestamp = _utc_now()
        return cls(
            id=uuid4(),
            source_kind=source_kind,
            source_name=source_name,
            external_id=external_id,
            published_at=published_at.astimezone(UTC),
            title=title,
            body=body,
            source_url=source_url,
            language=language,
            original_payload=original_payload,
            content_hash=hashlib.sha256(canonical_content).hexdigest(),
            created_at=timestamp,
            updated_at=timestamp,
        )


@dataclass(frozen=True, slots=True)
class NormalizationStatus:
    state: ProcessingState
    error: dict[str, str] | None = None
    retryable: bool = False

    @classmethod
    def failed(cls, *, code: str, message: str, retryable: bool) -> "NormalizationStatus":
        return cls(
            state=ProcessingState.FAILED,
            error={"code": code, "message": message},
            retryable=retryable,
        )


@dataclass(frozen=True, slots=True)
class NormalizedRecord:
    id: UUID
    raw_record_id: UUID
    normalizer_version: str
    status: NormalizationStatus
    normalized_data: dict[str, Any]
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)


@dataclass(frozen=True, slots=True)
class ProcessingRun:
    id: UUID
    run_type: str
    state: ProcessingState
    started_at: datetime
    finished_at: datetime | None = None
    component_versions: dict[str, str] = field(default_factory=dict)
    received_count: int = 0
    processed_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    sanitized_error: dict[str, str] | None = None

    def __post_init__(self) -> None:
        _require_aware(self.started_at, "started_at")
        if self.finished_at is not None:
            _require_aware(self.finished_at, "finished_at")
        counters = (
            self.received_count,
            self.processed_count,
            self.skipped_count,
            self.failed_count,
        )
        if any(count < 0 for count in counters):
            raise ValueError("processing counters must be non-negative")
