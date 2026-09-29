from vbe_hub.application.ai.embeddings import build_embedding_text


def test_representation_is_deterministic_and_excludes_audit_metadata() -> None:
    sheet = {
        "disease_or_condition": "Sarampo",
        "symptoms": ["febre", "manchas vermelhas"],
        "estimated_cases": 12,
        "temporal": {"start": "2026-03-10", "precision": "day"},
        "location": {"municipality": "Manaus", "district": "Centro"},
        "confidence": 0.91,
        "evidence": [{"field": "symptoms", "excerpt": "febre"}],
    }

    text = build_embedding_text(sheet)

    assert text == (
        "doenca_agravo: Sarampo\n"
        "sintomas: febre; manchas vermelhas\n"
        "casos_estimados: 12\n"
        "inicio_evento: 2026-03-10\n"
        "municipio: Manaus\n"
        "bairro_distrito: Centro"
    )
    assert "confidence" not in text
    assert "evidence" not in text


def test_representation_rejects_sheet_without_semantic_content() -> None:
    try:
        build_embedding_text({"confidence": 0.5, "evidence": []})
    except ValueError as error:
        assert str(error) == "technical sheet has no semantic content to embed"
    else:
        raise AssertionError("empty semantic representation must fail")
