"""Tests for h_shared_state_machine_for_step_life."""

import torch
from h_shared_state_machine_for_step_life import (
    StepStateMachine,
    PSN_StepLifecycleMachine,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _clear_registry,
    STATES,
)


def test_basic_lifecycle():
    """pending -> running -> approved works."""
    m = StepStateMachine()
    m.add_step("a")
    assert m.state("a") == "pending"
    m.start("a")
    assert m.state("a") == "running"
    m.approve("a")
    assert m.state("a") == "approved"


def test_illegal_transition_raises():
    """pending -> approved is not allowed."""
    m = StepStateMachine()
    m.add_step("a")
    try:
        m.approve("a")
        assert False, "should have raised"
    except ValueError:
        pass


def test_downstream_invalidation_on_edit():
    """Editing an approved step invalidates all transitive downstream steps."""
    m = StepStateMachine()
    m.add_step("a")
    m.add_step("b", ("a",))
    m.add_step("c", ("b",))
    m.add_step("d", ("c",))
    # approve a, b, c, d
    for s in ("a", "b", "c", "d"):
        m.start(s)
        m.approve(s)
    assert m.state("d") == "approved"
    # edit a -> b, c, d should be invalidated
    invalidated = m.edit("a")
    assert m.state("a") == "pending"
    assert m.state("b") == "invalidated"
    assert m.state("c") == "invalidated"
    assert m.state("d") == "invalidated"
    assert set(invalidated) == {"b", "c", "d"}


def test_reject_and_retry():
    """running -> rejected -> pending."""
    m = StepStateMachine()
    m.add_step("a")
    m.start("a")
    m.reject("a")
    assert m.state("a") == "rejected"
    m.retry("a")
    assert m.state("a") == "pending"


def test_unknown_step_raises():
    """Accessing an unknown step raises KeyError."""
    m = StepStateMachine()
    m.add_step("a")
    try:
        m.state("zzz")
        assert False, "should have raised"
    except KeyError:
        pass


def test_duplicate_step_raises():
    """Adding a duplicate step raises ValueError."""
    m = StepStateMachine()
    m.add_step("a")
    try:
        m.add_step("a")
        assert False, "should have raised"
    except ValueError:
        pass


def test_unknown_dependency_raises():
    """Adding a step with an unknown dependency raises ValueError."""
    m = StepStateMachine()
    try:
        m.add_step("a", ("ghost",))
        assert False, "should have raised"
    except ValueError:
        pass


def test_node_run_noop():
    """Node run with noop returns correct state tensor."""
    _clear_registry()
    node = PSN_StepLifecycleMachine()
    state_map, summary = node.run(
        machine_id="t1",
        steps="a,b,c",
        deps="a:;b:a;c:b",
        action="noop",
        target_step="a",
    )
    assert isinstance(state_map, torch.Tensor)
    assert state_map.shape == (1, 3, 1)
    assert state_map.dtype == torch.float32
    # all pending -> 0
    assert torch.all(state_map == 0).item()
    assert "a=pending" in summary
    assert "b=pending" in summary
    assert "c=pending" in summary


def test_node_run_start_approve():
    """Node run with start then approve."""
    _clear_registry()
    node = PSN_StepLifecycleMachine()
    state_map, _ = node.run("t2", "a,b", "a:;b:a", "start", "a")
    assert state_map[0, 0, 0].item() == 1  # running
    state_map, _ = node.run("t2", "a,b", "a:;b:a", "approve", "a")
    assert state_map[0, 0, 0].item() == 2  # approved


def test_node_run_edit_invalidates_downstream():
    """Node run with edit invalidates downstream steps."""
    _clear_registry()
    node = PSN_StepLifecycleMachine()
    # build and approve all
    node.run("t3", "a,b,c", "a:;b:a;c:b", "start", "a")
    node.run("t3", "a,b,c", "a:;b:a;c:b", "approve", "a")
    node.run("t3", "a,b,c", "a:;b:a;c:b", "start", "b")
    node.run("t3", "a,b,c", "a:;b:a;c:b", "approve", "b")
    node.run("t3", "a,b,c", "a:;b:a;c:b", "start", "c")
    node.run("t3", "a,b,c", "a:;b:a;c:b", "approve", "c")
    # now edit a
    state_map, summary = node.run("t3", "a,b,c", "a:;b:a;c:b", "edit", "a")
    assert state_map[0, 0, 0].item() == 0  # a back to pending
    assert state_map[0, 1, 0].item() == 4  # b invalidated
    assert state_map[0, 2, 0].item() == 4  # c invalidated
    assert "invalidated" in summary


