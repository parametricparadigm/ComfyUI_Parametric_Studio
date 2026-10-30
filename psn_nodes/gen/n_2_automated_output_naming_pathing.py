"""Automated Output Naming & Pathing (pure-logic, secure-by-design).

This module implements two closely related ComfyUI custom nodes:

1. ``PSN_Filename_Generator`` -- builds a deterministic, collision-resistant
   filename from a base name, a timestamp, a seed, and an optional suffix.
   All characters that are unsafe for filenames are sanitized.

2. ``PSN_Path_Validator`` -- joins a directory and a filename, then validates
   the resulting path against a configurable allow-list of root directories.
   It performs NO filesystem I/O; the ``create_dirs`` flag is accepted for
   interface compatibility but the node only reports whether the path is
   structurally valid and within the allowed roots.

No network, no subprocess, no file or OS access, no eval/exec.
"""

import re
import datetime

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Default allowed root: the usual place for ComfyUI's models. A plain string; this node does no file access, so it never expands "~".
DEFAULT_ALLOWED_ROOTS = (
    "~/ComfyUI/models",
)

# Characters that are never allowed in a filename component.
# We keep it simple: strip anything that is not alphanumeric, dash, underscore,
# or dot.  Leading/trailing dots and spaces are also trimmed.
_UNSAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]")

# A set of reserved Windows/Unix names that we also reject.
_RESERVED_NAMES = frozenset({
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
})

# Maximum length for a filename component (excluding extension).
_MAX_FILENAME_LEN = 200


# ---------------------------------------------------------------------------
# Helper functions (pure logic, no I/O)
# ---------------------------------------------------------------------------

def psn_sanitize_filename_component(name: str) -> str:
    """Sanitize a single filename component (no path separators).

    - Replaces unsafe characters with underscores.
    - Collapses consecutive underscores.
    - Strips leading/trailing dots and spaces.
    - Truncates to ``_MAX_FILENAME_LEN`` characters.
    - Returns an empty string if the result is empty or only dots.
    """
    if not name:
        return ""
    # Replace unsafe chars
    cleaned = _UNSAFE_FILENAME_RE.sub("_", name)
    # Collapse consecutive underscores
    cleaned = re.sub(r"_+", "_", cleaned)
    # Strip leading/trailing dots and spaces
    cleaned = cleaned.strip(". ")
    # Truncate
    if len(cleaned) > _MAX_FILENAME_LEN:
        cleaned = cleaned[:_MAX_FILENAME_LEN]
    # Final check: if it's empty or all dots, return empty
    if not cleaned or set(cleaned) == {"."}:
        return ""
    return cleaned


def psn_is_reserved_name(name: str) -> bool:
    """Check if a filename (without extension) is a reserved name."""
    stem = name.split(".")[0].upper()
    return stem in _RESERVED_NAMES


def psn_generate_filename(
    base_name: str,
    timestamp_format: str,
    seed: int,
    suffix: str = "",
    now: datetime.datetime = None,
) -> str:
    """Generate a sanitized, unique filename.

    Format: ``<base>_<timestamp>_<seed>[_<suffix>]``

    All components are sanitized.  If the base name is empty, a default
    ``"output"`` is used.
    """
    if now is None:
        now = datetime.datetime.now()

    # Sanitize base
    base = psn_sanitize_filename_component(base_name) or "output"

    # Format timestamp
    try:
        ts = now.strftime(timestamp_format)
    except (ValueError, TypeError):
        ts = now.strftime("%Y%m%d_%H%M%S")
    ts = psn_sanitize_filename_component(ts) or "ts"

    # Seed as string
    seed_str = str(int(seed))

    # Suffix (optional)
    suffix_clean = psn_sanitize_filename_component(suffix) if suffix else ""

    # Build parts
    parts = [base, ts, seed_str]
    if suffix_clean:
        parts.append(suffix_clean)

    filename = "_".join(parts)

    # Final safety: ensure no reserved name
    if psn_is_reserved_name(filename):
        filename = "x_" + filename

    return filename


