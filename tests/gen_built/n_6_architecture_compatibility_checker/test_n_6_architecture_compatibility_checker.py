"""Tests for n_6_architecture_compatibility_checker.

Run:  python3 -B test_n_6_architecture_compatibility_checker.py
Must print 'ok' and exit 0.
"""

import torch
from n_6_architecture_compatibility_checker import (
    PSN_ArchCompatibilityChecker,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _normalize_arch,
    _normalize_dtype,
    _get_model_arch,
    _get_model_dtype,
)

node = PSN_ArchCompatibilityChecker()

# ---------------------------------------------------------------------------
# 1. Module-level registration
# ---------------------------------------------------------------------------
assert "PSN_ArchCompatibilityChecker" in NODE_CLASS_MAPPINGS, "node not registered"
assert NODE_CLASS_MAPPINGS["PSN_ArchCompatibilityChecker"] is PSN_ArchCompatibilityChecker
assert "PSN_ArchCompatibilityChecker" in NODE_DISPLAY_NAME_MAPPINGS

# ---------------------------------------------------------------------------
# 2. INPUT_TYPES / RETURN_TYPES / FUNCTION / CATEGORY
# ---------------------------------------------------------------------------
it = PSN_ArchCompatibilityChecker.INPUT_TYPES()
assert "required" in it
assert "model" in it["required"]
assert it["required"]["model"] == ("MODEL",)
assert "expected_arch" in it["required"]
assert "expected_dtype" in it["required"]
assert PSN_ArchCompatibilityChecker.RETURN_TYPES == ("BOOLEAN", "STRING")
assert PSN_ArchCompatibilityChecker.RETURN_NAMES == ("IS_COMPATIBLE", "MISMATCH_DETAILS")
assert PSN_ArchCompatibilityChecker.FUNCTION == "run"
assert PSN_ArchCompatibilityChecker.CATEGORY.startswith("ParametricStudio/")

# ---------------------------------------------------------------------------
# 3. SD1.5 model checked against "sdxl" -> incompatible
# ---------------------------------------------------------------------------
sd15_model = {
    "model_config": {"model_type": "sd15"},
    "model_options": {"dtype": torch.float16},
}
compat, details = node.run(sd15_model, "sdxl", "fp16")
assert compat is False, f"expected incompatible, got {compat}"
assert "architecture" in details.lower(), f"details should mention architecture: {details}"

# ---------------------------------------------------------------------------
# 4. SDXL model checked against "sdxl" -> compatible
# ---------------------------------------------------------------------------
sdxl_model = {
    "model_config": {"model_type": "sdxl"},
    "model_options": {"dtype": torch.float16},
}
compat, details = node.run(sdxl_model, "sdxl", "fp16")
assert compat is True, f"expected compatible, got {compat}; details={details}"
assert details == "", f"expected empty details, got: {details}"

# ---------------------------------------------------------------------------
# 5. Dtype mismatch: SDXL fp32 checked against fp16 -> incompatible
# ---------------------------------------------------------------------------
sdxl_fp32 = {
    "model_config": {"model_type": "sdxl"},
    "model_options": {"dtype": torch.float32},
}
compat, details = node.run(sdxl_fp32, "sdxl", "fp16")
assert compat is False, f"expected incompatible (dtype), got {compat}"
assert "dtype" in details.lower(), f"details should mention dtype: {details}"

# ---------------------------------------------------------------------------
# 6. Unknown arch fallback: model with no recognisable arch
# ---------------------------------------------------------------------------
mystery_model = {"model_options": {"dtype": torch.float16}}
compat, details = node.run(mystery_model, "sdxl", "fp16")
assert compat is False, f"expected incompatible (unknown arch), got {compat}"
assert "unknown" in details.lower(), f"details should mention unknown: {details}"

# ---------------------------------------------------------------------------
# 7. expected_arch='unknown' skips arch check (only dtype matters)
# ---------------------------------------------------------------------------
compat, details = node.run(mystery_model, "unknown", "fp16")
assert compat is True, f"expected compatible when arch=unknown, got {compat}; details={details}"

# ---------------------------------------------------------------------------
# 8. Bad input: model is None -> should not crash, returns incompatible
# ---------------------------------------------------------------------------
compat, details = node.run(None, "sdxl", "fp16")
assert compat is False, f"expected incompatible for None model, got {compat}"
assert "unknown" in details.lower()

# ---------------------------------------------------------------------------
# 9. Bad input: expected_dtype is garbage string -> treated as no dtype check
# ---------------------------------------------------------------------------
compat, details = node.run(sdxl_model, "sdxl", "not_a_real_dtype")
# _normalize_dtype returns None for unrecognised strings, so dtype check is skipped
assert compat is True, f"expected compatible (dtype check skipped), got {compat}; details={details}"

# ---------------------------------------------------------------------------
# 10. Helper: _normalize_arch
# ---------------------------------------------------------------------------
assert _normalize_arch("SDXL") == "sdxl"
assert _normalize_arch("sd_15") == "sd15"
assert _normalize_arch("flux-dev") == "flux"
assert _normalize_arch("") == "unknown"
assert _normalize_arch(None) == "unknown"

# ---------------------------------------------------------------------------
# 11. Helper: _normalize_dtype
# ---------------------------------------------------------------------------
assert _normalize_dtype("fp16") == torch.float16
assert _normalize_dtype("FP32") == torch.float32
assert _normalize_dtype("bf16") == torch.bfloat16
assert _normalize_dtype("garbage") is None
assert _normalize_dtype(None) is None

# ---------------------------------------------------------------------------
# 12. Helper: _get_model_dtype from a torch.nn.Module with parameters
# ---------------------------------------------------------------------------
class _TinyNet(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.linear = torch.nn.Linear(4, 4, dtype=torch.float32)

    @property
    def dtype(self):
        return self.linear.weight.dtype

tiny = _TinyNet()
assert _get_model_dtype(tiny) == torch.float32

# ---------------------------------------------------------------------------
# 13. Helper: _get_model_arch from a torch.nn.Module with model_type attr
# ---------------------------------------------------------------------------
class _FakeModel:
    model_type = "sdxl"
    dtype = torch.float16

fm = _FakeModel()
assert _get_model_arch(fm) == "sdxl"
assert _get_model_dtype(fm) == torch.float16

# ---------------------------------------------------------------------------
# 14. Both arch and dtype mismatch -> both mentioned
# ---------------------------------------------------------------------------
bad_model = {
    "model_config": {"model_type": "sd15"},
    "model_options": {"dtype": torch.float32},
}
compat, details = node.run(bad_model, "sdxl", "fp16")
assert compat is False
assert "architecture" in details.lower()
assert "dtype" in details.lower()

print("ok")
