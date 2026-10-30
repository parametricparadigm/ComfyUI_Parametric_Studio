import torch

from n_1_modular_pipeline_subgraphs import (
    PSN_SubgraphPort,
    PSN_SubgraphWrapper,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def test_module_mappings():
    assert set(NODE_CLASS_MAPPINGS) == {"PSN_SubgraphPort", "PSN_SubgraphWrapper"}
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_SubgraphWrapper"] == "Subgraph Wrapper"
    for cls in NODE_CLASS_MAPPINGS.values():
        assert cls.FUNCTION == "run"
        assert cls.CATEGORY.startswith("ParametricStudio/")
        it = cls.INPUT_TYPES()
        assert "required" in it


def test_port_ok_and_type_safety():
    port = PSN_SubgraphPort()
    img = torch.rand(1, 4, 4, 3)
    val, status = port.run("in_0", "IMAGE", img)
    assert status == "ok"
    assert torch.equal(val, img)
    # input must not be mutated by the port
    val[0, 0, 0, 0] = 0.5
    assert not torch.equal(val, img)

    # bad type: 3-d tensor is not an IMAGE
    bad, status = port.run("in_0", "IMAGE", torch.rand(1, 4, 4))
    assert status.startswith("error")

    # out-of-range image values rejected
    bad, status = port.run("in_0", "IMAGE", torch.rand(1, 4, 4, 3) * 2.0)
    assert status.startswith("error")

    # empty port name rejected
    _, status = port.run("  ", "IMAGE", img)
    assert status.startswith("error")


def test_wrapper_routes_and_validates():
    PSN_SubgraphWrapper.clear_stages()
    w = PSN_SubgraphWrapper()

    def stage(inputs):
        # simulate a KSampler-like stage: scale the image and echo a mask
        return {"img_out": inputs["img"] * 0.5, "mask_out": inputs["mask"]}

    PSN_SubgraphWrapper.register_stage("sg_test", stage)

    img = torch.rand(2, 8, 8, 3)
    mask = torch.rand(2, 8, 8)
    handle, status = w.run(
        "sg_test",
        {"in_img": ("img", "IMAGE"), "in_mask": ("mask", "MASK")},
        {"out_img": ("img_out", "IMAGE"), "out_mask": ("mask_out", "MASK")},
        {"in_img": img, "in_mask": mask},
    )
    assert status == "ok"
    assert torch.equal(handle["out_img"], img * 0.5)
    assert torch.equal(handle["out_mask"], mask)
    # no in-place mutation of the inputs
    handle["out_img"].fill_(1.0)
    assert not torch.equal(handle["out_img"], img * 0.5)


def test_wrapper_bad_inputs():
    PSN_SubgraphWrapper.clear_stages()
    w = PSN_SubgraphWrapper()

    # missing input
    _, status = w.run("sg_x", {"a": "IMAGE"}, {}, {})
    assert status.startswith("error")

    # wrong type for declared input
    _, status = w.run("sg_x", {"a": "IMAGE"}, {}, {"a": torch.rand(2, 2)})
    assert status.startswith("error")

    # malformed input map
    _, status = w.run("sg_x", {"a": 123}, {}, {})
    assert status.startswith("error")

    # bad subgraph id
    _, status = w.run("", {}, {}, {})
    assert status.startswith("error")

    # stage that raises
    PSN_SubgraphWrapper.register_stage("sg_boom", lambda i: 1 / 0)
    _, status = w.run("sg_boom", {}, {}, {})
    assert status.startswith("error")

    # stage returning non-dict
    PSN_SubgraphWrapper.register_stage("sg_nodict", lambda i: [1, 2])
    _, status = w.run("sg_nodict", {}, {}, {})
    assert status.startswith("error")


def test_wrapper_latent_passthrough():
    PSN_SubgraphWrapper.clear_stages()
    w = PSN_SubgraphWrapper()
    latent = {"samples": torch.rand(1, 4, 16, 16)}
    handle, status = w.run(
        "sg_latent",
        {"lat": "LATENT"},
        {"lat_out": ("lat", "LATENT")},
        {"lat": latent},
    )
    assert status == "ok"
    assert isinstance(handle["lat_out"], dict)
    assert torch.equal(handle["lat_out"]["samples"], latent["samples"])
    # clone check: mutating the handle must not touch the original
    handle["lat_out"]["samples"].fill_(0.0)
    assert not torch.equal(handle["lat_out"]["samples"], latent["samples"])


def main():
    test_module_mappings()
    test_port_ok_and_type_safety()
    test_wrapper_routes_and_validates()
    test_wrapper_bad_inputs()
    test_wrapper_latent_passthrough()
    print("ok")


if __name__ == "__main__":
    main()
