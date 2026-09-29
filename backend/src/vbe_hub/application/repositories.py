from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from vbe_hub.domain.records import NormalizedRecord, ProcessingRun, Provenance, RawRecord


@dataclass(frozen=True, slots=True)
class StoredRawRecord:
    record: RawRecord
    provenance: Provenance


@dataclass(frozen=True, slots=True)
class IngestResult:
    record: RawRecord
    created: bool


class RawRecordRepository(Protocol):
    async def add(self, record: RawRecord, provenance: Provenance) -> IngestResult: ...

    async def get(self, record_id: UUID) -> StoredRawRecord | None: ...

    async def save_normalized(self, record: NormalizedRecord) -> None: ...

    async def get_normalized(
        self, raw_record_id: UUID, normalizer_version: str
    ) -> NormalizedRecord | None: ...


class ProcessingRunRepository(Protocol):
    async def add(self, run: ProcessingRun) -> None: ...

    async def get(self, run_id: UUID) -> ProcessingRun | None: ...
