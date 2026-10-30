"""Tests for n_1_vram_aware_model_switching."""

import torch

from n_1_vram_aware_model_switching import (
    PSN_VRAM_Check,
    PSN_VRAM_Model_Switch,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


# ---------------------------------------------------------------------------
# 1. Module-level registration
# ---------------------------------------------------------------------------

def test_node_mappings():
    assert "PSN_VRAM_Check" in NODE_CLASS_MAPPINGS
    assert "PSN_VRAM_Model_Switch" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_VRAM_Check"] is PSN_VRAM_Check
    assert NODE_CLASS_MAPPINGS["PSN_VRAM_Model_Switch"] is PSN_VRAM_Model_Switch
    assert "PSN_VRAM_Check" in NODE_DISPLAY_NAME_MAPPINGS
    assert "PSN_VRAM_Model_Switch" in NODE_DISPLAY_NAME_MAPPINGS


# ---------------------------------------------------------------------------
# 2. INPUT_TYPES structure
# ---------------------------------------------------------------------------

def test_input_types():
    it = PSN_VRAM_Model_Switch.INPUT_TYPES()
    assert "required" in it
    assert "high_res_model" in it["required"]
    assert "low_res_model" in it["required"]
    assert "vram_check" in it["required"]
    assert it["required"]["high_res_model"] == ("MODEL",)
    assert it["required"]["low_res_model"] == ("MODEL",)
    assert it["required"]["vram_check"] == ("BOOLEAN",)

    it2 = PSN_VRAM_Check.INPUT_TYPES()
    assert "threshold_gb" in it2["required"]


# ---------------------------------------------------------------------------
# 3. RETURN_TYPES / FUNCTION / CATEGORY
# ---------------------------------------------------------------------------

def test_return_types():
    assert PSN_VRAM_Model_Switch.RETURN_TYPES == ("MODEL",)
    assert PSN_VRAM_Model_Switch.RETURN_NAMES == ("selected_model",)
    assert PSN_VRAM_Model_Switch.FUNCTION == "run"
    assert PSN_VRAM_Model_Switch.CATEGORY == "ParametricStudio/Model"

    assert PSN_VRAM_Check.RETURN_TYPES == ("BOOLEAN",)
    assert PSN_VRAM_Check.RETURN_NAMES == ("vram_ok",)
    assert PSN_VRAM_Check.FUNCTION == "run"


# ---------------------------------------------------------------------------
# 4. Switch selects high_res_model when vram_check is True
# ---------------------------------------------------------------------------

def test_switch_high_res():
    node = PSN_VRAM_Model_Switch()
    high = torch.randn(2, 3, 4, 5)   # stand-in for a MODEL object
    low = torch.randn(2, 3, 4, 5)
    result = node.run(high, low, True)
    assert len(result) == 1
    assert result[0] is high


# ---------------------------------------------------------------------------
# 5. Switch selects low_res_model when vram_check is False
# ---------------------------------------------------------------------------

def test_switch_low_res():
    node = PSN_VRAM_Model_Switch()
    high = torch.randn(2, 3, 4, 5)
    low = torch.randn(2, 3, 4, 5)
    result = node.run(high, low, False)
    assert len(result) == 1
    assert result[0] is low


# ---------------------------------------------------------------------------
# 6. Bad input: vram_check not a boolean
# ---------------------------------------------------------------------------

def test_switch_bad_vram_check():
    node = PSN_VRAM_Model_Switch()
    high = torch.randn(1, 1, 1, 1)
    low = torch.randn(1, 1, 1, 1)
    try:
        node.run(high, low, "yes")
        assert False, "expected TypeError"
    except TypeError:
        pass


# ---------------------------------------------------------------------------
# 7. Bad input: None model
# ---------------------------------------------------------------------------

def test_switch_none_model():
    node = PSN_VRAM_Model_Switch()
    low = torch.randn(1, 1, 1, 1)
    try:
        node.run(None, low, True)
        assert False, "expected ValueError"
    except ValueError:
        pass
    try:
        node.run(low, None, False)
        assert False, "expected ValueError"
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# 8. VRAM Check: force_result=True returns True
# ---------------------------------------------------------------------------

def test_vram_check_force_true():
    node = PSN_VRAM_Check()
    result = node.run(threshold_gb=100.0, force_result=True)
    assert result == (True,)


# ---------------------------------------------------------------------------
# 9. VRAM Check: force_result=False on CPU returns False (no CUDA)
# ---------------------------------------------------------------------------

def test_vram_check_cpu():
    node = PSN_VRAM_Check()
    # On a CPU-only machine free_gb == 0.0, so any positive threshold fails.
    result = node.run(threshold_gb=1.0, force_result=False)
    assert result == (False,)


# ---------------------------------------------------------------------------
# 10. VRAM Check: threshold 0 always passes (0 >= 0)
# ---------------------------------------------------------------------------

def test_vram_check_zero_threshold():
    node = PSN_VRAM_Check()
    result = node.run(threshold_gb=0.0, force_result=False)
    assert result == (True,)


# ---------------------------------------------------------------------------
# 11. Inputs are not mutated
# ---------------------------------------------------------------------------

def test_no_mutation():
    node = PSN_VRAM_Model_Switch()
    high = torch.randn(2, 3, 4, 5)
    low = torch.randn(2, 3, 4, 5)
    high_before = high.clone()
    low_before = low.clone()
    node.run(high, low, True)
    node.run(high, low, False)
    assert torch.equal(high, high_before)
    assert torch.equal(low, low_before)


# ---------------------------------------------------------------------------
# 12. End-to-end: VRAM Check -> Switch
# ---------------------------------------------------------------------------

def test_end_to_end():
    check_node = PSN_VRAM_Check()
    switch_node = PSN_VRAM_Model_Switch()
    high = torch.randn(1, 4, 8, 8)
    low = torch.randn(1, 4, 8, 8)

    # Force VRAM check to True -> should select high_res_model
    vram_ok = check_node.run(threshold_gb=1.0, force_result=True)[0]
    selected = switch_node.run(high, low, vram_ok)[0]
    assert selected is high

    # Force VRAM check to False (simulate low VRAM) -> should select low_res_model
    # We can't force False via force_result, so use a very high threshold on CPU
    vram_ok_low = check_node.run(threshold_gb=9999.0, force_result=False)[0]
    assert vram_ok_low is False
    selected_low = switch_node.run(high, low, vram_ok_low)[0]
    assert selected_low is low


if __name__ == "__main__":
    test_node_mappings()
    test_input_types()
    test_return_types()
    test_switch_high_res()
    test_switch_low_res()
    test_switch_bad_vram_check()
    test_switch_none_model()
    test_vram_check_force_true()
    test_vram_check_cpu()
    test_vram_check_zero_threshold()
    test_no_mutation()
    test_end_to_end()
    print("ok")
