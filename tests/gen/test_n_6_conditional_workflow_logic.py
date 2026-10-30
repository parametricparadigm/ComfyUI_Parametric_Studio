"""
Tests for psn_nodes.gen.n_6_conditional_workflow_logic
"""

import pytest
from psn_nodes.gen.n_6_conditional_workflow_logic import (
    PSN_Boolean_Logic,
    PSN_Type_Caster,
)


class TestPSN_Boolean_Logic:
    def setup_method(self):
        self.node = PSN_Boolean_Logic()

    def test_and_operation(self):
        assert self.node.run(True, True, "AND") == (True,)
        assert self.node.run(True, False, "AND") == (False,)
        assert self.node.run(False, True, "AND") == (False,)
        assert self.node.run(False, False, "AND") == (False,)

    def test_or_operation(self):
        assert self.node.run(True, True, "OR") == (True,)
        assert self.node.run(True, False, "OR") == (True,)
        assert self.node.run(False, True, "OR") == (True,)
        assert self.node.run(False, False, "OR") == (False,)

    def test_not_operation(self):
        assert self.node.run(True, False, "NOT") == (False,)
        assert self.node.run(False, True, "NOT") == (True,)

    def test_xor_operation(self):
        assert self.node.run(True, True, "XOR") == (False,)
        assert self.node.run(True, False, "XOR") == (True,)
        assert self.node.run(False, True, "XOR") == (True,)
        assert self.node.run(False, False, "XOR") == (False,)

    def test_invalid_operation_raises(self):
        with pytest.raises(ValueError):
            self.node.run(True, True, "INVALID")


class TestPSN_Type_Caster:
    def setup_method(self):
        self.node = PSN_Type_Caster()

    def test_cast_to_string(self):
        assert self.node.run(123, "STRING", "default") == ("123",)
        assert self.node.run(True, "STRING", "default") == ("True",)
        assert self.node.run(3.14, "STRING", "default") == ("3.14",)

    def test_cast_to_int_valid(self):
        assert self.node.run("42", "INT", 0) == (42,)
        assert self.node.run(3.9, "INT", 0) == (3,)
        assert self.node.run(True, "INT", 0) == (1,)
        assert self.node.run(False, "INT", 0) == (0,)

    def test_cast_to_int_invalid_returns_default(self):
        assert self.node.run("abc", "INT", -1) == (-1,)
        assert self.node.run(None, "INT", -1) == (-1,)

    def test_cast_to_float_valid(self):
        assert self.node.run("3.14", "FLOAT", 0.0) == (3.14,)
        assert self.node.run(42, "FLOAT", 0.0) == (42.0,)
        assert self.node.run(True, "FLOAT", 0.0) == (1.0,)

    def test_cast_to_float_invalid_returns_default(self):
        assert self.node.run("xyz", "FLOAT", -1.0) == (-1.0,)

    def test_cast_to_boolean_valid(self):
        assert self.node.run("true", "BOOLEAN", False) == (True,)
        assert self.node.run("false", "BOOLEAN", True) == (False,)
        assert self.node.run(1, "BOOLEAN", False) == (True,)
        assert self.node.run(0, "BOOLEAN", True) == (False,)
        assert self.node.run("yes", "BOOLEAN", False) == (True,)
        assert self.node.run("no", "BOOLEAN", True) == (False,)

    def test_cast_to_boolean_invalid_returns_default(self):
        assert self.node.run("maybe", "BOOLEAN", False) == (False,)
        assert self.node.run(None, "BOOLEAN", True) == (True,)

    def test_invalid_target_type_returns_default(self):
        assert self.node.run(123, "INVALID", "fallback") == ("fallback",)
