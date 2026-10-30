import torch

from n_9_intermediate_candidate_inspection_and_ import (
    PSN_IntermediateInspector,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def make_latent(b=2, c=4, h=8, w=8, seed=0):
    g = torch.Generator().manual_seed(seed)
    x = torch.randn(b, c, h, w, generator=g)
    return {"samples": x}


def test_module_mappings():
    assert "PSN_IntermediateInspector" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_IntermediateInspector"] is PSN_IntermediateInspector
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_IntermediateInspector"] == "PSN Intermediate Inspector"


def test_input_types():
    it = PSN_IntermediateInspector.INPUT_TYPES()
    req = it["required"]
    assert req["latent"] == ("LATENT",)
    assert list(req["action"][0]) == ["inspect", "branch"]
    assert req["step"][1]["min"] == 0
    assert PSN_IntermediateInspector.RETURN_TYPES == ("LATENT", "IMAGE")
    assert PSN_IntermediateInspector.RETURN_NAMES == ("latent_out", "preview")
    assert PSN_IntermediateInspector.FUNCTION == "run"
    assert PSN_IntermediateInspector.CATEGORY.startswith("ParametricStudio/")


def test_inspect_passthrough_and_preview():
    node = PSN_IntermediateInspector()
    lat = make_latent()
    orig = lat["samples"].clone()
    out_lat, preview = node.run(lat, 10, "inspect")
    # inspect must not change the values
    assert torch.equal(out_lat["samples"], orig)
    # input not mutated
    assert torch.equal(lat["samples"], orig)
    # output dict is a fresh object
    assert out_lat is not lat
    # preview shape [B,H,W,C] and in 0..1
    b, c, h, w = orig.shape
    assert preview.shape == (b, h, w, 3)
    assert preview.min() >= 0.0 and preview.max() <= 1.0


def test_branch_changes_values_and_is_deterministic():
    node = PSN_IntermediateInspector()
    lat = make_latent(seed=7)
    orig = lat["samples"].clone()
    out1, _ = node.run(lat, 5, "branch")
    out2, _ = node.run(lat, 5, "branch")
    # branch must differ from the original
    assert not torch.equal(out1["samples"], orig)
    # deterministic for the same step
    assert torch.equal(out1["samples"], out2["samples"])
    # different step -> different branch
    out3, _ = node.run(lat, 6, "branch")
    assert not torch.equal(out1["samples"], out3["samples"])
    # input untouched
    assert torch.equal(lat["samples"], orig)


def test_bad_action_raises():
    node = PSN_IntermediateInspector()
    lat = make_latent()
    try:
        node.run(lat, 3, "explode")
    except ValueError as e:
        assert "action" in str(e)
    else:
        raise AssertionError("expected ValueError for bad action")


def test_bad_step_raises():
    node = PSN_IntermediateInspector()
    lat = make_latent()
    for bad in (-1, 2.5, "10", True):
        try:
            node.run(lat, bad, "inspect")
        except (ValueError, TypeError):
            pass
        else:
            raise AssertionError("expected error for step=%r" % (bad,))


def test_bad_latent_raises():
    node = PSN_IntermediateInspector()
    # not a dict
    try:
        node.run([1, 2, 3], 1, "inspect")
    except TypeError:
        pass
    else:
        raise AssertionError("expected TypeError for non-dict latent")
    # dict without samples tensor
    try:
        node.run({"samples": "nope"}, 1, "inspect")
    except TypeError:
        pass
    else:
        raise AssertionError("expected TypeError for non-tensor samples")
    # wrong dim
    try:
        node.run({"samples": torch.randn(2, 4, 8)}, 1, "inspect")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for 3D samples")


def test_single_channel_preview():
    node = PSN_IntermediateInspector()
    lat = {"samples": torch.randn(1, 1, 4, 4)}
    _, preview = node.run(lat, 0, "inspect")
    assert preview.shape == (1, 4, 4, 3)
    assert preview.min() >= 0.0 and preview.max() <= 1.0


def test_step_zero_branch():
    node = PSN_IntermediateInspector()
    lat = make_latent(seed=3)
    out, _ = node.run(lat, 0, "branch")
    assert out["samples"].shape == lat["samples"].shape
    assert not torch.equal(out["samples"], lat["samples"])


def main():
    test_module_mappings()
    test_input_types()
    test_inspect_passthrough_and_preview()
    test_branch_changes_values_and_is_deterministic()
    test_bad_action_raises()
    test_bad_step_raises()
    test_bad_latent_raises()
    test_single_channel_preview()
    test_step_zero_branch()
    print("ok")


if __name__ == "__main__":
    main()
