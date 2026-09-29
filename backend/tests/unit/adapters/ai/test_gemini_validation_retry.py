import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from vbe_hub.adapters.ai.gemini import GeminiClientResponse, GeminiStructuredExtractor
from vbe_hub.application.ai import StructuredExtractionRequest


class SequencedClient:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.calls = 0

    async def generate(self, request):
        payload = self.payloads[self.calls]
        self.calls += 1
        return GeminiClientResponse(payload=payload, input_tokens=10, output_tokens=10)


async def test_invalid_grounding_is_retried_before_returning_success() -> None:
    valid = json.loads(
        Path("tests/fixtures/ai/technical-sheet/v1/success.json").read_text(encoding="utf-8")
    )
    invalid = json.loads(json.dumps(valid))
    invalid["evidence"][0]["excerpt"] = "not present"
    client = SequencedClient([invalid, valid])
    text = (
        "Relato sintético: moradores do bairro Flores apresentam febre e manchas vermelhas. "
        "A investigação epidemiológica está em andamento."
    )
    extractor = GeminiStructuredExtractor(
        client=client,
        model="test-model",
        timeout_seconds=5,
        max_attempts=2,
        max_input_chars=4_000,
        max_output_tokens=1_024,
        now=lambda: datetime(2026, 9, 29, tzinfo=UTC),
        monotonic_values=iter([1.0, 1.1]),
    )

    result = await extractor.extract(
        StructuredExtractionRequest(
            record_id=UUID("00000000-0000-0000-0000-000000000008"),
            input_hash="8" * 64,
            normalized_data={"source_kind": "community", "text": text},
            schema_version="technical-sheet-v1",
            prompt_version="extract-v2",
            trace_id="retry-validation",
        )
    )

    assert result.technical_sheet["record_nature"] == "community"
    assert client.calls == 2
    assert result.metadata.input_units == 20
    assert result.metadata.output_units == 20
