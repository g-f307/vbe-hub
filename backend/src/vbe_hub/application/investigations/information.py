"""Operational reading model; original extraction and correlation remain unchanged."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from vbe_hub.application.investigations.projection import compose_technical_sheet


class SignalInformation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confidentiality: str | None = None
    signal_type: str | None = None
    etiology: str | None = None
    hazard_general: str | None = None
    hazard_specific: str | None = None
    tags: list[str] = Field(default_factory=list)
    signal_date: str | None = None
    detected_at: datetime
    notified_at: datetime | None = None
    origins: dict[str, str] = Field(default_factory=dict)


def project_information(
    *, source_payload: dict[str, Any], technical_sheet: dict[str, Any] | None,
    detected_at: datetime,
) -> SignalInformation:
    explicit = source_payload.get("signal_information")
    source = explicit if isinstance(explicit, dict) else {}
    sheet = technical_sheet or {}
    values: dict[str, Any] = {}
    origins = {"detected_at": "provenance:collected_at"}
    fields = ("confidentiality", "signal_type", "etiology", "hazard_general", "hazard_specific")
    for field in fields:
        value = source.get(field)
        if isinstance(value, str) and 0 < len(value.strip()) <= 200:
            values[field] = value.strip()
            origins[field] = f"source:signal_information.{field}"
    if "etiology" not in values and isinstance(sheet.get("disease_or_condition"), str):
        values["etiology"] = sheet["disease_or_condition"]
        origins["etiology"] = "extraction:disease_or_condition"
    tags = source.get("tags")
    if isinstance(tags, list):
        values["tags"] = list(dict.fromkeys(
            tag.strip().casefold() for tag in tags[:50]
            if isinstance(tag, str) and 0 < len(tag.strip()) <= 80
        ))
        if values["tags"]:
            origins["tags"] = "source:signal_information.tags"
    signal_date = _date_or_timestamp(source.get("signal_date"))
    if signal_date:
        values["signal_date"] = signal_date
        origins["signal_date"] = "source:signal_information.signal_date"
    else:
        temporal = sheet.get("temporal")
        start = _date_or_timestamp(temporal.get("start")) if isinstance(temporal, dict) else None
        if start:
            values["signal_date"] = start
            origins["signal_date"] = "extraction:temporal.start"
    notified = _timestamp(source.get("notified_at"))
    if notified:
        values["notified_at"] = notified
        origins["notified_at"] = "source:signal_information.notified_at"
    return SignalInformation(**values, detected_at=detected_at, origins=origins)


def _timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or len(value) > 40 or "T" not in value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
        return parsed if parsed.tzinfo is not None else None
    except ValueError:
        return None


def _date_or_timestamp(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    if _timestamp(value):
        return value
    try:
        return date.fromisoformat(value).isoformat() if len(value) == 10 else None
    except ValueError:
        return None


@dataclass(frozen=True)
class InformationProjection:
    information: SignalInformation
    provenance: dict[str, list[str]]
    conflicts: list[dict[str, Any]]


def compose_information(
    head_id: UUID, head: SignalInformation,
    evidence: list[tuple[UUID, SignalInformation]],
) -> InformationProjection:
    shared = {"etiology", "hazard_general", "hazard_specific", "tags", "signal_date"}
    projection = compose_technical_sheet(
        head_id, head.model_dump(mode="json", exclude={"origins"}),
        [(signal_id, info.model_dump(mode="json", include=shared)) for signal_id, info in evidence],
    )
    origins = dict(head.origins)
    by_id = {str(head_id): head, **{str(key): value for key, value in evidence}}
    for field, signal_ids in projection.provenance.items():
        source = by_id[signal_ids[-1]]
        if field in source.origins:
            origins[field] = source.origins[field]
    return InformationProjection(
        SignalInformation(**projection.technical_sheet, origins=origins),
        projection.provenance, projection.conflicts,
    )
