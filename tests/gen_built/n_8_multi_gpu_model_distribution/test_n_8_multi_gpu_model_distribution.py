"""Tests for n_8_multi_gpu_model_distribution.py"""

import torch
from n_8_multi_gpu_model_distribution import (
    PSN_MultiGPU_Init,
    PSN_MultiGPU_Sync,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _validate_device_map,
    _build_plan,
)

# ---------------------------------------------------------------------------
# 1. Module-level registration
# ---------------------------------------------------------------------------
assert "PSN_MultiGPU_Init" in NODE_CLASS_MAPPINGS
assert "PSN_MultiGPU_Sync" in NODE_CLASS_MAPPINGS
assert NODE_CLASS_MAPPINGS["PSN_MultiGPU_Init"] is PSN_MultiGPU_Init
assert NODE_CLASS_MAPPINGS["PSN_MultiGPU_Sync"] is PSN_MultiGPU_Sync
assert "PSN_MultiGPU_Init" in NODE_DISPLAY_NAME_MAPPINGS
assert "PSN_MultiGPU_Sync" in NODE_DISPLAY_NAME_MAPPINGS
print("1. registration ok")

# ---------------------------------------------------------------------------
# 2. INPUT_TYPES / RETURN_TYPES / FUNCTION / CATEGORY
# ---------------------------------------------------------------------------
it = PSN_MultiGPU_Init.INPUT_TYPES()
assert "required" in it
assert "model" in it["required"]
assert "device_map" in it["required"]
assert PSN_MultiGPU_Init.RETURN_TYPES == ("MODEL",)
assert PSN_MultiGPU_Init.FUNCTION == "run"
assert PSN_MultiGPU_Init.CATEGORY == "ParametricStudio/MultiGPU"

it2 = PSN_MultiGPU_Sync.INPUT_TYPES()
assert "model" in it2["required"]
assert PSN_MultiGPU_Sync.RETURN_TYPES == ("MODEL",)
assert PSN_MultiGPU_Sync.FUNCTION == "run"
assert PSN_MultiGPU_Sync.CATEGORY == "ParametricStudio/MultiGPU"
print("2. node metadata ok")

# ---------------------------------------------------------------------------
# 3. PSN_MultiGPU_Init happy path
# ---------------------------------------------------------------------------
init_node = PSN_MultiGPU_Init()
model = {"layers": {"layer0": 100, "layer1": 200, "layer2": 300}}
dm = {"layer0": "cuda:0", "layer1": "cuda:1", "layer2": "cpu"}
(result,) = init_node.run(model, dm)

assert "_psn_gpu_plan" in result
plan = result["_psn_gpu_plan"]
assert len(plan) == 3
assert plan[0]["layer"] == "layer0" and plan[0]["device"] == "cuda:0"
assert plan[1]["layer"] == "layer1" and plan[1]["device"] == "cuda:1"
assert plan[2]["layer"] == "layer2" and plan[2]["device"] == "cpu"
assert plan[0]["param_count"] == 100
# input not mutated
assert "_psn_gpu_plan" not in model
print("3. init happy path ok")

# ---------------------------------------------------------------------------
# 4. PSN_MultiGPU_Init with list-of-names layers (no param counts)
# ---------------------------------------------------------------------------
model2 = {"layers": ["a", "b", "c", "d"]}
dm2 = {"a": "cuda:0", "b": "cuda:1"}
(result2,) = init_node.run(model2, dm2)
plan2 = result2["_psn_gpu_plan"]
assert len(plan2) == 4
# c and d not in dm2 -> round-robin fallback: index 2 -> cuda:0, index 3 -> cuda:1
assert plan2[2]["device"] == "cuda:0"
assert plan2[3]["device"] == "cuda:1"
print("4. init list layers ok")

# ---------------------------------------------------------------------------
# 5. PSN_MultiGPU_Init bad device_map (non-dict)
# ---------------------------------------------------------------------------
try:
    init_node.run(model, "not a dict")
    assert False, "should have raised"
