"""Tests for n_7_llm_agent_chat_interface (offline, no network)."""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from n_7_llm_agent_chat_interface import (
    AgentInstance,
    PSN_LLM_Agent_Init,
    PSN_LLM_Agent_Chat,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _estimate_tokens,
    _mock_completion,
)

# ---------------------------------------------------------------------------
# 1. Module-level registration
# ---------------------------------------------------------------------------
assert "PSN_LLM_Agent_Init" in NODE_CLASS_MAPPINGS, "Init node missing from mappings"
assert "PSN_LLM_Agent_Chat" in NODE_CLASS_MAPPINGS, "Chat node missing from mappings"
assert NODE_CLASS_MAPPINGS["PSN_LLM_Agent_Init"] is PSN_LLM_Agent_Init
assert NODE_CLASS_MAPPINGS["PSN_LLM_Agent_Chat"] is PSN_LLM_Agent_Chat
assert "PSN_LLM_Agent_Init" in NODE_DISPLAY_NAME_MAPPINGS
assert "PSN_LLM_Agent_Chat" in NODE_DISPLAY_NAME_MAPPINGS
print("1. registration ok")

# ---------------------------------------------------------------------------
# 2. INPUT_TYPES / RETURN_TYPES / FUNCTION / CATEGORY
# ---------------------------------------------------------------------------
init_types = PSN_LLM_Agent_Init.INPUT_TYPES()
assert "required" in init_types and "provider" in init_types["required"]
assert "model_name" in init_types["required"]
assert "system_prompt" in init_types["required"]
assert "optional" in init_types and "api_key" in init_types["optional"]
assert PSN_LLM_Agent_Init.RETURN_TYPES == ("AGENT_INSTANCE",)
assert PSN_LLM_Agent_Init.FUNCTION == "run"
assert PSN_LLM_Agent_Init.CATEGORY == "ParametricStudio/LLM"

chat_types = PSN_LLM_Agent_Chat.INPUT_TYPES()
assert "agent_instance" in chat_types["required"]
assert "user_message" in chat_types["required"]
assert PSN_LLM_Agent_Chat.RETURN_TYPES == ("STRING", "STRING")
assert PSN_LLM_Agent_Chat.RETURN_NAMES == ("response", "usage")
assert PSN_LLM_Agent_Chat.FUNCTION == "run"
print("2. input/return types ok")

# ---------------------------------------------------------------------------
# 3. Init node: valid provider
# ---------------------------------------------------------------------------
node = PSN_LLM_Agent_Init()
agent, = node.run(provider="openai", model_name="gpt-4o-mini",
                  system_prompt="Be concise.", api_key="sk-test")
assert isinstance(agent, AgentInstance)
assert agent.provider == "openai"
assert agent.model_name == "gpt-4o-mini"
assert agent.api_key == "sk-test"
assert agent.system_prompt == "Be concise."
assert agent.history == []
print("3. init valid ok")

# ---------------------------------------------------------------------------
# 4. Init node: bad provider raises
# ---------------------------------------------------------------------------
try:
    node.run(provider="bogus", model_name="m", system_prompt="")
    raise AssertionError("expected ValueError for bad provider")
except ValueError:
    pass

# Init node: empty model_name raises
try:
    node.run(provider="ollama", model_name="   ", system_prompt="")
    raise AssertionError("expected ValueError for empty model_name")
except ValueError:
    pass
print("4. init bad input ok")

# ---------------------------------------------------------------------------
# 5. Chat node: basic round-trip
# ---------------------------------------------------------------------------
chat_node = PSN_LLM_Agent_Chat()
agent2, = node.run(provider="ollama", model_name="llama3", system_prompt="sys")
resp, usage_str = chat_node.run(agent2, user_message="Hello")
assert isinstance(resp, str) and len(resp) > 0
assert "ollama" in resp and "llama3" in resp
assert "Hello" in resp
usage = json.loads(usage_str)
assert usage["provider"] == "ollama"
assert usage["model"] == "llama3"
assert usage["prompt_tokens"] > 0
assert usage["completion_tokens"] > 0
assert usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"]
print("5. chat basic ok")

# ---------------------------------------------------------------------------
# 6. Chat node: history is accumulated across turns
# ---------------------------------------------------------------------------
resp2, usage2_str = chat_node.run(agent2, user_message="Second")
usage2 = json.loads(usage2_str)
# The second turn should see the first turn in history, so prompt_tokens should
# be >= the first turn's prompt_tokens.
assert usage2["prompt_tokens"] >= usage["prompt_tokens"], \
    f"expected prompt_tokens to grow, got {usage2['prompt_tokens']} < {usage['prompt_tokens']}"
assert "Second" in resp2
# Agent internal history should now have 4 entries (2 turns x 2 messages)
assert len(agent2.history) == 4
print("6. chat history ok")

# ---------------------------------------------------------------------------
# 7. Chat node: bad agent_instance type raises
# ---------------------------------------------------------------------------
try:
    chat_node.run("not-an-agent", user_message="hi")
    raise AssertionError("expected TypeError for bad agent_instance")
except TypeError:
    pass

# Chat node: None user_message raises
try:
    chat_node.run(agent2, user_message=None)
    raise AssertionError("expected ValueError for None user_message")
except ValueError:
    pass
print("7. chat bad input ok")

# ---------------------------------------------------------------------------
# 8. _estimate_tokens edge cases
# ---------------------------------------------------------------------------
assert _estimate_tokens("") == 0
assert _estimate_tokens("a") == 1  # max(1, 0) -> 1
assert _estimate_tokens("abcd") == 1
assert _estimate_tokens("a" * 100) == 25
print("8. token estimate ok")

# ---------------------------------------------------------------------------
# 9. _mock_completion is deterministic
# ---------------------------------------------------------------------------
r1 = _mock_completion("openai", "m", "s", ["h1"], "q1")
r2 = _mock_completion("openai", "m", "s", ["h1"], "q1")
assert r1 == r2, "mock completion must be deterministic"
assert r1["response"] == r2["response"]
print("9. determinism ok")

# ---------------------------------------------------------------------------
# 10. Chat with optional extra history lines
# ---------------------------------------------------------------------------
agent3, = node.run(provider="azure", model_name="gpt-4", system_prompt="")
resp3, usage3_str = chat_node.run(agent3, user_message="Hi",
                                   history="line1\nline2")
usage3 = json.loads(usage3_str)
assert "line1" in resp3 and "line2" in resp3
assert usage3["provider"] == "azure"
print("10. extra history ok")

print("ok")
