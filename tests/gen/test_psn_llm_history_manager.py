"""Tests for PSN_LLM_History_Manager node."""

import json

from psn_nodes.gen.psn_llm_history_manager import (
    PSN_LLM_History_Manager,
    _normalize_context,
    _trim_history,
    _context_to_json,
)


def _make_node():
    return PSN_LLM_History_Manager()


def test_append_single_message_to_empty_context():
    node = _make_node()
    result = node.run(context="{}", new_message="Hello", role="user")
    ctx = json.loads(result[0])
    assert len(ctx["history"]) == 1
    assert ctx["history"][0] == {"role": "user", "content": "Hello"}


def test_append_multiple_messages_preserves_order():
    node = _make_node()
    ctx_str = "{}"
    for msg, role in [("Hi", "user"), ("Hello", "assistant"), ("How are you?", "user")]:
        result = node.run(context=ctx_str, new_message=msg, role=role)
        ctx_str = result[0]
    ctx = json.loads(ctx_str)
    assert len(ctx["history"]) == 3
    assert ctx["history"][0]["content"] == "Hi"
    assert ctx["history"][1]["content"] == "Hello"
    assert ctx["history"][2]["content"] == "How are you?"
    assert ctx["history"][0]["role"] == "user"
    assert ctx["history"][1]["role"] == "assistant"
    assert ctx["history"][2]["role"] == "user"


def test_trims_history_when_exceeding_max_length():
    node = _make_node()
    ctx_str = json.dumps({"history": [], "max_length": 3})
    for i in range(5):
        result = node.run(context=ctx_str, new_message=f"msg{i}", role="user")
        ctx_str = result[0]
    ctx = json.loads(ctx_str)
    assert len(ctx["history"]) == 3
    # Should keep the last 3 messages
    assert ctx["history"][0]["content"] == "msg2"
    assert ctx["history"][1]["content"] == "msg3"
    assert ctx["history"][2]["content"] == "msg4"


def test_max_length_zero_clears_history():
    node = _make_node()
    ctx_str = json.dumps({"history": [{"role": "user", "content": "old"}], "max_length": 0})
    result = node.run(context=ctx_str, new_message="new", role="user")
    ctx = json.loads(result[0])
    assert len(ctx["history"]) == 0


def test_invalid_role_defaults_to_user():
    node = _make_node()
    result = node.run(context="{}", new_message="test", role="invalid_role")
    ctx = json.loads(result[0])
    assert ctx["history"][0]["role"] == "user"


def test_invalid_context_string_is_handled_gracefully():
    node = _make_node()
    result = node.run(context="not valid json", new_message="hello", role="user")
    ctx = json.loads(result[0])
    assert len(ctx["history"]) == 1
    assert ctx["history"][0]["content"] == "hello"


def test_context_as_dict_input():
    node = _make_node()
    ctx_dict = {"history": [{"role": "user", "content": "prev"}], "max_length": 10}
    result = node.run(context=json.dumps(ctx_dict), new_message="next", role="assistant")
    ctx = json.loads(result[0])
    assert len(ctx["history"]) == 2
    assert ctx["history"][0]["content"] == "prev"
    assert ctx["history"][1]["content"] == "next"
    assert ctx["history"][1]["role"] == "assistant"


def test_optional_max_length_overrides_context():
    node = _make_node()
    ctx_str = json.dumps({"history": [], "max_length": 100})
    result = node.run(context=ctx_str, new_message="a", role="user", max_length=2)
    ctx = json.loads(result[0])
    assert ctx["max_length"] == 2
    # Add more to test trimming with overridden max_length
    result = node.run(context=result[0], new_message="b", role="user", max_length=2)
    result = node.run(context=result[0], new_message="c", role="user", max_length=2)
    ctx = json.loads(result[0])
    assert len(ctx["history"]) == 2
    assert ctx["history"][0]["content"] == "b"
    assert ctx["history"][1]["content"] == "c"


def test_non_string_new_message_is_coerced():
    node = _make_node()
    result = node.run(context="{}", new_message=12345, role="user")
    ctx = json.loads(result[0])
    assert ctx["history"][0]["content"] == "12345"


def test_normalize_context_with_malformed_history_entries():
    data = {
        "history": [
            {"role": "user", "content": "valid"},
            {"role": 123, "content": "bad role"},
            {"role": "user", "content": 456},
            "not a dict",
            {"role": "assistant", "content": "also valid"},
        ],
        "max_length": "not a number",
    }
    ctx = _normalize_context(data)
    assert len(ctx["history"]) == 2
    assert ctx["history"][0]["content"] == "valid"
    assert ctx["history"][1]["content"] == "also valid"
    assert ctx["max_length"] == 100  # default fallback


def test_trim_history_keeps_most_recent():
    history = [{"role": "user", "content": str(i)} for i in range(10)]
    trimmed = _trim_history(history, 4)
    assert len(trimmed) == 4
    assert trimmed[0]["content"] == "6"
    assert trimmed[3]["content"] == "9"


def test_empty_new_message_is_allowed():
    node = _make_node()
    result = node.run(context="{}", new_message="", role="user")
    ctx = json.loads(result[0])
    assert len(ctx["history"]) == 1
    assert ctx["history"][0]["content"] == ""
