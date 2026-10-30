"""Tests for n_4_llm_enhanced_prompt_generation_via_oll.py

Run:  python3 -B test_n_4_llm_enhanced_prompt_generation_via_oll.py
Must print 'ok' and exit 0.
"""

import json
import sys

# Import the module under test
sys.path.insert(0, ".")
from n_4_llm_enhanced_prompt_generation_via_oll import (
    PSN_Ollama_Prompt_Enhancer,
    _template_enhance,
    _parse_ollama_response,
    _STYLE_PRESETS,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)

# ---------------------------------------------------------------------------
# 1. Module-level registration
# ---------------------------------------------------------------------------
assert "PSN_Ollama_Prompt_Enhancer" in NODE_CLASS_MAPPINGS, \
    "NODE_CLASS_MAPPINGS must contain PSN_Ollama_Prompt_Enhancer"
assert NODE_CLASS_MAPPINGS["PSN_Ollama_Prompt_Enhancer"] is PSN_Ollama_Prompt_Enhancer
assert "PSN_Ollama_Prompt_Enhancer" in NODE_DISPLAY_NAME_MAPPINGS
assert NODE_DISPLAY_NAME_MAPPINGS["PSN_Ollama_Prompt_Enhancer"] == "Ollama Prompt Enhancer"

# ---------------------------------------------------------------------------
# 2. INPUT_TYPES structure
# ---------------------------------------------------------------------------
node = PSN_Ollama_Prompt_Enhancer()
input_types = PSN_Ollama_Prompt_Enhancer.INPUT_TYPES()
assert "required" in input_types, "INPUT_TYPES must have 'required'"
assert "short_prompt" in input_types["required"]
assert "style" in input_types["required"]
assert "max_tokens" in input_types["required"]
assert "optional" in input_types
assert "ollama_url" in input_types["optional"]
assert "model_name" in input_types["optional"]

# RETURN_TYPES / RETURN_NAMES / FUNCTION / CATEGORY
assert node.RETURN_TYPES == ("STRING", "STRING")
assert node.RETURN_NAMES == ("enhanced_prompt", "negative_prompt")
assert node.FUNCTION == "run"
assert node.CATEGORY == "ParametricStudio/LLM"

# ---------------------------------------------------------------------------
# 3. Template-based enhancement (offline fallback)
# ---------------------------------------------------------------------------
enhanced, negative = _template_enhance("a cat", "realistic", 128)
assert isinstance(enhanced, str) and len(enhanced) > 0
assert "a cat" in enhanced
assert "photorealistic" in enhanced
assert "8k uhd" in enhanced
assert isinstance(negative, str) and len(negative) > 0
assert "cartoon" in negative

# Anime style
enhanced_anime, neg_anime = _template_enhance("a warrior", "anime", 128)
assert "anime style" in enhanced_anime
assert "photorealistic" in neg_anime

# Cinematic style
enhanced_cine, neg_cine = _template_enhance("a city", "cinematic", 128)
assert "cinematic" in enhanced_cine
assert "dramatic lighting" in enhanced_cine

# None style
enhanced_none, neg_none = _template_enhance("a tree", "none", 128)
assert "highly detailed" in enhanced_none

# ---------------------------------------------------------------------------
# 4. Edge case: empty short_prompt
# ---------------------------------------------------------------------------
enhanced_empty, neg_empty = _template_enhance("", "realistic", 128)
assert isinstance(enhanced_empty, str) and len(enhanced_empty) > 0
assert "a beautiful scene" in enhanced_empty

# ---------------------------------------------------------------------------
# 5. Edge case: unknown style falls back to "none"
# ---------------------------------------------------------------------------
enhanced_unknown, neg_unknown = _template_enhance("a dog", "watercolor", 128)
assert "highly detailed" in enhanced_unknown  # 'none' preset

# ---------------------------------------------------------------------------
# 6. Edge case: max_tokens truncation
# ---------------------------------------------------------------------------
enhanced_long, _ = _template_enhance("a very long prompt about a cat", "realistic", 16)
# 16 tokens * 4 chars = 64 chars max
assert len(enhanced_long) <= 64, f"Expected <= 64 chars, got {len(enhanced_long)}"

# ---------------------------------------------------------------------------
# 7. Ollama response parsing: JSON message format
# ---------------------------------------------------------------------------
raw_json = json.dumps({"message": {"content": "a detailed cat, photorealistic"}})
parsed = _parse_ollama_response(raw_json)
assert parsed == "a detailed cat, photorealistic"

# ---------------------------------------------------------------------------
# 8. Ollama response parsing: JSON response format
# ---------------------------------------------------------------------------
raw_json2 = json.dumps({"response": "a cinematic scene"})
parsed2 = _parse_ollama_response(raw_json2)
assert parsed2 == "a cinematic scene"

