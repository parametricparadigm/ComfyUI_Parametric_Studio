"""Tests for n_6_model_mixing_for_hybrid_styles.py"""
import json
import torch

from n_6_model_mixing_for_hybrid_styles import (
    PSN_ModelMix,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _parse_schedule,
    _weight_at,
    _blend_tensors,
)

# --- 1. Module-level mappings exist and are correct ---
assert "PSN_ModelMix" in NODE_CLASS_MAPPINGS, "PSN_ModelMix missing from NODE_CLASS_MAPPINGS"
assert NODE_CLASS_MAPPINGS["PSN_ModelMix"] is PSN_ModelMix
assert "PSN_ModelMix" in NODE_DISPLAY_NAME_MAPPINGS
assert NODE_DISPLAY_NAME_MAPPINGS["PSN_ModelMix"] == "Model Mix (Hybrid Styles)"

# --- 2. INPUT_TYPES has the required fields ---
it = PSN_ModelMix.INPUT_TYPES()
assert "required" in it
req = it["required"]
assert "model_a" in req and req["model_a"] == ("MODEL",)
assert "model_b" in req and req["model_b"] == ("MODEL",)
assert "mix_schedule" in req
assert "blend_mode" in req
assert list(req["blend_mode"][0]) == ["Linear", "Attention", "Feature"]

# --- 3. RETURN_TYPES and FUNCTION ---
assert PSN_ModelMix.RETURN_TYPES == ("MODEL",)
assert PSN_ModelMix.FUNCTION == "run"
assert PSN_ModelMix.CATEGORY == "ParametricStudio/ModelMixing"

# --- 4. Schedule parsing: valid schedule ---
pairs = _parse_schedule("[[0.0, 1.0], [0.5, 0.5], [1.0, 0.0]]")
assert pairs == [(0.0, 1.0), (0.5, 0.5), (1.0, 0.0)]

# --- 5. Weight at step 0 is 1.0 (100% Model A) ---
w0 = _weight_at(pairs, 0.0)
assert abs(w0 - 1.0) < 1e-9, f"Expected weight 1.0 at step 0, got {w0}"

# --- 6. Weight at step 1.0 is 0.0 (100% Model B) ---
w1 = _weight_at(pairs, 1.0)
assert abs(w1 - 0.0) < 1e-9, f"Expected weight 0.0 at step 1, got {w1}"

# --- 7. Weight at step 0.5 is 0.5 (50/50) ---
w05 = _weight_at(pairs, 0.5)
assert abs(w05 - 0.5) < 1e-9, f"Expected weight 0.5 at step 0.5, got {w05}"

# --- 8. Linear blend: at step 0, output equals t_a ---
t_a = torch.tensor([[1.0, 2.0], [3.0, 4.0]])
t_b = torch.tensor([[5.0, 6.0], [7.0, 8.0]])
blended = _blend_tensors(t_a, t_b, 1.0, "Linear")
assert torch.allclose(blended, t_a), f"Linear blend at w=1 should equal t_a, got {blended}"

# --- 9. Linear blend: at step 1, output equals t_b ---
blended = _blend_tensors(t_a, t_b, 0.0, "Linear")
assert torch.allclose(blended, t_b), f"Linear blend at w=0 should equal t_b, got {blended}"

# --- 10. Linear blend: at w=0.5, output is the mean ---
expected = 0.5 * t_a + 0.5 * t_b
blended = _blend_tensors(t_a, t_b, 0.5, "Linear")
assert torch.allclose(blended, expected), f"Linear blend at w=0.5 should be the mean, got {blended}"

# --- 11. Attention blend clamps to [0, 1] ---
t_a_big = torch.tensor([[2.0, -1.0]])
t_b_big = torch.tensor([[3.0, 0.5]])
blended = _blend_tensors(t_a_big, t_b_big, 0.5, "Attention")
assert (blended >= 0.0).all() and (blended <= 1.0).all(), f"Attention blend should be in [0,1], got {blended}"

# --- 12. Feature blend produces a valid tensor of the same shape ---
blended = _blend_tensors(t_a, t_b, 0.5, "Feature")
assert blended.shape == t_a.shape, f"Feature blend shape mismatch: {blended.shape}"

