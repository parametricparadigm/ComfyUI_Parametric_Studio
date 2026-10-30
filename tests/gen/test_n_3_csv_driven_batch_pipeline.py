"""
Tests for PSN_CSV_Batch_Reader node.
"""

import pytest
from psn_nodes.gen.n_3_csv_driven_batch_pipeline import PSN_CSV_Batch_Reader


@pytest.fixture
def node():
    return PSN_CSV_Batch_Reader()


def test_basic_csv_parsing(node):
    """Test basic CSV with 3 rows, verify prompt and params for each row."""
    csv_text = "prompt,seed,steps\nHello,42,20\nWorld,43,25\nTest,44,30"

    # Row 0
    prompt, params, has_next, row_count, error = node.run(csv_text, 0)
    assert prompt == "Hello"
    assert params == {"seed": "42", "steps": "20"}
    assert has_next is True
    assert row_count == 3
    assert error == ""

    # Row 1
    prompt, params, has_next, row_count, error = node.run(csv_text, 1)
    assert prompt == "World"
    assert params == {"seed": "43", "steps": "25"}
    assert has_next is True
    assert row_count == 3
    assert error == ""

    # Row 2 (last row)
    prompt, params, has_next, row_count, error = node.run(csv_text, 2)
    assert prompt == "Test"
    assert params == {"seed": "44", "steps": "30"}
    assert has_next is False
    assert row_count == 3
    assert error == ""


def test_has_next_transitions(node):
    """Verify has_next transitions correctly across rows."""
    csv_text = "prompt\nA\nB\nC"

    _, _, has_next_0, _, _ = node.run(csv_text, 0)
    _, _, has_next_1, _, _ = node.run(csv_text, 1)
    _, _, has_next_2, _, _ = node.run(csv_text, 2)

    assert has_next_0 is True
    assert has_next_1 is True
    assert has_next_2 is False


def test_no_prompt_column_uses_first_column(node):
    """When no 'prompt' column exists, use the first column as prompt."""
    csv_text = "text,seed\nHello,42\nWorld,43"

    prompt, params, has_next, row_count, error = node.run(csv_text, 0)
    assert prompt == "Hello"
    assert params == {"seed": "42"}
    assert has_next is True
    assert row_count == 2
    assert error == ""

    prompt, params, has_next, row_count, error = node.run(csv_text, 1)
    assert prompt == "World"
    assert params == {"seed": "43"}
    assert has_next is False
    assert row_count == 2
    assert error == ""


def test_empty_csv(node):
    """CSV with only headers and no data rows."""
    csv_text = "prompt,seed"

    prompt, params, has_next, row_count, error = node.run(csv_text, 0)
    assert prompt == ""
    assert params == {}
    assert has_next is False
    assert row_count == 0
    assert "no data rows" in error


def test_row_index_out_of_range(node):
    """row_index beyond available rows should return error."""
    csv_text = "prompt\nHello"

    prompt, params, has_next, row_count, error = node.run(csv_text, 5)
    assert prompt == ""
    assert params == {}
    assert has_next is False
    assert row_count == 1
    assert "out of range" in error


def test_negative_row_index(node):
    """Negative row_index should return error."""
    csv_text = "prompt\nHello"

    prompt, params, has_next, row_count, error = node.run(csv_text, -1)
    assert prompt == ""
    assert params == {}
    assert has_next is False
    assert row_count == 0
    assert "non-negative" in error


def test_invalid_csv_text_type(node):
    """Non-string csv_text should return error."""
    prompt, params, has_next, row_count, error = node.run(12345, 0)
    assert prompt == ""
    assert params == {}
    assert has_next is False
    assert row_count == 0
    assert "must be a string" in error


def test_invalid_row_index_type(node):
    """Non-int row_index should return error."""
    csv_text = "prompt\nHello"

    prompt, params, has_next, row_count, error = node.run(csv_text, "0")
    assert prompt == ""
    assert params == {}
    assert has_next is False
    assert row_count == 0
    assert "must be an integer" in error


def test_csv_with_quoted_fields(node):
    """CSV with quoted fields containing commas."""
    csv_text = 'prompt,seed\n"Hello, World",42\n"Foo, Bar",43'

    prompt, params, has_next, row_count, error = node.run(csv_text, 0)
    assert prompt == "Hello, World"
    assert params == {"seed": "42"}
    assert has_next is True
    assert row_count == 2
    assert error == ""

    prompt, params, has_next, row_count, error = node.run(csv_text, 1)
    assert prompt == "Foo, Bar"
    assert params == {"seed": "43"}
    assert has_next is False
    assert row_count == 2
    assert error == ""


def test_single_row_csv(node):
    """CSV with exactly one data row."""
    csv_text = "prompt,seed\nOnly,99"

    prompt, params, has_next, row_count, error = node.run(csv_text, 0)
    assert prompt == "Only"
    assert params == {"seed": "99"}
    assert has_next is False
    assert row_count == 1
    assert error == ""
