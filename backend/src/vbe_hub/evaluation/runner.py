from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from vbe_hub.application.ai import (
    AIExecutionMetadata,
    StructuredExtractionRequest,
    StructuredExtractor,
)
from vbe_hub.application.ai.technical_sheet import SCHEMA_VERSION


@dataclass(frozen=True, slots=True)
class EvaluationInput:
    record_id: str
    normalized_data: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class EvaluationPrediction:
    record_id: str
    technical_sheet: Mapping[str, Any]
    metadata: AIExecutionMetadata


async def extract_predictions(
    records: list[EvaluationInput],
    *,
    extractor: StructuredExtractor,
    prompt_version: str = "extract-v1",
) -> list[EvaluationPrediction]:
    predictions: list[EvaluationPrediction] = []
    for record in records:
        canonical = json.dumps(
            record.normalized_data, ensure_ascii=False, separators=(",", ":"), sort_keys=True
        ).encode()
        result = await extractor.extract(
            StructuredExtractionRequest(
                record_id=UUID(record.record_id),
                input_hash=hashlib.sha256(canonical).hexdigest(),
                normalized_data=record.normalized_data,
                schema_version=SCHEMA_VERSION,
                prompt_version=prompt_version,
                trace_id=f"technical-sheet-evaluation:{record.record_id}",
            )
        )
        predictions.append(
            EvaluationPrediction(
                record_id=record.record_id,
                technical_sheet=result.technical_sheet,
                metadata=result.metadata,
            )
        )
    return predictions
