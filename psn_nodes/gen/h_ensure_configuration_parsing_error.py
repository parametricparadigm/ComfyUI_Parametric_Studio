"""ComfyUI custom node: ensure configuration parsing errors name the source file.

The node parses a simple key/value configuration text (a lightweight
front-matter style format) and guarantees that every parsing failure is
reported through a dedicated exception whose message explicitly names the
source file. This makes debugging much easier when many similar config
files are managed across instances.
"""

import re

CAT = "ParametricStudio/Config"


class ConfigParseError(RuntimeError):
    """Raised when a configuration text cannot be parsed.

    The message always names the source file (``source``) so that the
    failure can be attributed to the right file even when many similar
    files are processed.
    """

    def __init__(self, message, source):
        self.source = source
        super().__init__("%s (source file: %s)" % (message, source))


def _parse_config(text, source="<unnamed>"):
    """Parse a simple ``key: value`` configuration text.

    Rules:
      * blank lines and lines starting with ``#`` are ignored;
      * each other line must be ``key: value`` where key is a
        non-empty identifier (letters, digits, ``_``, ``-``);
      * duplicate keys are an error;
      * a line without a ``:`` separator is an error.

    Returns a dict of key -> value (values are stripped strings).
    Raises :class:`ConfigParseError` naming ``source`` on any failure.
    """
    if not isinstance(text, str):
        raise ConfigParseError("configuration text must be a string", source)

    result = {}
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ConfigParseError(
                "line %d: expected 'key: value' but found no ':' separator" % lineno,
                source,
            )
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if not key or not re.fullmatch(r"[A-Za-z0-9_-]+", key):
            raise ConfigParseError(
                "line %d: invalid key %r" % (lineno, key), source
            )
        if key in result:
            raise ConfigParseError(
                "line %d: duplicate key %r" % (lineno, key), source
            )
        result[key] = value
    return result


def _parse_config_file(text, source):
    """Parse ``text`` as the content of the file named ``source``.

    Thin wrapper that mirrors the original ``parse_file`` idea: the
    source name is threaded into every error raised by the parser.
    """
    return _parse_config(text, source)


class PSN_ConfigParseGuard:
    """Parse a key/value configuration and guarantee errors name the file.

    On success the node returns the number of parsed keys and a
    comma-joined summary of ``key=value`` pairs. On failure it returns
    ``0`` keys and the full exception message, which always contains the
    source file name.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "config_text": ("STRING", {"multiline": True, "default": ""}),
                "source_name": (
                    "STRING",
                    {"default": "config.txt", "placeholder": "path or label of the file"},
                ),
            }
        }

    RETURN_TYPES = ("INT", "STRING")
    RETURN_NAMES = ("key_count", "result_or_error")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, config_text, source_name):
        source = source_name if isinstance(source_name, str) and source_name.strip() else "<unnamed>"
        try:
            parsed = _parse_config_file(config_text, source)
        except ConfigParseError as exc:
            # The message is guaranteed to name the source file.
            return (0, str(exc))
        summary = ", ".join("%s=%s" % (k, v) for k, v in parsed.items())
        return (len(parsed), summary)


NODE_CLASS_MAPPINGS = {
    "PSN_ConfigParseGuard": PSN_ConfigParseGuard,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_ConfigParseGuard": "Config Parse Guard (names source file)",
}
