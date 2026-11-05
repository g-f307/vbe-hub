from datetime import UTC, datetime

from vbe_hub.application.ai import (
    AIExecutionMetadata,
    ExecutionStatus,
    StructuredExtractionResult,
)
from vbe_hub.evaluation.command import run_evaluation


class RepairingExtractor:
    async def extract(self, request):
        return StructuredExtractionResult(
            technical_sheet={},
            evidence=(),
            grounding_repaired_fields=("record_nature", "suggested_relevance"),
            metadata=AIExecutionMetadata(
                provider="test",
                model="test-model",
                contract_version=request.schema_version,
                prompt_version=request.prompt_version,
                started_at=datetime(2026, 10, 28, tzinfo=UTC),
                duration_ms=10,
                status=ExecutionStatus.SUCCEEDED,
                input_units=5,
                output_units=3,
            ),
        )


async def test_evaluation_reports_grounding_repairs_without_source_content(tmp_path) -> None:
    report = await run_evaluation(
        split="calibration",
        extractor=RepairingExtractor(),
        provider="test",
        model="test-model",
        output_directory=tmp_path,
    )

    assert report["execution"]["grounding_repairs"] == {
        "records": 4,
        "fields": 8,
        "by_field": {"record_nature": 4, "suggested_relevance": 4},
    }
    assert "normalized_data" not in str(report)
