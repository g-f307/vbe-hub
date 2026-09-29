from vbe_hub.evaluation.protocol import ExperimentConfig


def test_identity_changes_when_prompt_or_reserved_dataset_changes() -> None:
    base = ExperimentConfig(
        dataset_version="technical-sheet-eval-v1",
        dataset_sha256="a" * 64,
        split="evaluation",
        seed=307,
        provider="gemini",
        model="gemini-3.5-flash-lite",
        prompt_version="extract-v1",
        schema_version="technical-sheet-v1",
        normalizer_version="1.0.0",
    )

    prompt_changed = base.model_copy(update={"prompt_version": "extract-v2"})
    dataset_changed = base.model_copy(update={"dataset_sha256": "b" * 64})

    assert base.identity != prompt_changed.identity
    assert base.identity != dataset_changed.identity
    assert prompt_changed.identity != dataset_changed.identity
