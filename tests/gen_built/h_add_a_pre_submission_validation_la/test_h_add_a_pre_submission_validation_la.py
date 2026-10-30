"""Tests for the pre-submission validation layer."""

import json
import sys
import os

# Ensure the module is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from h_add_a_pre_submission_validation_la import (
    PSN_PreSubmissionValidator,
    PSN_NeverWireRuleChecker,
    validate_graph,
    DEFAULT_NEVER_WIRE_RULES,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def test_module_structure():
    """Test that the module has the required structure."""
    # Check NODE_CLASS_MAPPINGS exists and has entries
    assert isinstance(NODE_CLASS_MAPPINGS, dict), "NODE_CLASS_MAPPINGS must be a dict"
    assert len(NODE_CLASS_MAPPINGS) >= 1, "Must have at least one node class"

    # Check NODE_DISPLAY_NAME_MAPPINGS exists
    assert isinstance(NODE_DISPLAY_NAME_MAPPINGS, dict), "NODE_DISPLAY_NAME_MAPPINGS must be a dict"
    for key in NODE_CLASS_MAPPINGS:
        assert key in NODE_DISPLAY_NAME_MAPPINGS, f"Missing display name for {key}"

    # Check node classes have required attributes
    for name, cls in NODE_CLASS_MAPPINGS.items():
        assert hasattr(cls, "INPUT_TYPES"), f"{name} missing INPUT_TYPES"
        assert hasattr(cls, "RETURN_TYPES"), f"{name} missing RETURN_TYPES"
        assert hasattr(cls, "FUNCTION"), f"{name} missing FUNCTION"
        assert hasattr(cls, "CATEGORY"), f"{name} missing CATEGORY"
        assert cls.FUNCTION == "run", f"{name} FUNCTION must be 'run'"
        assert cls.CATEGORY.startswith("ParametricStudio/"), f"{name} CATEGORY must start with 'ParametricStudio/'"

    print("  [PASS] Module structure")


def test_valid_graph():
    """Test that a valid graph passes validation."""
    graph = {
        "nodes": {
            "1": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": "model.safetensors"}
            },
            "2": {
                "class_type": "KSampler",
                "inputs": {
                    "model": ["1", 0],
                    "seed": 42
                }
            },
            "3": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["2", 0]
                }
            }
        }
    }
    is_valid, errors = validate_graph(graph)
    assert is_valid, f"Valid graph should pass, got errors: {errors}"
    assert errors == [], f"No errors expected, got: {errors}"
    print("  [PASS] Valid graph passes")


def test_never_wire_violation():
    """Test that a never-wire rule violation is detected."""
    graph = {
        "nodes": {
            "1": {
                "class_type": "KSampler",
                "inputs": {"seed": 42}
            },
            "2": {
                "class_type": "KSampler",
                "inputs": {
                    "model": ["1", 0],
                    "seed": 43
                }
            }
        }
    }
    is_valid, errors = validate_graph(graph)
    assert not is_valid, "Graph with KSampler->KSampler should be invalid"
    assert len(errors) >= 1, "Should have at least one error"
    assert any("Never-wire" in e for e in errors), f"Should have never-wire error, got: {errors}"
    print("  [PASS] Never-wire violation detected")


def test_dangling_input():
    """Test that dangling inputs (references to non-existent nodes) are detected."""
    graph = {
        "nodes": {
            "1": {
                "class_type": "KSampler",
                "inputs": {
                    "model": ["999", 0],  # Non-existent node
                    "seed": 42
                }
            }
        }
    }
    is_valid, errors = validate_graph(graph)
    assert not is_valid, "Graph with dangling input should be invalid"
    assert any("non-existent" in e for e in errors), f"Should have dangling input error, got: {errors}"
    print("  [PASS] Dangling input detected")


def test_cycle_detection():
    """Test that cycles in the graph are detected."""
    graph = {
        "nodes": {
            "1": {
                "class_type": "KSampler",
                "inputs": {
                    "model": ["2", 0],
                    "seed": 42
                }
            },
            "2": {
                "class_type": "KSampler",
                "inputs": {
                    "model": ["1", 0],
                    "seed": 43
                }
            }
        }
    }
    is_valid, errors = validate_graph(graph)
    assert not is_valid, "Graph with cycle should be invalid"
    assert any("Cycle" in e for e in errors), f"Should have cycle error, got: {errors}"
    print("  [PASS] Cycle detection")


def test_invalid_json():
    """Test that invalid JSON input is handled gracefully."""
    validator = PSN_PreSubmissionValidator()
    report, is_valid = validator.run("{invalid json", True)
    assert not is_valid, "Invalid JSON should result in is_valid=False"
    assert "ERROR" in report, f"Report should contain ERROR, got: {report}"
    print("  [PASS] Invalid JSON handled")


