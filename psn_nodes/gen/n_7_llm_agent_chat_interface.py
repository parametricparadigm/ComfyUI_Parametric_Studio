"""ParametricStudio - LLM Agent Chat Interface (offline core).

This module implements the *core* of an LLM agent chat interface for ComfyUI.
Because network access and third-party SDKs (openai, ollama, griptape) are not
available in this environment, the module ships with a deterministic, fully
offline **mock provider** that emulates the provider/client/response contract.

What IS implemented (torch/stdlib only):
  * PSN_LLM_Agent_Init  - builds a provider client object (mock) with config.
  * PSN_LLM_Agent_Chat  - sends a message + history to the client and returns
                          a response string plus a JSON usage string.
  * A small in-memory AgentInstance dataclass that carries the config and a
    conversation history.

What is NOT implemented (requires network / SDKs):
  * Real HTTP calls to OpenAI / Azure / Ollama endpoints.
  * Token counting via provider tokenizers (usage is estimated with a simple
    character-based heuristic).
  * Streaming responses.
  * Advanced griptape agent features (tools, memory backends, etc.).
"""

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

CAT = "ParametricStudio/LLM"

# ---------------------------------------------------------------------------
# Provider registry (mock implementations only - no network)
# ---------------------------------------------------------------------------

_PROVIDERS = ("openai", "ollama", "azure")


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token (common heuristic)."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def _mock_completion(provider: str, model: str, system_prompt: str,
                     history: List[str], user_message: str) -> Dict[str, Any]:
    """Deterministic offline stand-in for a real LLM completion call.

    Returns a dict shaped like a minimal provider response:
        {"response": str, "prompt_tokens": int, "completion_tokens": int}
    """
    # Build a deterministic, inspectable reply so tests can assert on it.
    parts = [f"[{provider}:{model}]"]
    if system_prompt:
        parts.append(f"sys={system_prompt!r}")
    for h in history:
        parts.append(f"h={h!r}")
    parts.append(f"q={user_message!r}")
    reply = " | ".join(parts)

    prompt_text = system_prompt + "\n" + "\n".join(history) + "\n" + user_message
    prompt_tokens = _estimate_tokens(prompt_text)
    completion_tokens = _estimate_tokens(reply)
    return {
        "response": reply,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
    }


# ---------------------------------------------------------------------------
# Agent instance (plain Python object, no tensors)
# ---------------------------------------------------------------------------

@dataclass
class AgentInstance:
    """Holds the configuration for one LLM agent.

    In a full implementation this would wrap a real SDK client; here it is a
    lightweight config carrier plus a mock completion function.
    """
    provider: str
    model_name: str
    api_key: Optional[str]
    system_prompt: str
    # conversation history maintained across chat calls (list of strings)
    history: List[str] = field(default_factory=list)

    def complete(self, user_message: str) -> Dict[str, Any]:
        """Run one completion turn (mock, offline)."""
        result = _mock_completion(
            self.provider,
            self.model_name,
            self.system_prompt,
            list(self.history),
            user_message,
        )
        # update internal history (never mutate caller's list)
        self.history = self.history + [user_message, result["response"]]
        return result


# ---------------------------------------------------------------------------
# ComfyUI nodes
# ---------------------------------------------------------------------------

class PSN_LLM_Agent_Init:
    """Initialize an LLM agent with a provider, model and system prompt."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "provider": (list(_PROVIDERS),),
                "model_name": ("STRING", {"default": "gpt-4o-mini", "multiline": False}),
                "system_prompt": ("STRING", {"default": "You are a helpful assistant.", "multiline": True}),
            },
            "optional": {
                "api_key": ("STRING", {"default": "", "multiline": False}),
            },
        }

    RETURN_TYPES = ("AGENT_INSTANCE",)
    RETURN_NAMES = ("agent_instance",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, provider: str, model_name: str, system_prompt: str,
            api_key: str = "") -> tuple:
        if provider not in _PROVIDERS:
            raise ValueError(f"Unknown provider: {provider!r}")
        if not model_name or not model_name.strip():
            raise ValueError("model_name must be a non-empty string")
        agent = AgentInstance(
            provider=provider,
            model_name=model_name.strip(),
            api_key=api_key or None,
            system_prompt=system_prompt or "",
        )
        return (agent,)


class PSN_LLM_Agent_Chat:
    """Send a message to an LLM agent and get a response + usage JSON."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "agent_instance": ("AGENT_INSTANCE",),
                "user_message": ("STRING", {"default": "Hello", "multiline": True}),
            },
            "optional": {
                "history": ("STRING", {"default": "", "multiline": True,
                                       "tooltip": "Optional extra history, one entry per line."}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("response", "usage")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, agent_instance: AgentInstance, user_message: str,
            history: str = "") -> tuple:
        if not isinstance(agent_instance, AgentInstance):
            raise TypeError("agent_instance must be an AgentInstance")
        if user_message is None:
            raise ValueError("user_message must not be None")

        # Build the full history: agent's internal history + optional extra lines
        extra: List[str] = []
        if history:
            extra = [line for line in history.splitlines() if line.strip()]

        # We pass the combined history to the mock completion but keep the
        # agent's internal history as the source of truth for future turns.
        full_history = list(agent_instance.history) + extra
        result = _mock_completion(
            agent_instance.provider,
            agent_instance.model_name,
            agent_instance.system_prompt,
            full_history,
            user_message,
        )

        # Update the agent's internal history (do not mutate in place)
        agent_instance.history = agent_instance.history + [user_message, result["response"]]

        usage = json.dumps({
            "provider": agent_instance.provider,
            "model": agent_instance.model_name,
            "prompt_tokens": result["prompt_tokens"],
            "completion_tokens": result["completion_tokens"],
            "total_tokens": result["prompt_tokens"] + result["completion_tokens"],
        })
        return (result["response"], usage)


# ---------------------------------------------------------------------------
# ComfyUI registration
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_LLM_Agent_Init": PSN_LLM_Agent_Init,
    "PSN_LLM_Agent_Chat": PSN_LLM_Agent_Chat,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_LLM_Agent_Init": "LLM Agent Init (ParametricStudio)",
    "PSN_LLM_Agent_Chat": "LLM Agent Chat (ParametricStudio)",
}
