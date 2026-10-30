"""PSN_Classic_Game_UI: a pure-logic, secure-by-design stand-in for a classic-game UI node.

This module does NOT open any socket, browser, window, or file, and does NOT import
torch/comfy/network/subprocess. It only performs the deterministic, testable parts of the
"embed a classic game UI" workflow:

  * validate the requested game_type against an allow-list,
  * validate the UI width/height against sane bounds,
  * deterministically derive a stable UI handle id from the validated params,
  * compute a deterministic initial score (0 for a fresh game),
  * emit a human-readable status/reason string.

The node therefore acts as a lightweight, safe test case for UI/API plumbing: it takes
plain values (strings, ints) and returns plain values (strings, ints, booleans).
"""

import json

# Allow-list of supported classic games.
_GAMES = ("tetris", "snake", "pacman", "checkers")

# Sane bounds for the embedded UI surface.
_MIN_W = 1
_MAX_W = 4096
_MIN_H = 1
_MAX_H = 4096

# A fresh game always starts at score 0.
_INITIAL_SCORE = 0


def _validate_game(game_type):
    """Return (ok, normalized_game, reason)."""
    if not isinstance(game_type, str):
        return (False, None, "game_type must be a string")
    g = game_type.strip().lower()
    if g not in _GAMES:
        return (False, None, "game_type must be one of: " + ", ".join(_GAMES))
    return (True, g, "ok")


def _validate_dims(width, height):
    """Return (ok, w, h, reason)."""
    if not isinstance(width, int) or isinstance(width, bool):
        return (False, None, None, "width must be an integer")
    if not isinstance(height, int) or isinstance(height, bool):
        return (False, None, None, "height must be an integer")
    if width < _MIN_W or width > _MAX_W:
        return (False, None, None, "width out of range [%d, %d]" % (_MIN_W, _MAX_W))
    if height < _MIN_H or height > _MAX_H:
        return (False, None, None, "height out of range [%d, %d]" % (_MIN_H, _MAX_H))
    return (True, width, height, "ok")


def _make_handle(game, width, height):
    """Deterministically build a stable UI handle id from validated params."""
    payload = json.dumps(
        {"game": game, "width": width, "height": height},
        sort_keys=True,
        separators=(",", ":"),
    )
    # A simple, dependency-free, deterministic digest (FNV-1a 64-bit) so the handle is
    # stable across runs without pulling in hashlib (still stdlib, but we keep it minimal).
    h = 0xCBF29CE484222325
    for ch in payload:
        h ^= ord(ch)
        h = (h * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return "ui_%s_%016x" % (game, h)


class PSN_Classic_Game_UI:
    """Embed a classic game UI (pure-logic stand-in) and report a stable handle + score."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "game_type": (list(_GAMES),),
                "width": ("INT", {"default": 256, "min": _MIN_W, "max": _MAX_W, "step": 1}),
                "height": ("INT", {"default": 256, "min": _MIN_H, "max": _MAX_H, "step": 1}),
            }
        }

    RETURN_TYPES = ("STRING", "INT", "BOOLEAN")
    RETURN_NAMES = ("ui_handle", "score", "ok")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/Games"

    def run(self, game_type, width, height):
        ok_g, game, why_g = _validate_game(game_type)
        if not ok_g:
            return ("", _INITIAL_SCORE, False)
        ok_d, w, h, why_d = _validate_dims(width, height)
        if not ok_d:
            return ("", _INITIAL_SCORE, False)
        handle = _make_handle(game, w, h)
        return (handle, _INITIAL_SCORE, True)


NODE_CLASS_MAPPINGS = {"PSN_Classic_Game_UI": PSN_Classic_Game_UI}
NODE_DISPLAY_NAME_MAPPINGS = {"PSN_Classic_Game_UI": "Classic Game UI (PSN)"}
