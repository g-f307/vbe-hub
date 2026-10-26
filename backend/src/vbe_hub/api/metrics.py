from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from vbe_hub.adapters.persistence.models import (
    NormalizedRecordModel,
    ProcessingRunModel,
    ProvenanceModel,
    RawRecordModel,
    TechnicalSheetExtractionModel,
)
from vbe_hub.adapters.persistence.priority_models import SuggestedPriorityModel
from vbe_hub.adapters.persistence.relation_models import RelationAssessmentModel
from vbe_hub.adapters.persistence.signal_models import ConsolidatedSignalModel
from vbe_hub.adapters.persistence.workflow_models import ReviewEventModel, SignalWorkflowModel
from vbe_hub.api.signals import get_signal_read_session

router = APIRouter(prefix="/metrics", tags=["metrics"])

MetricsSession = Annotated[AsyncSession, Depends(get_signal_read_session)]
_STALE_AFTER_SECONDS = 7 * 24 * 60 * 60


class DatasetSourceResponse(BaseModel):
    generator: str
    version: str
    seed: int | None
    records: int


class DatasetResponse(BaseModel):
    kind: Literal["synthetic"]
    status: Literal["unavailable", "single", "mixed"]
    sources: list[DatasetSourceResponse]


class MetricsWindowResponse(BaseModel):
    start: datetime | None
    end: datetime | None
    latest_activity_at: datetime | None
    lag_seconds: int | None
    freshness: Literal["unavailable", "current", "stale"]


class MetricResponse(BaseModel):
    value: int
    status: Literal["empty", "available"]
    origin: str


class DurationResponse(BaseModel):
    status: Literal["unavailable", "available"]
    samples: int
    average_ms: int | None
    maximum_ms: int | None


class ProcessingRunResponse(BaseModel):
    id: str
    type: str
    state: str
    started_at: datetime
    finished_at: datetime | None
    duration_ms: int | None
    received: int
    processed: int
    skipped: int
    failed: int
    component_versions: dict[str, str]


class LatestRunResponse(BaseModel):
    status: Literal["unavailable", "available"]
    run: ProcessingRunResponse | None


class ReconciliationResponse(BaseModel):
    key: str
    status: Literal["unavailable", "balanced", "gap", "excess"]
    expected: int
    observed: int
    difference: int


class EvaluationResponse(BaseModel):
    identity: str
    classification: Literal["synthetic_evaluation"]
    kind: str
    dataset_version: str
    evaluated_on: str
    status: str
    evidence_level: str
    artifact: str
    metrics: dict[str, int | float | None]
    limitation: str
    scope: str


class MetricsSummaryResponse(BaseModel):
    contract_version: Literal["metrics-summary-v1"]
    classification: Literal["technical_operational"]
    operational_status: Literal["empty", "ok", "partial_failure"]
    calculated_at: datetime
    interpretation: str
    dataset: DatasetResponse
    window: MetricsWindowResponse
    pipeline: dict[str, MetricResponse]
    durations: dict[str, DurationResponse]
    latest_run: LatestRunResponse
    reconciliation: list[ReconciliationResponse]
    evaluations: list[EvaluationResponse]

