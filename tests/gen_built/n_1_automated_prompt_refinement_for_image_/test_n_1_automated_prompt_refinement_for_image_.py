"""Tests for n_1_automated_prompt_refinement_for_image_.py

Run with:  python3 -B test_n_1_automated_prompt_refinement_for_image_.py
Must print 'ok' and exit 0.
"""

import importlib.util
import os
import sys

# Load the module from the same directory.
_here = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "n1_mod", os.path.join(_here, "n_1_automated_prompt_refinement_for_image_.py")
)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)


# ---------------------------------------------------------------------------
# 1. Module-level registration
# ---------------------------------------------------------------------------
assert hasattr(mod, "NODE_CLASS_MAPPINGS"), "NODE_CLASS_MAPPINGS missing"
assert hasattr(mod, "NODE_DISPLAY_NAME_MAPPINGS"), "NODE_DISPLAY_NAME_MAPPINGS missing"
assert "PSN_Prompt_Enhancer" in mod.NODE_CLASS_MAPPINGS
assert "PSN_Prompt_Validator" in mod.NODE_CLASS_MAPPINGS
assert mod.NODE_DISPLAY_NAME_MAPPINGS["PSN_Prompt_Enhancer"] == "PSN Prompt Enhancer"
assert mod.NODE_DISPLAY_NAME_MAPPINGS["PSN_Prompt_Validator"] == "PSN Prompt Validator"
print("1. registration ok")


# ---------------------------------------------------------------------------
# 2. INPUT_TYPES / RETURN_TYPES / FUNCTION / CATEGORY
# ---------------------------------------------------------------------------
enh = mod.PSN_Prompt_Enhancer
inp = enh.INPUT_TYPES()
assert "required" in inp
assert "raw_prompt" in inp["required"]
assert "target_model" in inp["required"]
assert "verbosity" in inp["required"]
assert enh.RETURN_TYPES == ("STRING", "STRING")
assert enh.RETURN_NAMES == ("enhanced_prompt", "negative_prompt")
assert enh.FUNCTION == "run"
assert enh.CATEGORY == "ParametricStudio/Prompt"

val = mod.PSN_Prompt_Validator
vinp = val.INPUT_TYPES()
assert "prompt" in vinp["required"]
assert "ban_list" in vinp["required"]
assert val.RETURN_TYPES == ("STRING", "STRING")
assert val.RETURN_NAMES == ("valid_prompt", "warnings")
assert val.FUNCTION == "run"
assert val.CATEGORY == "ParametricStudio/Prompt"
print("2. input/output types ok")


# ---------------------------------------------------------------------------
# 3. Enhancer: basic expansion
# ---------------------------------------------------------------------------
enhanced, negative = enh().run("a cat", "SDXL", 3)
assert isinstance(enhanced, str)
assert isinstance(negative, str)
assert len(enhanced) > len("a cat"), "enhanced prompt should be longer than input"
assert "a cat" in enhanced, "original prompt should be preserved"
assert "masterpiece" in enhanced, "SDXL style tag should appear at verbosity 3"
assert "blurry" in negative, "negative prompt should contain 'blurry'"
print("3. enhancer basic ok")


# ---------------------------------------------------------------------------
# 4. Enhancer: verbosity scaling
# ---------------------------------------------------------------------------
e1, _ = enh().run("a dog", "Flux", 1)
e5, _ = enh().run("a dog", "Flux", 5)
assert len(e5) >= len(e1), "higher verbosity should produce a longer or equal prompt"
# At verbosity 1 only the first style entry should be present.
assert "highly detailed" in e1
# At verbosity 5 all five style entries should be present.
assert "professional photography" in e5
print("4. verbosity scaling ok")


# ---------------------------------------------------------------------------
# 5. Enhancer: empty prompt edge case
# ---------------------------------------------------------------------------
enhanced_empty, neg_empty = enh().run("", "SD1.5", 3)
assert isinstance(enhanced_empty, str)
assert len(enhanced_empty) > 0, "empty prompt should still produce a non-empty enhanced prompt"
assert "blurry" in neg_empty
print("5. enhancer empty prompt ok")