def test_node_bad_action_raises():
    """Unknown action raises ValueError."""
    _clear_registry()
    node = PSN_StepLifecycleMachine()
    try:
        node.run("t4", "a", "a:", "teleport", "a")
        assert False, "should have raised"
    except ValueError:
        pass


def test_node_empty_steps_raises():
    """Empty steps string raises ValueError."""
    _clear_registry()
    node = PSN_StepLifecycleMachine()
    try:
        node.run("t5", "", "", "noop", "a")
        assert False, "should have raised"
    except ValueError:
        pass


def test_node_duplicate_steps_raises():
    """Duplicate step names raise ValueError."""
    _clear_registry()
    node = PSN_StepLifecycleMachine()
    try:
        node.run("t6", "a,a", "a:;a:", "noop", "a")
        assert False, "should have raised"
    except ValueError:
        pass


def test_node_mappings():
    """Module-level mappings exist and are correct."""
    assert "PSN_StepLifecycleMachine" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_StepLifecycleMachine"] is PSN_StepLifecycleMachine
    assert "PSN_StepLifecycleMachine" in NODE_DISPLAY_NAME_MAPPINGS
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_StepLifecycleMachine"] == "Step Lifecycle State Machine"


def test_node_input_types():
    """INPUT_TYPES returns the expected structure."""
    it = PSN_StepLifecycleMachine.INPUT_TYPES()
    assert "required" in it
    assert "machine_id" in it["required"]
    assert "steps" in it["required"]
    assert "deps" in it["required"]
    assert "action" in it["required"]
    assert "target_step" in it["required"]
    assert PSN_StepLifecycleMachine.RETURN_TYPES == ("MASK", "STRING")
    assert PSN_StepLifecycleMachine.FUNCTION == "run"
    assert PSN_StepLifecycleMachine.CATEGORY == "ParametricStudio/Pipelines"


def test_state_tensor_roundtrip():
    """State tensor values are in 0..4 and map back correctly."""
    from h_shared_state_machine_for_step_life import _state_tensor, _state_names
    states = ["pending", "running", "approved", "rejected", "invalidated"]
    t = _state_tensor(states)
    assert t.shape == (1, 5, 1)
    assert torch.all(t >= 0).item() and torch.all(t <= 4).item()
    back = _state_names(t)
    assert back == states


def test_reset_from_invalidated():
    """invalidated -> pending via reset."""
    m = StepStateMachine()
    m.add_step("a")
    m.start("a")
    m.invalidate("a")
    assert m.state("a") == "invalidated"
    m.reset("a")
    assert m.state("a") == "pending"


def test_log_records_transitions():
    """The log records every transition."""
    m = StepStateMachine()
    m.add_step("a")
    m.start("a")
    m.approve("a")
    log = m.log()
    assert len(log) == 3
    assert log[0] == ("a", None, "pending")
    assert log[1] == ("a", "pending", "running")
    assert log[2] == ("a", "running", "approved")


if __name__ == "__main__":
    test_basic_lifecycle()
    test_illegal_transition_raises()
    test_downstream_invalidation_on_edit()
    test_reject_and_retry()
    test_unknown_step_raises()
    test_duplicate_step_raises()
    test_unknown_dependency_raises()
    test_node_run_noop()
    test_node_run_start_approve()
    test_node_run_edit_invalidates_downstream()
    test_node_bad_action_raises()
    test_node_empty_steps_raises()
    test_node_duplicate_steps_raises()
    test_node_mappings()
    test_node_input_types()
    test_state_tensor_roundtrip()
    test_reset_from_invalidated()
    test_log_records_transitions()
    print("ok")