_EVALUATIONS: tuple[dict[str, Any], ...] = (
    {
        "identity": "3260ec0dc1945093",
        "classification": "synthetic_evaluation",
        "kind": "technical_sheet",
        "dataset_version": "technical-sheet-eval-v1",
        "evaluated_on": "2026-09-29",
        "status": "block",
        "evidence_level": "exploratory",
        "artifact": "docs/technical-sheet-baseline-2026-09-29.md",
        "metrics": {
            "attempted": 4,
            "succeeded": 3,
            "failed": 1,
            "operational_failure_rate": 0.25,
            "symptoms_f1": 0.666667,
            "estimated_cost_usd": None,
        },
        "limitation": "small synthetic sample; provider usage is a lower bound",
        "scope": "technical synthetic extraction validation; no clinical validity",
    },
    {
        "identity": "ce77f037927356db",
        "classification": "synthetic_evaluation",
        "kind": "relation",
        "dataset_version": "relation-evaluation-v3",
        "evaluated_on": "2026-09-30",
        "status": "approve_with_caveats",
        "evidence_level": "exploratory",
        "artifact": "docs/correlation-evaluation.md",
        "metrics": {
            "candidate_recall": 1.0,
            "pair_reduction": 0.804,
            "macro_f1": 1.0,
            "operational_failure_rate": 0.0,
            "provider_calls": 44,
            "estimated_cost_usd": None,
        },
        "limitation": "small synthetic sample; limited statistical generalization",
        "scope": "technical synthetic validation; no clinical or epidemiological validity",
    },
    {
        "identity": "a23f1eb5c9300765",
        "classification": "synthetic_evaluation",
        "kind": "grouping",
        "dataset_version": "grouping-evaluation-v2",
        "evaluated_on": "2026-10-07",
        "status": "approve_with_caveats",
        "evidence_level": "expanded_synthetic",
        "artifact": "docs/grouping-evaluation.md",
        "metrics": {
            "records": 270,
            "events": 60,
            "automatic_pairwise_f1": 0.983607,
            "reviewed_pairwise_f1": 1.0,
            "automatic_merges": 1,
            "reviewed_merges": 0,
        },
        "limitation": "synthetic frozen relation inputs; validates grouping only",
        "scope": "technical synthetic grouping validation; no epidemiological validity",
    },
)


@router.get("/summary", response_model=MetricsSummaryResponse)
async def metrics_summary(session: MetricsSession) -> dict[str, Any]:
    counts = await _counts(session)
    dataset = await _dataset(session)
    window = await _window(session)
    durations = await _durations(session)
    latest_run = await _latest_run(session)
    persistence_status = "available" if counts["raw_records"] else "empty"
    pending_review = max(counts["signals"] - counts["closed_workflows"], 0)
    reconciliation = [
        _reconciliation(
            "normalization_coverage",
            counts["raw_records"],
            counts["normalized_succeeded_records"],
        ),
        _reconciliation(
            "extraction_coverage",
            counts["normalized_succeeded_records"],
            counts["extracted_succeeded_records"],
        ),
        _reconciliation("priority_coverage", counts["signals"], counts["prioritized_signals"]),
    ]

    pipeline = {
        "raw_records": _metric(counts["raw_records"], persistence_status, "raw_records"),
        "normalized_records": _metric(
            counts["normalized_records"], persistence_status, "normalized_records"
        ),
        "failed_normalizations": _metric(
            counts["failed_normalizations"], persistence_status, "normalized_records.state=failed"
        ),
        "technical_sheets": _metric(
            counts["technical_sheets"], persistence_status, "technical_sheet_extractions"
        ),
        "failed_extractions": _metric(
            counts["failed_extractions"],
            persistence_status,
            "technical_sheet_extractions.state=failed",
        ),
        "assessed_pairs": _metric(
            counts["assessed_pairs"], persistence_status, "relation_assessments"
        ),
        "failed_relations": _metric(
            counts["failed_relations"], persistence_status, "relation_assessments.state=failed"
        ),
        "signals": _metric(counts["signals"], persistence_status, "consolidated_signals"),
        "priorities": _metric(counts["priorities"], persistence_status, "suggested_priorities"),
        "human_reviews": _metric(counts["human_reviews"], persistence_status, "review_events"),
        "pending_human_review": _metric(
            pending_review,
            persistence_status,
            "consolidated_signals - signal_workflows.state=closed",
        ),
    }
    return {
        "contract_version": "metrics-summary-v1",
        "classification": "technical_operational",
        "operational_status": _operational_status(counts, reconciliation, latest_run),
        "calculated_at": _iso(datetime.now(UTC)),
        "interpretation": (
            "Indicadores técnicos de dados sintéticos; não representam diagnóstico, "
            "surto confirmado ou prioridade sanitária final."
        ),
        "dataset": dataset,
        "window": window,
        "pipeline": pipeline,
        "durations": durations,
        "latest_run": latest_run,
        "reconciliation": reconciliation,
        "evaluations": list(_EVALUATIONS),
    }


