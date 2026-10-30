import json

import torch

import h_build_a_status_aggregation_system_ as mod


# --- module-level contract -------------------------------------------------

def test_module_contract():
    assert "PSN_StatusPollInstance" in mod.NODE_CLASS_MAPPINGS
    assert "PSN_StatusAggregateFleet" in mod.NODE_CLASS_MAPPINGS
    assert set(mod.NODE_DISPLAY_NAME_MAPPINGS) == set(mod.NODE_CLASS_MAPPINGS)
    for cls in mod.NODE_CLASS_MAPPINGS.values():
        assert cls.FUNCTION == "run"
        assert cls.CATEGORY.startswith("ParametricStudio/")
        assert isinstance(cls.RETURN_TYPES, tuple)
        assert isinstance(cls.RETURN_NAMES, tuple)
        assert len(cls.RETURN_TYPES) == len(cls.RETURN_NAMES)
        it = cls.INPUT_TYPES()
        assert "required" in it


# --- poll instance ----------------------------------------------------------

def test_poll_healthy():
    node = mod.PSN_StatusPollInstance()
    report, score, img = node.run(
        name="a", alive=True, queue=0, vram_used=2.0, vram_total=16.0,
        cpu=10.0, uptime=100.0, error="",
    )
    assert 0.0 <= score <= 1.0
    assert score > 0.9  # plenty of headroom, empty queue
    assert "instance: a" in report
    assert img.shape == (1, 1, 1, 3)
    assert torch.all((img >= 0.0) & (img <= 1.0))
    assert abs(img[0, 0, 0, 0].item() - score) < 1e-6


def test_poll_dead_instance():
    node = mod.PSN_StatusPollInstance()
    report, score, img = node.run(
        name="b", alive=False, queue=5, vram_used=0.0, vram_total=8.0,
        cpu=0.0, uptime=0.0, error="connection refused",
    )
    assert score == 0.0
    assert "alive: no" in report
    assert "error: connection refused" in report


def test_poll_bad_values_clamped():
    node = mod.PSN_StatusPollInstance()
    report, score, img = node.run(
        name="c", alive=True, queue=-5, vram_used=-1.0, vram_total=0.0,
        cpu=500.0, uptime=-3.0, error="",
    )
    assert "queue: 0" in report
    assert "cpu: 100.0%" in report
    assert "uptime: 0.0 s" in report
    assert score == 1.0  # no vram info, empty queue, alive


# --- aggregate fleet --------------------------------------------------------

def test_aggregate_healthy_fleet():
    node = mod.PSN_StatusAggregateFleet()
    snaps = [
        {"name": "a", "alive": True, "queue": 0, "vram_used": 1.0, "vram_total": 16.0},
        {"name": "b", "alive": True, "queue": 1, "vram_used": 2.0, "vram_total": 16.0},
    ]
    text = "\n".join(json.dumps(s) for s in snaps)
    report, fleet, img = node.run(snapshots=text, threshold=0.5)
    assert "fleet: healthy" in report
    assert fleet > 0.75
    assert img.shape == (1, 1, 1, 3)
    assert abs(img[0, 0, 0, 0].item() - fleet) < 1e-6


def test_aggregate_degraded_fleet():
    node = mod.PSN_StatusAggregateFleet()
    snaps = [
        {"name": "a", "alive": True, "queue": 0, "vram_used": 1.0, "vram_total": 16.0},
        {"name": "b", "alive": False, "queue": 0, "vram_used": 0.0, "vram_total": 16.0},
    ]
    text = json.dumps(snaps)  # array form
    report, fleet, img = node.run(snapshots=text, threshold=0.5)
    assert "fleet: degraded" in report
    assert "instances: 2 (1 alive)" in report
    assert "WARN" in report
    assert 0.0 < fleet < 1.0


def test_aggregate_empty_and_bad_input():
    node = mod.PSN_StatusAggregateFleet()
    report, fleet, img = node.run(snapshots="", threshold=0.5)
    assert "fleet: empty" in report
    assert fleet == 0.0
    assert img.shape == (1, 1, 1, 3)

    # bad input: not valid JSON
    try:
        node.run(snapshots="{not json", threshold=0.5)
        raise AssertionError("expected ValueError for bad JSON")
    except ValueError:
        pass

    # bad input: array of non-dicts
    try:
        node.run(snapshots=json.dumps(["nope"]), threshold=0.5)
        raise AssertionError("expected ValueError for non-dict snapshot")
    except ValueError:
        pass


def test_inputs_not_mutated():
    node = mod.PSN_StatusAggregateFleet()
    snap = {"name": "x", "alive": True, "queue": 3, "vram_used": 1.0, "vram_total": 8.0}
    before = json.loads(json.dumps(snap))
    node.run(snapshots=json.dumps(snap), threshold=0.5)
    assert snap == before


if __name__ == "__main__":
    test_module_contract()
    test_poll_healthy()
    test_poll_dead_instance()
    test_poll_bad_values_clamped()
    test_aggregate_healthy_fleet()
    test_aggregate_degraded_fleet()
    test_aggregate_empty_and_bad_input()
    test_inputs_not_mutated()
    print("ok")
