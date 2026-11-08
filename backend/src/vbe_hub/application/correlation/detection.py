from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from vbe_hub.domain.investigations import IndividualSignal


class IndividualSignalRepository(Protocol):
    async def get_or_create_signal(
        self,
        normalized_record_id: UUID,
        contract_version: str,
        created_at: datetime,
    ) -> IndividualSignal: ...


class SignalPreparationQueue(Protocol):
    async def enqueue(self, signal_id: UUID) -> bool: ...


class IndividualSignalDetectionService:
    """Materializes one source as one signal and schedules bounded AI preparation."""

    def __init__(
        self,
        *,
        repository: IndividualSignalRepository,
        queue: SignalPreparationQueue,
        contract_version: str = "individual-signal-v1",
    ) -> None:
        if not contract_version.strip():
            raise ValueError("contract_version must not be empty")
        self._repository = repository
        self._queue = queue
        self._contract_version = contract_version

    async def detect(
        self, normalized_record_id: UUID, *, detected_at: datetime
    ) -> IndividualSignal:
        signal = await self._repository.get_or_create_signal(
            normalized_record_id,
            self._contract_version,
            detected_at,
        )
        await self._queue.enqueue(signal.id)
        return signal