def psn_validate_path(
    directory: str,
    filename: str,
    allowed_roots: tuple = DEFAULT_ALLOWED_ROOTS,
) -> tuple:
    """Validate that ``directory/filename`` is within one of ``allowed_roots``.

    Returns ``(full_path, is_valid, reason)``.

    - ``full_path``: the joined path (normalized, no trailing slash).
    - ``is_valid``: True if the path is within an allowed root and the
      filename is non-empty and safe.
    - ``reason``: human-readable explanation if invalid.
    """
    # Sanitize filename
    safe_name = psn_sanitize_filename_component(filename)
    if not safe_name:
        return ("", False, "Filename is empty or contains only unsafe characters.")

    # Normalize directory: strip trailing slashes, ensure it's absolute-ish
    dir_clean = directory.strip()
    if not dir_clean:
        dir_clean = "/"

    # Join
    if dir_clean.endswith("/"):
        full_path = dir_clean + safe_name
    else:
        full_path = dir_clean + "/" + safe_name

    # Normalize: collapse double slashes (but keep leading // for network paths)
    while "//" in full_path:
        full_path = full_path.replace("//", "/")

    # Check against allowed roots
    is_within = False
    for root in allowed_roots:
        root_clean = root.rstrip("/")
        if full_path == root_clean or full_path.startswith(root_clean + "/"):
            is_within = True
            break

    if not is_within:
        return (full_path, False, "Path is not within any allowed root.")

    # Check for path traversal
    if ".." in full_path.split("/"):
        return (full_path, False, "Path contains traversal sequences ('..').")

    return (full_path, True, "OK")


# ---------------------------------------------------------------------------
# ComfyUI Node Classes
# ---------------------------------------------------------------------------

CAT = "ParametricStudio/Naming"


class PSN_Filename_Generator:
    """Generate a unique, sanitized filename from base name, timestamp, seed, and suffix."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "base_name": ("STRING", {"default": "output", "multiline": False}),
                "timestamp_format": ("STRING", {"default": "%Y%m%d_%H%M%S", "multiline": False}),
                "seed": ("INT", {"default": 0, "min": -2**31, "max": 2**31 - 1, "step": 1}),
            },
            "optional": {
                "suffix": ("STRING", {"default": "", "multiline": False}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("filename",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, base_name, timestamp_format, seed, suffix=""):
        filename = psn_generate_filename(
            base_name=base_name,
            timestamp_format=timestamp_format,
            seed=seed,
            suffix=suffix,
        )
        return (filename,)


class PSN_Path_Validator:
    """Validate and construct a full file path within allowed roots.

    No filesystem I/O is performed.  The ``create_dirs`` flag is accepted
    for interface compatibility but has no effect in this pure-logic node.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "directory": ("STRING", {"default": "~/ComfyUI/models", "multiline": False}),
                "filename": ("STRING", {"default": "", "multiline": False}),
            },
            "optional": {
                "create_dirs": ("BOOLEAN", {"default": False}),
                "allowed_roots": ("STRING", {"default": "~/ComfyUI/models", "multiline": True}),
            },
        }

    RETURN_TYPES = ("STRING", "BOOLEAN", "STRING")
    RETURN_NAMES = ("full_path", "is_valid", "reason")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, directory, filename, create_dirs=False, allowed_roots="~/ComfyUI/models"):
        # Parse allowed roots: split by newline or comma
        roots_list = [r.strip() for r in allowed_roots.replace(",", "\n").split("\n") if r.strip()]
        if not roots_list:
            roots_list = list(DEFAULT_ALLOWED_ROOTS)

        full_path, is_valid, reason = psn_validate_path(
            directory=directory,
            filename=filename,
            allowed_roots=tuple(roots_list),
        )
        return (full_path, is_valid, reason)


# ---------------------------------------------------------------------------
# Node mappings
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_Filename_Generator": PSN_Filename_Generator,
    "PSN_Path_Validator": PSN_Path_Validator,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Filename_Generator": "PSN Filename Generator",
    "PSN_Path_Validator": "PSN Path Validator",
}
