"""Tests for n_6_memory_heavy_model_streaming.

Run with:  python3 -B test_n_6_memory_heavy_model_streaming.py
Must print 'ok' and exit 0.
"""

import torch

from n_6_memory_heavy_model_streaming import (
    PSN_Weight_Ferry,
    PSN_Block_Offload_Manager,
    build_stream_schedule,
    apply_stream_schedule,
    offload_blocks,
    _is_descriptor,
    _clone_descriptor,
    _parse_block_list,
    _validate_indices,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def _make_model(n_blocks=8, device="cpu"):
    """Build a small model descriptor with *n_blocks* block tensors."""
    blocks = [torch.randn(2, 4, 4) for _ in range(n_blocks)]
    return {"blocks": blocks, "device": device, "stream_log": []}


# ---------------------------------------------------------------------------
# 1. build_stream_schedule: basic windowing
# ---------------------------------------------------------------------------
def test_schedule_basic():
    sched = build_stream_schedule(8, 4, prefetch=False)
    assert len(sched) == 2, "expected 2 windows for 8 blocks / size 4"
    assert sched[0] == {"start": 0, "end": 4, "prefetch_end": 4}
    assert sched[1] == {"start": 4, "end": 8, "prefetch_end": 8}


# ---------------------------------------------------------------------------
# 2. build_stream_schedule: prefetch extends the window
# ---------------------------------------------------------------------------
def test_schedule_prefetch():
    sched = build_stream_schedule(8, 4, prefetch=True)
    assert sched[0]["prefetch_end"] == 8, "first window should prefetch to end"
    assert sched[1]["prefetch_end"] == 8, "last window prefetch clamped to end"


# ---------------------------------------------------------------------------
# 3. build_stream_schedule: block_size larger than n_blocks
# ---------------------------------------------------------------------------
def test_schedule_single_window():
    sched = build_stream_schedule(3, 16, prefetch=True)
    assert len(sched) == 1
    assert sched[0] == {"start": 0, "end": 3, "prefetch_end": 3}


# ---------------------------------------------------------------------------
# 4. build_stream_schedule: bad inputs raise
# ---------------------------------------------------------------------------
def test_schedule_bad_inputs():
    for bad in [(0, 4, False), (8, 0, False), (8, -1, False), (-1, 4, False)]:
        try:
            build_stream_schedule(*bad)
            raise AssertionError("expected ValueError for %r" % (bad,))
        except (ValueError, TypeError):
            pass
    # non-int types
    for bad in [("8", 4, False), (8, "4", False), (8, 4, "yes")]:
        try:
            build_stream_schedule(*bad)
            raise AssertionError("expected TypeError for %r" % (bad,))
        except (ValueError, TypeError):
            pass


# ---------------------------------------------------------------------------
# 5. PSN_Weight_Ferry: node run produces patched descriptor with log
# ---------------------------------------------------------------------------
def test_weight_ferry_run():
    model = _make_model(8)
    node = PSN_Weight_Ferry()
    (patched,) = node.run(model, block_size=4, prefetch=True)
    assert _is_descriptor(patched)
    assert patched["block_size"] == 4
    assert patched["prefetch"] is True
    # stream_log should record moves for blocks 0..7
    assert len(patched["stream_log"]) > 0
    # original model must be unchanged (no in-place mutation)
    assert model["stream_log"] == []
    assert len(model["blocks"]) == 8
    # tensors must be distinct objects (cloned)
    assert patched["blocks"][0] is not model["blocks"][0]
    # values preserved
    assert torch.equal(patched["blocks"][0], model["blocks"][0])


# ---------------------------------------------------------------------------
# 6. PSN_Weight_Ferry: bad model input raises
# ---------------------------------------------------------------------------
def test_weight_ferry_bad_model():
    node = PSN_Weight_Ferry()
    for bad in [None, "not a model", [1, 2, 3], {"blocks": "nope"}]:
        try:
            node.run(bad, 4, True)
            raise AssertionError("expected ValueError for %r" % (bad,))
        except (ValueError, TypeError):
            pass


# ---------------------------------------------------------------------------
# 7. PSN_Block_Offload_Manager: parse and offload
# ---------------------------------------------------------------------------
def test_offload_manager_run():
    model = _make_model(8)
    node = PSN_Block_Offload_Manager()
    (patched,) = node.run(model, "1, 3, 5")
    assert patched["offload_blocks"] == [1, 3, 5]
    # log should contain offload entries
    assert any("offload 1" in e for e in patched["stream_log"])
    assert any("offload 3" in e for e in patched["stream_log"])
    assert any("offload 5" in e for e in patched["stream_log"])
    # original unchanged
    assert "offload_blocks" not in model or model.get("offload_blocks") is None


# ---------------------------------------------------------------------------
# 8. PSN_Block_Offload_Manager: empty string -> no offloads
# ---------------------------------------------------------------------------
def test_offload_manager_empty():
    model = _make_model(4)
    node = PSN_Block_Offload_Manager()
    (patched,) = node.run(model, "")
    assert patched["offload_blocks"] == []


# ---------------------------------------------------------------------------
# 9. PSN_Block_Offload_Manager: out-of-range index raises
# ---------------------------------------------------------------------------
def test_offload_manager_bad_index():
    model = _make_model(4)
    node = PSN_Block_Offload_Manager()
    try:
        node.run(model, "99")
        raise AssertionError("expected ValueError for out-of-range index")
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# 10. PSN_Block_Offload_Manager: non-numeric token raises
# ---------------------------------------------------------------------------
def test_offload_manager_bad_token():
    model = _make_model(4)
    node = PSN_Block_Offload_Manager()
    try:
        node.run(model, "abc")
        raise AssertionError("expected ValueError for non-numeric token")
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# 11. _parse_block_list: edge cases
# ---------------------------------------------------------------------------
def test_parse_block_list():
    assert _parse_block_list("", 10) == []
    assert _parse_block_list(None, 10) == []
    assert _parse_block_list(" 0 , 2 , 4 ", 10) == [0, 2, 4]
    assert _parse_block_list("0", 1) == [0]
    try:
        _parse_block_list("-1", 10)
        raise AssertionError("expected ValueError for negative index")
    except ValueError:
        pass
    try:
        _parse_block_list("1.5", 10)
        raise AssertionError("expected ValueError for float token")
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# 12. _clone_descriptor: deep copy, no shared tensors
# ---------------------------------------------------------------------------
def test_clone_descriptor():
    model = _make_model(3)
    clone = _clone_descriptor(model)
    assert clone is not model
    assert clone["blocks"][0] is not model["blocks"][0]
    assert torch.equal(clone["blocks"][0], model["blocks"][0])
    # mutating clone does not affect original
    clone["blocks"][0].fill_(999)
    assert not torch.equal(clone["blocks"][0], model["blocks"][0])


# ---------------------------------------------------------------------------
# 13. NODE_CLASS_MAPPINGS and display names
# ---------------------------------------------------------------------------
def test_mappings():
    assert "PSN_Weight_Ferry" in NODE_CLASS_MAPPINGS
    assert "PSN_Block_Offload_Manager" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_Weight_Ferry"] is PSN_Weight_Ferry
    assert NODE_CLASS_MAPPINGS["PSN_Block_Offload_Manager"] is PSN_Block_Offload_Manager
    assert "PSN_Weight_Ferry" in NODE_DISPLAY_NAME_MAPPINGS
    assert "PSN_Block_Offload_Manager" in NODE_DISPLAY_NAME_MAPPINGS


# ---------------------------------------------------------------------------
# 14. INPUT_TYPES contract
# ---------------------------------------------------------------------------
def test_input_types():
    it = PSN_Weight_Ferry.INPUT_TYPES()
    assert "required" in it
    assert "model" in it["required"]
    assert "block_size" in it["required"]
    assert "prefetch" in it["required"]
    assert PSN_Weight_Ferry.RETURN_TYPES == ("MODEL",)
    assert PSN_Weight_Ferry.FUNCTION == "run"

    it2 = PSN_Block_Offload_Manager.INPUT_TYPES()
    assert "model" in it2["required"]
    assert "offload_blocks" in it2["required"]
    assert PSN_Block_Offload_Manager.RETURN_TYPES == ("MODEL",)
    assert PSN_Block_Offload_Manager.FUNCTION == "run"


# ---------------------------------------------------------------------------
# 15. apply_stream_schedule: eviction logic
# ---------------------------------------------------------------------------
def test_apply_stream_schedule_eviction():
    model = _make_model(8)
    sched = build_stream_schedule(8, 4, prefetch=False)
    patched = apply_stream_schedule(model, sched)
    # blocks 0-3 should be evicted after window 1 moves to 4-7
    evicted = [e for e in patched["stream_log"] if e.startswith("evict")]
    assert len(evicted) == 4, "expected 4 evictions, got %r" % evicted
    # original unchanged
    assert model["stream_log"] == []


# ---------------------------------------------------------------------------
# 16. offload_blocks function: idempotent
# ---------------------------------------------------------------------------
def test_offload_idempotent():
    model = _make_model(8)
    p1 = offload_blocks(model, [1, 3])
    p2 = offload_blocks(p1, [1, 3])
    assert p2["offload_blocks"] == [1, 3]
    # no duplicate log entries
    offload_entries = [e for e in p2["stream_log"] if e.startswith("offload")]
    assert len(offload_entries) == 2, "expected 2 offload entries, got %r" % offload_entries


if __name__ == "__main__":
    test_schedule_basic()
    test_schedule_prefetch()
    test_schedule_single_window()
    test_schedule_bad_inputs()
    test_weight_ferry_run()
    test_weight_ferry_bad_model()
    test_offload_manager_run()
    test_offload_manager_empty()
    test_offload_manager_bad_index()
    test_offload_manager_bad_token()
    test_parse_block_list()
    test_clone_descriptor()
    test_mappings()
    test_input_types()
    test_apply_stream_schedule_eviction()
    test_offload_idempotent()
    print("ok")
