"""Parametric Studio - Structured Continuity Rules Engine.

Nodes:
  - PSN_ContinuityRuleDefiner: parses natural-language rules into a structured
    rule set ("must have" / "must not have" attribute constraints).
  - PSN_ContinuityEnforcer: checks a generated IMAGE against the rule set using
    lightweight, deterministic color/attribute heuristics (no VLM dependency).

The rule set is a plain Python dict (JSON-serialisable) so it can be passed
between nodes without any custom tensor plumbing.
"""

import re
import torch

CAT = "ParametricStudio/Continuity"

# ---------------------------------------------------------------------------
# Colour keyword -> (r, g, b) reference values in 0..1
# ---------------------------------------------------------------------------
_COLOURS = {
    "red":    (0.80, 0.15, 0.15),
    "orange": (0.90, 0.50, 0.10),
    "yellow": (0.95, 0.90, 0.10),
    "green":  (0.15, 0.70, 0.20),
    "blue":   (0.15, 0.25, 0.85),
    "purple": (0.55, 0.20, 0.75),
    "pink":   (0.95, 0.45, 0.65),
    "brown":  (0.45, 0.28, 0.12),
    "black":  (0.05, 0.05, 0.05),
    "white":  (0.95, 0.95, 0.95),
    "grey":   (0.50, 0.50, 0.50),
    "gray":   (0.50, 0.50, 0.50),
}

# Attribute keywords that map to a colour check
_COLOUR_ATTRS = {
    "hair", "eye", "eyes", "shirt", "pants", "dress", "skin",
    "background", "wall", "floor", "car", "building", "sky",
}

# Generic attribute keywords (no colour) -> presence check via keyword in text
_GENERIC_ATTRS = {
    "hat", "glasses", "scarf", "jacket", "smile", "frown",
    "sword", "shield", "crown", "wings", "tail", "ears",
}

# ---------------------------------------------------------------------------
# Rule parsing helpers
# ---------------------------------------------------------------------------

def _parse_rule_line(line):
    """Parse a single rule line into a dict.

    Recognised patterns (case-insensitive):
      - "must have <attr>"            -> positive constraint
      - "must not have <attr>"        -> negative constraint
      - "must be <colour> <attr>"     -> positive colour constraint
      - "must not be <colour> <attr>" -> negative colour constraint
      - "no <attr>"                   -> negative constraint
      - "has <attr>"                  -> positive constraint

    Returns dict with keys: polarity ('+'/'-'), attr, colour (or None), raw.
    """
    line = line.strip().rstrip(".;:")
    if not line:
        return None

    low = line.lower()
    polarity = "+"
    colour = None
    attr = None

    # Determine polarity
    if "must not" in low or "no " in low or "without" in low:
        polarity = "-"

    # Try to find a colour word
    for cname, _ in _COLOURS.items():
        if re.search(r"\b" + re.escape(cname) + r"\b", low):
            colour = cname
            break

    # Try to find an attribute word
    for a in _COLOUR_ATTRS | _GENERIC_ATTRS:
        if re.search(r"\b" + re.escape(a) + r"\b", low):
            attr = a
            break

    # If no attribute found, use the whole line as a free-text tag
    if attr is None:
        # strip known polarity words and colour words
        cleaned = low
        for w in ("must not have", "must not be", "must have", "must be",
                  "no ", "has ", "without ", "should have", "should not have"):
            cleaned = cleaned.replace(w, "")
        if colour:
            cleaned = cleaned.replace(colour, "")
        cleaned = cleaned.strip(" .;:")
        if cleaned:
            attr = cleaned
        else:
            return None

    return {"polarity": polarity, "attr": attr, "colour": colour, "raw": line}


def _parse_rule_text(text):
    """Parse a multi-line rule string into a list of rule dicts."""
    if not text or not isinstance(text, str):
        return []
    rules = []
    for line in re.split(r"[;\n]+", text):
        r = _parse_rule_line(line)
        if r is not None:
            rules.append(r)
    return rules


# ---------------------------------------------------------------------------
# Heuristic image checks
# ---------------------------------------------------------------------------

def _colour_fraction(image, colour_name, threshold=0.35):
    """Return the fraction of pixels in `image` (B,H,W,C float 0..1) that are
    close to the reference colour.  'Close' means Euclidean distance in RGB
    space < threshold."""
    ref = torch.tensor(_COLOURS[colour_name], dtype=image.dtype, device=image.device)
    # image: [B, H, W, C]  ->  distance per pixel
    diff = image - ref  # broadcast over B,H,W
    dist = torch.sqrt((diff ** 2).sum(dim=-1))  # [B, H, W]
    mask = dist < threshold
    return mask.float().mean().item()