def test_empty_graph():
    """Test that an empty graph is handled."""
    graph = {"nodes": {}}
    is_valid, errors = validate_graph(graph)
    assert is_valid, "Empty graph should be valid (no nodes to validate)"
    assert errors == [], f"No errors expected for empty graph, got: {errors}"
    print("  [PASS] Empty graph")


def test_non_dict_graph():
    """Test that non-dict graph input is handled."""
    is_valid, errors = validate_graph([1, 2, 3])
    assert not is_valid, "Non-dict graph should be invalid"
    assert len(errors) >= 1, "Should have errors for non-dict graph"
    print("  [PASS] Non-dict graph handled")


def test_never_wire_rule_checker():
    """Test the NeverWireRuleChecker node."""
    checker = PSN_NeverWireRuleChecker()

    # Test forbidden connection
    is_allowed, desc = checker.run("KSampler", "KSampler")
    assert not is_allowed, "KSampler->KSampler should be forbidden"
    assert "forbidden" in desc.lower(), f"Description should mention forbidden, got: {desc}"

    # Test allowed connection
    is_allowed, desc = checker.run("CheckpointLoaderSimple", "KSampler")
    assert is_allowed, "CheckpointLoaderSimple->KSampler should be allowed"
    assert "allowed" in desc.lower(), f"Description should mention allowed, got: {desc}"

    print("  [PASS] NeverWireRuleChecker")


def test_validator_node():
    """Test the PreSubmissionValidator node end-to-end."""
    validator = PSN_PreSubmissionValidator()

    # Valid graph
    valid_graph = {
        "nodes": {
            "1": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": "model.safetensors"}
            },
            "2": {
                "class_type": "KSampler",
                "inputs": {
                    "model": ["1", 0],
                    "seed": 42
                }
            }
        }
    }
    report, is_valid = validator.run(json.dumps(valid_graph), True)
    assert is_valid, f"Valid graph should pass, got report: {report}"
    assert "VALID" in report, f"Report should contain VALID, got: {report}"

    # Invalid graph (never-wire violation)
    invalid_graph = {
        "nodes": {
            "1": {
                "class_type": "KSampler",
                "inputs": {"seed": 42}
            },
            "2": {
                "class_type": "KSampler",
                "inputs": {
                    "model": ["1", 0],
                    "seed": 43
                }
            }
        }
    }
    report, is_valid = validator.run(json.dumps(invalid_graph), True)
    assert not is_valid, "Invalid graph should fail"
    assert "INVALID" in report, f"Report should contain INVALID, got: {report}"
    assert "STRICT" in report, f"Strict mode report should contain STRICT, got: {report}"

    print("  [PASS] PreSubmissionValidator node")


def test_custom_rules():
    """Test that custom never-wire rules can be added."""
    graph = {
        "nodes": {
            "1": {
                "class_type": "CustomNodeA",
                "inputs": {"val": 1}
            },
            "2": {
                "class_type": "CustomNodeB",
                "inputs": {
                    "input": ["1", 0]
                }
            }
        }
    }

    # Without custom rules, should be valid
    is_valid, errors = validate_graph(graph)
    assert is_valid, f"Graph should be valid without custom rules, got: {errors}"

    # With custom rule forbidding CustomNodeA -> CustomNodeB
    custom_rules = DEFAULT_NEVER_WIRE_RULES + [("CustomNodeA", "CustomNodeB")]
    is_valid, errors = validate_graph(graph, custom_rules)
    assert not is_valid, "Graph should be invalid with custom rule"
    assert any("Never-wire" in e for e in errors), f"Should have never-wire error, got: {errors}"

    print("  [PASS] Custom rules")


def test_input_types_signature():
    """Test that INPUT_TYPES returns the correct structure."""
    for name, cls in NODE_CLASS_MAPPINGS.items():
        it = cls.INPUT_TYPES()
        assert "required" in it, f"{name} INPUT_TYPES must have 'required'"
        assert isinstance(it["required"], dict), f"{name} 'required' must be a dict"
        # Check that each input has a type tuple
        for input_name, input_spec in it["required"].items():
            assert isinstance(input_spec, tuple), f"{name}.{input_name} spec must be a tuple"
            assert len(input_spec) >= 1, f"{name}.{input_name} spec must have at least a type"

    print("  [PASS] INPUT_TYPES signature")


if __name__ == "__main__":
    print("Running tests for pre-submission validation layer...")
    test_module_structure()
    test_valid_graph()
    test_never_wire_violation()
    test_dangling_input()
    test_cycle_detection()
    test_invalid_json()
    test_empty_graph()
    test_non_dict_graph()
    test_never_wire_rule_checker()
    test_validator_node()
    test_custom_rules()
    test_input_types_signature()
    print("ok")
