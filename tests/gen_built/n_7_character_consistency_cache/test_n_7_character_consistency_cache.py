import torch

from n_7_character_consistency_cache import (
    PSN_CharacterFeatureCache,
    PSN_CachedIdentityGenerator,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _CACHE,
)


def _img(b=1, h=8, w=8, c=3, seed=0):
    g = torch.Generator().manual_seed(seed)
    return torch.rand(b, h, w, c, generator=g)


# 1. module-level mappings exist and are correct
assert "PSN_CharacterFeatureCache" in NODE_CLASS_MAPPINGS
assert "PSN_CachedIdentityGenerator" in NODE_CLASS_MAPPINGS
assert NODE_DISPLAY_NAME_MAPPINGS["PSN_CharacterFeatureCache"] == "Character Feature Cache"
assert NODE_DISPLAY_NAME_MAPPINGS["PSN_CachedIdentityGenerator"] == "Cached Identity Generator"

# 2. INPUT_TYPES classmethod works and has required keys
it = PSN_CharacterFeatureCache.INPUT_TYPES()
assert "IMAGE" in it["required"]
assert "CACHE_KEY" in it["required"]
assert "FEATURE_TYPE" in it["required"]
it2 = PSN_CachedIdentityGenerator.INPUT_TYPES()
assert "PROMPT" in it2["required"]
assert "CACHE_ID" in it2["required"]
assert "NEGATIVE_PROMPT" in it2["required"]

# 3. cache node returns CACHE_ID and FEATURES with correct shapes
img = _img()
cache_node = PSN_CharacterFeatureCache()
cache_id, feats = cache_node.run(img, "char_a", "Embedding")
assert cache_id == "char_a"
assert isinstance(feats, torch.Tensor)
assert feats.shape[0] == 1  # batch
assert feats.shape[1] == 64  # projection dim

# 4. generator produces a valid IMAGE [B,H,W,C] in 0..1
gen = PSN_CachedIdentityGenerator()
out = gen.run("a portrait", "char_a", "")
assert len(out) == 1
image = out[0]
assert isinstance(image, torch.Tensor)
assert image.dim() == 4
assert image.shape[0] == 1
assert image.shape[-1] == 3
assert image.min() >= 0.0 and image.max() <= 1.0

# 5. consistency: same CACHE_ID + same prompt => identical output
out2 = gen.run("a portrait", "char_a", "")
assert torch.allclose(out[0], out2[0], atol=1e-6), "same cache id + prompt must give identical image"

# 6. different prompt => different output (still valid)
out3 = gen.run("a landscape", "char_a", "")
assert not torch.allclose(out[0], out3[0], atol=1e-4), "different prompt should change output"

# 7. bad input: unknown CACHE_ID raises KeyError
try:
    gen.run("a portrait", "nonexistent_key", "")
    raise AssertionError("expected KeyError for unknown CACHE_ID")
except KeyError:
    pass

# 8. bad input: non-tensor IMAGE raises TypeError
try:
    cache_node.run("not a tensor", "char_b", "Embedding")
    raise AssertionError("expected TypeError for non-tensor IMAGE")
except TypeError:
    pass

# 9. bad input: wrong-dim IMAGE raises ValueError
try:
    cache_node.run(torch.rand(4, 4), "char_c", "Embedding")
    raise AssertionError("expected ValueError for 2D IMAGE")
except ValueError:
    pass

# 10. cache invalidation: re-caching with a different image updates the entry
img_diff = _img(seed=99)
cache_id2, feats2 = cache_node.run(img_diff, "char_a", "Landmarks")
assert cache_id2 == "char_a"
# features should differ because the source image differs
assert not torch.allclose(feats, feats2, atol=1e-4), "different image should give different features"

# 11. batch > 1 works
img_b = _img(b=3, seed=5)
cid, fb = cache_node.run(img_b, "char_batch", "Embedding")
assert fb.shape[0] == 3
outb = gen.run("portrait", "char_batch", "")
assert outb[0].shape[0] == 3

# 12. inputs are not modified in place
img_orig = _img(seed=7)
img_copy = img_orig.clone()
cache_node.run(img_orig, "char_inplace", "Embedding")
assert torch.equal(img_orig, img_copy), "input image must not be modified in place"

print("ok")
