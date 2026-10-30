"""Tests for n_3_automated_prompt_chunking_for_long_des."""

import json
import torch

from n_3_automated_prompt_chunking_for_long_des import (
    PSN_Prompt_Chunker,
    PSN_Chunked_Conditioning_Builder,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _count_tokens,
    _split_by_strategy,
    _group_segments,
    _apply_overlap,
)


# ---------------------------------------------------------------------------
# Helper: fake CLIP for testing
# ---------------------------------------------------------------------------

class FakeCLIP:
    """Mimics ComfyUI CLIP.encode_from_string returning (cond, pooled)."""

    def __init__(self, dim=64):
        self.dim = dim

    def encode_from_string(self, text):
        # Deterministic: hash-based seed so same text -> same tensor
        seed = sum(ord(c) for c in text) % (2**31)
        g = torch.Generator().manual_seed(seed)
        n_tokens = max(1, len(text.split()))
        cond = torch.randn(1, n_tokens, self.dim, generator=g)
        pooled = torch.randn(1, self.dim, generator=g)
        return cond, pooled


# ---------------------------------------------------------------------------
# 1. Module-level mappings exist and are correct
# ---------------------------------------------------------------------------

def test_mappings():
    assert "PSN_Prompt_Chunker" in NODE_CLASS_MAPPINGS
    assert "PSN_Chunked_Conditioning_Builder" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_Prompt_Chunker"] is PSN_Prompt_Chunker
    assert NODE_CLASS_MAPPINGS["PSN_Chunked_Conditioning_Builder"] is PSN_Chunked_Conditioning_Builder
    assert "PSN_Prompt_Chunker" in NODE_DISPLAY_NAME_MAPPINGS
    assert "PSN_Chunked_Conditioning_Builder" in NODE_DISPLAY_NAME_MAPPINGS


# ---------------------------------------------------------------------------
# 2. Token counting basics
# ---------------------------------------------------------------------------

def test_count_tokens():
    assert _count_tokens("") == 0
    assert _count_tokens("hello") == 1
    assert _count_tokens("hello world") == 2
    assert _count_tokens("hello, world") == 3  # 2 words + 1 punct


# ---------------------------------------------------------------------------
# 3. PSN_Prompt_Chunker: sentence strategy respects max_tokens
# ---------------------------------------------------------------------------

def test_chunker_sentence():
    node = PSN_Prompt_Chunker()
    prompt = "The cat sat on the mat. The dog ran in the park. The bird flew over the tree."
    chunks_str, count = node.run(prompt, max_tokens=10, split_strategy="sentence", overlap_tokens=0)
    chunks = json.loads(chunks_str)
    assert count == len(chunks)
    assert count >= 2  # should split into multiple chunks
    # Each chunk should be a valid sentence (or part thereof)
    for c in chunks:
        assert isinstance(c, str)
        assert len(c) > 0


# ---------------------------------------------------------------------------
# 4. PSN_Prompt_Chunker: comma strategy
# ---------------------------------------------------------------------------

def test_chunker_comma():
    node = PSN_Prompt_Chunker()
    prompt = "red, blue, green, yellow, purple, orange"
    chunks_str, count = node.run(prompt, max_tokens=3, split_strategy="comma", overlap_tokens=0)
    chunks = json.loads(chunks_str)
    assert count == len(chunks)
    assert count >= 2
    # Verify all original words are present across chunks
    all_words = set()
    for c in chunks:
        all_words.update(c.replace(",", " ").split())
    assert {"red", "blue", "green", "yellow", "purple", "orange"} <= all_words


# ---------------------------------------------------------------------------
# 5. PSN_Prompt_Chunker: fixed strategy with overlap
# ---------------------------------------------------------------------------

def test_chunker_fixed_overlap():
    node = PSN_Prompt_Chunker()
    prompt = "one two three four five six seven eight nine ten"
    chunks_str, count = node.run(prompt, max_tokens=4, split_strategy="fixed", overlap_tokens=2)
    chunks = json.loads(chunks_str)
    assert count >= 2
    # With overlap, later chunks should contain tail words of previous chunk
    if count >= 2:
        prev_words = chunks[0].split()
        next_words = chunks[1].split()
        # The last 2 words of chunk 0 should appear at the start of chunk 1
        tail = prev_words[-2:]
        assert all(w in next_words for w in tail), f"Overlap missing: {tail} not in {next_words}"