async def _counts(session: AsyncSession) -> dict[str, int]:
    statement = select(
        _count(RawRecordModel).label("raw_records"),
        _count(NormalizedRecordModel).label("normalized_records"),
        _count(NormalizedRecordModel, NormalizedRecordModel.state == "failed").label(
            "failed_normalizations"
        ),
        _distinct_count(
            NormalizedRecordModel,
            NormalizedRecordModel.raw_record_id,
            NormalizedRecordModel.state == "succeeded",
        ).label("normalized_succeeded_records"),
        _count(TechnicalSheetExtractionModel).label("technical_sheets"),
        _count(
            TechnicalSheetExtractionModel, TechnicalSheetExtractionModel.state == "failed"
        ).label("failed_extractions"),
        _distinct_count(
            TechnicalSheetExtractionModel,
            TechnicalSheetExtractionModel.normalized_record_id,
            TechnicalSheetExtractionModel.state == "succeeded",
        ).label("extracted_succeeded_records"),
        _count(RelationAssessmentModel).label("assessed_pairs"),
        _count(RelationAssessmentModel, RelationAssessmentModel.state == "failed").label(
            "failed_relations"
        ),
        _count(ConsolidatedSignalModel).label("signals"),
        _count(SuggestedPriorityModel).label("priorities"),
        _distinct_count(SuggestedPriorityModel, SuggestedPriorityModel.signal_id).label(
            "prioritized_signals"
        ),
        _count(ReviewEventModel).label("human_reviews"),
        _count(SignalWorkflowModel, SignalWorkflowModel.state == "closed").label(
            "closed_workflows"
        ),
    )
    row = (await session.execute(statement)).one()._mapping
    return {key: int(value or 0) for key, value in row.items()}


def _count(model: type, condition=None):
    query = select(func.count()).select_from(model)
    if condition is not None:
        query = query.where(condition)
    return query.scalar_subquery()


def _distinct_count(model: type, column, condition=None):
    query = select(func.count(func.distinct(column))).select_from(model)
    if condition is not None:
        query = query.where(condition)
    return query.scalar_subquery()


async def _dataset(session: AsyncSession) -> dict[str, Any]:
    rows = (
        await session.execute(
            select(
                ProvenanceModel.generator_name,
                ProvenanceModel.generator_version,
                ProvenanceModel.seed,
                func.count(),
            )
            .group_by(
                ProvenanceModel.generator_name,
                ProvenanceModel.generator_version,
                ProvenanceModel.seed,
            )
            .order_by(
                ProvenanceModel.generator_name,
                ProvenanceModel.generator_version,
                ProvenanceModel.seed,
            )
        )
    ).all()
    sources = [
        {
            "generator": generator or "not-recorded",
            "version": version or "not-recorded",
            "seed": seed,
            "records": int(records),
        }
        for generator, version, seed, records in rows
    ]
    status = "unavailable" if not sources else "single" if len(sources) == 1 else "mixed"
    return {"kind": "synthetic", "status": status, "sources": sources}


async def _window(session: AsyncSession) -> dict[str, Any]:
    start, end = (
        await session.execute(
            select(func.min(RawRecordModel.published_at), func.max(RawRecordModel.published_at))
        )
    ).one()
    activity = (
        await session.execute(
            select(
                _maximum(RawRecordModel, RawRecordModel.updated_at),
                _maximum(NormalizedRecordModel, NormalizedRecordModel.updated_at),
                _maximum(TechnicalSheetExtractionModel, TechnicalSheetExtractionModel.created_at),
                _maximum(RelationAssessmentModel, RelationAssessmentModel.created_at),
                _maximum(ConsolidatedSignalModel, ConsolidatedSignalModel.created_at),
                _maximum(SuggestedPriorityModel, SuggestedPriorityModel.created_at),
                _maximum(SignalWorkflowModel, SignalWorkflowModel.updated_at),
                _maximum(ReviewEventModel, ReviewEventModel.occurred_at),
            )
        )
    ).one()
    latest = max((value for value in activity if value is not None), default=None)
    if latest is None:
        lag_seconds = None
        freshness = "unavailable"
    else:
        lag_seconds = max(int((datetime.now(UTC) - latest).total_seconds()), 0)
        freshness = "stale" if lag_seconds > _STALE_AFTER_SECONDS else "current"
    return {
        "start": _iso(start),
        "end": _iso(end),
        "latest_activity_at": _iso(latest),
        "lag_seconds": lag_seconds,
        "freshness": freshness,
    }


