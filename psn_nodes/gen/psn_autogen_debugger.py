"""PSN_AutoGen_Debugger: pure-logic group-chat debate resolver for workflow errors.

This module implements ONLY the deterministic, secure-by-design core of a
multi-agent debate loop. It does NOT open sockets, call any LLM, import torch,
import comfy, or perform any network/file/OS I/O. The LLM backend is abstracted
away: the node accepts a plain ``llm_connection`` value (any JSON-serialisable
object) and a ``mock_llm`` callable (or JSON text) that maps a prompt string to
a response string. When no mock is supplied, a deterministic built-in responder
is used so the node is fully testable offline.

The debate protocol:
  1. Each agent proposes a fix for the error.
  2. Subsequent agents critique the running transcript.
  3. Consensus is reached when a response contains the marker ``CONSENSUS:``
     followed by the agreed resolution, or when the max-turn limit is hit.

All identifiers start with a letter. No dunder tricks, no eval/exec.
"""

import json

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CONSENSUS_MARKER = "CONSENSUS:"
_MAX_TURNS_DEFAULT = 6
_MAX_TURNS_MIN = 1
_MAX_TURNS_MAX = 50
_MAX_AGENTS_MIN = 1
_MAX_AGENTS_MAX = 12
_MAX_LOG_CHARS = 20000

# Default deterministic responder used when no mock_llm is provided.
# It simply echoes a canned proposal; consensus is never auto-reached,
# so the loop terminates via max_turns.
def _default_llm(prompt):
    return "Proposal: adjust the parameter to a safe default value."


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sanitize_agents(agents):
    """Validate and normalise the agents list.

    Returns (cleaned_list, error_string_or_None).
    """
    if agents is None:
        return [], "agents list is required"
    if not isinstance(agents, (list, tuple)):
        return [], "agents must be a list of strings"
    cleaned = []
    for idx, agent in enumerate(agents):
        if not isinstance(agent, str):
            return [], "agents[%d] is not a string" % idx
        name = agent.strip()
        if not name:
            return [], "agents[%d] is empty" % idx
        if len(name) > 64:
            return [], "agents[%d] exceeds 64 characters" % idx
        if name in cleaned:
            return [], "duplicate agent name: %s" % name
        cleaned.append(name)
    if len(cleaned) < _MAX_AGENTS_MIN:
        return [], "at least one agent is required"
    if len(cleaned) > _MAX_AGENTS_MAX:
        return [], "too many agents (max %d)" % _MAX_AGENTS_MAX
    return cleaned, None


def _build_prompt(error_log, agent_name, transcript, turn_index):
    """Build the prompt string for a single agent turn."""
    lines = []
    lines.append("You are %s in a group chat debugging a workflow error." % agent_name)
    lines.append("Error log: %s" % error_log)
    if transcript:
        lines.append("Transcript so far:")
        for entry in transcript:
            lines.append("  %s" % entry)
    lines.append("Turn %d. Propose a fix or critique the current proposals." % turn_index)
    lines.append("If consensus is reached, start your response with '%s' followed by the agreed fix." % _CONSENSUS_MARKER)
    return "\n".join(lines)


def _extract_consensus(response):
    """Return the resolution string if the response contains the consensus marker, else None."""
    if not isinstance(response, str):
        return None
    idx = response.find(_CONSENSUS_MARKER)
    if idx == -1:
        return None
    resolution = response[idx + len(_CONSENSUS_MARKER):].strip()
    if not resolution:
        return None
    return resolution


def _run_debate(error_log, agents, llm_callable, max_turns):
    """Run the debate loop.

    Returns (resolution, chat_log_entries, reason).
    """
    transcript = []
    resolution = None
    reason = "max_turns_reached"

    for turn in range(max_turns):
        agent_name = agents[turn % len(agents)]
        prompt = _build_prompt(error_log, agent_name, transcript, turn)
        try:
            response = llm_callable(prompt)
        except Exception:
            response = "Error: LLM call failed."
        if not isinstance(response, str):
            response = str(response)
        # Truncate very long responses to keep the log bounded.
        if len(response) > 2000:
            response = response[:2000] + " [truncated]"
        entry = "[%d] %s: %s" % (turn, agent_name, response)
        transcript.append(entry)

        consensus = _extract_consensus(response)
        if consensus is not None:
            resolution = consensus
            reason = "consensus_reached"
            break

    chat_log = "\n".join(transcript)
    if len(chat_log) > _MAX_LOG_CHARS:
        chat_log = chat_log[:_MAX_LOG_CHARS] + "\n[log truncated]"
    return resolution, chat_log, reason


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

class PSN_AutoGen_Debugger:
    """Multiple agents debate and resolve workflow errors or parameter conflicts.

    Pure-logic implementation: no network, no LLM calls. The LLM is abstracted
    via a ``mock_llm`` input (a callable or JSON text describing a simple
    responder). When omitted, a deterministic built-in responder is used.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "error_log": ("STRING", {"default": "", "multiline": True}),
                "agents": ("STRING", {"default": "Engineer,Artist,Manager", "multiline": False}),
                "max_turns": ("INT", {"default": _MAX_TURNS_DEFAULT, "min": _MAX_TURNS_MIN, "max": _MAX_TURNS_MAX, "step": 1}),
            },
            "optional": {
                "llm_connection": (None,),
                "mock_llm": (None,),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("resolution", "chat_log", "reason")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/AutoGen"

    def run(self, error_log, agents, max_turns, llm_connection=None, mock_llm=None):
        # Parse agents from comma-separated string
        if isinstance(agents, str):
            agent_list = [a.strip() for a in agents.split(",") if a.strip()]
        elif isinstance(agents, (list, tuple)):
            agent_list = list(agents)
        else:
            agent_list = []

        cleaned_agents, err = _sanitize_agents(agent_list)
        if err is not None:
            return ("ERROR: " + err, "", "invalid_agents")

        # Determine the LLM callable
        llm_callable = _default_llm
        if mock_llm is not None:
            if callable(mock_llm):
                llm_callable = mock_llm
            elif isinstance(mock_llm, str):
                # Try to parse as JSON with a "responses" list
                try:
                    data = json.loads(mock_llm)
                    if isinstance(data, dict) and "responses" in data:
                        responses = data["responses"]
                        if isinstance(responses, list) and all(isinstance(r, str) for r in responses):
                            counter = [0]
                            def _json_llm(prompt):
                                idx = counter[0] % len(responses)
                                counter[0] += 1
                                return responses[idx]
                            llm_callable = _json_llm
                except (json.JSONDecodeError, ValueError):
                    pass
            # If mock_llm is neither callable nor valid JSON, fall through to default

        resolution, chat_log, reason = _run_debate(error_log, cleaned_agents, llm_callable, max_turns)
        return (resolution, chat_log, reason)


# ---------------------------------------------------------------------------
# Mappings
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_AutoGen_Debugger": PSN_AutoGen_Debugger,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_AutoGen_Debugger": "PSN AutoGen Debugger",
}
