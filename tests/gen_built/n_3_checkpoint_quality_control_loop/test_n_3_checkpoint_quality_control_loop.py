import copy

from n_3_checkpoint_quality_control_loop import (
    PSN_CheckpointQualityTagger,
    PSN_CheckpointRegistryLookup,
    PSN_CheckpointBestPicker,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def test_module_mappings():
    assert "PSN_CheckpointQualityTagger" in NODE_CLASS_MAPPINGS
    assert "PSN_CheckpointRegistryLookup" in NODE_CLASS_MAPPINGS
    assert "PSN_CheckpointBestPicker" in NODE_CLASS_MAPPINGS
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_CheckpointQualityTagger"] == "Checkpoint Quality Tagger"


def test_input_types_shape():
    it = PSN_CheckpointQualityTagger.INPUT_TYPES()
    assert "checkpoint_name" in it["required"]
    assert "quality_score" in it["required"]
    assert "tags" in it["required"]
    assert PSN_CheckpointQualityTagger.RETURN_TYPES == ("CHECKPOINT_REGISTRY",)
    assert PSN_CheckpointQualityTagger.FUNCTION == "run"
    assert PSN_CheckpointQualityTagger.CATEGORY.startswith("ParametricStudio/")


def test_tag_new_checkpoint():
    node = PSN_CheckpointQualityTagger()
    (reg,) = node.run("ckpt_a", 0.8, "high-detail,fast")
    assert reg["checkpoints"]["ckpt_a"]["quality_score"] == 0.8
    assert reg["checkpoints"]["ckpt_a"]["tags"] == ["high-detail", "fast"]


def test_tag_updates_existing_and_keeps_history():
    node = PSN_CheckpointQualityTagger()
    (reg1,) = node.run("ckpt_b", 0.4, "fast")
    (reg2,) = node.run("ckpt_b", 0.9, "fast,sharp", registry=reg1)
    entry = reg2["checkpoints"]["ckpt_b"]
    assert entry["quality_score"] == 0.9
    assert entry["history"] == [0.4]
    # tags merged without duplicates
    assert entry["tags"] == ["fast", "sharp"]
    # original registry not mutated
    assert reg1["checkpoints"]["ckpt_b"]["quality_score"] == 0.4


def test_bad_score_rejected():
    node = PSN_CheckpointQualityTagger()
    try:
        node.run("x", 1.5, "")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for score > 1")
    try:
        node.run("x", -0.1, "")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for score < 0")
    try:
        node.run("x", "0.5", "")
    except TypeError:
        pass
    else:
        raise AssertionError("expected TypeError for non-numeric score")


def test_empty_name_rejected():
    node = PSN_CheckpointQualityTagger()
    try:
        node.run("   ", 0.5, "")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for blank name")


def test_lookup_found_and_missing():
    tagger = PSN_CheckpointQualityTagger()
    (reg,) = tagger.run("m1", 0.7, "a, b")
    lookup = PSN_CheckpointRegistryLookup()
    score, tags, found = lookup.run("m1", reg)
    assert found is True
    assert score == 0.7
    assert tags == "a,b"
    score2, tags2, found2 = lookup.run("nope", reg)
    assert found2 is False
    assert score2 == 0.0
    assert tags2 == ""


def test_best_picker():
    tagger = PSN_CheckpointQualityTagger()
    reg = None
    for name, s in [("a", 0.2), ("b", 0.9), ("c", 0.5)]:
        (reg,) = tagger.run(name, s, "", registry=reg)
    picker = PSN_CheckpointBestPicker()
    best, score, has = picker.run(reg)
    assert has is True
    assert best == "b"
    assert score == 0.9
    empty = {"checkpoints": {}}
    best2, score2, has2 = picker.run(empty)
    assert has2 is False
    assert best2 == ""
    assert score2 == 0.0


def test_bad_registry_type():
    lookup = PSN_CheckpointRegistryLookup()
    try:
        lookup.run("x", [1, 2, 3])
    except TypeError:
        pass
    else:
        raise AssertionError("expected TypeError for non-dict registry")
    try:
        lookup.run("x", {"wrong": 1})
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for registry missing checkpoints")


def main():
    test_module_mappings()
    test_input_types_shape()
    test_tag_new_checkpoint()
    test_tag_updates_existing_and_keeps_history()
    test_bad_score_rejected()
    test_empty_name_rejected()
    test_lookup_found_and_missing()
    test_best_picker()
    test_bad_registry_type()
    print("ok")


if __name__ == "__main__":
    main()