# ---------------------------------------------------------------------------
# 9. Ollama response parsing: plain text fallback
# ---------------------------------------------------------------------------
parsed3 = _parse_ollama_response("just a plain text prompt")
assert parsed3 == "just a plain text prompt"

# ---------------------------------------------------------------------------
# 10. Ollama response parsing: empty / whitespace
# ---------------------------------------------------------------------------
assert _parse_ollama_response("") == ""
assert _parse_ollama_response("   ") == ""

# ---------------------------------------------------------------------------
# 11. Node run: template fallback (default _ollama_request raises)
# ---------------------------------------------------------------------------
node2 = PSN_Ollama_Prompt_Enhancer()
enhanced_out, negative_out = node2.run(
    short_prompt="a sunset",
    style="cinematic",
    max_tokens=128,
)
assert isinstance(enhanced_out, str) and len(enhanced_out) > 0
assert "a sunset" in enhanced_out
assert "cinematic" in enhanced_out
assert isinstance(negative_out, str) and len(negative_out) > 0

# ---------------------------------------------------------------------------
# 12. Node run: mock Ollama request (inject a fake)
# ---------------------------------------------------------------------------
def _mock_ollama_request(url, model, prompt, max_tokens):
    return json.dumps({"message": {"content": "a mock enhanced prompt, very detailed"}})

node3 = PSN_Ollama_Prompt_Enhancer()
node3._ollama_request = staticmethod(_mock_ollama_request)
enhanced_mock, negative_mock = node3.run(
    short_prompt="a bird",
    style="anime",
    max_tokens=128,
)
assert "mock enhanced prompt" in enhanced_mock
assert isinstance(negative_mock, str) and len(negative_mock) > 0

# ---------------------------------------------------------------------------
# 13. Node run: mock Ollama with negative prompt in response
# ---------------------------------------------------------------------------
def _mock_ollama_with_neg(url, model, prompt, max_tokens):
    return json.dumps({"message": {"content": "a detailed scene, beautiful. Negative: blurry, ugly"}})

node4 = PSN_Ollama_Prompt_Enhancer()
node4._ollama_request = staticmethod(_mock_ollama_with_neg)
enhanced_neg, negative_neg = node4.run(
    short_prompt="a forest",
    style="realistic",
    max_tokens=128,
)
assert "a detailed scene" in enhanced_neg
assert "blurry" in negative_neg

# ---------------------------------------------------------------------------
# 14. Bad input: non-string short_prompt
# ---------------------------------------------------------------------------
node5 = PSN_Ollama_Prompt_Enhancer()
try:
    node5.run(short_prompt=12345, style="realistic", max_tokens=128)
    assert False, "Expected TypeError for non-string short_prompt"
except TypeError:
    pass

# ---------------------------------------------------------------------------
# 15. Bad input: non-string style
# ---------------------------------------------------------------------------
node6 = PSN_Ollama_Prompt_Enhancer()
try:
    node6.run(short_prompt="a cat", style=42, max_tokens=128)
    assert False, "Expected TypeError for non-string style"
except TypeError:
    pass

# ---------------------------------------------------------------------------
# 16. Bad input: invalid max_tokens
# ---------------------------------------------------------------------------
node7 = PSN_Ollama_Prompt_Enhancer()
try:
    node7.run(short_prompt="a cat", style="realistic", max_tokens=0)
    assert False, "Expected ValueError for max_tokens=0"
except ValueError:
    pass

try:
    node7.run(short_prompt="a cat", style="realistic", max_tokens=-5)
    assert False, "Expected ValueError for negative max_tokens"
except ValueError:
    pass

# ---------------------------------------------------------------------------
# 17. All style presets exist and have positive + negative
# ---------------------------------------------------------------------------
for style_name in ["realistic", "anime", "cinematic", "none"]:
    assert style_name in _STYLE_PRESETS, f"Missing style preset: {style_name}"
    assert "positive" in _STYLE_PRESETS[style_name]
    assert "negative" in _STYLE_PRESETS[style_name]
    assert len(_STYLE_PRESETS[style_name]["positive"]) > 0
    assert len(_STYLE_PRESETS[style_name]["negative"]) > 0

# ---------------------------------------------------------------------------
# 18. Node run: whitespace-only short_prompt
# ---------------------------------------------------------------------------
node8 = PSN_Ollama_Prompt_Enhancer()
enhanced_ws, neg_ws = node8.run(short_prompt="   ", style="none", max_tokens=64)
assert isinstance(enhanced_ws, str) and len(enhanced_ws) > 0
assert "a beautiful scene" in enhanced_ws

# ---------------------------------------------------------------------------
print("ok")