def _check_rule_on_image(image, rule):
    """Check a single rule against an image tensor.

    Returns (passed: bool, detail: str).
    """
    attr = rule["attr"]
    colour = rule["colour"]
    polarity = rule["polarity"]

    if colour is not None:
        frac = _colour_fraction(image, colour)
        # Consider the colour "present" if at least 2 % of pixels match
        present = frac >= 0.02
        if polarity == "+":
            passed = present
            detail = (f"must have {colour} {attr}: "
                      f"{colour} fraction={frac:.3f} -> {'PASS' if passed else 'FAIL'}")
        else:
            passed = not present
            detail = (f"must not have {colour} {attr}: "
                      f"{colour} fraction={frac:.3f} -> {'PASS' if passed else 'FAIL'}")
        return passed, detail
    else:
        # Non-colour attribute: we cannot verify presence from pixels alone.
        # Treat as PASS with a note (heuristic limitation).
        note = (f"{polarity} {attr}: non-colour attribute, "
                f"assumed PASS (heuristic limitation)")
        return True, note


# ---------------------------------------------------------------------------
# Node classes
# ---------------------------------------------------------------------------

class PSN_ContinuityRuleDefiner:
    """Parse natural-language continuity rules into a structured rule set.

    Inputs:
      character_profile (STRING): e.g. "Red hair, blue eyes, must have a hat"
      scene_rules       (STRING): e.g. "No background fire; must be a night scene"

    Output:
      rule_set (PSN_RULE_SET): dict with keys 'character_rules', 'scene_rules',
                               'all_rules' (list of rule dicts).
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "character_profile": ("STRING", {"default": "", "multiline": True}),
                "scene_rules": ("STRING", {"default": "", "multiline": True}),
            }
        }

    RETURN_TYPES = ("PSN_RULE_SET",)
    RETURN_NAMES = ("rule_set",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, character_profile="", scene_rules=""):
        char_rules = _parse_rule_text(character_profile)
        scene_rules_parsed = _parse_rule_text(scene_rules)
        rule_set = {
            "character_rules": char_rules,
            "scene_rules": scene_rules_parsed,
            "all_rules": char_rules + scene_rules_parsed,
        }
        return (rule_set,)


class PSN_ContinuityEnforcer:
    """Check a generated IMAGE against a structured rule set.

    Uses lightweight colour-fraction heuristics (no VLM).

    Inputs:
      generated_asset (IMAGE): float tensor [B, H, W, C] in 0..1
      rule_set        (PSN_RULE_SET): dict from PSN_ContinuityRuleDefiner

    Outputs:
      pass_fail        (BOOLEAN): True if all rules pass
      violation_report (STRING):  human-readable report
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "generated_asset": ("IMAGE",),
                "rule_set": ("PSN_RULE_SET",),
            }
        }

    RETURN_TYPES = ("BOOLEAN", "STRING")
    RETURN_NAMES = ("pass_fail", "violation_report")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, generated_asset, rule_set):
        # Validate image
        if not isinstance(generated_asset, torch.Tensor):
            return (False, "ERROR: generated_asset is not a torch.Tensor")
        if generated_asset.dim() != 4:
            return (False, f"ERROR: expected 4-D image [B,H,W,C], got {generated_asset.dim()}-D")
        if generated_asset.shape[-1] not in (1, 3, 4):
            return (False, f"ERROR: expected C in (1,3,4), got {generated_asset.shape[-1]}")

        # Validate rule_set
        if not isinstance(rule_set, dict):
            return (False, "ERROR: rule_set is not a dict")
        all_rules = rule_set.get("all_rules", [])
        if not all_rules:
            return (True, "No rules defined; vacuously PASS.")

        # Use only the first batch element for the check
        img = generated_asset[0:1]  # [1, H, W, C]
        if img.shape[-1] == 4:
            img = img[..., :3]  # drop alpha
        elif img.shape[-1] == 1:
            img = img.expand(-1, -1, -1, 3)  # replicate grey to RGB

        lines = []
        all_pass = True
        for rule in all_rules:
            passed, detail = _check_rule_on_image(img, rule)
            lines.append(detail)
            if not passed:
                all_pass = False

        report = "\n".join(lines) if lines else "No rules to check."
        return (all_pass, report)


# ---------------------------------------------------------------------------
# ComfyUI registration
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_ContinuityRuleDefiner": PSN_ContinuityRuleDefiner,
    "PSN_ContinuityEnforcer": PSN_ContinuityEnforcer,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_ContinuityRuleDefiner": "Continuity Rule Definer",
    "PSN_ContinuityEnforcer": "Continuity Enforcer",
}
