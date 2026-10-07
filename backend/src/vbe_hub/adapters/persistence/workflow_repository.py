from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from vbe_hub.adapters.persistence.priority_models import SuggestedPriorityModel
from vbe_hub.adapters.persistence.relation_models import RelationAssessmentModel
from vbe_hub.adapters.persistence.signal_models import (
    ConsolidatedSignalModel,
    SignalMemberModel,
    SignalRelationLinkModel,
)
from vbe_hub.adapters.persistence.workflow_models import (
    ReviewEventModel,
    SignalWorkflowModel,
)
from vbe_hub.application.workflow import (
    ConcurrencyConflict,
    ReviewEvent,
    ReviewTargetType,
    SignalWorkflow,
    WorkflowNotFound,
    WorkflowState,
)


class SqlAlchemyWorkflowRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(self, signal_id: UUID) -> SignalWorkflow:
        row = await self._session.get(SignalWorkflowModel, signal_id)
        if row is not None:
            return self._workflow(row)
        if await self._session.get(ConsolidatedSignalModel, signal_id) is None:
            raise WorkflowNotFound(signal_id)
        await self._session.execute(
            insert(SignalWorkflowModel)
            .values(
                signal_id=signal_id,
                state=WorkflowState.DETECTED.value,
                version=0,
                state_machine_version="workflow-v1",
                updated_at=datetime.now(UTC),
            )
            .on_conflict_do_nothing(index_elements=["signal_id"])
        )
        await self._session.flush()
        row = await self._session.get(SignalWorkflowModel, signal_id)
        if row is None:
            raise WorkflowNotFound(signal_id)
        return self._workflow(row)

    async def get_event_by_operation(self, operation_key: str) -> ReviewEvent | None:
        row = await self._session.scalar(
            select(ReviewEventModel).where(ReviewEventModel.operation_key == operation_key)
        )
        return None if row is None else self._event(row)

    async def get_latest_decision(
        self,
        signal_id: UUID,
        target_type: ReviewTargetType,
        target_id: UUID,
    ) -> ReviewEvent | None:
        row = await self._session.scalar(
            select(ReviewEventModel)
            .where(
                ReviewEventModel.signal_id == signal_id,
                ReviewEventModel.target_type == target_type.value,
                ReviewEventModel.target_id == target_id,
            )
            .order_by(ReviewEventModel.sequence.desc())
            .limit(1)
        )
        return None if row is None else self._event(row)

    async def review_target_exists(
        self,
        signal_id: UUID,
        target_type: ReviewTargetType,
        target_id: UUID,
        suggestion_identity_key: str,
    ) -> bool:
        if target_type is ReviewTargetType.GROUPING:
            return bool(
                target_id == signal_id
                and await self._session.scalar(
                    select(ConsolidatedSignalModel.id).where(
                        ConsolidatedSignalModel.id == signal_id,
                        ConsolidatedSignalModel.identity_key == suggestion_identity_key,
                    )
                )
            )
        if target_type is ReviewTargetType.PRIORITY:
            return bool(
                await self._session.scalar(
                    select(SuggestedPriorityModel.id).where(
                        SuggestedPriorityModel.id == target_id,
                        SuggestedPriorityModel.signal_id == signal_id,
                        SuggestedPriorityModel.identity_key == suggestion_identity_key,
                    )
                )
            )
        if target_type is ReviewTargetType.RELATION:
            return bool(
                await self._session.scalar(
                    select(SignalRelationLinkModel.relation_assessment_id)
                    .join(
                        RelationAssessmentModel,
                        RelationAssessmentModel.id
                        == SignalRelationLinkModel.relation_assessment_id,
                    )
                    .where(
                        SignalRelationLinkModel.signal_id == signal_id,
                        SignalRelationLinkModel.relation_assessment_id == target_id,
                        RelationAssessmentModel.cache_key == suggestion_identity_key,
                    )
                )
            )
        return bool(
            await self._session.scalar(
                select(SignalMemberModel.normalized_record_id)
                .join(
                    ConsolidatedSignalModel,
                    ConsolidatedSignalModel.id == SignalMemberModel.signal_id,
                )
                .where(
                    SignalMemberModel.signal_id == signal_id,
                    SignalMemberModel.normalized_record_id == target_id,
                    ConsolidatedSignalModel.identity_key == suggestion_identity_key,
                )
            )
        )

    async def append(
        self,
        *,
        event: ReviewEvent,
        expected_version: int,
        next_state: WorkflowState,
    ) -> SignalWorkflow:
        row = (
            await self._session.execute(
                update(SignalWorkflowModel)
                .where(
                    SignalWorkflowModel.signal_id == event.signal_id,
                    SignalWorkflowModel.version == expected_version,
                )
                .values(
                    state=next_state.value,
                    version=expected_version + 1,
                    updated_at=event.occurred_at,
                )
                .returning(SignalWorkflowModel)
            )
        ).scalar_one_or_none()
        if row is None:
            current = await self._session.get(SignalWorkflowModel, event.signal_id)
            raise ConcurrencyConflict(
                expected_version,
                current.version if current is not None else -1,
            )
        await self._session.execute(
            insert(ReviewEventModel).values(
                id=event.id,
                operation_key=event.operation_key,
                operation_fingerprint=event.operation_fingerprint,
                signal_id=event.signal_id,
                sequence=event.sequence,
                workflow_version=event.workflow_version,
                workflow_state=event.workflow_state.value,
                state_machine_version=event.state_machine_version,
                actor_id=event.actor_id,
                occurred_at=event.occurred_at,
                action=event.action,
                target_type=event.target_type.value if event.target_type else None,
                target_id=event.target_id,
                previous_value=dict(event.previous_value),
                new_value=dict(event.new_value),
                reason_code=event.reason_code,
                comment=event.comment,
            )
        )
        await self._session.flush()
        return self._workflow(row)

    async def list_events(self, signal_id: UUID) -> list[ReviewEvent]:
        rows = list(
            (
                await self._session.scalars(
                    select(ReviewEventModel)
                    .where(ReviewEventModel.signal_id == signal_id)
                    .order_by(ReviewEventModel.sequence)
                )
            ).all()
        )
        return [self._event(row) for row in rows]

    @staticmethod
    def _workflow(row: SignalWorkflowModel) -> SignalWorkflow:
        return SignalWorkflow(
            signal_id=row.signal_id,
            state=WorkflowState(row.state),
            version=row.version,
            state_machine_version=row.state_machine_version,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _event(row: ReviewEventModel) -> ReviewEvent:
        return ReviewEvent(
            id=row.id,
            operation_key=row.operation_key,
            operation_fingerprint=row.operation_fingerprint,
            signal_id=row.signal_id,
            sequence=row.sequence,
            workflow_version=row.workflow_version,
            workflow_state=WorkflowState(row.workflow_state),
            state_machine_version=row.state_machine_version,
            actor_id=row.actor_id,
            occurred_at=row.occurred_at,
            action=row.action,
            target_type=ReviewTargetType(row.target_type) if row.target_type else None,
            target_id=row.target_id,
            previous_value=row.previous_value,
            new_value=row.new_value,
            reason_code=row.reason_code,
            comment=row.comment,
        )
