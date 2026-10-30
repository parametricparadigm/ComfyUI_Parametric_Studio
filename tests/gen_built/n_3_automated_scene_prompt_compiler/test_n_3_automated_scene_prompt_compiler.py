"""Tests for n_3_automated_scene_prompt_compiler."""

import importlib
import sys

sys.path.insert(0, ".")

mod = importlib.import_module("n_3_automated_scene_prompt_compiler")

node_cls = mod.PSN_ScenePromptCompiler
node = node_cls()

# --- 1. Basic spec test: "A man walking" + layout "center" + camera "static"
#     -> output contains "man", "center frame", "static shot"
out, neg = node.run("A man walking", "center", "static", "")
assert "man" in out, f"expected 'man' in: {out}"
assert "center frame" in out, f"expected 'center frame' in: {out}"
assert "static shot" in out, f"expected 'static shot' in: {out}"

# --- 2. Duplicates are removed (case-insensitive)
out2, _ = node.run("Man, man, MAN", "center, center", "static, static", "")
parts = [p.strip() for p in out2.split(",")]
assert parts.count("man") == 1, f"duplicate 'man' not removed: {parts}"
assert parts.count("center frame") == 1, f"duplicate 'center frame' not removed: {parts}"
assert parts.count("static shot") == 1, f"duplicate 'static shot' not removed: {parts}"

# --- 3. Negative prompt is cleaned and deduped
out3, neg3 = node.run("a cat", "left", "pan", "blurry, blurry, BLURRY, low quality")
assert neg3 == "blurry, low quality", f"unexpected negative: {neg3!r}"

# --- 4. Empty / bad inputs do not crash
out4, neg4 = node.run("", "", "", "")
assert isinstance(out4, str)
assert isinstance(neg4, str)

# --- 5. Non-string inputs are handled gracefully (no crash)
out5, _ = node.run(None, 123, None, 456)
assert isinstance(out5, str)

# --- 6. Bloat guard: max_tags limits output
many_desc = ", ".join(f"subject{i}" for i in range(60))
out6, _ = node.run(many_desc, "", "", "", max_tags=10)
parts6 = [p.strip() for p in out6.split(",") if p.strip()]
assert len(parts6) <= 10, f"bloat guard failed, got {len(parts6)} tags"

# --- 7. Layout JSON dict is parsed
out7, _ = node.run("a dog", '{"position": "foreground", "angle": "low angle"}', "dolly in", "")
assert "foreground" in out7, f"expected 'foreground' in: {out7}"
assert "low angle shot" in out7, f"expected 'low angle shot' in: {out7}"
assert "dolly in shot" in out7, f"expected 'dolly in shot' in: {out7}"

# --- 8. Quality tags are appended
out8, _ = node.run("a bird", "", "", "", quality_tags="cinematic, 4k")
assert "cinematic" in out8, f"expected 'cinematic' in: {out8}"
assert "4k" in out8, f"expected '4k' in: {out8}"

# --- 9. Node registration sanity
assert "PSN_ScenePromptCompiler" in mod.NODE_CLASS_MAPPINGS
assert "PSN_ScenePromptCompiler" in mod.NODE_DISPLAY_NAME_MAPPINGS
assert node_cls.FUNCTION == "run"
assert node_cls.CATEGORY.startswith("ParametricStudio/")
assert node_cls.RETURN_TYPES == ("STRING", "STRING")

# --- 10. INPUT_TYPES has required fields
it = node_cls.INPUT_TYPES()
for key in ("raw_description", "layout_json", "camera_prompt_fragment", "negative_prompt"):
    assert key in it["required"], f"missing required input {key}"

print("ok")
