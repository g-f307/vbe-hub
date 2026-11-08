from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from vbe_hub.application.ai import ProviderError
from vbe_hub.application.correlation.candidates import (
    CandidateInput,
    CandidatePolicy,
    CandidateSelector,
)


@dataclass(frozen=True, slots=True)
class PreparedSignal:
    signal_id: UUID
    normalized_record_id: UUID
    technical_sheet: Mapping[str, Any]
    semantic_score: float


@dataclass(frozen=True, slots=True)
class PrecomputationResult:
    considered: int
    submitted: int
    ready: int
    failed: int


class PreparedSignalSource(Protocol):
    async def anchor(self, signal_id: UUID) -> PreparedSignal | None: ...

    async def nearest(
        self, anchor: PreparedSignal, limit: int
    ) -> Sequence[PreparedSignal]: ...


class SuggestionRepository(Protocol):
    async def mark_pending(
        self, left: UUID, right: UUID, contract_version: str
    ) -> None: ...

    async def mark_ready(
        self,
        left: UUID,
        right: UUID,
        contract_version: str,
        assessment_id: UUID,
    ) -> None: ...

    async def mark_failed(
        self, left: UUID, right: UUID, contract_version: str, error_code: str
    ) -> None: ...


class RelationAssessor(Protocol):
    async def assess(
        self,
        *,
        left_id: UUID,
        right_id: UUID,
        left: Mapping[str, Any],
        right: Mapping[str, Any],
    ) -> Any: ...


class RelatedSignalPrecomputer:
    """Bounded preselection followed by auditable relation assessments."""

    def __init__(
        self,
        *,
        source: PreparedSignalSource,
        suggestions: SuggestionRepository,
        assessor: RelationAssessor,
        policy: CandidatePolicy,
        neighbor_limit: int,
        candidate_limit: int,
        contract_version: str,
    ) -> None:
        if neighbor_limit <= 0:
            raise ValueError("neighbor_limit must be positive")
        if candidate_limit <= 0 or candidate_limit > neighbor_limit:
            raise ValueError("candidate_limit must be positive and not exceed neighbor_limit")
        if not contract_version.strip():
            raise ValueError("contract_version must not be empty")
        self._source = source
        self._suggestions = suggestions
        self._assessor = assessor
        self._selector = CandidateSelector(policy)
        self._neighbor_limit = neighbor_limit
        self._candidate_limit = candidate_limit
        self._contract_version = contract_version

    async def process(self, signal_id: UUID) -> PrecomputationResult:
        anchor = await self._source.anchor(signal_id)
        if anchor is None:
            return PrecomputationResult(considered=0, submitted=0, ready=0, failed=0)
        neighbors = tuple(await self._source.nearest(anchor, self._neighbor_limit))
        by_record = {item.normalized_record_id: item for item in neighbors}
        selection = self._selector.select(
            anchor_id=anchor.normalized_record_id,
            anchor_sheet=anchor.technical_sheet,
            neighbors=tuple(
                CandidateInput(item.normalized_record_id, item.semantic_score, item.technical_sheet)
                for item in neighbors
            ),
        )
        ready = failed = 0
        selected = selection.included[: self._candidate_limit]
        for decision in selected:
            candidate = by_record[decision.normalized_record_id]
            left, right = sorted((anchor.signal_id, candidate.signal_id))
            await self._suggestions.mark_pending(left, right, self._contract_version)
            try:
                assessment = await self._assessor.assess(
                    left_id=anchor.normalized_record_id,
                    right_id=candidate.normalized_record_id,
                    left=anchor.technical_sheet,
                    right=candidate.technical_sheet,
                )
            except ProviderError as error:
                await self._suggestions.mark_failed(
                    left, right, self._contract_version, error.code.value
                )
                failed += 1
                continue
            await self._suggestions.mark_ready(
                left, right, self._contract_version, assessment.id
            )
            ready += 1
        return PrecomputationResult(
            considered=len(selection.decisions),
            submitted=len(selected),
            ready=ready,
            failed=failed,
        )
