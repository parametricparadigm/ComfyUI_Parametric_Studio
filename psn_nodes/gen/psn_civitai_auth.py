"""PSN_Civitai_Auth: pure-logic configuration and validation for Civitai API access.

This module implements ONLY the secure, pure-Python part of a Civitai auth node:
it validates the endpoint against an allow-list, validates the token shape,
redacts the token for safe display, and builds an immutable config object.
It performs NO network I/O, NO file/OS access, and NO subprocess/eval.
The actual HTTP calls (which would use `requests`) are intentionally out of scope;
downstream nodes receive the validated config and are responsible for transport.
"""

from dataclasses import dataclass
from typing import Any, Dict, Tuple

CAT = "ParametricStudio/Civitai"

# Allow-list of known Civitai endpoints. Only these are accepted.
ALLOWED_ENDPOINTS = ("production", "staging", "local")

# Token shape: Civitai API tokens are opaque strings; we require a minimum
# length and forbid whitespace/control characters to catch obvious mistakes.
_MIN_TOKEN_LEN = 8
_MAX_TOKEN_LEN = 256


def _validate_endpoint(endpoint: str) -> Tuple[bool, str]:
    """Return (ok, reason) for the endpoint allow-list check."""
    if not isinstance(endpoint, str):
        return False, "endpoint must be a string"
    ep = endpoint.strip()
    if not ep:
        return False, "endpoint must not be empty"
    if ep not in ALLOWED_ENDPOINTS:
        return False, "endpoint not in allow-list: %s" % (ep,)
    return True, "ok"


def _validate_token(api_token: str) -> Tuple[bool, str]:
    """Return (ok, reason) for the token shape check (no secrets are stored here)."""
    if not isinstance(api_token, str):
        return False, "api_token must be a string"
    tok = api_token.strip()
    if len(tok) < _MIN_TOKEN_LEN:
        return False, "api_token too short (min %d)" % (_MIN_TOKEN_LEN,)
    if len(tok) > _MAX_TOKEN_LEN:
        return False, "api_token too long (max %d)" % (_MAX_TOKEN_LEN,)
    # Reject whitespace and control characters inside the token.
    for ch in tok:
        if ch.isspace() or ord(ch) < 32 or ord(ch) == 127:
            return False, "api_token contains whitespace or control characters"
    return True, "ok"


def redact_token(api_token: str) -> str:
    """Return a safe, redacted representation of the token for display/logging.

    For tokens longer than 4 characters, the first 2 and last 2 characters are
    kept, and the middle is replaced with asterisks. For tokens of length 4 or
    less, the entire token is replaced with asterisks.
    """
    if not isinstance(api_token, str):
        return "<invalid>"
    tok = api_token.strip()
    if len(tok) <= 4:
        return "*" * len(tok)
    return tok[:2] + "*" * (len(tok) - 4) + tok[-2:]


@dataclass(frozen=True)
class CivitaiConfig:
    """Immutable, validated Civitai configuration object.

    The raw token is intentionally NOT stored in this object. Only a redacted
    form and validation metadata are kept, so the config can be passed around
    and logged safely. Downstream transport nodes must receive the raw token
    through a separate, non-logged channel if they need it.
    """
    endpoint: str
    token_redacted: str
    token_valid: bool
    token_reason: str
    endpoint_valid: bool
    endpoint_reason: str

    def is_valid(self) -> bool:
        return self.token_valid and self.endpoint_valid

    def to_dict(self) -> Dict[str, Any]:
        return {
            "endpoint": self.endpoint,
            "token_redacted": self.token_redacted,
            "token_valid": self.token_valid,
            "token_reason": self.token_reason,
            "endpoint_valid": self.endpoint_valid,
            "endpoint_reason": self.endpoint_reason,
            "valid": self.is_valid(),
        }


def build_config(api_token: str, endpoint: str) -> CivitaiConfig:
    """Validate inputs and build an immutable CivitaiConfig."""
    tok_ok, tok_why = _validate_token(api_token)
    ep_ok, ep_why = _validate_endpoint(endpoint)
    ep_norm = endpoint.strip() if isinstance(endpoint, str) else ""
    return CivitaiConfig(
        endpoint=ep_norm,
        token_redacted=redact_token(api_token) if isinstance(api_token, str) else "<invalid>",
        token_valid=tok_ok,
        token_reason=tok_why,
        endpoint_valid=ep_ok,
        endpoint_reason=ep_why,
    )


class PSN_Civitai_Auth:
    """Configure and validate a Civitai API token and endpoint.

    Pure-logic node: validates the endpoint against an allow-list and the token
    shape, then emits an immutable CivitaiConfig. No network, file, or OS access.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "api_token": ("STRING", {"default": "", "multiline": False}),
                "endpoint": (list(ALLOWED_ENDPOINTS), {"default": "production"}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("CIVITAI_CONFIG",)
    RETURN_NAMES = ("civitai_config",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, api_token: str, endpoint: str) -> Tuple[CivitaiConfig]:
        cfg = build_config(api_token, endpoint)
        return (cfg,)


NODE_CLASS_MAPPINGS = {"PSN_Civitai_Auth": PSN_Civitai_Auth}
NODE_DISPLAY_NAME_MAPPINGS = {"PSN_Civitai_Auth": "Civitai Auth (PSN)"}