def _maximum(model: type, column):
    return select(func.max(column)).select_from(model).scalar_subquery()


async def _durations(session: AsyncSession) -> dict[str, Any]:
    row = (
        await session.execute(
            select(
                _duration_count(TechnicalSheetExtractionModel),
                _duration_average(TechnicalSheetExtractionModel),
                _duration_maximum(TechnicalSheetExtractionModel),
                _duration_count(RelationAssessmentModel),
                _duration_average(RelationAssessmentModel),
                _duration_maximum(RelationAssessmentModel),
            )
        )
    ).one()
    return {
        "technical_sheet_extraction": _duration(row[0], row[1], row[2]),
        "relation_assessment": _duration(row[3], row[4], row[5]),
    }


def _duration_count(model: type):
    return select(func.count()).select_from(model).scalar_subquery()


def _duration_average(model: type):
    return select(func.avg(model.duration_ms)).select_from(model).scalar_subquery()


def _duration_maximum(model: type):
    return select(func.max(model.duration_ms)).select_from(model).scalar_subquery()


def _duration(samples: int, average, maximum: int | None) -> dict[str, Any]:
    count = int(samples or 0)
    return {
        "status": "available" if count else "unavailable",
        "samples": count,
        "average_ms": round(float(average)) if average is not None else None,
        "maximum_ms": int(maximum) if maximum is not None else None,
    }


async def _latest_run(session: AsyncSession) -> dict[str, Any]:
    run = await session.scalar(
        select(ProcessingRunModel).order_by(ProcessingRunModel.started_at.desc()).limit(1)
    )
    if run is None:
        return {"status": "unavailable", "run": None}
    duration_ms = (
        max(int((run.finished_at - run.started_at).total_seconds() * 1000), 0)
        if run.finished_at is not None
        else None
    )
    return {
        "status": "available",
        "run": {
            "id": str(run.id),
            "type": run.run_type,
            "state": run.state,
            "started_at": _iso(run.started_at),
            "finished_at": _iso(run.finished_at),
            "duration_ms": duration_ms,
            "received": run.received_count,
            "processed": run.processed_count,
            "skipped": run.skipped_count,
            "failed": run.failed_count,
            "component_versions": run.component_versions,
        },
    }


def _metric(value: int, status: str, origin: str) -> dict[str, int | str]:
    return {"value": value, "status": status, "origin": origin}


def _operational_status(
    counts: dict[str, int],
    reconciliation: list[dict[str, int | str]],
    latest_run: dict[str, Any],
) -> str:
    if counts["raw_records"] == 0:
        return "empty"
    stage_failures = (
        counts["failed_normalizations"]
        + counts["failed_extractions"]
        + counts["failed_relations"]
    )
    run = latest_run["run"]
    run_failed = run is not None and (run["state"] == "failed" or run["failed"] > 0)
    has_gap = any(item["status"] in {"gap", "excess"} for item in reconciliation)
    return "partial_failure" if stage_failures or run_failed or has_gap else "ok"


def _reconciliation(key: str, expected: int, observed: int) -> dict[str, int | str]:
    difference = observed - expected
    if expected == 0:
        status = "unavailable"
    elif difference == 0:
        status = "balanced"
    elif difference < 0:
        status = "gap"
    else:
        status = "excess"
    return {
        "key": key,
        "status": status,
        "expected": expected,
        "observed": observed,
        "difference": difference,
    }


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
