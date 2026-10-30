"""PSN_Cloud_LLM_Fallback: routes a task to a local or cloud LLM based on complexity and resource guard.

This module implements ONLY the pure-logic, secure-by-design part of the spec:
- complexity estimation (token count + keyword density)
- routing decision (local vs cloud) based on complexity threshold and a resource guard flag
- payload formatting for the chosen backend (no actual network calls)

No torch, no ComfyUI imports, no network, no file/OS access.
The node takes plain values (strings, floats, booleans) and returns plain values.
"""

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/LLM"

# Keyword list that signals "complex" tasks (used for keyword-density scoring)
_COMPLEX_KEYWORDS = frozenset({
    "analyze", "compare", "evaluate", "optimize", "debug", "refactor",
    "architect", "design", "implement", "integrate", "migrate", "scale",
    "benchmark", "profile", "diagnose", "troubleshoot", "synthesize",
    "abstract", "generalize", "formalize", "derive", "prove", "verify",
})

# Allowed source labels
_SOURCES = ("local", "cloud")


def _estimate_complexity(task_prompt: str) -> float:
    """Estimate task complexity in [0.0, 1.0] from token count and keyword density.

    - token_count: number of whitespace-separated tokens
    - keyword_hits: number of tokens (lowercased) that appear in _COMPLEX_KEYWORDS
    - score = min(1.0, 0.6 * min(token_count / 50.0, 1.0) + 0.4 * min(keyword_hits / 5.0, 1.0))
    """
    if not isinstance(task_prompt, str):
        task_prompt = str(task_prompt)
    tokens = task_prompt.split()
    token_count = len(tokens)
    lower_tokens = [t.lower().strip(".,;:!?\"'()[]{}") for t in tokens]
    keyword_hits = sum(1 for t in lower_tokens if t in _COMPLEX_KEYWORDS)

    token_score = min(token_count / 50.0, 1.0)
    keyword_score = min(keyword_hits / 5.0, 1.0)
    score = 0.6 * token_score + 0.4 * keyword_score
    return max(0.0, min(1.0, score))


def _format_local_payload(task_prompt: str) -> str:
    """Format the payload that would be sent to the local model."""
    return f"[LOCAL] {task_prompt}"


def _format_cloud_payload(task_prompt: str) -> str:
    """Format the payload that would be sent to the cloud API."""
    return f"[CLOUD] {task_prompt}"


class PSN_Cloud_LLM_Fallback:
    """Routes a task prompt to local or cloud LLM based on complexity and resource guard."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "task_prompt": ("STRING", {"default": "", "multiline": True}),
                "complexity_threshold": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
            },
            "optional": {
                "local_handle": ("STRING", {"default": "local_model"}),
                "cloud_handle": ("STRING", {"default": "cloud_model"}),
                "resource_guard_ok": ("BOOLEAN", {"default": True}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("response", "source")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, task_prompt, complexity_threshold, local_handle="local_model",
            cloud_handle="cloud_model", resource_guard_ok=True):
        """
        Estimate complexity and route to local or cloud.

        Returns:
            response (str): formatted payload for the chosen backend
            source (str): "local" or "cloud"
        """
        # Validate inputs
        if not isinstance(task_prompt, str):
            task_prompt = str(task_prompt)
        if not isinstance(complexity_threshold, (int, float)):
            complexity_threshold = 0.5
        complexity_threshold = max(0.0, min(1.0, float(complexity_threshold)))
        if not isinstance(resource_guard_ok, bool):
            resource_guard_ok = bool(resource_guard_ok)

        complexity = _estimate_complexity(task_prompt)

        # Route to cloud if complexity exceeds threshold OR resource guard says local is unavailable
        use_cloud = (complexity > complexity_threshold) or (not resource_guard_ok)

        if use_cloud:
            response = _format_cloud_payload(task_prompt)
            source = "cloud"
        else:
            response = _format_local_payload(task_prompt)
            source = "local"

        return (response, source)


NODE_CLASS_MAPPINGS = {
    "PSN_Cloud_LLM_Fallback": PSN_Cloud_LLM_Fallback,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Cloud_LLM_Fallback": "PSN Cloud LLM Fallback",
}
