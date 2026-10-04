from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from vbe_hub.adapters.persistence.priority_models import SuggestedPriorityModel
from vbe_hub.application.correlation.priority import (
    PriorityComponent,
    SuggestedPriority,
    TriageBand,
)


class SqlAlchemyPriorityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, priority: SuggestedPriority) -> None:
        statement = (
            insert(SuggestedPriorityModel)
            .values(
                id=priority.id,
                identity_key=priority.identity_key,
                policy_version=priority.policy_version,
                configuration_hash=priority.configuration_hash,
                configuration=dict(priority.configuration),
                signal_id=priority.signal_id,
                signal_identity_key=priority.signal_identity_key,
                signal_policy_version=priority.signal_policy_version,
                evaluated_at=priority.evaluated_at,
                score=priority.score,
                band=priority.band.value,
                confidence=priority.confidence,
                components={
                    name: {
                        "value": item.value,
                        "weight": item.weight,
                        "contribution": item.contribution,
                        "explanation": item.explanation,
                        "facts": dict(item.facts),
                        "origin_ids": [str(value) for value in item.origin_ids],
                        "relation_ids": [str(value) for value in item.relation_ids],
                    }
                    for name, item in priority.components.items()
                },
                gaps=list(priority.gaps),
                created_at=datetime.now(UTC),
            )
            .on_conflict_do_nothing(index_elements=["identity_key"])
        )
        await self._session.execute(statement)
        await self._session.flush()

    async def get(self, priority_id: UUID) -> SuggestedPriority | None:
        row = await self._session.get(SuggestedPriorityModel, priority_id)
        return None if row is None else self._to_domain(row)

    async def list_by_signal(self, signal_id: UUID) -> list[SuggestedPriority]:
        rows = list(
            (
                await self._session.scalars(
                    select(SuggestedPriorityModel)
                    .where(SuggestedPriorityModel.signal_id == signal_id)
                    .order_by(
                        SuggestedPriorityModel.evaluated_at,
                        SuggestedPriorityModel.policy_version,
                    )
                )
            ).all()
        )
        return [self._to_domain(row) for row in rows]

    @staticmethod
    def _to_domain(row: SuggestedPriorityModel) -> SuggestedPriority:
        return SuggestedPriority(
            id=row.id,
            identity_key=row.identity_key,
            policy_version=row.policy_version,
            configuration_hash=row.configuration_hash,
            configuration=row.configuration,
            signal_id=row.signal_id,
            signal_identity_key=row.signal_identity_key,
            signal_policy_version=row.signal_policy_version,
            evaluated_at=row.evaluated_at,
            score=row.score,
            band=TriageBand(row.band),
            confidence=row.confidence,
            components={
                name: PriorityComponent(
                    value=item["value"],
                    weight=item["weight"],
                    contribution=item["contribution"],
                    explanation=item["explanation"],
                    facts=item["facts"],
                    origin_ids=tuple(UUID(value) for value in item["origin_ids"]),
                    relation_ids=tuple(UUID(value) for value in item["relation_ids"]),
                )
                for name, item in row.components.items()
            },
            gaps=tuple(row.gaps),
        )