# --- 13. Bad input: invalid JSON ---
try:
    _parse_schedule("not json")
    assert False, "Should have raised ValueError for invalid JSON"
except ValueError:
    pass

# --- 14. Bad input: step_percent out of range ---
try:
    _parse_schedule("[[1.5, 0.5]]")
    assert False, "Should have raised ValueError for step_percent > 1"
except ValueError:
    pass

# --- 15. Bad input: weight_a out of range ---
try:
    _parse_schedule("[[0.5, 1.5]]")
    assert False, "Should have raised ValueError for weight_a > 1"
except ValueError:
    pass

# --- 16. Bad input: empty schedule ---
try:
    _parse_schedule("[]")
    assert False, "Should have raised ValueError for empty schedule"
except ValueError:
    pass

# --- 17. Bad input: wrong pair length ---
try:
    _parse_schedule("[[0.5, 0.5, 0.5]]")
    assert False, "Should have raised ValueError for 3-element pair"
except ValueError:
    pass

# --- 18. Bad input: non-numeric values ---
try:
    _parse_schedule("[[\"a\", 0.5]]")
    assert False, "Should have raised ValueError for non-numeric step_percent"
except ValueError:
    pass

# --- 19. Shape mismatch raises ---
try:
    _blend_tensors(torch.tensor([[1.0]]), torch.tensor([[1.0, 2.0]]), 0.5, "Linear")
    assert False, "Should have raised ValueError for shape mismatch"
except ValueError:
    pass

# --- 20. Unknown blend mode raises ---
try:
    _blend_tensors(t_a, t_b, 0.5, "Bogus")
    assert False, "Should have raised ValueError for unknown blend mode"
except ValueError:
    pass

# --- 21. End-to-end: run the node with a simple schedule ---
node = PSN_ModelMix()
model_a = {"model": "A"}
model_b = {"model": "B"}
schedule = "[[0.0, 1.0], [1.0, 0.0]]"
out = node.run(model_a, model_b, schedule, "Linear")
assert len(out) == 1
result = out[0]
assert result["model_a"] is model_a
assert result["model_b"] is model_b
assert result["blend_mode"] == "Linear"
# Check get_weight
assert abs(result["get_weight"](0.0) - 1.0) < 1e-9
assert abs(result["get_weight"](1.0) - 0.0) < 1e-9
assert abs(result["get_weight"](0.5) - 0.5) < 1e-9
# Check blend
blended = result["blend"](t_a, t_b, 0.0)
assert torch.allclose(blended, t_a)
blended = result["blend"](t_a, t_b, 1.0)
assert torch.allclose(blended, t_b)

# --- 22. End-to-end: Attention mode ---
out = node.run(model_a, model_b, "[[0.0, 1.0], [1.0, 0.0]]", "Attention")
result = out[0]
blended = result["blend"](t_a_big, t_b_big, 0.5)
assert (blended >= 0.0).all() and (blended <= 1.0).all()

# --- 23. End-to-end: Feature mode ---
out = node.run(model_a, model_b, "[[0.0, 1.0], [1.0, 0.0]]", "Feature")
result = out[0]
blended = result["blend"](t_a, t_b, 0.5)
assert blended.shape == t_a.shape

# --- 24. Bad input to run: invalid schedule string ---
try:
    node.run(model_a, model_b, "not json", "Linear")
    assert False, "Should have raised ValueError for invalid schedule in run"
except ValueError:
    pass

# --- 25. Schedule with a single point (constant weight) ---
pairs = _parse_schedule("[[0.0, 0.7]]")
assert abs(_weight_at(pairs, 0.0) - 0.7) < 1e-9
assert abs(_weight_at(pairs, 0.5) - 0.7) < 1e-9
assert abs(_weight_at(pairs, 1.0) - 0.7) < 1e-9

# --- 26. Schedule with unsorted input gets sorted ---
pairs = _parse_schedule("[[1.0, 0.0], [0.0, 1.0]]")
assert pairs == [(0.0, 1.0), (1.0, 0.0)]

print("ok")
