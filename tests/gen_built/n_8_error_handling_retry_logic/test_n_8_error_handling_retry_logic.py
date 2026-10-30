"""Tests for n_8_error_handling_retry_logic.py"""

import torch
from n_8_error_handling_retry_logic import (
    PSN_Error_Catcher,
    PSN_Retry_Switch,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def test_error_catcher_success():
    """When error_flag is False, output passes through and error_message is empty."""
    node = PSN_Error_Catcher()
    img = torch.rand(1, 4, 4, 3)
    success, msg = node.run(img, False, "some error")
    assert torch.equal(success, img), "Output should pass through unchanged on success"
    assert msg == "", "Error message should be empty on success"


def test_error_catcher_error():
    """When error_flag is True, output is None and error_message is captured."""
    node = PSN_Error_Catcher()
    img = torch.rand(1, 4, 4, 3)
    success, msg = node.run(img, True, "CUDA OOM")
    assert success is None, "Output should be None on error"
    assert msg == "CUDA OOM", "Error message should be captured"


def test_error_catcher_error_default_message():
    """When error_flag is True and no message given, a default is used."""
    node = PSN_Error_Catcher()
    success, msg = node.run("data", True, "")
    assert success is None
    assert msg == "Unknown error", "Should use default error message"


def test_retry_switch_should_retry():
    """When retry_count < max_retries, should_retry is True and params are adjusted."""
    node = PSN_Retry_Switch()
    should_retry, params = node.run("OOM", 1, 3, base_steps=20, base_cfg=7.0)
    assert should_retry is True, "Should retry when count < max"
    assert params["steps"] < 20, "Steps should be reduced on retry"
    assert params["retry_count"] == 2, "Retry count should be incremented"
    assert params["error_message"] == "OOM"


def test_retry_switch_no_retry_at_max():
    """When retry_count >= max_retries, should_retry is False."""
    node = PSN_Retry_Switch()
    should_retry, params = node.run("OOM", 3, 3, base_steps=20, base_cfg=7.0)
    assert should_retry is False, "Should not retry when count >= max"
    assert params["steps"] == 20, "Steps should remain at base when not retrying"
    assert params["retry_count"] == 3


def test_retry_switch_zero_max_retries():
    """When max_retries is 0, should never retry."""
    node = PSN_Retry_Switch()
    should_retry, params = node.run("err", 0, 0, base_steps=10, base_cfg=5.0)
    assert should_retry is False, "Should not retry when max_retries is 0"


def test_retry_switch_edge_negative_clamped():
    """Negative retry_count should be clamped to 0."""
    node = PSN_Retry_Switch()
    should_retry, params = node.run("err", -5, 3, base_steps=20, base_cfg=7.0)
    assert should_retry is True, "Clamped to 0 < 3, so should retry"
    assert params["retry_count"] == 1


def test_node_mappings():
    """Verify module-level mappings exist and are correct."""
    assert "PSN_Error_Catcher" in NODE_CLASS_MAPPINGS
    assert "PSN_Retry_Switch" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_Error_Catcher"] is PSN_Error_Catcher
    assert NODE_CLASS_MAPPINGS["PSN_Retry_Switch"] is PSN_Retry_Switch
    assert "PSN_Error_Catcher" in NODE_DISPLAY_NAME_MAPPINGS
    assert "PSN_Retry_Switch" in NODE_DISPLAY_NAME_MAPPINGS


def test_input_types_exist():
    """Verify INPUT_TYPES classmethod returns proper dict."""
    it = PSN_Error_Catcher.INPUT_TYPES()
    assert "required" in it
    assert "output" in it["required"]
    assert "error_flag" in it["required"]

    it2 = PSN_Retry_Switch.INPUT_TYPES()
    assert "required" in it2
    assert "error_message" in it2["required"]
    assert "retry_count" in it2["required"]
    assert "max_retries" in it2["required"]


if __name__ == "__main__":
    test_error_catcher_success()
    test_error_catcher_error()
    test_error_catcher_error_default_message()
    test_retry_switch_should_retry()
    test_retry_switch_no_retry_at_max()
    test_retry_switch_zero_max_retries()
    test_retry_switch_edge_negative_clamped()
    test_node_mappings()
    test_input_types_exist()
    print("ok")
