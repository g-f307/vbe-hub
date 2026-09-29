from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from vbe_hub.domain.records import RawRecord, SourceKind
from vbe_hub.normalization.errors import NormalizationError

_PRECISION_ALIASES = {
    "country": "country",
    "state": "state",
    "municipality": "municipality",
    "district": "district",
    "neighborhood": "district",
    "specific": "specific",
    "exact": "specific",
}


def _optional_text(payload: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if value is None or value == "":
            continue
        if not isinstance(value, str):
            raise NormalizationError(f"{key} must be text or null")
        return value.strip() or None
    return None


def _non_negative_integer(payload: dict[str, Any], key: str) -> int | None:
    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise NormalizationError(f"{key} must be a non-negative integer or null")
    return value


def _symptoms(payload: dict[str, Any]) -> list[str]:
    value = payload.get("symptoms")
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise NormalizationError("symptoms must be a list of text values or null")
    return [item.strip() for item in value if item.strip()]


def _language(value: str) -> str:
    parts = value.replace("_", "-").split("-")
    if len(parts) == 1:
        return parts[0].lower()
    return f"{parts[0].lower()}-{parts[1].upper()}"


def _timestamp(payload: dict[str, Any], key: str) -> str | None:
    raw_value = payload.get(key)
    if raw_value is None or raw_value == "":
        return None
    if not isinstance(raw_value, str):
        raise NormalizationError(f"{key} must be an ISO 8601 timestamp or null")
    try:
        value = datetime.fromisoformat(raw_value)
    except ValueError as error:
        raise NormalizationError(f"{key} must be an ISO 8601 timestamp or null") from error
    if value.tzinfo is None or value.utcoffset() is None:
        raise NormalizationError(f"{key} must include timezone information")
    return value.astimezone(UTC).isoformat()


def _precision(payload: dict[str, Any]) -> str | None:
    value = payload.get("geographic_precision")
    if value is None or value == "" or value == "unknown":
        return None
    if not isinstance(value, str) or value not in _PRECISION_ALIASES:
        raise NormalizationError("geographic_precision is not supported")
    return _PRECISION_ALIASES[value]


class _BaseNormalizer:
    district_keys: tuple[str, ...]
    source_kind: SourceKind

    def normalize(self, record: RawRecord) -> dict[str, Any]:
        if record.source_kind is not self.source_kind:
            raise NormalizationError(
                f"source kind {record.source_kind.value} is not supported by this adapter"
            )
        payload = record.original_payload
        return {
            "source_kind": record.source_kind.value,
            "source_name": record.source_name,
            "external_id": record.external_id,
            "published_at": record.published_at.astimezone(UTC).isoformat(),
            "language": _language(record.language),
            "title": record.title,
            "text": record.body,
            "location": {
                "country": _optional_text(payload, "country"),
                "state": _optional_text(payload, "state"),
                "municipality": _optional_text(payload, "municipality"),
                "district": _optional_text(payload, *self.district_keys),
                "specific": _optional_text(payload, "specific_location", "location"),
                "precision": _precision(payload),
            },
            "magnitude": {
                "estimated_cases": _non_negative_integer(payload, "estimated_cases"),
                "estimated_deaths": _non_negative_integer(payload, "estimated_deaths"),
            },
            "symptoms": _symptoms(payload),
            "affected_group": _optional_text(payload, "affected_group"),
            "environment": _optional_text(payload, "environment"),
            "metadata": {
                "source_url": record.source_url,
                "reported_window_start": _timestamp(payload, "report_window_start"),
                "reported_window_end": _timestamp(payload, "report_window_end"),
                "topic": _optional_text(payload, "topic"),
            },
        }


class MediaNormalizer(_BaseNormalizer):
    district_keys = ("district", "neighborhood")
    source_kind = SourceKind.MEDIA


class CommunityNormalizer(_BaseNormalizer):
    district_keys = ("neighborhood", "district")
    source_kind = SourceKind.COMMUNITY
