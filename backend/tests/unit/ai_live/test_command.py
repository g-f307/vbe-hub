import json
from types import SimpleNamespace

import pytest

from vbe_hub.ai_live.__main__ import run_live
from vbe_hub.application.ai import ProviderError, ProviderErrorCode
from vbe_hub.infrastructure.settings import Settings


class NeverCalledFactory:
    def __init__(self) -> None:
        self.called = False

    def __call__(self, **_: object) -> object:
        self.called = True
        raise AssertionError("network client must not be created")


class StubModels:
    async def generate_content(self, **_: object) -> object:
        payload = json.loads(
            """{
              "record_nature": null,
              "disease_or_condition": null,
              "pathogen": null,
              "syndrome": null,
              "symptoms": [],
              "estimated_cases": null,
              "estimated_deaths": null,
              "affected_group": null,
              "environment": null,
              "temporal": {"start": null, "end": null, "precision": "unknown"},
              "location": {"country": null, "state": null, "municipality": null,
                "district": null, "specific": null, "precision": "unknown"},
              "action_in_progress": null,
              "suggested_relevance": null,
              "confidence": null,
              "evidence": []
            }"""
        )
        return SimpleNamespace(
            parsed=payload,
            usage_metadata=SimpleNamespace(prompt_token_count=30, candidates_token_count=20),
        )


class StubAsyncClient:
    def __init__(self) -> None:
        self.models = StubModels()

    async def __aenter__(self) -> "StubAsyncClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        return None


class StubRootClient:
    aio = StubAsyncClient()


def settings(**overrides: object) -> Settings:
    return Settings(
        DATABASE_URL="postgresql://unit:unit@not-used:5432/unit",
        REDIS_URL="redis://not-used:6379/0",
        _env_file=None,
        **overrides,
    )


async def test_missing_api_key_fails_before_client_or_network() -> None:
    factory = NeverCalledFactory()

    with pytest.raises(ProviderError) as captured:
        await run_live(settings(), client_factory=factory)

    assert captured.value.code is ProviderErrorCode.CONFIGURATION
    assert str(captured.value) == "GEMINI_API_KEY is required for the opt-in live command."
    assert factory.called is False


async def test_live_command_uses_only_bundled_synthetic_input_and_returns_summary() -> None:
    captured: dict[str, object] = {}

    def factory(**kwargs: object) -> StubRootClient:
        captured.update(kwargs)
        return StubRootClient()

    summary = await run_live(settings(GEMINI_API_KEY="test-key"), client_factory=factory)

    assert captured["api_key"] == "test-key"
    assert summary["provider"] == "gemini"
    assert summary["model"] == "gemini-3.5-flash-lite"
    assert summary["input_units"] == 30
    assert summary["output_units"] == 20
    assert summary["technical_sheet"]["record_nature"] is None
    assert "input" not in summary
    assert "api_key" not in summary
