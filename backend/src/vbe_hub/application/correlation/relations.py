import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any, Protocol
from uuid import UUID, uuid4

from vbe_hub.application.ai import (
    AIExecutionMetadata,
    ExecutionStatus,
    ProviderError,
    RelationJudge,
    RelationKind,
    RelationRequest,
)

RELATION_RULES_VERSION = "relation-rules-v1"
RELATION_PROMPT_VERSION = "relate-v1"


class RelationMethod(StrEnum):
    RULE = "rule"
    PROVIDER = "provider"


@dataclass(frozen=True, slots=True)
class RelationAssessmentRecord:
    id: UUID
    cache_key: str
    left_id: UUID
    right_id: UUID
    relation: RelationKind | None
    method: RelationMethod
    confidence: float | None
    justification: str | None
    updating_record_id: UUID | None
    rules_version: str
    metadata: AIExecutionMetadata
    sanitized_error: str | None
    created_at: datetime


class RelationAssessmentRepository(Protocol):
    async def get(self, cache_key: str) -> RelationAssessmentRecord | None: ...
    async def save(self, record: RelationAssessmentRecord) -> None: ...


class RelationAssessmentService:
    def __init__(
        self,
        *,
        judge: RelationJudge,
        repository: RelationAssessmentRepository,
        now=lambda: datetime.now(UTC),
    ) -> None:
        self._judge, self._repository, self._now = judge, repository, now

    async def assess(
        self, *, left_id: UUID, right_id: UUID, left: Mapping[str, Any], right: Mapping[str, Any]
    ) -> RelationAssessmentRecord:
        if left_id == right_id:
            raise ValueError("relation candidates must be different records")
        if str(right_id) < str(left_id):
            left_id, right_id, left, right = right_id, left_id, right, left
        cache_key = _cache_key(left_id, right_id)
        if cached := await self._repository.get(cache_key):
            return cached
        if _comparable_sheet(left) == _comparable_sheet(right):
            record = RelationAssessmentRecord(
                id=uuid4(),
                cache_key=cache_key,
                left_id=left_id,
                right_id=right_id,
                relation=RelationKind.DUPLICATE,
                method=RelationMethod.RULE,
                confidence=1.0,
                justification="Fichas técnicas semanticamente idênticas.",
                updating_record_id=None,
                rules_version=RELATION_RULES_VERSION,
                metadata=AIExecutionMetadata(
                    provider="deterministic",
                    model=RELATION_RULES_VERSION,
                    contract_version="relation-v1",
                    prompt_version=None,
                    started_at=self._now(),
                    duration_ms=0,
                    status=ExecutionStatus.SUCCEEDED,
                ),
                sanitized_error=None,
                created_at=self._now(),
            )
            await self._repository.save(record)
            return record
        request = RelationRequest(
            left_id=left_id,
            right_id=right_id,
            left=left,
            right=right,
            prompt_version=RELATION_PROMPT_VERSION,
            trace_id=cache_key[:16],
        )
        try:
            result = await self._judge.judge(request)
        except ProviderError as error:
            metadata = error.metadata
            if metadata is None:
                raise
            failed = RelationAssessmentRecord(
                id=uuid4(),
                cache_key=cache_key,
                left_id=left_id,
                right_id=right_id,
                relation=None,
                method=RelationMethod.PROVIDER,
                confidence=None,
                justification=None,
                updating_record_id=None,
                rules_version=RELATION_RULES_VERSION,
                metadata=metadata,
                sanitized_error=str(error),
                created_at=self._now(),
            )
            await self._repository.save(failed)
            raise
        updating_id = None
        if result.relation is RelationKind.UPDATES:
            updating_id = _later_record(left_id, right_id, left, right)
            if updating_id is None:
                raise ValueError("updates relation requires distinct event dates")
        record = RelationAssessmentRecord(
            id=uuid4(),
            cache_key=cache_key,
            left_id=left_id,
            right_id=right_id,
            relation=result.relation,
            method=RelationMethod.PROVIDER,
            confidence=result.confidence,
            justification=result.justification,
            updating_record_id=updating_id,
            rules_version=RELATION_RULES_VERSION,
            metadata=result.metadata,
            sanitized_error=None,
            created_at=self._now(),
        )
        await self._repository.save(record)
        return record


def _cache_key(left_id: UUID, right_id: UUID) -> str:
    value = f"{left_id}:{right_id}:{RELATION_RULES_VERSION}:{RELATION_PROMPT_VERSION}"
    return hashlib.sha256(value.encode()).hexdigest()


def _comparable_sheet(sheet: Mapping[str, Any]) -> str:
    excluded = {"confidence", "evidence", "suggested_relevance"}
    return json.dumps(
        {k: v for k, v in sheet.items() if k not in excluded},
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )


def _later_record(
    left_id: UUID, right_id: UUID, left: Mapping[str, Any], right: Mapping[str, Any]
) -> UUID | None:
    left_date, right_date = _start_date(left), _start_date(right)
    if left_date is None or right_date is None or left_date == right_date:
        return None
    return right_id if right_date > left_date else left_id


def _start_date(sheet: Mapping[str, Any]) -> date | None:
    temporal = sheet.get("temporal")
    value = temporal.get("start") if isinstance(temporal, Mapping) else None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None
