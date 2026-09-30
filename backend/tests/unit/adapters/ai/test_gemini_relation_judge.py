from datetime import UTC, datetime
from uuid import UUID

import pytest

from vbe_hub.adapters.ai.gemini import GeminiClientResponse
from vbe_hub.adapters.ai.gemini_relations import GeminiRelationJudge
from vbe_hub.application.ai import ProviderError, RelationKind, RelationRequest

NOW = datetime(2026, 9, 30, 12, tzinfo=UTC)


class Client:
    def __init__(self, payload):
        self.payload = payload
        self.request = None

    async def generate(self, request):
        self.request = request
        return GeminiClientResponse(payload=self.payload, input_tokens=20, output_tokens=8)


def request():
    return RelationRequest(
        left_id=UUID("00000000-0000-0000-0000-000000000012"),
        right_id=UUID("00000000-0000-0000-0000-000000000013"),
        left={"disease_or_condition": "Sarampo"},
        right={"symptoms": ["febre"]},
        prompt_version="relate-v1",
        trace_id="trace-12-13",
    )


async def test_judge_fences_records_and_validates_structured_relation() -> None:
    client = Client(
        {
            "relation": "corroborates",
            "justification": "Fontes independentes convergem.",
            "confidence": 0.87,
        }
    )
    judge = GeminiRelationJudge(
        client=client,
        model="gemini-test",
        timeout_seconds=10,
        max_input_chars=4000,
        now=lambda: NOW,
    )

    result = await judge.judge(request())

    assert result.relation is RelationKind.CORROBORATES
    assert result.metadata.input_units == 20
    assert "UNTRUSTED_PAIR_START" in client.request.contents
    assert client.request.tools == ()


async def test_judge_rejects_invalid_relation_without_persistable_result() -> None:
    judge = GeminiRelationJudge(
        client=Client({"relation": "same_outbreak", "justification": "inválida", "confidence": 1}),
        model="gemini-test",
        timeout_seconds=10,
        max_input_chars=4000,
        now=lambda: NOW,
    )
    with pytest.raises(ProviderError, match="invalid relation response"):
        await judge.judge(request())