# ---------------------------------------------------------------------------
# 6. PSN_Prompt_Chunker: bad input (non-string prompt)
# ---------------------------------------------------------------------------

def test_chunker_bad_input():
    node = PSN_Prompt_Chunker()
    try:
        node.run(12345, max_tokens=10, split_strategy="sentence", overlap_tokens=0)
        assert False, "Expected TypeError"
    except TypeError:
        pass


# ---------------------------------------------------------------------------
# 7. PSN_Prompt_Chunker: empty prompt
# ---------------------------------------------------------------------------

def test_chunker_empty():
    node = PSN_Prompt_Chunker()
    chunks_str, count = node.run("", max_tokens=10, split_strategy="sentence", overlap_tokens=0)
    chunks = json.loads(chunks_str)
    assert count == 0
    assert chunks == []


# ---------------------------------------------------------------------------
# 8. PSN_Chunked_Conditioning_Builder: basic encoding
# ---------------------------------------------------------------------------

def test_conditioning_builder_basic():
    clip = FakeCLIP(dim=32)
    node = PSN_Chunked_Conditioning_Builder()
    chunks = json.dumps(["a red car", "a blue sky"])
    (conditioning,) = node.run(clip, chunks, weights=1.0)
    assert isinstance(conditioning, list)
    assert len(conditioning) == 1
    cond, extra = conditioning[0]
    assert isinstance(cond, torch.Tensor)
    assert cond.dim() == 3  # [1, N, D]
    assert cond.shape[0] == 1
    assert cond.shape[2] == 32
    assert "pooled" in extra
    assert extra["pooled"].shape == (1, 32)


# ---------------------------------------------------------------------------
# 9. PSN_Chunked_Conditioning_Builder: weights scaling
# ---------------------------------------------------------------------------

def test_conditioning_builder_weights():
    clip = FakeCLIP(dim=16)
    node = PSN_Chunked_Conditioning_Builder()
    chunks = json.dumps(["hello world"])
    (cond_w1,) = node.run(clip, chunks, weights=1.0)
    (cond_w2,) = node.run(clip, chunks, weights=2.0)
    # cond_w2 should be exactly 2x cond_w1
    assert torch.allclose(cond_w2[0][0], cond_w1[0][0] * 2.0, atol=1e-5)


# ---------------------------------------------------------------------------
# 10. PSN_Chunked_Conditioning_Builder: bad JSON input
# ---------------------------------------------------------------------------

def test_conditioning_builder_bad_json():
    clip = FakeCLIP(dim=16)
    node = PSN_Chunked_Conditioning_Builder()
    try:
        node.run(clip, "not valid json", weights=1.0)
        assert False, "Expected ValueError"
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# 11. PSN_Chunked_Conditioning_Builder: empty chunk list
# ---------------------------------------------------------------------------

def test_conditioning_builder_empty():
    clip = FakeCLIP(dim=16)
    node = PSN_Chunked_Conditioning_Builder()
    try:
        node.run(clip, "[]", weights=1.0)
        assert False, "Expected ValueError"
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# 12. End-to-end: chunker -> builder
# ---------------------------------------------------------------------------

def test_end_to_end():
    chunker = PSN_Prompt_Chunker()
    builder = PSN_Chunked_Conditioning_Builder()
    clip = FakeCLIP(dim=32)

    prompt = "A beautiful sunset over the ocean. The sky is painted in orange and pink. Waves crash gently on the shore."
    chunks_str, count = chunker.run(prompt, max_tokens=12, split_strategy="sentence", overlap_tokens=0)
    assert count >= 2

    (conditioning,) = builder.run(clip, chunks_str, weights=1.0)
    cond, extra = conditioning[0]
    assert cond.shape[0] == 1
    assert cond.shape[2] == 32
    assert extra["pooled"].shape == (1, 32)


# ---------------------------------------------------------------------------
# Run all tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_mappings()
    test_count_tokens()
    test_chunker_sentence()
    test_chunker_comma()
    test_chunker_fixed_overlap()
    test_chunker_bad_input()
    test_chunker_empty()
    test_conditioning_builder_basic()
    test_conditioning_builder_weights()
    test_conditioning_builder_bad_json()
    test_conditioning_builder_empty()
    test_end_to_end()
    print("ok")
