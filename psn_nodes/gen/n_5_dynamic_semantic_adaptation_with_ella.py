"""
PSN_ELLA_Semantic_Connector: A pure-logic, secure-by-design implementation of the
Dynamic Semantic Adaptation (ELLA) connector.

This module implements ONLY the pure-logic, secure-by-design part of the spec:
- Message/payload formatting for the ELLA connector request
- Config validation (sigma range, strength range, model allow-list)
- Allow-list checks for model identifiers
- Rate limiting for connector invocations
- Token redaction for sensitive fields in payloads
- Parsing of connector responses

It does NOT open sockets, access files, use torch, import comfy, or perform
network I/O. All functions and node wrappers take plain values (numbers,
strings, JSON text) and return plain values.

The node simulates the ELLA semantic adaptation by applying a deterministic
transformation to a conditioning payload based on sigma and strength, using
only the Python standard library.
"""

import json
import time
import hashlib

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CAT = "ParametricStudio/ELLA"

# Allow-list of valid ELLA model identifiers
ALLOWED_ELLA_MODELS = (
    "ella_v1_small",
    "ella_v1_medium",
    "ella_v1_large",
    "ella_v2_small",
    "ella_v2_medium",
    "ella_v2_large",
)

# Rate limiting: max requests per sliding window
RATE_LIMIT_MAX_REQUESTS = 10
RATE_LIMIT_WINDOW_SECONDS = 60.0

# Sensitive field names that must be redacted in payloads
SENSITIVE_FIELDS = frozenset({
    "api_key", "token", "secret", "password", "credential",
    "auth_token", "access_key", "private_key",
})

# ---------------------------------------------------------------------------
# Rate Limiter (pure in-memory, no I/O)
# ---------------------------------------------------------------------------

class _RateLimiter:
    """Simple sliding-window rate limiter using only time.time()."""

    def __init__(self, max_requests: int, window_seconds: float):
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._timestamps = []

    def allow(self) -> bool:
        now = time.time()
        cutoff = now - self._window_seconds
        # Remove expired timestamps
        self._timestamps = [t for t in self._timestamps if t > cutoff]
        if len(self._timestamps) >= self._max_requests:
            return False
        self._timestamps.append(now)
        return True

    def reset(self) -> None:
        self._timestamps = []


# Module-level rate limiter instance
_ella_rate_limiter = _RateLimiter(RATE_LIMIT_MAX_REQUESTS, RATE_LIMIT_WINDOW_SECONDS)

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _validate_sigma(sigma: float) -> tuple:
    """Validate sigma is a finite non-negative float. Returns (ok, reason)."""
    if not isinstance(sigma, (int, float)):
        return False, "sigma must be a number"
    if isinstance(sigma, float) and (sigma != sigma or sigma in (float("inf"), float("-inf"))):
        return False, "sigma must be a finite number"
    if sigma < 0:
        return False, "sigma must be non-negative"
    return True, "ok"


def _validate_strength(strength: float) -> tuple:
    """Validate strength is in [0, 1]. Returns (ok, reason)."""
    if not isinstance(strength, (int, float)):
        return False, "strength must be a number"
    if isinstance(strength, float) and (strength != strength or strength in (float("inf"), float("-inf"))):
        return False, "strength must be a finite number"
    if strength < 0.0 or strength > 1.0:
        return False, "strength must be in [0, 1]"
    return True, "ok"


def _validate_model(model_id: str) -> tuple:
    """Validate model_id is in the allow-list. Returns (ok, reason)."""
    if not isinstance(model_id, str):
        return False, "model_id must be a string"
    if model_id not in ALLOWED_ELLA_MODELS:
        return False, f"model_id '{model_id}' not in allow-list"
    return True, "ok"


def _redact_sensitive(payload: dict) -> dict:
    """Return a copy of payload with sensitive fields redacted (recursively)."""
    redacted = {}
    for key, value in payload.items():
        if key in SENSITIVE_FIELDS:
            redacted[key] = "***REDACTED***"
        elif isinstance(value, dict):
            redacted[key] = _redact_sensitive(value)
        else:
            redacted[key] = value
    return redacted


