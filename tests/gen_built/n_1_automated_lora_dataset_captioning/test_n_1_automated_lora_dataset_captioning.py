"""Tests for n_1_automated_lora_dataset_captioning.py."""

import torch

from n_1_automated_lora_dataset_captioning import (
    PSN_VLM_Caption_Generator,
    PSN_Caption_Auditor,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


class MockLLM:
    """Mock VLM handle that returns a fixed caption."""

    def __init__(self, response):
        self._response = response
        self.last_prompt = None
        self.last_stats = None

    def generate(self, prompt, image_stats):
        self.last_prompt = prompt
        self.last_stats = image_stats
        return self._response


class FailingLLM:
    """Mock VLM handle that raises an exception."""

    def generate(self, prompt, image_stats):
        raise RuntimeError("boom")


def make_image(b=1, h=8, w=8, c=3, value=0.5):
    return torch.full((b, h, w, c), value, dtype=torch.float32)


# ---------------------------------------------------------------------------
# 1. Module-level registration
# ---------------------------------------------------------------------------
assert "PSN_VLM_Caption_Generator" in NODE_CLASS_MAPPINGS
assert "PSN_Caption_Auditor" in NODE_CLASS_MAPPINGS
assert NODE_DISPLAY_NAME_MAPPINGS["PSN_VLM_Caption_Generator"] == "VLM Caption Generator"
assert NODE_DISPLAY_NAME_MAPPINGS["PSN_Caption_Auditor"] == "Caption Auditor"

# ---------------------------------------------------------------------------
# 2. INPUT_TYPES structure
# ---------------------------------------------------------------------------
it = PSN_VLM_Caption_Generator.INPUT_TYPES()
assert "image" in it["required"]
assert "caption_style" in it["required"]
assert PSN_VLM_Caption_Generator.RETURN_TYPES == ("STRING", "FLOAT")
assert PSN_VLM_Caption_Generator.FUNCTION == "run"
assert PSN_VLM_Caption_Generator.CATEGORY.startswith("ParametricStudio/")

it2 = PSN_Caption_Auditor.INPUT_TYPES()
assert "caption" in it2["required"]
assert PSN_Caption_Auditor.RETURN_TYPES == ("BOOLEAN", "STRING")

# ---------------------------------------------------------------------------
# 3. Caption generator: template fallback, detailed style
# ---------------------------------------------------------------------------
gen = PSN_VLM_Caption_Generator()
img = make_image(value=0.3)  # dim, neutral
caption, conf = gen.run(img, "detailed")
assert isinstance(caption, str) and len(caption) > 0
assert isinstance(conf, float)
assert 0.0 <= conf <= 1.0
assert "dim" in caption  # brightness word for 0.3

# ---------------------------------------------------------------------------
# 4. Caption generator: booru_tags style normalisation
# ---------------------------------------------------------------------------
caption_b, conf_b = gen.run(make_image(value=0.8), "booru_tags")
assert isinstance(caption_b, str) and len(caption_b) > 0
# booru tags should be lowercase, comma-separated, no spaces
for tag in caption_b.split(","):
    assert " " not in tag.strip(), "booru tag contains space: %r" % tag
    assert tag.strip() == tag.strip().lower(), "booru tag not lowercase: %r" % tag
assert conf_b > 0.0

# ---------------------------------------------------------------------------
# 5. Caption generator: mock LLM handle is used
# ---------------------------------------------------------------------------
mock = MockLLM("a red fox in a snowy forest")
caption_m, conf_m = gen.run(make_image(), "natural_language", llm_handle=mock)
assert caption_m == "a red fox in a snowy forest"
assert mock.last_prompt is not None
assert "natural-language" in mock.last_prompt or "captioner" in mock.last_prompt
assert mock.last_stats is not None
assert mock.last_stats["width"] == 8
assert mock.last_stats["height"] == 8

# ---------------------------------------------------------------------------
# 6. Caption generator: failing LLM falls back to template
# ---------------------------------------------------------------------------
caption_f, conf_f = gen.run(make_image(), "concise", llm_handle=FailingLLM())
assert isinstance(caption_f, str) and len(caption_f) > 0
assert conf_f > 0.0

# ---------------------------------------------------------------------------
# 7. Caption generator: bad input (wrong shape) raises
# ---------------------------------------------------------------------------
try:
    gen.run(torch.zeros(4, 4, 3), "detailed")  # 3D, not 4D
    assert False, "expected ValueError for 3D tensor"
except ValueError:
    pass

# ---------------------------------------------------------------------------
# 8. Caption generator: bad input (non-tensor) raises
# ---------------------------------------------------------------------------
try:
    gen.run("not a tensor", "detailed")
    assert False, "expected TypeError for non-tensor"
except TypeError:
    pass

# ---------------------------------------------------------------------------
# 9. Caption generator: negative_prompt_hint appears in system prompt
# ---------------------------------------------------------------------------
mock2 = MockLLM("some caption")
gen.run(make_image(), "detailed", llm_handle=mock2, negative_prompt_hint="blur, watermark")
assert "blur" in mock2.last_prompt
assert "watermark" in mock2.last_prompt

# ---------------------------------------------------------------------------
# 10. Caption auditor: valid caption
# ---------------------------------------------------------------------------
aud = PSN_Caption_Auditor()
is_valid, suggestion = aud.run("a cat sitting on a mat", allowed_terms="cat, dog", banned_terms="nsfw, gore")
assert is_valid is True
assert suggestion == ""

# ---------------------------------------------------------------------------
# 11. Caption auditor: banned term present -> invalid
# ---------------------------------------------------------------------------
is_valid2, suggestion2 = aud.run("a cat with gore", allowed_terms="", banned_terms="gore, nsfw")
assert is_valid2 is False
assert "gore" in suggestion2

# ---------------------------------------------------------------------------
# 12. Caption auditor: no allowed term present -> invalid
# ---------------------------------------------------------------------------
is_valid3, suggestion3 = aud.run("a bird in the sky", allowed_terms="cat, dog", banned_terms="")
assert is_valid3 is False
assert "cat" in suggestion3 or "dog" in suggestion3

# ---------------------------------------------------------------------------
# 13. Caption auditor: empty caption -> invalid
# ---------------------------------------------------------------------------
is_valid4, suggestion4 = aud.run("", allowed_terms="", banned_terms="")
assert is_valid4 is False
assert "empty" in suggestion4

# ---------------------------------------------------------------------------
# 14. Caption auditor: case-insensitive banned match
# ---------------------------------------------------------------------------
is_valid5, _ = aud.run("A CAT with GORE", allowed_terms="", banned_terms="gore")
assert is_valid5 is False

# ---------------------------------------------------------------------------
# 15. Confidence score: empty caption -> 0.0
# ---------------------------------------------------------------------------
from n_1_automated_lora_dataset_captioning import _confidence_score
assert _confidence_score("", "detailed") == 0.0
assert _confidence_score("   ", "detailed") == 0.0

# ---------------------------------------------------------------------------
# 16. Confidence score: booru style with bad tags -> lower confidence
# ---------------------------------------------------------------------------
conf_good = _confidence_score("1girl, solo, red_hair", "booru_tags")
conf_bad = _confidence_score("Hello World, !@#$", "booru_tags")
assert conf_good > conf_bad

# ---------------------------------------------------------------------------
# 17. Image stats: bright vs dark image
# ---------------------------------------------------------------------------
from n_1_automated_lora_dataset_captioning import _image_stats
stats_bright = _image_stats(make_image(value=0.9))
stats_dark = _image_stats(make_image(value=0.1))
assert stats_bright["mean_brightness"] > stats_dark["mean_brightness"]
assert stats_bright["dominant_hue"] == "neutral"

# ---------------------------------------------------------------------------
# 18. Image stats: red-dominant image
# ---------------------------------------------------------------------------
red_img = torch.zeros(1, 4, 4, 3, dtype=torch.float32)
red_img[..., 0] = 0.9  # red channel high
red_img[..., 1] = 0.1
red_img[..., 2] = 0.1
stats_red = _image_stats(red_img)
assert stats_red["dominant_hue"] == "red"

# ---------------------------------------------------------------------------
# 19. Batch image works
# ---------------------------------------------------------------------------
caption_batch, conf_batch = gen.run(make_image(b=3, value=0.5), "concise")
assert isinstance(caption_batch, str) and len(caption_batch) > 0
assert conf_batch > 0.0

# ---------------------------------------------------------------------------
# 20. Input not modified in place
# ---------------------------------------------------------------------------
img_orig = make_image(value=0.5)
img_copy = img_orig.clone()
gen.run(img_orig, "detailed")
assert torch.equal(img_orig, img_copy), "input image was modified in place"

print("ok")
