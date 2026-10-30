"""Tests for n_10_multi_gpu_distribution_for_large_mode."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import torch

from n_10_multi_gpu_distribution_for_large_mode import (
    PSN_Distribute_Model,
    PSN_Gather_Results,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _parse_device_map,
    _validate_device,
    _compute_layer_assignment,
    _estimate_vram,
    _simulate_distribution,
)

# ---------------------------------------------------------------------------
# 1. Module-level registration
# ---------------------------------------------------------------------------
assert "PSN_Distribute_Model" in NODE_CLASS_MAPPINGS, "PSN_Distribute_Model missing from NODE_CLASS_MAPPINGS"
assert "PSN_Gather_Results" in NODE_CLASS_MAPPINGS, "PSN_Gather_Results missing from NODE_CLASS_MAPPINGS"
assert "PSN_Distribute_Model" in NODE_DISPLAY_NAME_MAPPINGS, "PSN_Distribute_Model missing from NODE_DISPLAY_NAME_MAPPINGS"
assert "PSN_Gather_Results" in NODE_DISPLAY_NAME_MAPPINGS, "PSN_Gather_Results missing from NODE_DISPLAY_NAME_MAPPINGS"

# ---------------------------------------------------------------------------
# 2. INPUT_TYPES structure
# ---------------------------------------------------------------------------
dist_inputs = PSN_Distribute_Model.INPUT_TYPES()
assert "required" in dist_inputs, "PSN_Distribute_Model missing 'required' in INPUT_TYPES"
assert "model" in dist_inputs["required"], "PSN_Distribute_Model missing 'model' input"
assert "device_map" in dist_inputs["required"], "PSN_Distribute_Model missing 'device_map' input"
assert "num_layers" in dist_inputs["required"], "PSN_Distribute_Model missing 'num_layers' input"
assert "offload_threshold" in dist_inputs["required"], "PSN_Distribute_Model missing 'offload_threshold' input"

gather_inputs = PSN_Gather_Results.INPUT_TYPES()
assert "required" in gather_inputs, "PSN_Gather_Results missing 'required' in INPUT_TYPES"
assert "distributed_model" in gather_inputs["required"], "PSN_Gather_Results missing 'distributed_model' input"
assert "output" in gather_inputs["required"], "PSN_Gather_Results missing 'output' input"

# ---------------------------------------------------------------------------
# 3. RETURN_TYPES and FUNCTION
# ---------------------------------------------------------------------------
assert PSN_Distribute_Model.RETURN_TYPES == ("MODEL", "STRING"), "PSN_Distribute_Model RETURN_TYPES mismatch"
assert PSN_Distribute_Model.FUNCTION == "run", "PSN_Distribute_Model FUNCTION must be 'run'"
assert PSN_Distribute_Model.CATEGORY == "ParametricStudio/MultiGPU", "PSN_Distribute_Model CATEGORY mismatch"

assert PSN_Gather_Results.RETURN_TYPES == ("IMAGE", "STRING"), "PSN_Gather_Results RETURN_TYPES mismatch"
assert PSN_Gather_Results.FUNCTION == "run", "PSN_Gather_Results FUNCTION must be 'run'"
assert PSN_Gather_Results.CATEGORY == "ParametricStudio/MultiGPU", "PSN_Gather_Results CATEGORY mismatch"

# ---------------------------------------------------------------------------
# 4. _parse_device_map: valid and invalid inputs
# ---------------------------------------------------------------------------
assert _parse_device_map("cuda:0,cuda:1") == ["cuda:0", "cuda:1"], "_parse_device_map failed for cuda:0,cuda:1"
assert _parse_device_map("cpu") == ["cpu"], "_parse_device_map failed for cpu"
assert _parse_device_map("cuda:0, cuda:1, cpu") == ["cuda:0", "cuda:1", "cpu"], "_parse_device_map failed with spaces"

try:
    _parse_device_map("")
    assert False, "_parse_device_map should raise for empty string"
except ValueError:
    pass

try:
    _parse_device_map(None)
    assert False, "_parse_device_map should raise for None"
except ValueError:
    pass

# ---------------------------------------------------------------------------
# 5. _validate_device: valid and invalid
# ---------------------------------------------------------------------------
_validate_device("cpu")  # should not raise
_validate_device("cuda:0")  # should not raise
_validate_device("cuda:1")  # should not raise
_validate_device("cuda")  # should not raise

try:
    _validate_device("cuda:abc")
    assert False, "_validate_device should raise for cuda:abc"
except ValueError:
    pass

try:
    _validate_device("tpu:0")
    assert False, "_validate_device should raise for tpu:0"
except ValueError:
    pass

# ---------------------------------------------------------------------------
# 6. _compute_layer_assignment: round-robin
# ---------------------------------------------------------------------------
# 4 layers, 2 devices -> [0,2] and [1,3]
assign = _compute_layer_assignment(4, ["cuda:0", "cuda:1"])
assert assign == [[0, 2], [1, 3]], f"_compute_layer_assignment 4/2 failed: {assign}"

# 5 layers, 2 devices -> [0,2,4] and [1,3]
assign = _compute_layer_assignment(5, ["cuda:0", "cuda:1"])
assert assign == [[0, 2, 4], [1, 3]], f"_compute_layer_assignment 5/2 failed: {assign}"

# 1 layer, 1 device -> [0]
assign = _compute_layer_assignment(1, ["cpu"])
assert assign == [[0]], f"_compute_layer_assignment 1/1 failed: {assign}"

# 3 layers, 3 devices -> [0], [1], [2]
assign = _compute_layer_assignment(3, ["cuda:0", "cuda:1", "cuda:2"])
assert assign == [[0], [1], [2]], f"_compute_layer_assignment 3/3 failed: {assign}"

# ---------------------------------------------------------------------------
# 7. _estimate_vram
# ---------------------------------------------------------------------------
vram = _estimate_vram(10, 100.0, ["cuda:0", "cuda:1"])
assert abs(vram["cuda:0"] - 2000.0) < 1e-6, f"_estimate_vram cuda:0 failed: {vram}"
assert abs(vram["cuda:1"] - 2000.0) < 1e-6, f"_estimate_vram cuda:1 failed: {vram}"

# ---------------------------------------------------------------------------
# 8. _simulate_distribution: offload threshold
# ---------------------------------------------------------------------------
# With 2 devices and threshold 0.5, each device has 50% share -> not > 0.5, so no offload
sim = _simulate_distribution(4, ["cuda:0", "cuda:1"], 0.5)
assert sim["offloaded_layers"] == [], f"Expected no offload at threshold 0.5, got {sim['offloaded_layers']}"

# With threshold 0.4, each device has 50% > 40% -> all layers offloaded
sim = _simulate_distribution(4, ["cuda:0", "cuda:1"], 0.4)
assert sorted(sim["offloaded_layers"]) == [0, 1, 2, 3], f"Expected all layers offloaded at threshold 0.4, got {sim['offloaded_layers']}"

# With 3 devices and threshold 0.5, each has ~33% < 50% -> no offload
sim = _simulate_distribution(6, ["cuda:0", "cuda:1", "cuda:2"], 0.5)
assert sim["offloaded_layers"] == [], f"Expected no offload at threshold 0.5 with 3 devices, got {sim['offloaded_layers']}"

# ---------------------------------------------------------------------------
# 9. PSN_Distribute_Model.run: happy path
# ---------------------------------------------------------------------------
node = PSN_Distribute_Model()
fake_model = object()  # MODEL is opaque in ComfyUI
result = node.run(fake_model, "cuda:0,cuda:1", 4, 0.5)
assert len(result) == 2, f"PSN_Distribute_Model.run should return 2 values, got {len(result)}"
assert result[0] is fake_model, "PSN_Distribute_Model.run should return the model unchanged"
assert isinstance(result[1], str), "PSN_Distribute_Model.run should return a string plan"
assert "cuda:0" in result[1], "Plan should mention cuda:0"
assert "cuda:1" in result[1], "Plan should mention cuda:1"

# ---------------------------------------------------------------------------
# 10. PSN_Distribute_Model.run: bad device_map
# ---------------------------------------------------------------------------
try:
    node.run(fake_model, "", 4, 0.5)
    assert False, "PSN_Distribute_Model.run should raise for empty device_map"
except ValueError:
    pass

try:
    node.run(fake_model, "tpu:0", 4, 0.5)
    assert False, "PSN_Distribute_Model.run should raise for tpu:0"
except ValueError:
    pass

# ---------------------------------------------------------------------------
# 11. PSN_Gather_Results.run: happy path
# ---------------------------------------------------------------------------
gather_node = PSN_Gather_Results()
img = torch.randn(1, 8, 8, 3)  # [B,H,W,C]
result = gather_node.run(fake_model, img, "Device map: cuda:0, cuda:1")
assert len(result) == 2, f"PSN_Gather_Results.run should return 2 values, got {len(result)}"
assert isinstance(result[0], torch.Tensor), "PSN_Gather_Results.run should return a tensor"
assert result[0].shape == (1, 8, 8, 3), f"Output shape mismatch: {result[0].shape}"
assert isinstance(result[1], str), "PSN_Gather_Results.run should return a string"
assert "2" in result[1], "Gather info should mention 2 devices"

# ---------------------------------------------------------------------------
# 12. PSN_Gather_Results.run: bad input (not a tensor)
# ---------------------------------------------------------------------------
try:
    gather_node.run(fake_model, "not a tensor", "")
    assert False, "PSN_Gather_Results.run should raise for non-tensor output"
except TypeError:
    pass

# ---------------------------------------------------------------------------
# 13. PSN_Gather_Results.run: bad input (wrong dims)
# ---------------------------------------------------------------------------
try:
    bad_img = torch.randn(1, 8, 8)  # 3D, not 4D
    gather_node.run(fake_model, bad_img, "")
    assert False, "PSN_Gather_Results.run should raise for 3D tensor"
except ValueError:
    pass

# ---------------------------------------------------------------------------
# 14. No in-place modification of input tensor
# ---------------------------------------------------------------------------
img = torch.randn(2, 4, 4, 3)
img_copy = img.clone()
gather_node.run(fake_model, img, "Device map: cuda:0")
assert torch.equal(img, img_copy), "Input tensor was modified in place!"

# ---------------------------------------------------------------------------
# 15. Edge case: single device
# ---------------------------------------------------------------------------
result = node.run(fake_model, "cpu", 8, 0.5)
assert result[0] is fake_model, "Single device: model should be unchanged"
assert "cpu" in result[1], "Single device: plan should mention cpu"

print("ok")