except ValueError as e:
    assert "device_map" in str(e)
print("5. init bad device_map ok")

# ---------------------------------------------------------------------------
# 6. PSN_MultiGPU_Init bad device string
# ---------------------------------------------------------------------------
try:
    init_node.run(model, {"layer0": "tpu:0"})
    assert False, "should have raised"
except ValueError as e:
    assert "unrecognised" in str(e)
print("6. init bad device string ok")

# ---------------------------------------------------------------------------
# 7. PSN_MultiGPU_Sync happy path - all-reduce mean
# ---------------------------------------------------------------------------
sync_node = PSN_MultiGPU_Sync()
# build a model that has already been through Init
model_sync = {"layers": {"w": 4}}
(model_sync,) = init_node.run(model_sync, {"w": "cuda:0"})

# two devices each with a gradient for layer 'w'
g1 = torch.tensor([1.0, 2.0, 3.0, 4.0])
g2 = torch.tensor([3.0, 4.0, 5.0, 6.0])
model_sync["grad_shards"] = {
    "cuda:0": {"w": g1},
    "cuda:1": {"w": g2},
}
(result_sync,) = sync_node.run(model_sync)

assert "_psn_synced_grads" in result_sync
synced_w = result_sync["_psn_synced_grads"]["w"]
expected = torch.tensor([2.0, 3.0, 4.0, 5.0])
assert torch.allclose(synced_w, expected), "all-reduce mean mismatch"
# input not mutated
assert "_psn_synced_grads" not in model_sync
print("7. sync happy path ok")

# ---------------------------------------------------------------------------
# 8. PSN_MultiGPU_Sync without prior Init (missing plan)
# ---------------------------------------------------------------------------
try:
    sync_node.run({"layers": {"w": 4}, "grad_shards": {"cuda:0": {"w": torch.zeros(4)}}})
    assert False, "should have raised"
except ValueError as e:
    assert "_psn_gpu_plan" in str(e)
print("8. sync missing plan ok")

# ---------------------------------------------------------------------------
# 9. PSN_MultiGPU_Sync with non-tensor gradient
# ---------------------------------------------------------------------------
model_bad = {"layers": {"w": 4}}
(model_bad,) = init_node.run(model_bad, {"w": "cuda:0"})
model_bad["grad_shards"] = {"cuda:0": {"w": [1.0, 2.0]}}
try:
    sync_node.run(model_bad)
    assert False, "should have raised"
except ValueError as e:
    assert "torch.Tensor" in str(e)
print("9. sync non-tensor grad ok")

# ---------------------------------------------------------------------------
# 10. PSN_MultiGPU_Sync with 2-D gradient (bad shape)
# ---------------------------------------------------------------------------
model_bad2 = {"layers": {"w": 4}}
(model_bad2,) = init_node.run(model_bad2, {"w": "cuda:0"})
model_bad2["grad_shards"] = {"cuda:0": {"w": torch.zeros(2, 2)}}
try:
    sync_node.run(model_bad2)
    assert False, "should have raised"
except ValueError as e:
    assert "1-D" in str(e)
print("10. sync 2-D grad ok")

# ---------------------------------------------------------------------------
# 11. _validate_device_map edge: empty dict
# ---------------------------------------------------------------------------
try:
    _validate_device_map({})
    assert False, "should have raised"
except ValueError as e:
    assert "empty" in str(e)
print("11. empty device_map ok")

# ---------------------------------------------------------------------------
# 12. _build_plan with dict layers
# ---------------------------------------------------------------------------
plan = _build_plan({"x": 10, "y": 20}, {"x": "cuda:0", "y": "cuda:1"})
assert plan[0] == {"layer": "x", "device": "cuda:0", "param_count": 10}
assert plan[1] == {"layer": "y", "device": "cuda:1", "param_count": 20}
print("12. build_plan dict ok")

print("ok")
