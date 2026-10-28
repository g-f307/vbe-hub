from datetime import date
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "technical-sheet-v1"
MAX_EVIDENCE_EXCERPT_CHARS = 240


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TemporalPrecision(StrEnum):
    EXACT = "exact"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    APPROXIMATE = "approximate"
    UNKNOWN = "unknown"


class GeographicPrecision(StrEnum):
    COUNTRY = "country"
    STATE = "state"
    MUNICIPALITY = "municipality"
    DISTRICT = "district"
    SPECIFIC = "specific"
    UNKNOWN = "unknown"


class SuggestedRelevance(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class TemporalInformation(StrictModel):
    start: date | None
    end: date | None
    precision: TemporalPrecision


class LocationInformation(StrictModel):
    country: str | None
    state: str | None
    municipality: str | None
    district: str | None
    specific: str | None
    precision: GeographicPrecision


class TechnicalSheetEvidence(StrictModel):
    field: str = Field(min_length=1, max_length=80)
    excerpt: str = Field(min_length=1, max_length=MAX_EVIDENCE_EXCERPT_CHARS)


class TechnicalSheet(StrictModel):
    record_nature: Literal["media", "community"] | None
    disease_or_condition: str | None
    pathogen: str | None
    syndrome: str | None
    symptoms: list[str]
    estimated_cases: Annotated[int, Field(ge=0)] | None
    estimated_deaths: Annotated[int, Field(ge=0)] | None
    affected_group: str | None
    environment: str | None
    temporal: TemporalInformation
    location: LocationInformation
    action_in_progress: str | None
    suggested_relevance: SuggestedRelevance | None
    confidence: Annotated[float, Field(ge=0, le=1)] | None
    evidence: list[TechnicalSheetEvidence]


def validate_grounded_sheet(payload: dict[str, Any], *, source_text: str) -> TechnicalSheet:
    sheet = TechnicalSheet.model_validate(payload)
    evidence_fields = {item.field for item in sheet.evidence}

    for item in sheet.evidence:
        if item.excerpt not in source_text:
            raise ValueError(f"evidence for {item.field} must be a literal excerpt of source text")

    for field_name in _populated_fields(sheet):
        if field_name not in evidence_fields:
            raise ValueError(f"{field_name} requires evidence")

    return sheet


def repair_ungrounded_fields(
    payload: dict[str, Any], *, source_text: str
) -> tuple[TechnicalSheet, tuple[str, ...]]:
    """Drop unsupported fields while preserving the valid, grounded remainder.

    Schema-invalid payloads still fail closed. This repair only handles grounding failures and
    never invents or rewrites model output.
    """

    sheet = TechnicalSheet.model_validate(payload)
    grounded_evidence = [item for item in sheet.evidence if item.excerpt in source_text]
    grounded_fields = {item.field for item in grounded_evidence}
    repaired = sheet.model_dump(mode="python")
    repaired["evidence"] = [item.model_dump(mode="python") for item in grounded_evidence]

    repaired_fields = tuple(sorted(_populated_fields(sheet).difference(grounded_fields)))
    for field_name in repaired_fields:
        if field_name == "symptoms":
            repaired["symptoms"] = []
        elif field_name.startswith("temporal."):
            repaired["temporal"][field_name.removeprefix("temporal.")] = None
        elif field_name.startswith("location."):
            repaired["location"][field_name.removeprefix("location.")] = None
        else:
            repaired[field_name] = None

    return validate_grounded_sheet(repaired, source_text=source_text), repaired_fields


def _populated_fields(sheet: TechnicalSheet) -> set[str]:
    populated: set[str] = set()
    direct_fields = (
        "record_nature",
        "disease_or_condition",
        "pathogen",
        "syndrome",
        "estimated_cases",
        "estimated_deaths",
        "affected_group",
        "environment",
        "action_in_progress",
        "suggested_relevance",
        "confidence",
    )
    populated.update(name for name in direct_fields if getattr(sheet, name) is not None)
    if sheet.symptoms:
        populated.add("symptoms")
    for name in ("start", "end"):
        if getattr(sheet.temporal, name) is not None:
            populated.add(f"temporal.{name}")
    for name in ("country", "state", "municipality", "district", "specific"):
        if getattr(sheet.location, name) is not None:
            populated.add(f"location.{name}")
    return populated
