from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from vbe_hub.adapters.persistence.investigation_models import (
    IndividualSignalModel,
    InvestigationFileMemberModel,
    InvestigationFileModel,
    InvestigationMembershipEventModel,
    SignalRelationSuggestionModel,
)
from vbe_hub.application.correlation.precompute import SignalRelationSuggestion
from vbe_hub.domain.investigations import (
    IndividualSignal,
    InvestigationConcurrencyConflict,
    InvestigationFile,
    InvestigationMember,
    InvestigationMemberNotFound,
    InvestigationMembershipEvent,
    InvestigationOperationConflict,
    LastInvestigationMemberError,
)


class SqlAlchemyInvestigationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create_signal(
        self,
        normalized_record_id: UUID,
        contract_version: str,
        created_at: datetime,
    ) -> IndividualSignal:
        proposed_id = uuid4()
        await self._session.execute(
            insert(IndividualSignalModel)
            .values(
                id=proposed_id,
                normalized_record_id=normalized_record_id,
                contract_version=contract_version,
                created_at=created_at,
            )
            .on_conflict_do_nothing(index_elements=["normalized_record_id", "contract_version"])
        )
        row = await self._session.scalar(
            select(IndividualSignalModel).where(
                IndividualSignalModel.normalized_record_id == normalized_record_id,
                IndividualSignalModel.contract_version == contract_version,
            )
        )
        if row is None:  # pragma: no cover - guarded by the insert/FK transaction
            raise RuntimeError("individual signal was not persisted")
        return self._signal(row)

    async def get_signal(self, signal_id: UUID) -> IndividualSignal | None:
        row = await self._session.get(IndividualSignalModel, signal_id)
        return None if row is None else self._signal(row)

    async def create_file(
        self,
        signal_id: UUID,
        actor_id: str,
        operation_key: str,
        occurred_at: datetime,
    ) -> InvestigationFile:
        fingerprint = self._fingerprint("add", signal_id, actor_id, None, None)
        replay = await self._replay(operation_key, fingerprint)
        if replay is not None:
            return replay

        file_id = uuid4()
        file_row = InvestigationFileModel(
            id=file_id,
            version=1,
            created_at=occurred_at,
            updated_at=occurred_at,
        )
        self._session.add(file_row)
        await self._session.flush()
        self._session.add(
            InvestigationFileMemberModel(
                id=uuid4(),
                investigation_file_id=file_id,
                signal_id=signal_id,
                added_at=occurred_at,
                added_by=actor_id,
                removed_at=None,
                removed_by=None,
                removal_reason=None,
            )
        )
        self._session.add(
            self._event_row(
                file_id=file_id,
                signal_id=signal_id,
                operation_key=operation_key,
                fingerprint=fingerprint,
                sequence=1,
                action="add",
                actor_id=actor_id,
                occurred_at=occurred_at,
                previous_value={},
                new_value={"active": True},
                reason_code=None,
            )
        )
        await self._session.flush()
        return self._file(file_row)

    async def add_member(
        self,
        investigation_file_id: UUID,
        signal_id: UUID,
        actor_id: str,
        operation_key: str,
        expected_version: int,
        occurred_at: datetime,
    ) -> InvestigationFile:
        return await self._append(
            investigation_file_id=investigation_file_id,
            signal_id=signal_id,
            actor_id=actor_id,
            operation_key=operation_key,
            expected_version=expected_version,
            occurred_at=occurred_at,
            action="add",
            reason_code=None,
        )

    async def reject_suggestion(
        self,
        investigation_file_id: UUID,
        signal_id: UUID,
        actor_id: str,
        operation_key: str,
        expected_version: int,
        occurred_at: datetime,
        reason_code: str,
    ) -> InvestigationFile:
        return await self._append(
            investigation_file_id=investigation_file_id,
            signal_id=signal_id,
            actor_id=actor_id,
            operation_key=operation_key,
            expected_version=expected_version,
            occurred_at=occurred_at,
            action="reject",
            reason_code=reason_code,
        )

    async def remove_member(
        self,
        investigation_file_id: UUID,
        signal_id: UUID,
        actor_id: str,
        operation_key: str,
        expected_version: int,
        occurred_at: datetime,
        reason_code: str,
    ) -> InvestigationFile:
        fingerprint = self._fingerprint(
            "remove", signal_id, actor_id, reason_code, investigation_file_id
        )
        replay = await self._replay(operation_key, fingerprint)
        if replay is not None:
            return replay
        active_member = await self._session.scalar(
            select(InvestigationFileMemberModel.id).where(
                InvestigationFileMemberModel.investigation_file_id == investigation_file_id,
                InvestigationFileMemberModel.signal_id == signal_id,
                InvestigationFileMemberModel.removed_at.is_(None),
            )
        )
        if active_member is None:
            raise InvestigationMemberNotFound(signal_id)
        active_count = await self._session.scalar(
            select(func.count())
            .select_from(InvestigationFileMemberModel)
            .where(
                InvestigationFileMemberModel.investigation_file_id == investigation_file_id,
                InvestigationFileMemberModel.removed_at.is_(None),
            )
        )
        if active_count is None or active_count <= 1:
            raise LastInvestigationMemberError("an investigation file cannot be empty")
        return await self._append(
            investigation_file_id=investigation_file_id,
            signal_id=signal_id,
            actor_id=actor_id,
            operation_key=operation_key,
            expected_version=expected_version,
            occurred_at=occurred_at,
            action="remove",
            reason_code=reason_code,
        )

    async def transfer_member(
        self,
        source_file_id: UUID,
        destination_file_id: UUID,
        signal_id: UUID,
        actor_id: str,
        operation_key: str,
        source_expected_version: int,
        destination_expected_version: int,
        occurred_at: datetime,
        reason_code: str,
    ) -> tuple[InvestigationFile, InvestigationFile]:
        """Move one signal between files in the caller's database transaction."""
        source = await self.remove_member(
            source_file_id,
            signal_id,
            actor_id,
            f"{operation_key}:remove",
            source_expected_version,
            occurred_at,
            reason_code,
        )
        destination = await self.add_member(
            destination_file_id,
            signal_id,
            actor_id,
            f"{operation_key}:add",
            destination_expected_version,
            occurred_at,
        )
        return source, destination

    async def list_active_members(self, investigation_file_id: UUID) -> list[InvestigationMember]:
        rows = list(
            (
                await self._session.scalars(
                    select(InvestigationFileMemberModel)
                    .where(
                        InvestigationFileMemberModel.investigation_file_id == investigation_file_id,
                        InvestigationFileMemberModel.removed_at.is_(None),
                    )
                    .order_by(
                        InvestigationFileMemberModel.added_at,
                        InvestigationFileMemberModel.id,
                    )
                )
            ).all()
        )
        return [self._member(row) for row in rows]

    async def list_events(self, investigation_file_id: UUID) -> list[InvestigationMembershipEvent]:
        rows = list(
            (
                await self._session.scalars(
                    select(InvestigationMembershipEventModel)
                    .where(
                        InvestigationMembershipEventModel.investigation_file_id
                        == investigation_file_id
                    )
                    .order_by(InvestigationMembershipEventModel.sequence)
                )
            ).all()
        )
        return [self._event(row) for row in rows]

    async def _append(
        self,
        *,
        investigation_file_id: UUID,
        signal_id: UUID,
        actor_id: str,
        operation_key: str,
        expected_version: int,
        occurred_at: datetime,
        action: str,
        reason_code: str | None,
    ) -> InvestigationFile:
        fingerprint = self._fingerprint(
            action, signal_id, actor_id, reason_code, investigation_file_id
        )
        replay = await self._replay(operation_key, fingerprint)
        if replay is not None:
            return replay

        next_version = expected_version + 1
        file_row = (
            await self._session.execute(
                update(InvestigationFileModel)
                .where(
                    InvestigationFileModel.id == investigation_file_id,
                    InvestigationFileModel.version == expected_version,
                )
                .values(version=next_version, updated_at=occurred_at)
                .returning(InvestigationFileModel)
            )
        ).scalar_one_or_none()
        if file_row is None:
            current = await self._session.get(InvestigationFileModel, investigation_file_id)
            raise InvestigationConcurrencyConflict(
                expected_version, -1 if current is None else current.version
            )

        if action == "add":
            self._session.add(
                InvestigationFileMemberModel(
                    id=uuid4(),
                    investigation_file_id=investigation_file_id,
                    signal_id=signal_id,
                    added_at=occurred_at,
                    added_by=actor_id,
                    removed_at=None,
                    removed_by=None,
                    removal_reason=None,
                )
            )
            previous_value, new_value = {}, {"active": True}
        elif action == "remove":
            await self._session.execute(
                update(InvestigationFileMemberModel)
                .where(
                    InvestigationFileMemberModel.investigation_file_id == investigation_file_id,
                    InvestigationFileMemberModel.signal_id == signal_id,
                    InvestigationFileMemberModel.removed_at.is_(None),
                )
                .values(
                    removed_at=occurred_at,
                    removed_by=actor_id,
                    removal_reason=reason_code,
                )
            )
            previous_value, new_value = {"active": True}, {"active": False}
        else:
            previous_value, new_value = {}, {"rejected": True}

        self._session.add(
            self._event_row(
                file_id=investigation_file_id,
                signal_id=signal_id,
                operation_key=operation_key,
                fingerprint=fingerprint,
                sequence=next_version,
                action=action,
                actor_id=actor_id,
                occurred_at=occurred_at,
                previous_value=previous_value,
                new_value=new_value,
                reason_code=reason_code,
            )
        )
        await self._session.flush()
        return self._file(file_row)

    async def _replay(self, operation_key: str, fingerprint: str) -> InvestigationFile | None:
        event = await self._session.scalar(
            select(InvestigationMembershipEventModel).where(
                InvestigationMembershipEventModel.operation_key == operation_key
            )
        )
        if event is None:
            return None
        if event.operation_fingerprint != fingerprint:
            raise InvestigationOperationConflict(operation_key)
        row = await self._session.get(InvestigationFileModel, event.investigation_file_id)
        return None if row is None else self._file(row)

    @staticmethod
    def _fingerprint(
        action: str,
        signal_id: UUID,
        actor_id: str,
        reason_code: str | None,
        investigation_file_id: UUID | None,
    ) -> str:
        payload = json.dumps(
            {
                "action": action,
                "signal_id": str(signal_id),
                "actor_id": actor_id,
                "reason_code": reason_code,
                "investigation_file_id": (
                    str(investigation_file_id) if investigation_file_id else None
                ),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    @staticmethod
    def _event_row(**values) -> InvestigationMembershipEventModel:
        values["investigation_file_id"] = values.pop("file_id")
        values["operation_fingerprint"] = values.pop("fingerprint")
        return InvestigationMembershipEventModel(
            id=uuid4(), file_version=values["sequence"], **values
        )

    @staticmethod
    def _signal(row: IndividualSignalModel) -> IndividualSignal:
        return IndividualSignal(
            id=row.id,
            normalized_record_id=row.normalized_record_id,
            contract_version=row.contract_version,
            created_at=row.created_at,
        )

    @staticmethod
    def _file(row: InvestigationFileModel) -> InvestigationFile:
        return InvestigationFile(row.id, row.version, row.created_at, row.updated_at)

    @staticmethod
    def _member(row: InvestigationFileMemberModel) -> InvestigationMember:
        return InvestigationMember(
            row.id,
            row.investigation_file_id,
            row.signal_id,
            row.added_at,
            row.added_by,
            row.removed_at,
            row.removed_by,
            row.removal_reason,
        )

    @staticmethod
    def _event(row: InvestigationMembershipEventModel) -> InvestigationMembershipEvent:
        return InvestigationMembershipEvent(
            row.id,
            row.operation_key,
            row.operation_fingerprint,
            row.investigation_file_id,
            row.signal_id,
            row.sequence,
            row.action,
            row.actor_id,
            row.occurred_at,
            row.reason_code,
        )


class SqlAlchemySignalSuggestionRepository:
    def __init__(
        self, session: AsyncSession, *, now: Callable[[], datetime] = datetime.now
    ) -> None:
        self._session = session
        self._now = now

    async def mark_pending(self, left: UUID, right: UUID, contract_version: str) -> None:
        left, right = sorted((left, right))
        timestamp = self._now()
        values = {
            "id": uuid4(),
            "left_signal_id": left,
            "right_signal_id": right,
            "relation_assessment_id": None,
            "status": "pending",
            "contract_version": contract_version,
            "error_code": None,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        await self._session.execute(
            insert(SignalRelationSuggestionModel)
            .values(**values)
            .on_conflict_do_update(
                index_elements=["left_signal_id", "right_signal_id", "contract_version"],
                set_={
                    "relation_assessment_id": None,
                    "status": "pending",
                    "error_code": None,
                    "updated_at": timestamp,
                },
            )
        )
        await self._session.flush()

    async def mark_ready(
        self,
        left: UUID,
        right: UUID,
        contract_version: str,
        assessment_id: UUID,
    ) -> None:
        await self._set_result(
            left,
            right,
            contract_version,
            status="ready",
            assessment_id=assessment_id,
            error_code=None,
        )

    async def mark_failed(
        self, left: UUID, right: UUID, contract_version: str, error_code: str
    ) -> None:
        await self._set_result(
            left,
            right,
            contract_version,
            status="failed",
            assessment_id=None,
            error_code=error_code,
        )

    async def list_for_signal(
        self, signal_id: UUID, *, status: str = "ready"
    ) -> list[SignalRelationSuggestion]:
        rows = list(
            (
                await self._session.scalars(
                    select(SignalRelationSuggestionModel)
                    .where(
                        or_(
                            SignalRelationSuggestionModel.left_signal_id == signal_id,
                            SignalRelationSuggestionModel.right_signal_id == signal_id,
                        ),
                        SignalRelationSuggestionModel.status == status,
                    )
                    .order_by(
                        SignalRelationSuggestionModel.updated_at.desc(),
                        SignalRelationSuggestionModel.id,
                    )
                )
            ).all()
        )
        return [self._to_suggestion(row) for row in rows]

    async def _set_result(
        self,
        left: UUID,
        right: UUID,
        contract_version: str,
        *,
        status: str,
        assessment_id: UUID | None,
        error_code: str | None,
    ) -> None:
        left, right = sorted((left, right))
        result = await self._session.execute(
            update(SignalRelationSuggestionModel)
            .where(
                SignalRelationSuggestionModel.left_signal_id == left,
                SignalRelationSuggestionModel.right_signal_id == right,
                SignalRelationSuggestionModel.contract_version == contract_version,
            )
            .values(
                status=status,
                relation_assessment_id=assessment_id,
                error_code=error_code,
                updated_at=self._now(),
            )
        )
        if result.rowcount != 1:
            raise RuntimeError("relation suggestion must be pending before completion")
        await self._session.flush()

    @staticmethod
    def _to_suggestion(row: SignalRelationSuggestionModel) -> SignalRelationSuggestion:
        return SignalRelationSuggestion(
            id=row.id,
            left_signal_id=row.left_signal_id,
            right_signal_id=row.right_signal_id,
            relation_assessment_id=row.relation_assessment_id,
            status=row.status,
            contract_version=row.contract_version,
            error_code=row.error_code,
        )
