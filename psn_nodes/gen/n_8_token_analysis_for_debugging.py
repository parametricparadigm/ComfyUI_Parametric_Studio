"""PSN_TokenAnalyzer: pure-logic token analysis for debugging text conditioning.

This module implements the *pure-logic, secure-by-design* part of the
"Token Analysis for Debugging" spec.  The real ComfyUI node would decode a
CONDITIONING tensor with a CLIP model; that requires torch/transformers and
GPU access, which are out of scope here.  Instead this node operates on plain
values (a JSON text payload describing the conditioning, plus an optional
token vocabulary) and performs:

  * parsing and validation of the conditioning payload,
  * allow-list / sanity checks on token IDs and weights,
  * normalization of weights,
  * ranking of the most influential tokens,
  * generation of a human-readable analysis report.

It never opens sockets, reads/writes files, or shells out.  All inputs are
plain numbers, strings, or JSON text.
"""

import json
import math

CAT = "ParametricStudio/Debugging"

# ---------------------------------------------------------------------------
# Small safe helpers (kept local so the module is self-contained).
# ---------------------------------------------------------------------------

def _is_number(value):
    """Return True if value is an int/float (but not bool) and finite."""
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return math.isfinite(value)
    return False


def _coerce_number(value, default=0.0):
    """Best-effort conversion of a scalar to a finite float."""
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value) if math.isfinite(value) else default
    if isinstance(value, str):
        try:
            num = float(value.strip())
        except (ValueError, TypeError):
            return default
        return num if math.isfinite(num) else default
    return default


def _parse_conditioning(conditioning):
    """Parse a conditioning payload into a list of (token_id, weight) pairs.

    Accepts either:
      * a JSON string, or
      * an already-parsed dict / list.

    Supported shapes:
      {"tokens": [1, 2, 3], "weights": [0.5, 0.3, 0.2]}
      [{"id": 1, "weight": 0.5}, ...]
      [1, 2, 3]                      # weights default to 1.0
      {"token_ids": [...], "token_weights": [...]}

    Returns (pairs, error_message).  pairs is a list of (int, float).
    """
    if conditioning is None:
        return [], "conditioning is empty"

    data = conditioning
    if isinstance(data, str):
        text = data.strip()
        if not text:
            return [], "conditioning string is empty"
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, ValueError) as exc:
            return [], "invalid JSON: %s" % exc

    if isinstance(data, dict):
        ids = data.get("tokens", data.get("token_ids"))
        weights = data.get("weights", data.get("token_weights"))
        if ids is None:
            return [], "missing 'tokens'/'token_ids' key"
        if not isinstance(ids, list):
            return [], "'tokens' must be a list"
        if weights is None:
            weights = [1.0] * len(ids)
        if not isinstance(weights, list):
            return [], "'weights' must be a list"
        if len(ids) != len(weights):
            return [], "token count (%d) != weight count (%d)" % (len(ids), len(weights))
        pairs = []
        for idx, (tid, w) in enumerate(zip(ids, weights)):
            if isinstance(tid, bool) or not isinstance(tid, int):
                return [], "token id at index %d is not an integer" % idx
            if tid < 0:
                return [], "token id at index %d is negative" % idx
            wnum = _coerce_number(w, 0.0)
            if wnum < 0:
                return [], "weight at index %d is negative" % idx
            pairs.append((tid, wnum))
        return pairs, None

    if isinstance(data, list):
        pairs = []
        for idx, item in enumerate(data):
            if isinstance(item, dict):
                tid = item.get("id", item.get("token_id"))
                w = item.get("weight", item.get("w", 1.0))
                if tid is None:
                    return [], "item %d missing 'id'" % idx
                if isinstance(tid, bool) or not isinstance(tid, int):
                    return [], "item %d id is not an integer" % idx
                if tid < 0:
                    return [], "item %d id is negative" % idx
                wnum = _coerce_number(w, 1.0)
                if wnum < 0:
                    return [], "item %d weight is negative" % idx
                pairs.append((tid, wnum))
            elif isinstance(item, int) and not isinstance(item, bool):
                if item < 0:
                    return [], "item %d is negative" % idx
                pairs.append((item, 1.0))
            else:
                return [], "item %d is not a valid token entry" % idx
        return pairs, None

    return [], "unsupported conditioning type: %s" % type(data).__name__