def _deterministic_transform(conditioning: dict, sigma: float, strength: float, model_id: str) -> dict:
    """
    Apply a deterministic semantic adaptation to the conditioning payload.

    The transformation:
    1. Computes a hash-based offset from sigma, strength, and model_id.
    2. Scales each numeric value in the conditioning by a factor derived
       from the hash, modulated by strength.
    3. Adds a small sigma-dependent shift to simulate timestep-aware
       semantic adjustment.

    This is a pure function: same inputs always produce same outputs.
    """
    # Build a deterministic seed from inputs
    seed_str = f"{sigma:.6f}|{strength:.6f}|{model_id}"
    seed_bytes = seed_str.encode("utf-8")
    digest = hashlib.sha256(seed_bytes).digest()
    # Use first 8 bytes as a float-like offset in [0, 1)
    offset = int.from_bytes(digest[:8], byteorder="big") / (2 ** 64)

    # Scale factor: 1.0 + strength * (offset - 0.5) * 2.0
    # This gives a range of [1 - strength, 1 + strength]
    scale = 1.0 + strength * (offset - 0.5) * 2.0

    # Sigma-dependent shift: small, proportional to sigma
    sigma_shift = sigma * 0.01

    transformed = {}
    for key, value in conditioning.items():
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            transformed[key] = value * scale + sigma_shift
        else:
            transformed[key] = value

    return transformed


def _format_request_payload(
    conditioning: dict,
    sigma: float,
    strength: float,
    model_id: str,
) -> str:
    """
    Format the ELLA connector request as a JSON string.
    Sensitive fields are redacted before serialization.
    """
    payload = {
        "type": "ella_semantic_connector",
        "model": model_id,
        "sigma": sigma,
        "strength": strength,
        "conditioning": conditioning,
    }
    redacted = _redact_sensitive(payload)
    return json.dumps(redacted, sort_keys=True, separators=(",", ":"))


def _parse_response(response_text: str) -> tuple:
    """
    Parse the ELLA connector response JSON text.
    Returns (ok, parsed_dict_or_error_string).
    """
    if not isinstance(response_text, str):
        return False, "response must be a string"
    try:
        parsed = json.loads(response_text)
    except (json.JSONDecodeError, ValueError):
        return False, "invalid JSON in response"
    if not isinstance(parsed, dict):
        return False, "response must be a JSON object"
    if "conditioning" not in parsed:
        return False, "response missing 'conditioning' field"
    return True, parsed


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

class PSN_ELLA_Semantic_Connector:
    """
    Dynamically adjust semantic features during the diffusion process using
    a Timestep-Aware Semantic Connector (ELLA).

    This is a pure-logic implementation: it validates inputs, checks the
    model allow-list, enforces rate limiting, redacts sensitive fields,
    and applies a deterministic transformation to the conditioning payload.
    No GPU, torch, network, or file I/O is performed.

    Inputs:
        conditioning: JSON text representing the conditioning payload (dict)
        sigma: Current timestep sigma (float, >= 0)
        ella_model: Model identifier (must be in allow-list)
        strength: Adaptation strength in [0, 1]

    Outputs:
        conditioning: JSON text of the adapted conditioning payload
        status: "ok" or an error description
        request_payload: The formatted (redacted) request JSON text
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "conditioning": ("STRING", {"default": "{}", "multiline": True}),
                "sigma": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1e9, "step": 0.001}),
                "ella_model": (list(ALLOWED_ELLA_MODELS),),
                "strength": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("conditioning", "status", "request_payload")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, conditioning, sigma, ella_model, strength):
        # Validate sigma
        ok, reason = _validate_sigma(sigma)
        if not ok:
            return ("{}", f"error: {reason}", "")

        # Validate strength
        ok, reason = _validate_strength(strength)
        if not ok:
            return ("{}", f"error: {reason}", "")

        # Validate model
        ok, reason = _validate_model(ella_model)
        if not ok:
            return ("{}", f"error: {reason}", "")

        # Parse conditioning JSON
        if not isinstance(conditioning, str):
            return ("{}", "error: conditioning must be a JSON string", "")
        try:
            cond_dict = json.loads(conditioning)
        except (json.JSONDecodeError, ValueError):
            return ("{}", "error: invalid JSON in conditioning", "")
        if not isinstance(cond_dict, dict):
            return ("{}", "error: conditioning must be a JSON object", "")

        # Rate limit check
        if not _ella_rate_limiter.allow():
            return ("{}", "error: rate limit exceeded", "")

        # Format request payload (with redaction)
        request_payload = _format_request_payload(cond_dict, sigma, strength, ella_model)

        # Apply deterministic transformation
        adapted = _deterministic_transform(cond_dict, sigma, strength, ella_model)

        # Serialize result
        result_json = json.dumps(adapted, sort_keys=True, separators=(",", ":"))

        return (result_json, "ok", request_payload)


# ---------------------------------------------------------------------------
# Module-level mappings
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_ELLA_Semantic_Connector": PSN_ELLA_Semantic_Connector,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_ELLA_Semantic_Connector": "ELLA Semantic Connector",
}
