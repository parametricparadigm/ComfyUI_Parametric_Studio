import json
import numpy as np, pytest, torch
from PIL import Image, ImageFilter
from psn import imagecheck as IC
from psn_nodes import quality as Q

def texture(seed=0, n=256):
    rng = np.random.default_rng(seed); base = rng.integers(0, 255, (n // 8, n // 8, 3), dtype=np.uint8); return Image.fromarray(base).resize((n, n), Image.NEAREST)

def test_blur_lowers_sharpness_and_noise_raises_grain():
    sharp = texture(); soft = sharp.filter(ImageFilter.GaussianBlur(4)); a, b = IC.measure(sharp), IC.measure(soft)
    assert a["sharpness"] > 5 * b["sharpness"]
    clean = Image.fromarray(np.full((128, 128, 3), 128, np.uint8)); noisy = Image.fromarray(np.clip(128 + np.random.default_rng(1).normal(0, 12, (128, 128, 3)), 0, 255).astype(np.uint8))
    assert IC.measure(noisy)["grain"] > IC.measure(clean)["grain"] + 5

def test_clipping_contrast_and_colour_measures():
    dark = np.zeros((64, 64, 3), np.uint8); m = IC.measure(dark); assert m["clipped_dark_pct"] == 100 and m["contrast"] == 0
    white = np.full((64, 64, 3), 255, np.uint8); assert IC.measure(white)["clipped_bright_pct"] == 100
    grey = np.full((64, 64, 3), 100, np.uint8); red = grey.copy(); red[..., 0] = 255; assert IC.measure(red)["colorfulness"] > IC.measure(grey)["colorfulness"]
    f = np.random.default_rng(2).random((64, 64, 3)).astype(np.float32); assert 0 < IC.measure(f)["contrast"] < 100          # float 0..1 arrays are accepted

def test_assess_reasons():
    ok, why = IC.assess(IC.measure(texture())); assert ok and why == []
    ok, why = IC.assess(IC.measure(texture().filter(ImageFilter.GaussianBlur(6)))); assert not ok and "blurry" in why[0]
    ok, why = IC.assess(IC.measure(np.zeros((64, 64, 3), np.uint8))); assert not ok and any("crushed" in w for w in why) and any("flat" in w for w in why)

def test_near_duplicates_find_resized_and_recompressed_copies_but_not_different_images():
    a = texture(0); b = a.resize((128, 128)).resize((256, 256)); c = texture(5); d = a.filter(ImageFilter.GaussianBlur(0.6))
    hs = [IC.dhash(x) for x in (a, b, c, d, texture(9))]; keep, drop = IC.near_duplicates(hs, 8)
    assert 0 in keep and 1 in drop and 3 in drop and 2 in keep and 4 in keep
    assert IC.distance(hs[0], hs[0]) == 0 and IC.distance(hs[0], hs[2]) > 12

def test_nodes_on_a_real_batch():
    imgs = torch.stack([torch.from_numpy(np.asarray(x, np.float32) / 255) for x in (texture(0), texture(0), texture(7))])
    out, rep, ok = Q.PSN_ImageQuality().run(imgs, 40.0, 25.0); assert out is imgs and ok and len(json.loads(rep)) == 3
    uniq, info = Q.PSN_ImageDedupe().run(imgs, 5); assert uniq.shape[0] == 2 and json.loads(info) == {"kept": [0, 2], "dropped": [1]}
    bad = imgs.clone(); bad[1] = 0; _, rep, ok = Q.PSN_ImageQuality().run(bad, 40.0, 25.0); assert not ok and json.loads(rep)[1]["why"]
