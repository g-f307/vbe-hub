from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from vbe_hub.adapters.persistence.individual_workflow_models import (
    IndividualSignalWorkflowModel,
    InvestigationWorkflowModel,
    WorkflowV2EventModel,
)
from vbe_hub.adapters.persistence.investigation_models import (
    IndividualSignalModel,
    InvestigationFileMemberModel,
    InvestigationFileModel,
)
from vbe_hub.application.individual_workflow import (
    SubjectWorkflow,
    SubjectWorkflowEvent,
    WorkflowSubjectType,
)
from vbe_hub.application.workflow import ConcurrencyConflict, WorkflowState


class SqlAlchemyIndividualWorkflowRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self, subject_type: WorkflowSubjectType, subject_id: UUID
    ) -> SubjectWorkflow | None:
        if subject_type is WorkflowSubjectType.SIGNAL:
            row = await self._session.get(IndividualSignalWorkflowModel, subject_id)
            return None if row is None else self._signal_workflow(row)
        row = await self._session.get(InvestigationWorkflowModel, subject_id)
        return None if row is None else self._investigation_workflow(row)

    async def subject_exists(self, subject_type: WorkflowSubjectType, subject_id: UUID) -> bool:
        model = (
            IndividualSignalModel
            if subject_type is WorkflowSubjectType.SIGNAL
            else InvestigationFileModel
        )
        return await self._session.get(model, subject_id) is not None

    async def members_not_in_triage(self, investigation_file_id: UUID) -> list[UUID]:
        rows = list(
            (
                await self._session.scalars(
                    select(InvestigationFileMemberModel.signal_id)
                    .join(
                        IndividualSignalWorkflowModel,
                        IndividualSignalWorkflowModel.signal_id
                        == InvestigationFileMemberModel.signal_id,
                    )
                    .where(
                        InvestigationFileMemberModel.investigation_file_id == investigation_file_id,
                        InvestigationFileMemberModel.removed_at.is_(None),
                        IndividualSignalWorkflowModel.state != WorkflowState.TRIAGE.value,
                    )
                )
            ).all()
        )
        return rows

    async def get_event(self, operation_key: str) -> SubjectWorkflowEvent | None:
        row = await self._session.scalar(
            select(WorkflowV2EventModel).where(WorkflowV2EventModel.operation_key == operation_key)
        )
        return None if row is None else self._event(row)

    async def append(
        self,
        event: SubjectWorkflowEvent,
        *,
        expected_version: int,
        initial: bool,
    ) -> SubjectWorkflow:
        if event.subject_type is WorkflowSubjectType.SIGNAL:
            result = (
                await self._session.execute(
                    update(IndividualSignalWorkflowModel)
                    .where(
                        IndividualSignalWorkflowModel.signal_id == event.subject_id,
                        IndividualSignalWorkflowModel.version == expected_version,
                    )
                    .values(
                        state=event.workflow_state.value,
                        version=event.workflow_version,
                        updated_at=event.occurred_at,
                    )
                    .returning(IndividualSignalWorkflowModel)
                )
            ).scalar_one_or_none()
            if result is None:
                current = await self._session.get(IndividualSignalWorkflowModel, event.subject_id)
                raise ConcurrencyConflict(
                    expected_version, -1 if current is None else current.version
                )
            workflow = self._signal_workflow(result)
        elif initial:
            inserted = (
                await self._session.execute(
                    insert(InvestigationWorkflowModel)
                    .values(
                        investigation_file_id=event.subject_id,
                        state=event.workflow_state.value,
                        version=event.workflow_version,
                        state_machine_version=event.state_machine_version,
                        updated_at=event.occurred_at,
                    )
                    .on_conflict_do_nothing(index_elements=["investigation_file_id"])
                    .returning(InvestigationWorkflowModel)
                )
            ).scalar_one_or_none()
            if inserted is None:
                current = await self._session.get(InvestigationWorkflowModel, event.subject_id)
                raise ConcurrencyConflict(
                    expected_version, -1 if current is None else current.version
                )
            workflow = self._investigation_workflow(inserted)
        else:
            updated = (
                await self._session.execute(
                    update(InvestigationWorkflowModel)
                    .where(
                        InvestigationWorkflowModel.investigation_file_id == event.subject_id,
                        InvestigationWorkflowModel.version == expected_version,
                    )
                    .values(
                        state=event.workflow_state.value,
                        version=event.workflow_version,
                        updated_at=event.occurred_at,
                    )
                    .returning(InvestigationWorkflowModel)
                )
            ).scalar_one_or_none()
            if updated is None:
                current = await self._session.get(InvestigationWorkflowModel, event.subject_id)
                raise ConcurrencyConflict(
                    expected_version, -1 if current is None else current.version
                )
            workflow = self._investigation_workflow(updated)
        self._session.add(
            WorkflowV2EventModel(
                id=event.id,
                operation_key=event.operation_key,
                operation_fingerprint=event.operation_fingerprint,
                subject_type=event.subject_type.value,
                signal_id=(
                    event.subject_id if event.subject_type is WorkflowSubjectType.SIGNAL else None
                ),
                investigation_file_id=(
                    event.subject_id
                    if event.subject_type is WorkflowSubjectType.INVESTIGATION
                    else None
                ),
                sequence=event.sequence,
                workflow_version=event.workflow_version,
                workflow_state=event.workflow_state.value,
                state_machine_version=event.state_machine_version,
                actor_id=event.actor_id,
                occurred_at=event.occurred_at,
                previous_value=event.previous_value,
                new_value=event.new_value,
                reason_code=event.reason_code,
                comment=event.comment,
            )
        )
        await self._session.flush()
        return workflow

    async def list_events(
        self, subject_type: WorkflowSubjectType, subject_id: UUID
    ) -> list[SubjectWorkflowEvent]:
        subject_filter = (
            WorkflowV2EventModel.signal_id == subject_id
            if subject_type is WorkflowSubjectType.SIGNAL
            else WorkflowV2EventModel.investigation_file_id == subject_id
        )
        rows = list(
            (
                await self._session.scalars(
                    select(WorkflowV2EventModel)
                    .where(subject_filter)
                    .order_by(WorkflowV2EventModel.sequence)
                )
            ).all()
        )
        return [self._event(row) for row in rows]

    @staticmethod
    def _signal_workflow(row: IndividualSignalWorkflowModel) -> SubjectWorkflow:
        return SubjectWorkflow(
            WorkflowSubjectType.SIGNAL,
            row.signal_id,
            WorkflowState(row.state),
            row.version,
            row.state_machine_version,
            row.updated_at,
        )

    @staticmethod
    def _investigation_workflow(row: InvestigationWorkflowModel) -> SubjectWorkflow:
        return SubjectWorkflow(
            WorkflowSubjectType.INVESTIGATION,
            row.investigation_file_id,
            WorkflowState(row.state),
            row.version,
            row.state_machine_version,
            row.updated_at,
        )

    @staticmethod
    def _event(row: WorkflowV2EventModel) -> SubjectWorkflowEvent:
        subject_type = WorkflowSubjectType(row.subject_type)
        subject_id = (
            row.signal_id
            if subject_type is WorkflowSubjectType.SIGNAL
            else row.investigation_file_id
        )
        assert subject_id is not None
        return SubjectWorkflowEvent(
            row.id,
            row.operation_key,
            row.operation_fingerprint,
            subject_type,
            subject_id,
            row.sequence,
            row.workflow_version,
            WorkflowState(row.workflow_state),
            row.state_machine_version,
            row.actor_id,
            row.occurred_at,
            row.previous_value,
            row.new_value,
            row.reason_code,
            row.comment,
        )
