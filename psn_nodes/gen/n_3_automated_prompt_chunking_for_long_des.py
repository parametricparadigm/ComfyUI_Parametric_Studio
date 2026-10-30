"""Automated Prompt Chunking for Long Descriptions.

Splits long prompts into CLIP-friendly chunks and (optionally) encodes them
into a single CONDITIONING object.
"""

import re
import torch

CAT = "ParametricStudio/PromptChunking"


# ---------------------------------------------------------------------------
# Token counting helpers (approximate, no external tokenizer needed)
# ---------------------------------------------------------------------------

def _count_tokens(text: str) -> int:
    """Approximate token count for a string.

    Uses a simple heuristic: each word (whitespace-separated) counts as one
    token, plus one extra token per punctuation cluster.  This is a rough
    proxy for BPE tokenizers but is good enough for chunking decisions.
    """
    if not text:
        return 0
    words = text.split()
    # Count punctuation clusters as extra tokens
    punct = re.findall(r"[\.,;:!\?\-]+", text)
    return len(words) + len(punct)


def _split_by_strategy(text: str, strategy: str) -> list:
    """Split *text* into candidate segments according to *strategy*.

    Returns a list of non-empty strings.
    """
    text = text.strip()
    if not text:
        return []

    if strategy == "sentence":
        # Split on sentence-ending punctuation followed by whitespace or end.
        parts = re.split(r"(?<=[.!?])\s+", text)
    elif strategy == "comma":
        parts = re.split(r",\s*", text)
    elif strategy == "fixed":
        # Split on whitespace into words; the caller will re-group them.
        parts = text.split()
    else:
        raise ValueError(f"Unknown split_strategy: {strategy!r}")

    return [p.strip() for p in parts if p.strip()]


def _group_segments(segments: list, max_tokens: int, strategy: str) -> list:
    """Group *segments* into chunks that each fit within *max_tokens*.

    For 'fixed' strategy, *segments* are individual words and we join them
    with spaces.  For 'sentence'/'comma' we join with the appropriate
    separator.
    """
    if not segments:
        return []

    sep = " " if strategy == "fixed" else (" " if strategy == "sentence" else ", ")
    chunks = []
    current = []
    current_tokens = 0

    for seg in segments:
        seg_tokens = _count_tokens(seg)
        # If a single segment exceeds max_tokens, emit it alone (can't split further
        # without breaking words).
        if seg_tokens > max_tokens:
            if current:
                chunks.append(sep.join(current))
                current = []
                current_tokens = 0
            chunks.append(seg)
            continue

        # Account for the separator token when joining
        extra = 1 if current else 0
        if current_tokens + seg_tokens + extra > max_tokens and current:
            chunks.append(sep.join(current))
            current = [seg]
            current_tokens = seg_tokens
        else:
            current.append(seg)
            current_tokens += seg_tokens + extra

    if current:
        chunks.append(sep.join(current))

    return chunks


def _apply_overlap(chunks: list, overlap_tokens: int) -> list:
    """Prepend the last *overlap_tokens* tokens of the previous chunk to the
    next chunk for context continuity.
    """
    if overlap_tokens <= 0 or len(chunks) < 2:
        return list(chunks)

    result = [chunks[0]]
    for i in range(1, len(chunks)):
        prev_words = chunks[i - 1].split()
        tail = prev_words[-overlap_tokens:] if len(prev_words) >= overlap_tokens else prev_words
        overlap_text = " ".join(tail)
        result.append(overlap_text + " " + chunks[i])
    return result


# ---------------------------------------------------------------------------
# Node 1: PSN_Prompt_Chunker
# ---------------------------------------------------------------------------

class PSN_Prompt_Chunker:
    """Split a long prompt into CLIP-friendly chunks.

    Outputs a single STRING that is a JSON-encoded list of chunk strings,
    plus an INT chunk count.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"default": "", "multiline": True}),
                "max_tokens": ("INT", {"default": 75, "min": 1, "max": 512}),
                "split_strategy": (["sentence", "comma", "fixed"],),
                "overlap_tokens": ("INT", {"default": 0, "min": 0, "max": 64}),
            }
        }

    RETURN_TYPES = ("STRING", "INT")
    RETURN_NAMES = ("chunks", "chunk_count")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, prompt: str, max_tokens: int, split_strategy: str, overlap_tokens: int):
        if not isinstance(prompt, str):
            raise TypeError("prompt must be a string")
        if max_tokens < 1:
            raise ValueError("max_tokens must be >= 1")
        if overlap_tokens < 0:
            raise ValueError("overlap_tokens must be >= 0")

        segments = _split_by_strategy(prompt, split_strategy)
        chunks = _group_segments(segments, max_tokens, split_strategy)
        chunks = _apply_overlap(chunks, overlap_tokens)

        import json
        chunks_str = json.dumps(chunks)
        return (chunks_str, len(chunks))


# ---------------------------------------------------------------------------
# Node 2: PSN_Chunked_Conditioning_Builder
# ---------------------------------------------------------------------------

class PSN_Chunked_Conditioning_Builder:
    """Encode each prompt chunk with CLIP and combine into one CONDITIONING.

    In a real ComfyUI environment *clip* is a CLIP object with a
    ``encode_from_string`` method.  For testing we accept any object that
    exposes ``encode_from_string(text) -> (cond, pooled)`` where *cond* is a
    tensor of shape [1, N, D] and *pooled* is [1, D].
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "clip": ("CLIP",),
                "chunks": ("STRING", {"default": "[]", "multiline": True}),
            },
            "optional": {
                "weights": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 10.0}),
            },
        }

    RETURN_TYPES = ("CONDITIONING",)
    RETURN_NAMES = ("conditioning",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, clip, chunks: str, weights: float = 1.0):
        import json

        if not isinstance(chunks, str):
            raise TypeError("chunks must be a JSON string")
        try:
            chunk_list = json.loads(chunks)
        except json.JSONDecodeError as e:
            raise ValueError(f"chunks is not valid JSON: {e}")

        if not isinstance(chunk_list, list):
            raise ValueError("chunks must be a JSON list of strings")
        if len(chunk_list) == 0:
            raise ValueError("chunks list must not be empty")

        conds = []
        pooleds = []
        for i, text in enumerate(chunk_list):
            if not isinstance(text, str):
                raise TypeError(f"chunk {i} is not a string")
            cond, pooled = clip.encode_from_string(text)
            # cond: [1, N, D], pooled: [1, D]
            if weights != 1.0:
                cond = cond * weights
                pooled = pooled * weights
            conds.append(cond)
            pooleds.append(pooled)

        # Combine: concatenate along the sequence dimension for cond,
        # average pooled vectors.
        combined_cond = torch.cat(conds, dim=1)  # [1, sum(N_i), D]
        combined_pooled = torch.stack(pooleds, dim=0).mean(dim=0)  # [1, D]

        # ComfyUI CONDITIONING is a list of [cond_tensor, dict]
        conditioning = [[combined_cond, {"pooled": combined_pooled}]]
        return (conditioning,)


# ---------------------------------------------------------------------------
# Module-level mappings
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_Prompt_Chunker": PSN_Prompt_Chunker,
    "PSN_Chunked_Conditioning_Builder": PSN_Chunked_Conditioning_Builder,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Prompt_Chunker": "PSN Prompt Chunker",
    "PSN_Chunked_Conditioning_Builder": "PSN Chunked Conditioning Builder",
}
