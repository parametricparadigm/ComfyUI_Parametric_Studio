"""Tests for h_use_a_context_manager_pattern_to_a.py (plain asserts)."""

import torch

import h_use_a_context_manager_pattern_to_a as mod


def _img(b=1, h=4, w=4, c=3, v=0.5):
    return torch.full((b, h, w, c), v, dtype=torch.float32)


def test_registry_and_context_manager_lifecycle():
    reg = mod.SidecarRegistry()
    reg.register("svc", port=9000, startup_cost=0.0)
    st = reg.state("svc")
    assert st.running is False
    with mod.Sidecar("svc", registry=reg) as info:
        assert info["started_by_us"] is True
        assert reg.state("svc").running is True
    # non-persistent sidecar we started must be stopped on exit
    assert reg.state("svc").running is False
    assert reg.state("svc").start_count == 1
    assert reg.state("svc").stop_count == 1


def test_context_manager_does_not_stop_preexisting_or_persistent():
    reg = mod.SidecarRegistry()
    reg.register("shared", port=9001, startup_cost=0.0, persistent=True)
    reg.register("manual", port=9002, startup_cost=0.0)
    # persistent: started by us but must stay running
    with mod.Sidecar("shared", registry=reg):
        pass
    assert reg.state("shared").running is True
    assert reg.state("shared").stop_count == 0
    # manual: pre-started, we must not stop it
    reg.state("manual").running = True
    with mod.Sidecar("manual", registry=reg) as info:
        assert info["started_by_us"] is False
    assert reg.state("manual").running is True
    assert reg.state("manual").stop_count == 0


def test_context_manager_teardown_on_exception():
    reg = mod.SidecarRegistry()
    reg.register("boom", port=9003, startup_cost=0.0)
    raised = False
    try:
        with mod.Sidecar("boom", registry=reg):
            assert reg.state("boom").running is True
            raise RuntimeError("task failed")
    except RuntimeError:
        raised = True
    assert raised is True
    # teardown still happened
    assert reg.state("boom").running is False
    assert reg.state("boom").stop_count == 1


def test_unknown_sidecar_raises():
    reg = mod.SidecarRegistry()
    reg.register("known", port=9004, startup_cost=0.0)
    try:
        with mod.Sidecar("nope", registry=reg):
            pass
        assert False, "expected KeyError"
    except KeyError:
        pass


def test_register_validation():
    reg = mod.SidecarRegistry()
    for bad in ("", "  "):
        try:
            reg.register(bad, 9005)
            assert False, "expected ValueError for empty name"
        except ValueError:
            pass
    for bad_port in (0, -1, 70000, "8192"):
        try:
            reg.register("x", bad_port)
            assert False, f"expected ValueError for port {bad_port!r}"
        except ValueError:
            pass
    try:
        reg.register("y", 9006, startup_cost=-0.1)
        assert False, "expected ValueError for negative startup_cost"
    except ValueError:
        pass


def test_node_run_happy_path_and_no_inplace_mutation():
    node = mod.PSN_SidecarGuardedTask()
    img = _img(v=0.4)
    before = img.clone()
    out, report = node.run(img, "foley", "a bird sings", ensure_running=True)
    # input untouched
    assert torch.equal(img, before)
    # output is a valid image tensor
    assert isinstance(out, torch.Tensor)
    assert out.shape == img.shape
    assert out.dtype == torch.float32
    assert out.min() >= 0.0 and out.max() <= 1.0
    # report sanity
    assert report["name"] == "foley"
    assert report["port"] == 8192
    assert report["started_by_us"] is True
    assert report["error"] is None
    assert report["task_ms"] >= 0.0
    # foley is non-persistent and we started it -> stopped afterwards
    assert mod.REGISTRY.state("foley").running is False


def test_node_output_depends_on_prompt():
    node = mod.PSN_SidecarGuardedTask()
    img = _img(v=0.5)
    out_a, _ = node.run(img, "foley", "alpha prompt", ensure_running=True)
    out_b, _ = node.run(img, "foley", "beta prompt", ensure_running=True)
    assert not torch.equal(out_a, out_b)


def test_node_bad_inputs():
    node = mod.PSN_SidecarGuardedTask()
    # not a tensor
    try:
        node.run("nope", "foley", "p")
        assert False, "expected TypeError"
    except TypeError:
        pass
    # wrong ndim
    try:
        node.run(torch.zeros(4, 4, 3), "foley", "p")
        assert False, "expected ValueError for 3D"
    except ValueError:
        pass
    # bad channel count
    try:
        node.run(torch.zeros(1, 4, 4, 5), "foley", "p")
        assert False, "expected ValueError for 5 channels"
    except ValueError:
        pass
    # out of range
    try:
        node.run(torch.full((1, 4, 4, 3), 1.5), "foley", "p")
        assert False, "expected ValueError for >1"
    except ValueError:
        pass
    # non-finite
    try:
        node.run(torch.full((1, 4, 4, 3), float("nan")), "foley", "p")
        assert False, "expected ValueError for nan"
    except ValueError:
        pass
    # unknown sidecar
    try:
        node.run(_img(), "does_not_exist", "p")
        assert False, "expected ValueError for unknown sidecar"
    except ValueError:
        pass
    # non-string prompt
    try:
        node.run(_img(), "foley", 123)
        assert False, "expected TypeError for prompt"
    except TypeError:
        pass


def test_node_unguarded_mode():
    node = mod.PSN_SidecarGuardedTask()
    img = _img(v=0.3)
    out, report = node.run(img, "foley", "quiet", ensure_running=False)
    assert isinstance(out, torch.Tensor)
    assert report["started_by_us"] is False
    assert report["error"] is None


def test_module_mappings():
    assert "PSN_SidecarGuardedTask" in mod.NODE_CLASS_MAPPINGS
    assert "PSN_SidecarGuardedTask" in mod.NODE_DISPLAY_NAME_MAPPINGS
    cls = mod.NODE_CLASS_MAPPINGS["PSN_SidecarGuardedTask"]
    spec = cls.INPUT_TYPES()
    assert "required" in spec and "image" in spec["required"]
    assert cls.RETURN_TYPES == ("IMAGE", "SIDECAR_REPORT")
    assert cls.FUNCTION == "run"
    assert cls.CATEGORY.startswith("ParametricStudio/")


if __name__ == "__main__":
    test_registry_and_context_manager_lifecycle()
    test_context_manager_does_not_stop_preexisting_or_persistent()
    test_context_manager_teardown_on_exception()
    test_unknown_sidecar_raises()
    test_register_validation()
    test_node_run_happy_path_and_no_inplace_mutation()
    test_node_output_depends_on_prompt()
    test_node_bad_inputs()
    test_node_unguarded_mode()
    test_module_mappings()
    print("ok")
