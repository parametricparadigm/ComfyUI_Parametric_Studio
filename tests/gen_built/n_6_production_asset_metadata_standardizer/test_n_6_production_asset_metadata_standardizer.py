import json

import torch

import n_6_production_asset_metadata_standardizer as mod


def make_image():
    return torch.rand(2, 4, 4, 3)


def test_inject_and_read_back():
    img = make_image()
    node = mod.PSN_MetadataInjector()
    (tagged,) = node.run(img, json.dumps({"studio_id": "PS", "shot_id": "A1", "version": "v1"}), True)
    assert isinstance(tagged, torch.Tensor)
    assert tagged.shape == img.shape
    assert tagged.metadata == {"studio_id": "PS", "shot_id": "A1", "version": "v1"}
    # input untouched
    assert not hasattr(img, "metadata") or img.metadata is None


def test_inject_preserves_when_not_overwrite():
    img = make_image()
    img.metadata = {"studio_id": "OLD", "custom": "keep"}
    node = mod.PSN_MetadataInjector()
    (tagged,) = node.run(img, json.dumps({"shot_id": "B2"}), False)
    assert tagged.metadata["studio_id"] == "OLD"
    assert tagged.metadata["custom"] == "keep"
    assert tagged.metadata["shot_id"] == "B2"
    # original dict not mutated
    assert "shot_id" not in img.metadata


def test_inject_overwrite_replaces():
    img = make_image()
    img.metadata = {"studio_id": "OLD"}
    node = mod.PSN_MetadataInjector()
    (tagged,) = node.run(img, json.dumps({"studio_id": "NEW"}), True)
    assert tagged.metadata == {"studio_id": "NEW"}


def test_validator_valid():
    img = make_image()
    img.metadata = {"studio_id": "PS", "shot_id": "A1", "version": "v1"}
    node = mod.PSN_MetadataValidator()
    is_valid, missing = node.run(img)
    assert is_valid is True
    assert missing == ""


def test_validator_missing_keys():
    img = make_image()
    img.metadata = {"studio_id": "PS"}
    node = mod.PSN_MetadataValidator()
    is_valid, missing = node.run(img)
    assert is_valid is False
    assert set(missing.split(",")) == {"shot_id", "version"}


def test_validator_empty_metadata():
    img = make_image()
    node = mod.PSN_MetadataValidator()
    is_valid, missing = node.run(img)
    assert is_valid is False
    assert set(missing.split(",")) == set(mod.REQUIRED_KEYS)


def test_bad_json_raises():
    node = mod.PSN_MetadataInjector()
    try:
        node.run(make_image(), "not json {", True)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for bad JSON")


def test_bad_asset_raises():
    node = mod.PSN_MetadataInjector()
    try:
        node.run("not a tensor", "{}", True)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for bad asset")


def test_latent_asset_supported():
    latent = {"samples": torch.rand(1, 4, 8, 8)}
    node = mod.PSN_MetadataInjector()
    (tagged,) = node.run(latent, json.dumps({"studio_id": "PS", "shot_id": "A1", "version": "v1"}), True)
    assert isinstance(tagged, dict)
    assert tagged["samples"].shape == latent["samples"].shape
    assert tagged["metadata"]["studio_id"] == "PS"
    # original latent dict not mutated
    assert "metadata" not in latent


def test_size_limit_enforced():
    node = mod.PSN_MetadataInjector()
    big = json.dumps({"k": "x" * (mod.MAX_METADATA_BYTES + 100)})
    try:
        node.run(make_image(), big, True)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for oversized metadata")


def test_mappings_present():
    assert "PSN_MetadataInjector" in mod.NODE_CLASS_MAPPINGS
    assert "PSN_MetadataValidator" in mod.NODE_CLASS_MAPPINGS
    assert mod.PSN_MetadataInjector.FUNCTION == "run"
    assert mod.PSN_MetadataInjector.CATEGORY.startswith("ParametricStudio/")
    assert mod.PSN_MetadataValidator.RETURN_TYPES == ("BOOLEAN", "STRING")


if __name__ == "__main__":
    test_inject_and_read_back()
    test_inject_preserves_when_not_overwrite()
    test_inject_overwrite_replaces()
    test_validator_valid()
    test_validator_missing_keys()
    test_validator_empty_metadata()
    test_bad_json_raises()
    test_bad_asset_raises()
    test_latent_asset_supported()
    test_size_limit_enforced()
    test_mappings_present()
    print("ok")
