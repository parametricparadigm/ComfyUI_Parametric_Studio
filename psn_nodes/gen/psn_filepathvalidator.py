"""PSN_FilePathValidator: pure-logic, secure-by-design file path format validator.

This node validates the *format* and *backend compatibility* of a file path
WITHOUT touching the filesystem, network, or OS. It performs no file I/O,
no socket access, and no subprocess calls. It only inspects the path string
and the backend port value to determine whether the path is well-formed and
compatible with the target backend.

Inputs:
    file_path (STRING): The path string to validate.
    backend_port (INT): The ComfyUI server port number.

Outputs:
    valid (BOOLEAN): True if the path format is valid and backend-compatible.
    error_message (STRING): Human-readable error if invalid, empty string if valid.

Validation rules:
    1. file_path must be a non-empty string.
    2. file_path must not contain null bytes.
    3. file_path must not contain path traversal sequences ('..').
    4. file_path must not contain control characters (ASCII 0-31 except tab).
    5. backend_port must be an integer in range [1, 65535].
    6. If the path looks like a URL (starts with http:// or https://), it is
       rejected because this node validates local filesystem paths only.
    7. The path must not be excessively long (> 4096 chars).
"""

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/Validation"


class PSN_FilePathValidator:
    """Validates file path format and backend port compatibility (pure logic, no I/O)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "file_path": ("STRING", {"default": "", "multiline": False}),
                "backend_port": ("INT", {"default": 8188, "min": 1, "max": 65535}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("BOOLEAN", "STRING")
    RETURN_NAMES = ("valid", "error_message")
    FUNCTION = "run"
    CATEGORY = CAT

    @staticmethod
    def _validate_path(file_path):
        """Validate the path string. Returns (is_valid, error_message)."""
        if not isinstance(file_path, str):
            return False, "file_path must be a string."

        if len(file_path) == 0:
            return False, "file_path must not be empty."

        if len(file_path) > 4096:
            return False, "file_path exceeds maximum length of 4096 characters."

        if "\x00" in file_path:
            return False, "file_path contains null bytes."

        # Reject control characters (ASCII 0-31), except tab (9)
        for ch in file_path:
            code = ord(ch)
            if code < 32 and code != 9:
                return False, "file_path contains invalid control character (U+%04X)." % code

        # Reject path traversal
        if ".." in file_path:
            return False, "file_path contains path traversal sequence '..'."

        # Reject URLs (this node is for local filesystem paths only)
        lower = file_path.lower()
        if lower.startswith("http://") or lower.startswith("https://"):
            return False, "file_path appears to be a URL; only local filesystem paths are supported."

        # Reject paths that start with a protocol scheme other than file://
        # (e.g., ftp://, smb://, etc.)
        if "://" in file_path:
            scheme = file_path.split("://", 1)[0].lower()
            if scheme != "file":
                return False, "file_path uses unsupported protocol scheme '%s://'." % scheme

        return True, ""

    @staticmethod
    def _validate_port(backend_port):
        """Validate the backend port. Returns (is_valid, error_message)."""
        if not isinstance(backend_port, int) or isinstance(backend_port, bool):
            return False, "backend_port must be an integer."

        if backend_port < 1 or backend_port > 65535:
            return False, "backend_port must be between 1 and 65535, got %d." % backend_port

        return True, ""

    def run(self, file_path, backend_port):
        """Validate file path format and backend port. Returns (valid, error_message)."""
        path_ok, path_err = self._validate_path(file_path)
        if not path_ok:
            return (False, path_err)

        port_ok, port_err = self._validate_port(backend_port)
        if not port_ok:
            return (False, port_err)

        return (True, "")


NODE_CLASS_MAPPINGS = {
    "PSN_FilePathValidator": PSN_FilePathValidator,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_FilePathValidator": "PSN File Path Validator",
}
