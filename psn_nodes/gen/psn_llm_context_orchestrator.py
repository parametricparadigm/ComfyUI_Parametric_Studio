"""PSN_LLM_Context_Orchestrator: pure-logic context manager for LLM provider swapping.

This module implements a secure, dependency-free orchestrator that manages a
unified context architecture for LLM providers. It does NOT perform any network
I/O, file access, or GPU operations. It only manipulates in-memory data structures
representing provider configuration and conversation history.

The PSN_LLM_CONTEXT is represented as a plain dictionary (JSON-serializable) to
avoid custom class dependencies and ensure compatibility with ComfyUI's data
passing conventions. The context dict contains:
  - "provider_type": str (one of "local", "cloud_openai", "cloud_gemini")
  - "model_id": str
  - "history": list of {"role": str, "content": str}
  - "metadata": dict (arbitrary key-value pairs, preserved across updates)

The node validates provider_type against an allow-list, updates the provider
settings, and preserves the existing history and metadata.
"""

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/LLM"

ALLOWED_PROVIDERS = ("local", "cloud_openai", "cloud_gemini")


def _validate_provider(provider_type):
    """Validate that provider_type is in the allow-list. Returns (ok, reason)."""
    if not isinstance(provider_type, str):
        return False, "provider_type must be a string"
    if provider_type not in ALLOWED_PROVIDERS:
        return False, f"provider_type '{provider_type}' not in allow-list {ALLOWED_PROVIDERS}"
    return True, "ok"


def _validate_model_id(model_id):
    """Validate model_id is a non-empty string. Returns (ok, reason)."""
    if not isinstance(model_id, str):
        return False, "model_id must be a string"
    if not model_id.strip():
        return False, "model_id must be a non-empty string"
    return True, "ok"


def _default_context():
    """Return a fresh default context dict."""
    return {
        "provider_type": "local",
        "model_id": "default",
        "history": [],
        "metadata": {},
    }


def _sanitize_context(raw):
    """Coerce raw input into a valid context dict. Returns (context, error)."""
    if raw is None:
        return _default_context(), None
    if not isinstance(raw, dict):
        return None, "context must be a dict"
    ctx = {}
    ctx["provider_type"] = raw.get("provider_type", "local")
    ctx["model_id"] = raw.get("model_id", "default")
    history = raw.get("history", [])
    if not isinstance(history, list):
        return None, "context['history'] must be a list"
    sanitized_history = []
    for i, entry in enumerate(history):
        if not isinstance(entry, dict):
            return None, f"context['history'][{i}] must be a dict"
        role = entry.get("role", "user")
        content = entry.get("content", "")
        if not isinstance(role, str) or not isinstance(content, str):
            return None, f"context['history'][{i}] must have string 'role' and 'content'"
        sanitized_history.append({"role": role, "content": content})
    ctx["history"] = sanitized_history
    metadata = raw.get("metadata", {})
    if not isinstance(metadata, dict):
        return None, "context['metadata'] must be a dict"
    ctx["metadata"] = dict(metadata)
    return ctx, None


class PSN_LLM_Context_Orchestrator:
    """Updates the LLM context with new provider settings, preserving history."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "provider_type": (list(ALLOWED_PROVIDERS),),
                "model_id": ("STRING", {"default": "default", "multiline": False}),
            },
            "optional": {
                "context": ("PSN_LLM_CONTEXT",),
            },
        }

    RETURN_TYPES = ("PSN_LLM_CONTEXT",)
    RETURN_NAMES = ("updated_context",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, provider_type, model_id, context=None):
        """Update context with new provider settings. Preserves history and metadata."""
        # Validate provider
        ok, reason = _validate_provider(provider_type)
        if not ok:
            raise ValueError(reason)

        # Validate model_id
        ok, reason = _validate_model_id(model_id)
        if not ok:
            raise ValueError(reason)

        # Sanitize incoming context
        ctx, err = _sanitize_context(context)
        if err:
            raise ValueError(err)

        # Update provider settings, preserve history and metadata
        ctx["provider_type"] = provider_type
        ctx["model_id"] = model_id

        return (ctx,)


NODE_CLASS_MAPPINGS = {
    "PSN_LLM_Context_Orchestrator": PSN_LLM_Context_Orchestrator,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_LLM_Context_Orchestrator": "PSN LLM Context Orchestrator",
}
