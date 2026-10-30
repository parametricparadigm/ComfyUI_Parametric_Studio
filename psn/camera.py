"""One camera move per clip. Video models collapse or go erratic when a prompt asks for several moves at once (rule from the owner's Wan 2.2 guide). camera_moves() finds the canonical moves named in a prompt; one_move_problems() enforces at most one. Original code."""
import re
MOVES = {"push_in": r"push(?:ing)?[- ]in|dolly(?:ing)?[- ]in|zoom(?:ing)?[- ]in|move(?:s|ing)? closer", "pull_out": r"pull(?:ing)?[- ]out|pull(?:ing)?[- ]back|dolly(?:ing)?[- ]out|zoom(?:ing)?[- ]out",
         "pan": r"\bpan(?:s|ning)?\b", "tilt": r"\btilt(?:s|ing)?\b", "orbit": r"\borbit(?:s|ing)?\b|arc(?:s|ing)? around|circl(?:e|es|ing) around", "track": r"tracking shot|\btrack(?:s|ing)? (?:the|with|along)\b|follow(?:s|ing)? (?:the|him|her|them)",
         "crane": r"\bcrane\b|boom (?:up|down)", "handheld": r"hand-?held"}
def camera_moves(text): return sorted(k for k, rx in MOVES.items() if re.search(rx, text or "", re.I))
def one_move_problems(text):
    m = camera_moves(text); return [f"asks for {len(m)} camera moves ({', '.join(m)}); use exactly one per clip"] if len(m) > 1 else []
