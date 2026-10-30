"""Tests for n_2_dynamic_prompt_iteration.py."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from n_2_dynamic_prompt_iteration import (
    PSN_PromptIterator,
    PSN_ListToPromptQueue,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def test_basic_iteration_order_and_done():
    """Feed a list of 3 strings, call PSN_PromptIterator 3 times, verify order and is_done."""
    node = PSN_PromptIterator()
    prompts = ["alpha", "beta", "gamma"]

    # Call 1: index 0
    cur, nxt, done = node.run(prompts, 0)
    assert cur == "alpha", f"expected 'alpha', got {cur!r}"
    assert nxt == 1, f"expected next_index 1, got {nxt}"
    assert done is False, f"expected is_done False, got {done}"

    # Call 2: index 1
    cur, nxt, done = node.run(prompts, 1)
    assert cur == "beta", f"expected 'beta', got {cur!r}"
    assert nxt == 2, f"expected next_index 2, got {nxt}"
    assert done is False, f"expected is_done False, got {done}"

    # Call 3: index 2 (last item)
    cur, nxt, done = node.run(prompts, 2)
    assert cur == "gamma", f"expected 'gamma', got {cur!r}"
    assert nxt == 3, f"expected next_index 3, got {nxt}"
    assert done is True, f"expected is_done True after last item, got {done}"


def test_manual_index_stepping():
    """Verify that passing a specific index returns the correct prompt."""
    node = PSN_PromptIterator()
    prompts = ["a", "b", "c", "d"]

    cur, nxt, done = node.run(prompts, 3)
    assert cur == "d", f"expected 'd', got {cur!r}"
    assert nxt == 4
    assert done is True

    # Jump to index 1
    cur, nxt, done = node.run(prompts, 1)
    assert cur == "b", f"expected 'b', got {cur!r}"
    assert nxt == 2
    assert done is False


def test_out_of_range_index():
    """Index beyond the list length should return last prompt and is_done=True."""
    node = PSN_PromptIterator()
    prompts = ["x", "y"]

    cur, nxt, done = node.run(prompts, 5)
    assert cur == "y", f"expected last prompt 'y', got {cur!r}"
    assert nxt == 2, f"expected next_index 2 (len), got {nxt}"
    assert done is True


def test_empty_list():
    """Empty list should return empty string, next_index 0, is_done True."""
    node = PSN_PromptIterator()
    cur, nxt, done = node.run([], 0)
    assert cur == "", f"expected empty string, got {cur!r}"
    assert nxt == 0
    assert done is True


def test_list_to_prompt_queue_normalization():
    """PSN_ListToPromptQueue should normalize various inputs into a list of strings."""
    node = PSN_ListToPromptQueue()

    # List input
    result = node.run(["p1", "p2", "p3"])
    assert result[0] == ["p1", "p2", "p3"], f"got {result[0]!r}"

    # Tuple input
    result = node.run(("t1", "t2"))
    assert result[0] == ["t1", "t2"], f"got {result[0]!r}"

    # Single string (no comma)
    result = node.run("single prompt")
    assert result[0] == ["single prompt"], f"got {result[0]!r}"

    # Comma-separated string
    result = node.run("a, b, c")
    assert result[0] == ["a", "b", "c"], f"got {result[0]!r}"


def test_bad_input_non_string_element():
    """A list containing a non-string element should raise ValueError."""
    node = PSN_PromptIterator()
    try:
        node.run(["ok", 42, "also ok"], 0)
        assert False, "expected ValueError for non-string element"
    except ValueError as e:
        assert "expected str" in str(e), f"unexpected error message: {e}"


def test_bad_input_none():
    """None input should raise ValueError."""
    node = PSN_PromptIterator()
    try:
        node.run(None, 0)
        assert False, "expected ValueError for None input"
    except ValueError as e:
        assert "must not be None" in str(e), f"unexpected error message: {e}"


def test_node_mappings_exist():
    """Verify NODE_CLASS_MAPPINGS and NODE_DISPLAY_NAME_MAPPINGS are correct."""
    assert "PSN_PromptIterator" in NODE_CLASS_MAPPINGS
    assert "PSN_ListToPromptQueue" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_PromptIterator"] is PSN_PromptIterator
    assert NODE_CLASS_MAPPINGS["PSN_ListToPromptQueue"] is PSN_ListToPromptQueue
    assert "PSN_PromptIterator" in NODE_DISPLAY_NAME_MAPPINGS
    assert "PSN_ListToPromptQueue" in NODE_DISPLAY_NAME_MAPPINGS


def test_input_types_signature():
    """Verify INPUT_TYPES classmethod returns expected structure."""
    it = PSN_PromptIterator.INPUT_TYPES()
    assert "required" in it
    assert "prompt_list" in it["required"]
    assert "index" in it["required"]

    it2 = PSN_ListToPromptQueue.INPUT_TYPES()
    assert "required" in it2
    assert "list_input" in it2["required"]


def test_return_types():
    """Verify RETURN_TYPES and RETURN_NAMES match expected outputs."""
    assert PSN_PromptIterator.RETURN_TYPES == ("STRING", "INT", "BOOLEAN")
    assert PSN_PromptIterator.RETURN_NAMES == ("current_prompt", "next_index", "is_done")
    assert PSN_ListToPromptQueue.RETURN_TYPES == ("LIST[STRING]",)
    assert PSN_ListToPromptQueue.RETURN_NAMES == ("queue",)


def test_function_and_category():
    """Verify FUNCTION and CATEGORY are set correctly."""
    assert PSN_PromptIterator.FUNCTION == "run"
    assert PSN_PromptIterator.CATEGORY.startswith("ParametricStudio/")
    assert PSN_ListToPromptQueue.FUNCTION == "run"
    assert PSN_ListToPromptQueue.CATEGORY.startswith("ParametricStudio/")


if __name__ == "__main__":
    test_basic_iteration_order_and_done()
    test_manual_index_stepping()
    test_out_of_range_index()
    test_empty_list()
    test_list_to_prompt_queue_normalization()
    test_bad_input_non_string_element()
    test_bad_input_none()
    test_node_mappings_exist()
    test_input_types_signature()
    test_return_types()
    test_function_and_category()
    print("ok")
