"""PSN_Hash_Phrase_Generator: deterministic English phrases from workflow parameters.

Pure-logic, secure-by-design node. It converts a plain string (or JSON text) into a
deterministic English phrase using SHA-256 and a static Diceware-style word list.
No network, no file/OS access, no subprocess, no eval/exec, no torch/ComfyUI imports.
"""

import hashlib
import json

CAT = "ParametricStudio/Debug"

# Static, versioned word list. Phrases are only valid for this exact list.
_WORD_LIST = [
    "apple", "brave", "cloud", "delta", "ember", "frost", "grape", "harbor",
    "ivory", "jungle", "kettle", "lunar", "maple", "noble", "ocean", "prism",
    "quartz", "river", "solar", "timber", "umbra", "velvet", "willow", "zephyr",
    "anchor", "breeze", "cinder", "dawn", "echo", "fable", "glade", "hazel",
    "iris", "jade", "kayak", "larch", "moss", "nectar", "onyx", "pearl",
    "quill", "reef", "sable", "thorn", "unity", "vapor", "wren", "yonder",
]
_WORD_LIST_VERSION = "1.0"
_WORD_COUNT = len(_WORD_LIST)
# 6 bits per word (2**6 == 64). 32 words would need 5 bits; we use 6 for safety.
_BITS_PER_WORD = 6
_MAX_WORDS = 43  # 256 bits / 6 bits = 42.66 -> 42 full words; cap at 43 for safety


def _validate_word_count(word_count):
    """Validate and clamp word count to a safe range."""
    if not isinstance(word_count, int) or isinstance(word_count, bool):
        raise ValueError("word_count must be an integer")
    if word_count < 1:
        raise ValueError("word_count must be at least 1")
    if word_count > _MAX_WORDS:
        raise ValueError("word_count must be at most %d" % _MAX_WORDS)
    return word_count


def _hash_to_phrase(input_string, word_count):
    """Convert input string to a deterministic phrase using SHA-256 and the word list."""
    if not isinstance(input_string, str):
        raise ValueError("input_string must be a string")
    _validate_word_count(word_count)

    digest = hashlib.sha256(input_string.encode("utf-8")).digest()
    # Convert digest to an integer for bit extraction
    hash_int = int.from_bytes(digest, byteorder="big")

    words = []
    for i in range(word_count):
        # Extract 6 bits starting at position i*6
        shift = i * _BITS_PER_WORD
        # Mask to get 6 bits
        word_index = (hash_int >> shift) & 0x3F
        # Ensure index is within word list bounds (should always be < 64)
        if word_index >= _WORD_COUNT:
            # Wrap around if somehow out of bounds (shouldn't happen with 64 words)
            word_index = word_index % _WORD_COUNT
        words.append(_WORD_LIST[word_index])

    return " ".join(words)


class PSN_Hash_Phrase_Generator:
    """Convert workflow parameters into deterministic English phrases for debugging."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_string": ("STRING", {"default": "", "multiline": True}),
                "word_count": ("INT", {"default": 6, "min": 1, "max": _MAX_WORDS, "step": 1}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("phrase",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, input_string, word_count):
        phrase = _hash_to_phrase(input_string, word_count)
        return (phrase,)


NODE_CLASS_MAPPINGS = {
    "PSN_Hash_Phrase_Generator": PSN_Hash_Phrase_Generator,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Hash_Phrase_Generator": "PSN Hash Phrase Generator",
}
