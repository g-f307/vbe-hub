from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID, uuid5

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from vbe_hub.adapters.persistence.signal_models import (
    ConsolidatedSignalModel,
    SignalGroupingConflictModel,
    SignalMemberModel,
    SignalRelationLinkModel,
)
from vbe_hub.application.correlation.signals import (
    ConsolidatedSignal,
    ConsolidationConflict,
    ConsolidationResult,
    FieldValue,
    MagnitudeObservation,
)

_CONFLICT_NAMESPACE = UUID("f9da2aa7-411b-4c77-a420-457770869ee1")


class SqlAlchemySignalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, result: ConsolidationResult) -> None:
        now = datetime.now(UTC)
        for signal in result.signals:
            values = self._signal_values(signal, now)
            statement = (
                insert(ConsolidatedSignalModel)
                .values(**values)
                .on_conflict_do_update(
                    index_elements=["identity_key"],
                    set_={key: value for key, value in values.items() if key != "id"},
                )
            )
            await self._session.execute(statement)
            context_relation_id = next(
                (
                    relation_id
                    for relation_id, role in signal.relation_roles.items()
                    if role == "context"
                ),
                None,
            )
            for record_id in signal.core_record_ids:
                await self._save_member(signal.id, record_id, "core", None)
            for record_id in signal.context_record_ids:
                await self._save_member(
                    signal.id,
                    record_id,
                    "context",
                    context_relation_id,
                )
            for relation_id in signal.relation_ids:
                await self._save_relation_link(
                    signal.id,
                    relation_id,
                    signal.relation_roles[relation_id],
                )

        policy_versions = {item.policy_version for item in result.signals}
        if len(policy_versions) > 1:
            raise ValueError("a consolidation result must use one policy version")
        policy_version = next(iter(policy_versions), None)
        if policy_version is not None:
            for conflict in result.conflicts:
                await self._save_conflict(policy_version, conflict, now)
        await self._session.flush()

    async def get(self, signal_id: UUID) -> ConsolidatedSignal | None:
        row = await self._session.get(ConsolidatedSignalModel, signal_id)
        return None if row is None else await self._to_signal(row)

    async def list_by_policy(self, policy_version: str) -> list[ConsolidatedSignal]:
        rows = list(
            (
                await self._session.scalars(
                    select(ConsolidatedSignalModel)
                    .where(ConsolidatedSignalModel.policy_version == policy_version)
                    .order_by(ConsolidatedSignalModel.id)
                )
            ).all()
        )
        return [await self._to_signal(row) for row in rows]

    async def list_conflicts(self, policy_version: str) -> list[ConsolidationConflict]:
        rows = list(
            (
                await self._session.scalars(
                    select(SignalGroupingConflictModel)
                    .where(SignalGroupingConflictModel.policy_version == policy_version)
                    .order_by(
                        SignalGroupingConflictModel.relation_assessment_id,
                        SignalGroupingConflictModel.code,
                    )
                )
            ).all()
        )
        return [
            ConsolidationConflict(
                relation_id=row.relation_assessment_id,
                left_id=row.left_record_id,
                right_id=row.right_record_id,
                code=row.code,
                details=row.details,
            )
            for row in rows
        ]

    async def _save_member(
        self,
        signal_id: UUID,
        record_id: UUID,
        role: str,
        joined_by_relation_id: UUID | None,
    ) -> None:
        values = {
            "signal_id": signal_id,
            "normalized_record_id": record_id,
            "role": role,
            "joined_by_relation_id": joined_by_relation_id,
        }
        statement = (
            insert(SignalMemberModel)
            .values(**values)
            .on_conflict_do_update(
                index_elements=["signal_id", "normalized_record_id"],
                set_={
                    "role": role,
                    "joined_by_relation_id": joined_by_relation_id,
                },
            )
        )
        await self._session.execute(statement)

    async def _save_relation_link(
        self, signal_id: UUID, relation_id: UUID, role: str
    ) -> None:
        statement = (
            insert(SignalRelationLinkModel)
            .values(
                signal_id=signal_id,
                relation_assessment_id=relation_id,
                role=role,
            )
            .on_conflict_do_update(
                index_elements=["signal_id", "relation_assessment_id"],
                set_={"role": role},
            )
        )
        await self._session.execute(statement)

    async def _save_conflict(
        self,
        policy_version: str,
        conflict: ConsolidationConflict,
        created_at: datetime,
    ) -> None:
        conflict_id = uuid5(
            _CONFLICT_NAMESPACE,
            f"{policy_version}:{conflict.relation_id}:{conflict.code}",
        )
        values = {
            "id": conflict_id,
            "policy_version": policy_version,
            "relation_assessment_id": conflict.relation_id,
            "left_record_id": conflict.left_id,
            "right_record_id": conflict.right_id,
            "code": conflict.code,
            "details": dict(conflict.details),
            "created_at": created_at,
        }
        statement = (
            insert(SignalGroupingConflictModel)
            .values(**values)
            .on_conflict_do_update(
                index_elements=[
                    "policy_version",
                    "relation_assessment_id",
                    "code",
                ],
                set_={
                    "left_record_id": conflict.left_id,
                    "right_record_id": conflict.right_id,
                    "details": dict(conflict.details),
                },
            )
        )
        await self._session.execute(statement)

    async def _to_signal(self, row: ConsolidatedSignalModel) -> ConsolidatedSignal:
        members = list(
            (
                await self._session.scalars(
                    select(SignalMemberModel)
                    .where(SignalMemberModel.signal_id == row.id)
                    .order_by(SignalMemberModel.normalized_record_id)
                )
            ).all()
        )
        links = list(
            (
                await self._session.scalars(
                    select(SignalRelationLinkModel)
                    .where(SignalRelationLinkModel.signal_id == row.id)
                    .order_by(SignalRelationLinkModel.relation_assessment_id)
                )
            ).all()
        )
        core = tuple(item.normalized_record_id for item in members if item.role == "core")
        context = tuple(item.normalized_record_id for item in members if item.role == "context")
        relation_ids = tuple(item.relation_assessment_id for item in links)
        return ConsolidatedSignal(
            id=row.id,
            identity_key=row.identity_key,
            policy_version=row.policy_version,
            processing_state=row.processing_state,
            title=row.title,
            summary=row.summary,
            core_record_ids=core,
            context_record_ids=context,
            relation_ids=relation_ids,
            relation_roles={item.relation_assessment_id: item.role for item in links},
            period_start=row.period_start,
            period_end=row.period_end,
            location=row.location,
            conditions=tuple(row.conditions),
            symptoms=tuple(row.symptoms),
            magnitude_history=tuple(
                MagnitudeObservation(
                    record_id=UUID(item["record_id"]),
                    observed_at=(
                        date.fromisoformat(item["observed_at"])
                        if item["observed_at"] is not None
                        else None
                    ),
                    estimated_cases=item["estimated_cases"],
                    estimated_deaths=item["estimated_deaths"],
                )
                for item in row.magnitude_history
            ),
            current_estimated_cases=row.current_estimated_cases,
            field_provenance={
                field_name: tuple(
                    FieldValue(
                        value=item["value"],
                        record_ids=tuple(UUID(value) for value in item["record_ids"]),
                    )
                    for item in entries
                )
                for field_name, entries in row.field_provenance.items()
            },
            divergence_codes=tuple(row.divergence_codes),
        )

    @staticmethod
    def _signal_values(signal: ConsolidatedSignal, created_at: datetime) -> dict:
        return {
            "id": signal.id,
            "identity_key": signal.identity_key,
            "policy_version": signal.policy_version,
            "processing_state": signal.processing_state,
            "title": signal.title,
            "summary": signal.summary,
            "period_start": signal.period_start,
            "period_end": signal.period_end,
            "location": dict(signal.location),
            "conditions": list(signal.conditions),
            "symptoms": list(signal.symptoms),
            "magnitude_history": [
                {
                    "record_id": str(item.record_id),
                    "observed_at": (
                        item.observed_at.isoformat() if item.observed_at is not None else None
                    ),
                    "estimated_cases": item.estimated_cases,
                    "estimated_deaths": item.estimated_deaths,
                }
                for item in signal.magnitude_history
            ],
            "current_estimated_cases": signal.current_estimated_cases,
            "field_provenance": {
                field_name: [
                    {
                        "value": item.value,
                        "record_ids": [str(value) for value in item.record_ids],
                    }
                    for item in entries
                ]
                for field_name, entries in signal.field_provenance.items()
            },
            "divergence_codes": list(signal.divergence_codes),
            "created_at": created_at,
        }
