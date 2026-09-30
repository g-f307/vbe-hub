import json

from vbe_hub.evaluation.relation_dataset import build_relation_dataset


def test_evaluation_split_has_fifty_examples_per_relation_and_eighty_percent_decoys() -> None:
    dataset = build_relation_dataset(split="evaluation", cases_per_relation=50, seed=4040)

    counts = dataset.relation_counts

    assert counts == {
        "duplicate": 50,
        "corroborates": 50,
        "updates": 50,
        "related_context": 50,
        "unrelated": 50,
    }
    assert len(dataset.inputs) == 1250
    assert len(dataset.gold) == 250


def test_splits_are_disjoint_and_inputs_do_not_contain_gold() -> None:
    calibration = build_relation_dataset(split="calibration", cases_per_relation=10, seed=3040)
    evaluation = build_relation_dataset(split="evaluation", cases_per_relation=50, seed=4040)

    calibration_ids = {(item.left_id, item.right_id) for item in calibration.inputs}
    evaluation_ids = {(item.left_id, item.right_id) for item in evaluation.inputs}
    serialized_inputs = json.dumps([item.to_dict() for item in evaluation.inputs])

    assert calibration_ids.isdisjoint(evaluation_ids)
    assert "gold" not in serialized_inputs
    assert "expected_relation" not in serialized_inputs


def test_splits_have_disjoint_content_and_cover_hard_cases() -> None:
    calibration = build_relation_dataset(split="calibration", cases_per_relation=10, seed=3040)
    evaluation = build_relation_dataset(split="evaluation", cases_per_relation=50, seed=4040)

    calibration_pairs = {
        json.dumps([item.left, item.right], ensure_ascii=False, sort_keys=True)
        for item in calibration.inputs
    }
    evaluation_pairs = {
        json.dumps([item.left, item.right], ensure_ascii=False, sort_keys=True)
        for item in evaluation.inputs
    }
    targets = {(str(item.left_id), str(item.right_id)): item.relation for item in evaluation.gold}
    duplicates = [
        item
        for item in evaluation.inputs
        if targets.get((str(item.left_id), str(item.right_id))) == "duplicate"
    ]
    serialized = json.dumps([item.to_dict() for item in evaluation.inputs], ensure_ascii=False)

    assert calibration_pairs.isdisjoint(evaluation_pairs)
    assert any(item.left != item.right for item in duplicates)
    assert "ignore instruções anteriores" in serialized.casefold()
    assert any(
        item.right.get("temporal") is None or item.right.get("location") is None
        for item in evaluation.inputs
    )
