"""
Tests for PSN Stateful Multi-Step Video Generation nodes.
"""

import pytest
from psn_nodes.gen.n_4_stateful_multi_step_video_generation import (
    PSN_State_Store,
    PSN_State_Retrieve,
    PSN_State_Clear,
    _STATE_STORE,
)


@pytest.fixture(autouse=True)
def clear_state():
    """Clear the state store before and after each test."""
    _STATE_STORE.clear()
    yield
    _STATE_STORE.clear()


def test_store_and_retrieve_basic():
    """Test basic store and retrieve functionality."""
    store_node = PSN_State_Store()
    retrieve_node = PSN_State_Retrieve()
    
    # Store a value
    status = store_node.run("test_key", 42)
    assert status == (True,)
    
    # Retrieve the value
    result = retrieve_node.run("test_key")
    assert result == (42,)


def test_store_and_retrieve_with_default():
    """Test retrieve with default value when key doesn't exist."""
    retrieve_node = PSN_State_Retrieve()
    
    # Retrieve non-existent key with default
    result = retrieve_node.run("nonexistent_key", default="fallback")
    assert result == ("fallback",)
    
    # Retrieve non-existent key without default
    result = retrieve_node.run("nonexistent_key")
    assert result == (None,)


def test_store_overwrite_value():
    """Test that storing a new value overwrites the old one."""
    store_node = PSN_State_Store()
    retrieve_node = PSN_State_Retrieve()
    
    # Store initial value
    store_node.run("test_key", "initial")
    result = retrieve_node.run("test_key")
    assert result == ("initial",)
    
    # Store new value
    store_node.run("test_key", "updated")
    result = retrieve_node.run("test_key")
    assert result == ("updated",)


def test_store_with_invalid_key():
    """Test storing with invalid keys (empty or non-string)."""
    store_node = PSN_State_Store()
    
    # Empty key
    status = store_node.run("", "value")
    assert status == (False,)
    
    # Whitespace-only key
    status = store_node.run("   ", "value")
    assert status == (False,)
    
    # Non-string key (should not happen in ComfyUI, but test for safety)
    status = store_node.run(123, "value")
    assert status == (False,)


def test_retrieve_with_invalid_key():
    """Test retrieving with invalid keys."""
    retrieve_node = PSN_State_Retrieve()
    
    # Empty key
    result = retrieve_node.run("", default="fallback")
    assert result == ("fallback",)
    
    # Whitespace-only key
    result = retrieve_node.run("   ", default="fallback")
    assert result == ("fallback",)
    
    # Non-string key
    result = retrieve_node.run(123, default="fallback")
    assert result == ("fallback",)


def test_clear_specific_key():
    """Test clearing a specific key."""
    store_node = PSN_State_Store()
    retrieve_node = PSN_State_Retrieve()
    clear_node = PSN_State_Clear()
    
    # Store two values
    store_node.run("key1", "value1")
    store_node.run("key2", "value2")
    
    # Clear key1
    status = clear_node.run("key1")
    assert status == (True,)
    
    # key1 should be gone, key2 should remain
    result1 = retrieve_node.run("key1", default="missing")
    result2 = retrieve_node.run("key2")
    assert result1 == ("missing",)
    assert result2 == ("value2",)


def test_clear_all_keys():
    """Test clearing all keys."""
    store_node = PSN_State_Store()
    retrieve_node = PSN_State_Retrieve()
    clear_node = PSN_State_Clear()
    
    # Store multiple values
    store_node.run("key1", "value1")
    store_node.run("key2", "value2")
    store_node.run("key3", "value3")
    
    # Clear all
    status = clear_node.run("")
    assert status == (True,)
    
    # All keys should be gone
    result1 = retrieve_node.run("key1", default="missing")
    result2 = retrieve_node.run("key2", default="missing")
    result3 = retrieve_node.run("key3", default="missing")
    assert result1 == ("missing",)
    assert result2 == ("missing",)
    assert result3 == ("missing",)


def test_store_complex_value():
    """Test storing and retrieving complex values (simulating latents)."""
    store_node = PSN_State_Store()
    retrieve_node = PSN_State_Retrieve()
    
    # Simulate a latent tensor as a list of lists
    latent = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
    
    # Store the latent
    status = store_node.run("last_latent", latent)
    assert status == (True,)
    
    # Retrieve the latent
    result = retrieve_node.run("last_latent")
    assert result == (latent,)
    
    # Verify it's the same object (reference)
    assert result[0] is latent


def test_multi_step_workflow_simulation():
    """Simulate a 2-frame video workflow where Frame 2 depends on Frame 1."""
    store_node = PSN_State_Store()
    retrieve_node = PSN_State_Retrieve()
    
    # Frame 1: Generate latent and store it
    frame1_latent = [1.0, 2.0, 3.0]
    store_node.run("last_latent", frame1_latent)
    
    # Frame 2: Retrieve Frame 1's latent and use it
    frame1_retrieved = retrieve_node.run("last_latent")
    assert frame1_retrieved == (frame1_latent,)
    
    # Simulate Frame 2 generation using Frame 1's latent
    frame2_latent = [x * 2 for x in frame1_retrieved[0]]
    
    # Store Frame 2's latent for potential Frame 3
    store_node.run("last_latent", frame2_latent)
    
    # Verify Frame 2's latent is stored correctly
    frame2_retrieved = retrieve_node.run("last_latent")
    assert frame2_retrieved == (frame2_latent,)


def test_namespaced_keys_for_concurrency():
    """Test that namespaced keys can be used to avoid race conditions."""
    store_node = PSN_State_Store()
    retrieve_node = PSN_State_Retrieve()
    
    # Simulate two concurrent graphs with different namespaces
    store_node.run("graph1/last_latent", [1.0, 2.0])
    store_node.run("graph2/last_latent", [3.0, 4.0])
    
    # Retrieve from each graph
    result1 = retrieve_node.run("graph1/last_latent")
    result2 = retrieve_node.run("graph2/last_latent")
    
    assert result1 == ([1.0, 2.0],)
    assert result2 == ([3.0, 4.0],)