def _normalize_weights(pairs):
    """Return (normalized_pairs, total, all_zero)."""
    total = sum(w for _, w in pairs)
    if total <= 0:
        return [(tid, 0.0) for tid, _ in pairs], 0.0, True
    return [(tid, w / total) for tid, w in pairs], total, False


def _rank_tokens(pairs, top_n=10):
    """Return the top_n (token_id, weight) pairs sorted by weight desc."""
    ordered = sorted(pairs, key=lambda p: (-p[1], p[0]))
    return ordered[:max(0, top_n)]


def _build_report(pairs, normalized, total, all_zero, top_n, vocab=None):
    """Build a human-readable analysis report string."""
    lines = []
    lines.append("=== PSN Token Analysis Report ===")
    lines.append("Total tokens: %d" % len(pairs))
    if all_zero:
        lines.append("Warning: all weights are zero; normalization skipped.")
    else:
        lines.append("Raw weight sum: %.6f" % total)
        lines.append("Normalized weights sum to 1.0")

    unique_ids = sorted({tid for tid, _ in pairs})
    lines.append("Unique token ids: %d" % len(unique_ids))
    if unique_ids:
        lines.append("Token id range: %d .. %d" % (min(unique_ids), max(unique_ids)))

    if vocab:
        lines.append("Vocabulary size: %d" % len(vocab))
        out_of_range = [tid for tid in unique_ids if tid >= len(vocab)]
        if out_of_range:
            lines.append("Warning: %d token id(s) exceed vocabulary size: %s"
                         % (len(out_of_range), out_of_range[:10]))

    lines.append("")
    lines.append("Top %d most influential tokens:" % top_n)
    top = _rank_tokens(normalized, top_n)
    if not top:
        lines.append("  (none)")
    for rank, (tid, w) in enumerate(top, start=1):
        label = ""
        if vocab and tid < len(vocab):
            label = " (%s)" % vocab[tid]
        lines.append("  %2d. token_id=%-6d weight=%.6f%s" % (rank, tid, w, label))

    # Distribution summary
    if normalized and not all_zero:
        weights = [w for _, w in normalized]
        mean_w = sum(weights) / len(weights)
        max_w = max(weights)
        min_w = min(weights)
        lines.append("")
        lines.append("Weight distribution: min=%.6f mean=%.6f max=%.6f"
                     % (min_w, mean_w, max_w))
        # Entropy (base 2) as a rough diversity measure
        entropy = 0.0
        for w in weights:
            if w > 0:
                entropy -= w * math.log2(w)
        lines.append("Shannon entropy (bits): %.4f" % entropy)

    lines.append("=== End of Report ===")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

class PSN_TokenAnalyzer:
    """Analyze and report on text conditioning tokens for debugging.

    Pure-logic implementation: takes a JSON-text conditioning payload and an
    optional vocabulary, validates it, normalizes weights, ranks the most
    influential tokens, and emits a text report.  No GPU, no torch, no I/O.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "conditioning": ("STRING", {"default": "", "multiline": True}),
            },
            "optional": {
                "vocabulary": ("STRING", {"default": "", "multiline": True}),
                "top_n": ("INT", {"default": 10, "min": 1, "max": 1000, "step": 1}),
            },
        }

    RETURN_TYPES = ("INT", "FLOAT", "STRING")
    RETURN_NAMES = ("token_count", "max_weight", "analysis_report")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, conditioning, vocabulary="", top_n=10):
        pairs, err = _parse_conditioning(conditioning)
        if err is not None:
            report = "=== PSN Token Analysis Report ===\nError: %s\n=== End of Report ===" % err
            return (0, 0.0, report)

        normalized, total, all_zero = _normalize_weights(pairs)

        vocab = None
        if vocabulary:
            text = vocabulary.strip()
            if text:
                try:
                    vocab = json.loads(text)
                    if not isinstance(vocab, list):
                        vocab = None
                except (json.JSONDecodeError, ValueError):
                    vocab = None

        report = _build_report(pairs, normalized, total, all_zero, top_n, vocab)

        max_weight = max((w for _, w in normalized), default=0.0)
        return (len(pairs), max_weight, report)


NODE_CLASS_MAPPINGS = {
    "PSN_TokenAnalyzer": PSN_TokenAnalyzer,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_TokenAnalyzer": "PSN Token Analyzer (Debugging)",
}