# ---------------------------------------------------------------------------
# 6. Enhancer: bad input (invalid target_model)
# ---------------------------------------------------------------------------
try:
    enh().run("test", "INVALID_MODEL", 3)
    assert False, "should have raised ValueError for invalid target_model"
except ValueError:
    pass
print("6. enhancer bad model ok")


# ---------------------------------------------------------------------------
# 7. Enhancer: bad input (verbosity out of range)
# ---------------------------------------------------------------------------
try:
    enh().run("test", "SDXL", 0)
    assert False, "should have raised ValueError for verbosity 0"
except ValueError:
    pass
try:
    enh().run("test", "SDXL", 6)
    assert False, "should have raised ValueError for verbosity 6"
except ValueError:
    pass
print("7. enhancer bad verbosity ok")


# ---------------------------------------------------------------------------
# 8. Validator: banned token removal
# ---------------------------------------------------------------------------
valid, warnings = val().run("a beautiful sunset with clouds", "clouds,sunset", 3) if False else val().run("a beautiful sunset with clouds", "clouds,sunset")
assert "clouds" not in valid.lower(), "banned token 'clouds' should be removed"
assert "sunset" not in valid.lower(), "banned token 'sunset' should be removed"
assert "beautiful" in valid.lower(), "non-banned token should remain"
assert "clouds" in warnings.lower(), "warnings should mention removed token 'clouds'"
assert "sunset" in warnings.lower(), "warnings should mention removed token 'sunset'"
print("8. validator banned removal ok")


# ---------------------------------------------------------------------------
# 9. Validator: no banned tokens -> no warnings
# ---------------------------------------------------------------------------
valid2, warnings2 = val().run("a clean prompt", "badword")
assert warnings2 == "", "no warnings expected when no banned tokens found"
assert "clean" in valid2.lower()
print("9. validator no-ban ok")


# ---------------------------------------------------------------------------
# 10. Validator: empty prompt edge case
# ---------------------------------------------------------------------------
valid3, warnings3 = val().run("", "badword")
assert valid3 == "", "empty prompt should stay empty"
assert warnings3 == "", "no warnings for empty prompt"
print("10. validator empty prompt ok")


# ---------------------------------------------------------------------------
# 11. Validator: token budget enforcement
# ---------------------------------------------------------------------------
# Build a very long prompt (100 words) and verify it gets truncated.
long_prompt = ", ".join("word%d" % i for i in range(100))
valid4, _ = val().run(long_prompt, "")
tokens = mod._tokenize(valid4)
assert len(tokens) <= mod.CLIP_TOKEN_LIMIT, (
    "prompt should be truncated to CLIP token limit, got %d tokens" % len(tokens)
)
print("11. validator token budget ok")


# ---------------------------------------------------------------------------
# 12. Validator: bad input (non-string prompt)
# ---------------------------------------------------------------------------
try:
    val().run(12345, "badword")
    assert False, "should have raised TypeError for non-string prompt"
except TypeError:
    pass
print("12. validator bad input ok")


# ---------------------------------------------------------------------------
# 13. Enhancer: bad input (non-string raw_prompt)
# ---------------------------------------------------------------------------
try:
    enh().run(12345, "SDXL", 3)
    assert False, "should have raised TypeError for non-string raw_prompt"
except TypeError:
    pass
print("13. enhancer bad input ok")


# ---------------------------------------------------------------------------
# 14. All target models produce valid output
# ---------------------------------------------------------------------------
for model_name in ("SDXL", "Flux", "SD1.5"):
    e, n = enh().run("test subject", model_name, 3)
    assert isinstance(e, str) and len(e) > 0
    assert isinstance(n, str) and len(n) > 0
print("14. all models ok")

print("ok")
