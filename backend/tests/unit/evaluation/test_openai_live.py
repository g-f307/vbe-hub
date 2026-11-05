import importlib
from types import SimpleNamespace

import pytest
from pydantic import SecretStr


def test_live_command_requires_openai_key_without_exposing_a_value() -> None:
    module = importlib.import_module("vbe_hub.evaluation.openai_live")

    with pytest.raises(SystemExit, match="OPENAI_API_KEY is required") as captured:
        module.require_openai_api_key(SimpleNamespace(openai_api_key=None))

    assert "sk-" not in str(captured.value)


def test_live_command_unwraps_configured_key_only_at_provider_boundary() -> None:
    module = importlib.import_module("vbe_hub.evaluation.openai_live")

    key = module.require_openai_api_key(
        SimpleNamespace(openai_api_key=SecretStr("synthetic-openai-key"))
    )

    assert key == "synthetic-openai-key"
