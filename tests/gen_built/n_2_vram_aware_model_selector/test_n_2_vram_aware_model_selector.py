"""Tests for n_2_vram_aware_model_selector."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from n_2_vram_aware_model_selector import (
    PSN_VRAMModelSelector,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _estimate_vram_gb,
    _normalize_dtype,
)

_GB = 1024.0 ** 3


def _entry(name, path, size_gb, dtype="fp16"):
    return {
        "name": name,
        "path": path,
        "file_size_bytes": int(size_gb * _GB),
        "dtype": dtype,
    }


# ---------------------------------------------------------------------------
# 1. Basic selection: 1GB, 5GB, 10GB models, budget 6GB -> 5GB selected
# ---------------------------------------------------------------------------
node = PSN_VRAMModelSelector()
models = [
    _entry("small", "/models/small.safetensors", 1.0),
    _entry("medium", "/models/medium.safetensors", 5.0),
    _entry("large", "/models/large.safetensors", 10.0),
]
path, name = node.run(models, 6.0, False)
assert name == "medium", f"expected medium, got {name}"
assert path == "/models/medium.safetensors", f"expected medium path, got {path}"

# ---------------------------------------------------------------------------
# 2. Budget too small for any model -> empty strings
# ---------------------------------------------------------------------------
path, name = node.run(models, 0.5, False)
assert path == "", f"expected empty path, got {path!r}"
assert name == "", f"expected empty name, got {name!r}"

# ---------------------------------------------------------------------------
# 3. prefer_quantized=True picks the most quantized model that fits
# ---------------------------------------------------------------------------
models_q = [
    _entry("fp16_big", "/m/fp16_big.safetensors", 4.0, "fp16"),
    _entry("int8_mid", "/m/int8_mid.safetensors", 3.0, "int8"),
    _entry("int4_small", "/m/int4_small.safetensors", 2.0, "int4"),
]
path, name = node.run(models_q, 5.0, True)
assert name == "int4_small", f"expected int4_small, got {name}"

# ---------------------------------------------------------------------------
# 4. prefer_quantized=False picks the largest (best quality) model that fits
# ---------------------------------------------------------------------------
path, name = node.run(models_q, 5.0, False)
assert name == "fp16_big", f"expected fp16_big (largest that fits), got {name}"

# ---------------------------------------------------------------------------
# 5. Edge: empty model list -> empty strings
# ---------------------------------------------------------------------------
path, name = node.run([], 8.0, False)
assert path == "" and name == ""

# ---------------------------------------------------------------------------
# 6. Bad input: model_list is not a list -> TypeError
# ---------------------------------------------------------------------------
try:
    node.run("not a list", 8.0, False)
    assert False, "expected TypeError"
except TypeError:
    pass

# ---------------------------------------------------------------------------
# 7. Bad input: max_vram_gb <= 0 -> ValueError
# ---------------------------------------------------------------------------
try:
    node.run(models, -1.0, False)
    assert False, "expected ValueError"
except ValueError:
    pass

# ---------------------------------------------------------------------------
# 8. Entry with param_count instead of file_size_bytes
# ---------------------------------------------------------------------------
# 1B params * 2 bytes (fp16) = 2 GB
entry_pc = {"name": "pc_model", "path": "/m/pc.safetensors", "param_count": 1_000_000_000, "dtype": "fp16"}
vram = _estimate_vram_gb(entry_pc)
assert abs(vram - 1.862645149230957) < 0.01, f"expected ~1.86 GB, got {vram}"

# ---------------------------------------------------------------------------
# 9. _normalize_dtype handles aliases
# ---------------------------------------------------------------------------
assert _normalize_dtype("float16") == "fp16"
assert _normalize_dtype("bfloat16") == "bf16"
assert _normalize_dtype("q8") == "int8"
assert _normalize_dtype(None) == "fp16"
assert _normalize_dtype("unknown_xyz") == "fp16"  # fallback

# ---------------------------------------------------------------------------
# 10. NODE_CLASS_MAPPINGS and display names are correct
# ---------------------------------------------------------------------------
assert "PSN_VRAMModelSelector" in NODE_CLASS_MAPPINGS
assert NODE_CLASS_MAPPINGS["PSN_VRAMModelSelector"] is PSN_VRAMModelSelector
assert NODE_DISPLAY_NAME_MAPPINGS["PSN_VRAMModelSelector"] == "VRAM-Aware Model Selector"

# ---------------------------------------------------------------------------
# 11. INPUT_TYPES / RETURN_TYPES / FUNCTION / CATEGORY sanity
# ---------------------------------------------------------------------------
it = PSN_VRAMModelSelector.INPUT_TYPES()
assert "model_list" in it["required"]
assert "max_vram_gb" in it["required"]
assert "prefer_quantized" in it["required"]
assert PSN_VRAMModelSelector.RETURN_TYPES == ("STRING", "STRING")
assert PSN_VRAMModelSelector.RETURN_NAMES == ("SELECTED_MODEL_PATH", "SELECTED_MODEL_NAME")
assert PSN_VRAMModelSelector.FUNCTION == "run"
assert PSN_VRAMModelSelector.CATEGORY == "ParametricStudio/Models"

# ---------------------------------------------------------------------------
# 12. Single model that fits exactly at the budget boundary
# ---------------------------------------------------------------------------
models_exact = [_entry("exact", "/m/exact.safetensors", 6.0)]
path, name = node.run(models_exact, 6.0, False)
assert name == "exact", f"expected exact, got {name}"

print("ok")
