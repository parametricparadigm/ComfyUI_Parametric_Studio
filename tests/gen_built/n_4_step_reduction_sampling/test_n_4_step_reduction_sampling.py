"""Tests for n_4_step_reduction_sampling.py"""

import torch

from n_4_step_reduction_sampling import (
    PSN_Step_Skip_Accelerator,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _linear_forecast,
    _chebyshev_forecast,
)


# ---------------------------------------------------------------------------
# 1. Module-level mappings exist and are correct
# ---------------------------------------------------------------------------
assert "PSN_Step_Skip_Accelerator" in NODE_CLASS_MAPPINGS, "node missing from mappings"
assert NODE_CLASS_MAPPINGS["PSN_Step_Skip_Accelerator"] is PSN_Step_Skip_Accelerator
assert "PSN_Step_Skip_Accelerator" in NODE_DISPLAY_NAME_MAPPINGS


# ---------------------------------------------------------------------------
# 2. INPUT_TYPES has the required fields
# ---------------------------------------------------------------------------
it = PSN_Step_Skip_Accelerator.INPUT_TYPES()
assert "required" in it
assert "model" in it["required"]
assert "skip_ratio" in it["required"]
assert "forecast_method" in it["required"]


# ---------------------------------------------------------------------------
# 3. Basic run: returns a patched model dict, input not mutated
# ---------------------------------------------------------------------------
model_in = {"model_options": {"existing_key": 42}}
result = PSN_Step_Skip_Accelerator().run(model_in, 0.25, "linear")
assert len(result) == 1
patched = result[0]
assert isinstance(patched, dict)
assert "_psn_step_skip_hook" in patched
assert "psn_step_skip" in patched["model_options"]
# input not mutated
assert "_psn_step_skip_hook" not in model_in
assert model_in["model_options"] == {"existing_key": 42}


# ---------------------------------------------------------------------------
# 4. Hook: first two calls do NOT skip (need history >= 2)
# ---------------------------------------------------------------------------
hook = patched["_psn_step_skip_hook"]
# step 1
should_skip, pred = hook(torch.tensor([1.0, 2.0]))
assert should_skip is False
assert pred is None
# step 2
should_skip, pred = hook(torch.tensor([2.0, 4.0]))
assert should_skip is False  # step 2, k=4 (1/0.25), 2 % 4 != 0


# ---------------------------------------------------------------------------
# 5. Hook: step 4 SHOULD skip (k = round(1/0.25) = 4)
# ---------------------------------------------------------------------------
hook(torch.tensor([3.0, 6.0]))  # step 3
should_skip, pred = hook(torch.tensor([4.0, 8.0]))  # step 4
assert should_skip is True, "expected skip at step 4"
assert pred is not None
assert pred.shape == torch.Size([2])
# linear forecast: last two are [3,6] and [4,8], slope = [1,2], pred = [5,10]
assert torch.allclose(pred, torch.tensor([5.0, 10.0])), f"linear forecast wrong: {pred}"


# ---------------------------------------------------------------------------
# 6. Bad input: skip_ratio out of range raises ValueError
# ---------------------------------------------------------------------------
try:
    PSN_Step_Skip_Accelerator().run(model_in, 0.75, "linear")
    assert False, "should have raised ValueError"
except ValueError:
    pass


# ---------------------------------------------------------------------------
# 7. Bad input: invalid forecast_method raises ValueError
# ---------------------------------------------------------------------------
try:
    PSN_Step_Skip_Accelerator().run(model_in, 0.25, "quadratic")
    assert False, "should have raised ValueError"
except ValueError:
    pass


# ---------------------------------------------------------------------------
# 8. Bad input: model not a dict raises TypeError
# ---------------------------------------------------------------------------
try:
    PSN_Step_Skip_Accelerator().run("not a dict", 0.25, "linear")
    assert False, "should have raised TypeError"
except TypeError:
    pass


# ---------------------------------------------------------------------------
# 9. Chebyshev forecast: constant sequence predicts the same value
# ---------------------------------------------------------------------------
hist = [torch.tensor([5.0, 5.0]) for _ in range(4)]
pred = _chebyshev_forecast(hist, step_idx=4, order=3)
assert torch.allclose(pred, torch.tensor([5.0, 5.0])), f"chebyshev constant wrong: {pred}"


# ---------------------------------------------------------------------------
# 10. skip_ratio = 0.0 never skips
# ---------------------------------------------------------------------------
result0 = PSN_Step_Skip_Accelerator().run(model_in, 0.0, "linear")
patched0 = result0[0]
hook0 = patched0["_psn_step_skip_hook"]
for i in range(10):
    should_skip, _ = hook0(torch.tensor([float(i)]))
    assert should_skip is False, f"should not skip at step {i+1} with ratio 0"


# ---------------------------------------------------------------------------
# 11. RETURN_TYPES and FUNCTION are correct
# ---------------------------------------------------------------------------
assert PSN_Step_Skip_Accelerator.RETURN_TYPES == ("MODEL",)
assert PSN_Step_Skip_Accelerator.FUNCTION == "run"
assert PSN_Step_Skip_Accelerator.CATEGORY == "ParametricStudio/Sampling"


print("ok")
