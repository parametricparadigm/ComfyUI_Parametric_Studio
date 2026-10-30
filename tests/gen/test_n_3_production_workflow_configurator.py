"""
Tests for PSN_Workflow_Configurator node.
"""

import pytest
from psn_nodes.gen.n_3_production_workflow_configurator import (
    PSN_Workflow_Configurator,
    _SESSION_REGISTRY,
    _clear_registry
)


@pytest.fixture(autouse=True)
def clean_registry():
    """Ensure the registry is clean before and after each test."""
    _clear_registry()
    yield
    _clear_registry()


def test_set_and_get_in_global_scope():
    """Test basic set and get in Global scope."""
    node = PSN_Workflow_Configurator()
    
    # Set a value
    result, source, success = node.run(
        config_name="test_config",
        scope="Global",
        key="resolution",
        mode="Set",
        value=1920
    )
    assert success is True
    assert result is True
    assert source == "Global"
    
    # Get the value
    result, source, success = node.run(
        config_name="test_config",
        scope="Global",
        key="resolution",
        mode="Get",
        inherit=False
    )
    assert success is True
    assert result == 1920
    assert source == "Global"


def test_inheritance_from_global_to_pipeline():
    """Test that Pipeline scope inherits from Global scope when inherit=True."""
    node = PSN_Workflow_Configurator()
    
    # Set a value in Global scope
    node.run(
        config_name="shared_config",
        scope="Global",
        key="quality",
        mode="Set",
        value="high"
    )
    
    # Get in Pipeline scope with inheritance enabled
    result, source, success = node.run(
        config_name="shared_config",
        scope="Pipeline",
        key="quality",
        mode="Get",
        inherit=True
    )
    assert success is True
    assert result == "high"
    assert source == "Global"
    
    # Get in Pipeline scope with inheritance disabled
    result, source, success = node.run(
        config_name="shared_config",
        scope="Pipeline",
        key="quality",
        mode="Get",
        inherit=False
    )
    assert success is False
    assert result is None
    assert source == "not_found"


def test_isolation_when_inheritance_disabled():
    """Test that scopes are isolated when inheritance is disabled."""
    node = PSN_Workflow_Configurator()
    
    # Set a value in Global scope
    node.run(
        config_name="iso_config",
        scope="Global",
        key="param",
        mode="Set",
        value="global_value"
    )
    
    # Set a different value in Pipeline scope
    node.run(
        config_name="iso_config",
        scope="Pipeline",
        key="param",
        mode="Set",
        value="pipeline_value"
    )
    
    # Get in Pipeline scope with inheritance enabled - should get Pipeline value (narrower overrides broader)
    result, source, success = node.run(
        config_name="iso_config",
        scope="Pipeline",
        key="param",
        mode="Get",
        inherit=True
    )
    assert success is True
    assert result == "pipeline_value"
    assert source == "Pipeline"
    
    # Get in Node scope with inheritance enabled - should get Pipeline value (closer than Global)
    result, source, success = node.run(
        config_name="iso_config",
        scope="Node",
        key="param",
        mode="Get",
        inherit=True
    )
    assert success is True
    assert result == "pipeline_value"
    assert source == "Pipeline"


def test_delete_operation():
    """Test the Delete operation."""
    node = PSN_Workflow_Configurator()
    
    # Set a value
    node.run(
        config_name="del_config",
        scope="Global",
        key="temp_key",
        mode="Set",
        value="temp_value"
    )
    
    # Verify it exists
    result, source, success = node.run(
        config_name="del_config",
        scope="Global",
        key="temp_key",
        mode="Get",
        inherit=False
    )
    assert success is True
    assert result == "temp_value"
    
    # Delete it
    result, source, success = node.run(
        config_name="del_config",
        scope="Global",
        key="temp_key",
        mode="Delete"
    )
    assert success is True
    assert result is True
    
    # Verify it's gone
    result, source, success = node.run(
        config_name="del_config",
        scope="Global",
        key="temp_key",
        mode="Get",
        inherit=False
    )
    assert success is False
    assert result is None


def test_invalid_inputs():
    """Test that invalid inputs are handled gracefully."""
    node = PSN_Workflow_Configurator()
    
    # Empty config_name
    result, source, success = node.run(
        config_name="",
        scope="Global",
        key="key",
        mode="Get"
    )
    assert success is False
    assert source == "error"
    
    # Invalid scope
    result, source, success = node.run(
        config_name="valid",
        scope="InvalidScope",
        key="key",
        mode="Get"
    )
    assert success is False
    assert source == "error"
    
    # Empty key
    result, source, success = node.run(
        config_name="valid",
        scope="Global",
        key="",
        mode="Get"
    )
    assert success is False
    assert source == "error"
    
    # Invalid mode
    result, source, success = node.run(
        config_name="valid",
        scope="Global",
        key="key",
        mode="InvalidMode"
    )
    assert success is False
    assert source == "error"


def test_complex_value_types():
    """Test that complex value types (dicts, lists) are stored and retrieved correctly."""
    node = PSN_Workflow_Configurator()
    
    # Set a complex value
    complex_value = {
        "layers": [1, 2, 3],
        "settings": {"lr": 0.001, "epochs": 100}
    }
    
    node.run(
        config_name="complex_config",
        scope="Global",
        key="model_config",
        mode="Set",
        value=complex_value
    )
    
    # Get the value
    result, source, success = node.run(
        config_name="complex_config",
        scope="Global",
        key="model_config",
        mode="Get",
        inherit=False
    )
    assert success is True
    assert result == complex_value
    
    # Modify the original and verify the stored value is not affected (deep copy)
    complex_value["layers"].append(4)
    
    result, source, success = node.run(
        config_name="complex_config",
        scope="Global",
        key="model_config",
        mode="Get",
        inherit=False
    )
    assert success is True
    assert result["layers"] == [1, 2, 3]  # Should not be affected by external modification


def test_multiple_configs_in_same_scope():
    """Test that multiple configs can coexist in the same scope."""
    node = PSN_Workflow_Configurator()
    
    # Set values in different configs
    node.run(
        config_name="config_a",
        scope="Global",
        key="shared_key",
        mode="Set",
        value="value_a"
    )
    node.run(
        config_name="config_b",
        scope="Global",
        key="shared_key",
        mode="Set",
        value="value_b"
    )
    
    # Verify each config has its own value
    result_a, _, success_a = node.run(
        config_name="config_a",
        scope="Global",
        key="shared_key",
        mode="Get",
        inherit=False
    )
    result_b, _, success_b = node.run(
        config_name="config_b",
        scope="Global",
        key="shared_key",
        mode="Get",
        inherit=False
    )
    
    assert success_a is True
    assert result_a == "value_a"
    assert success_b is True
    assert result_b == "value_b"
