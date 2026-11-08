from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class IndividualSignal:
    id: UUID
    normalized_record_id: UUID
    contract_version: str
    created_at: datetime


@dataclass(frozen=True)
class InvestigationFile:
    id: UUID
    version: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class InvestigationMember:
    id: UUID
    investigation_file_id: UUID
    signal_id: UUID
    added_at: datetime
    added_by: str
    removed_at: datetime | None = None
    removed_by: str | None = None
    removal_reason: str | None = None


@dataclass(frozen=True)
class InvestigationMembershipEvent:
    id: UUID
    operation_key: str
    operation_fingerprint: str
    investigation_file_id: UUID
    signal_id: UUID
    sequence: int
    action: str
    actor_id: str
    occurred_at: datetime
    reason_code: str | None


class InvestigationConcurrencyConflict(Exception):
    def __init__(self, expected_version: int, current_version: int) -> None:
        self.expected_version = expected_version
        self.current_version = current_version
        super().__init__(
            f"expected investigation version {expected_version}, found {current_version}"
        )


class InvestigationOperationConflict(Exception):
    pass


class LastInvestigationMemberError(Exception):
    pass


class InvestigationMemberNotFound(Exception):
    pass
