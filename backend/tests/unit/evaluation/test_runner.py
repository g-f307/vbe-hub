from datetime import UTC, datetime

from vbe_hub.application.ai import (
    AIExecutionMetadata,
    ExecutionStatus,
    StructuredExtractionResult,
)
from vbe_hub.evaluation.runner import EvaluationInput, extract_predictions


class CapturingExtractor:
    def __init__(self) -> None:
        self.requests = []

    async def extract(self, request):
        self.requests.append(request)
        return StructuredExtractionResult(
            technical_sheet={"disease_or_condition": "sarampo"},
            evidence=(),
            metadata=AIExecutionMetadata(
                provider="test",
                model="test-model",
                contract_version="technical-sheet-v1",
                prompt_version="extract-v1",
                started_at=datetime(2026, 1, 1, tzinfo=UTC),
                duration_ms=12,
                status=ExecutionStatus.SUCCEEDED,
                input_units=10,
                output_units=5,
            ),
        )


async def test_extractor_receives_only_pipeline_input_without_gold() -> None:
    extractor = CapturingExtractor()
    records = [
        EvaluationInput(
            record_id="00000000-0000-0000-0000-000000000009",
            normalized_data={"text": "Possível sarampo em Manaus.", "synthetic": True},
        )
    ]

    predictions = await extract_predictions(records, extractor=extractor)

    assert predictions[0].technical_sheet["disease_or_condition"] == "sarampo"
    assert extractor.requests[0].normalized_data == records[0].normalized_data
    assert "gold" not in extractor.requests[0].normalized_data
    assert "expected" not in extractor.requests[0].normalized_data
