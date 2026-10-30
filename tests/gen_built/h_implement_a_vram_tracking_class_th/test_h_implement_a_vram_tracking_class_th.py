import torch

from h_implement_a_vram_tracking_class_th import (
    PSN_VramGate,
    VramError,
    VramTracker,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def test_tracker_basic():
    t = VramTracker(device="cpu", total_bytes=1024 ** 3)  # 1 GiB
    assert t.total_bytes == 1024 ** 3
    t.simulate_usage(10 * 1024 ** 2)  # 10 MiB observed
    t.reserve("a", 100 * 1024 ** 2)   # 100 MiB
    t.reserve("b", 200 * 1024 ** 2)   # 200 MiB
    assert t._reserved == 300 * 1024 ** 2
    assert t.available_bytes() == 1024 ** 3 - 310 * 1024 ** 2
    assert 0.0 < t.utilization() < 1.0


def test_tracker_release():
    t = VramTracker(device="cpu", total_bytes=1024 ** 3)
    t.reserve("a", 100 * 1024 ** 2)
    t.reserve("b", 200 * 1024 ** 2)
    freed = t.release("a")
    assert freed == 100 * 1024 ** 2
    assert t._reserved == 200 * 1024 ** 2
    freed = t.release_all()
    assert freed == 200 * 1024 ** 2
    assert t._reserved == 0
    try:
        t.release("nope")
        assert False, "expected KeyError"
    except KeyError:
        pass


def test_tracker_oom():
    t = VramTracker(device="cpu", total_bytes=100 * 1024 ** 2)  # 100 MiB
    t.reserve("big", 60 * 1024 ** 2)
    try:
        t.reserve("too_big", 50 * 1024 ** 2)  # 60+50 > 100
        assert False, "expected VramError"
    except VramError:
        pass
    # reservation after release should succeed
    t.release("big")
    t.reserve("ok", 90 * 1024 ** 2)
    assert t._reserved == 90 * 1024 ** 2


def test_tracker_bad_input():
    try:
        VramTracker(device="cpu", total_bytes=-1)
        assert False, "expected ValueError"
    except ValueError:
        pass
    try:
        VramTracker(device="cpu", total_bytes="nope")
        assert False, "expected TypeError"
    except TypeError:
        pass
    t = VramTracker(device="cpu", total_bytes=1024 ** 3)
    try:
        t.reserve("", 10)
        assert False, "expected ValueError"
    except ValueError:
        pass
    try:
        t.reserve("x", -5)
        assert False, "expected ValueError"
    except ValueError:
        pass
    try:
        t.simulate_usage(-1)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_node_ok():
    img = torch.rand(2, 8, 8, 3)  # small CPU tensor in 0..1
    node = PSN_VramGate()
    out_img, ok, status = node.run(img, budget_mb=64, total_mb=1024)
    assert ok is True
    assert isinstance(status, str) and "vram" in status
    assert out_img.shape == img.shape
    assert not (out_img is img)  # not the same object (no in-place)
    assert torch.allclose(out_img, img)


def test_node_oom():
    img = torch.rand(1, 4, 4, 3)
    node = PSN_VramGate()
    # budget larger than total -> should fail
    out_img, ok, status = node.run(img, budget_mb=2048, total_mb=1024)
    assert ok is False
    assert "vram" in status


def test_node_bad_input():
    node = PSN_VramGate()
    # wrong shape
    try:
        node.run(torch.rand(4, 4, 3), budget_mb=1, total_mb=1024)
        assert False, "expected ValueError"
    except ValueError:
        pass
    # out of range values
    try:
        node.run(torch.rand(1, 4, 4, 3) * 2.0, budget_mb=1, total_mb=1024)
        assert False, "expected ValueError"
    except ValueError:
        pass
    # not a tensor
    try:
        node.run("hello", budget_mb=1, total_mb=1024)
        assert False, "expected TypeError"
    except TypeError:
        pass
    # negative budget
    try:
        node.run(torch.rand(1, 4, 4, 3), budget_mb=-1, total_mb=1024)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_node_mappings():
    assert "PSN_VramGate" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_VramGate"] is PSN_VramGate
    assert "PSN_VramGate" in NODE_DISPLAY_NAME_MAPPINGS
    assert PSN_VramGate.FUNCTION == "run"
    assert PSN_VramGate.CATEGORY.startswith("ParametricStudio/")
    it = PSN_VramGate.INPUT_TYPES()
    assert "image" in it["required"]
    assert "budget_mb" in it["required"]
    assert PSN_VramGate.RETURN_TYPES == ("IMAGE", "BOOLEAN", "STRING")


def test_node_does_not_mutate():
    img = torch.rand(1, 4, 4, 3)
    snapshot = img.clone()
    node = PSN_VramGate()
    node.run(img, budget_mb=16, total_mb=1024)
    assert torch.equal(img, snapshot), "input was mutated"


if __name__ == "__main__":
    test_tracker_basic()
    test_tracker_release()
    test_tracker_oom()
    test_tracker_bad_input()
    test_node_ok()
    test_node_oom()
    test_node_bad_input()
    test_node_mappings()
    test_node_does_not_mutate()
    print("ok")
