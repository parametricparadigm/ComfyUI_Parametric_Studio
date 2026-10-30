"""
Tests for PSN_Dynamic_Switch node.

Covers:
- Boolean-based 2-way switching (True/False)
- Index-based multi-switching (indices 1-4)
- Out-of-range index clamping
- Optional inputs (input_3, input_4) being None
- Edge cases: all inputs same, mixed types
- Bad input: index out of range, condition as non-boolean (should still work via truthiness)
"""

import pytest
from psn_nodes.gen.n_10_dynamic_parameter_switching import PSN_Dynamic_Switch


@pytest.fixture
def node():
    return PSN_Dynamic_Switch()


def test_boolean_switch_false_selects_input_1(node):
    """When condition is False and use_index is False, input_1 is returned."""
    result = node.run("A", "B", condition=False, use_index=False, index=1)
    assert result == "A"


def test_boolean_switch_true_selects_input_2(node):
    """When condition is True and use_index is False, input_2 is returned."""
    result = node.run("A", "B", condition=True, use_index=False, index=1)
    assert result == "B"


def test_index_switch_1_selects_input_1(node):
    """When use_index is True and index=1, input_1 is returned."""
    result = node.run("A", "B", condition=False, use_index=True, index=1, input_3="C", input_4="D")
    assert result == "A"


def test_index_switch_2_selects_input_2(node):
    """When use_index is True and index=2, input_2 is returned."""
    result = node.run("A", "B", condition=False, use_index=True, index=2, input_3="C", input_4="D")
    assert result == "B"


def test_index_switch_3_selects_input_3(node):
    """When use_index is True and index=3, input_3 is returned."""
    result = node.run("A", "B", condition=False, use_index=True, index=3, input_3="C", input_4="D")
    assert result == "C"


def test_index_switch_4_selects_input_4(node):
    """When use_index is True and index=4, input_4 is returned."""
    result = node.run("A", "B", condition=False, use_index=True, index=4, input_3="C", input_4="D")
    assert result == "D"


def test_index_out_of_range_high_clamps_to_4(node):
    """Index > 4 clamps to 4, returning input_4."""
    result = node.run("A", "B", condition=False, use_index=True, index=99, input_3="C", input_4="D")
    assert result == "D"


def test_index_out_of_range_low_clamps_to_1(node):
    """Index < 1 clamps to 1, returning input_1."""
    result = node.run("A", "B", condition=False, use_index=True, index=-5, input_3="C", input_4="D")
    assert result == "A"


def test_index_3_with_none_input_3_falls_back_to_input_1(node):
    """When index=3 but input_3 is None, falls back to input_1."""
    result = node.run("A", "B", condition=False, use_index=True, index=3, input_3=None, input_4="D")
    assert result == "A"


def test_index_4_with_none_input_4_falls_back_to_input_1(node):
    """When index=4 but input_4 is None, falls back to input_1."""
    result = node.run("A", "B", condition=False, use_index=True, index=4, input_3="C", input_4=None)
    assert result == "A"


def test_mixed_types_boolean_switch(node):
    """Works with non-string types (numbers, lists, dicts)."""
    result = node.run(42, [1, 2, 3], condition=True, use_index=False, index=1)
    assert result == [1, 2, 3]


def test_mixed_types_index_switch(node):
    """Works with non-string types in index mode."""
    result = node.run(42, [1, 2, 3], condition=False, use_index=True, index=2, input_3={"k": "v"}, input_4=None)
    assert result == [1, 2, 3]


def test_all_inputs_same_value(node):
    """When all inputs are the same, output is that value regardless of selection."""
    result = node.run("X", "X", condition=True, use_index=False, index=1, input_3="X", input_4="X")
    assert result == "X"


def test_condition_truthy_non_boolean(node):
    """Condition is treated as truthy/falsy; non-boolean truthy values select input_2."""
    result = node.run("A", "B", condition=1, use_index=False, index=1)
    assert result == "B"


def test_condition_falsy_non_boolean(node):
    """Condition is treated as truthy/falsy; non-boolean falsy values select input_1."""
    result = node.run("A", "B", condition=0, use_index=False, index=1)
    assert result == "A"
