import math
import xml.etree.ElementTree as ET

import torch

from n_1_text_to_motion_pipeline_validation import (
    PSN_TextToMotion_Generate,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    STATUS_OK,
    STATUS_BAD_PROMPT,
    STATUS_BAD_DURATION,
    STATUS_BAD_MODEL,
    STATUS_BAD_SEED,
    NUM_JOINTS,
    FPS,
)

node = PSN_TextToMotion_Generate()

# 1. Basic successful run: check output types, shapes, and status
motion_data, bvh_string, status = node.run(
    prompt="a person walking forward",
    duration=2.0,
    seed=42,
    model_type="MDM",
)

assert status == STATUS_OK, "status should be 0 on success, got %r" % status
assert isinstance(motion_data, dict), "motion_data should be a dict"
assert "rotations" in motion_data, "motion_data must contain 'rotations'"
assert "translations" in motion_data, "motion_data must contain 'translations'"

rot = motion_data["rotations"]
trans = motion_data["translations"]

expected_frames = int(round(2.0 * FPS))
assert rot.shape == (expected_frames, NUM_JOINTS, 3), \
    "rotations shape mismatch: %s" % (rot.shape,)
assert trans.shape == (expected_frames, NUM_JOINTS, 3), \
    "translations shape mismatch: %s" % (trans.shape,)
assert isinstance(rot, torch.Tensor), "rotations should be a torch.Tensor"
assert isinstance(trans, torch.Tensor), "translations should be a torch.Tensor"

# 2. BVH string is non-empty and structurally valid
assert isinstance(bvh_string, str), "bvh_string should be a str"
assert len(bvh_string) > 0, "bvh_string should not be empty"
assert bvh_string.startswith("HIERARCHY"), "BVH should start with HIERARCHY"
assert "MOTION" in bvh_string, "BVH should contain MOTION section"
assert "Frames: %d" % expected_frames in bvh_string, \
    "BVH should declare the correct frame count"

# 3. Reproducibility: same seed + params -> identical output
md1, bvh1, st1 = node.run("jump", 1.0, 123, "Kimodo")
md2, bvh2, st2 = node.run("jump", 1.0, 123, "Kimodo")
assert st1 == STATUS_OK and st2 == STATUS_OK
assert torch.equal(md1["rotations"], md2["rotations"]), \
    "same seed should give identical rotations"
assert torch.equal(md1["translations"], md2["translations"]), \
    "same seed should give identical translations"
assert bvh1 == bvh2, "same seed should give identical BVH string"

# 4. Different seed -> different output
md3, _, _ = node.run("jump", 1.0, 999, "Kimodo")
assert not torch.equal(md1["rotations"], md3["rotations"]), \
    "different seeds should give different rotations"

# 5. Bad prompt (empty string) -> STATUS_BAD_PROMPT
_, _, st = node.run("", 2.0, 42, "MDM")
assert st == STATUS_BAD_PROMPT, "empty prompt should give STATUS_BAD_PROMPT, got %r" % st

# 6. Bad prompt (non-string) -> STATUS_BAD_PROMPT
_, _, st = node.run(12345, 2.0, 42, "MDM")
assert st == STATUS_BAD_PROMPT, "non-string prompt should give STATUS_BAD_PROMPT, got %r" % st

# 7. Bad duration (zero) -> STATUS_BAD_DURATION
_, _, st = node.run("walk", 0.0, 42, "MDM")
assert st == STATUS_BAD_DURATION, "zero duration should give STATUS_BAD_DURATION, got %r" % st

# 8. Bad duration (negative) -> STATUS_BAD_DURATION
_, _, st = node.run("walk", -1.0, 42, "MDM")
assert st == STATUS_BAD_DURATION, "negative duration should give STATUS_BAD_DURATION, got %r" % st

# 9. Bad model_type -> STATUS_BAD_MODEL
_, _, st = node.run("walk", 2.0, 42, "NonExistentModel")
assert st == STATUS_BAD_MODEL, "bad model_type should give STATUS_BAD_MODEL, got %r" % st

# 10. Bad seed (negative) -> STATUS_BAD_SEED
_, _, st = node.run("walk", 2.0, -1, "MDM")
assert st == STATUS_BAD_SEED, "negative seed should give STATUS_BAD_SEED, got %r" % st

# 11. Different model_type gives different latent (model offset)
md_mdm, _, _ = node.run("walk", 1.0, 42, "MDM")
md_kimodo, _, _ = node.run("walk", 1.0, 42, "Kimodo")
assert not torch.equal(md_mdm["rotations"], md_kimodo["rotations"]), \
    "different model_type should give different rotations"

# 12. Node registration: NODE_CLASS_MAPPINGS and DISPLAY_NAME_MAPPINGS
assert "PSN_TextToMotion_Generate" in NODE_CLASS_MAPPINGS
assert NODE_CLASS_MAPPINGS["PSN_TextToMotion_Generate"] is PSN_TextToMotion_Generate
assert "PSN_TextToMotion_Generate" in NODE_DISPLAY_NAME_MAPPINGS

# 13. INPUT_TYPES classmethod returns expected structure
it = PSN_TextToMotion_Generate.INPUT_TYPES()
assert "required" in it
assert "prompt" in it["required"]
assert "duration" in it["required"]
assert "seed" in it["required"]
assert "model_type" in it["required"]

# 14. RETURN_TYPES and RETURN_NAMES
assert PSN_TextToMotion_Generate.RETURN_TYPES == ("ANIMOFLOW_NPZ", "ANIMOFLOW_BVH", "INT")
assert PSN_TextToMotion_Generate.RETURN_NAMES == ("motion_data", "rigged_animation", "status")
assert PSN_TextToMotion_Generate.FUNCTION == "run"
assert PSN_TextToMotion_Generate.CATEGORY == "ParametricStudio/Motion"

# 15. Inputs are not modified in place
orig_prompt = "a person running"
orig_duration = 3.0
md, bvh, st = node.run(orig_prompt, orig_duration, 7, "MoMask")
assert st == STATUS_OK
assert orig_prompt == "a person running", "prompt was modified in place"
assert orig_duration == 3.0, "duration was modified in place"

# 16. Edge case: very short duration (0.1s -> 3 frames)
md, bvh, st = node.run("blink", 0.1, 0, "MDM")
assert st == STATUS_OK
expected_frames = max(1, int(round(0.1 * FPS)))
assert md["rotations"].shape[0] == expected_frames, \
    "frame count for 0.1s should be %d, got %d" % (expected_frames, md["rotations"].shape[0])

# 17. Edge case: seed = 0 is valid
_, _, st = node.run("idle", 1.0, 0, "MDM")
assert st == STATUS_OK, "seed=0 should be valid"

# 18. BVH frame data line count matches expected frames
md, bvh, st = node.run("dance", 1.0, 55, "MDM")
assert st == STATUS_OK
lines = bvh.strip().split("\n")
motion_idx = None
for i, line in enumerate(lines):
    if line.strip() == "MOTION":
        motion_idx = i
        break
assert motion_idx is not None, "BVH should have a MOTION section"
frames_line = lines[motion_idx + 1]
assert frames_line.startswith("Frames:"), "line after MOTION should be Frames:"
declared_frames = int(frames_line.split(":")[1].strip())
data_lines = lines[motion_idx + 3:]
data_lines = [l for l in data_lines if l.strip()]
assert len(data_lines) == declared_frames, \
    "BVH data lines (%d) should match declared frames (%d)" % (len(data_lines), declared_frames)

print("ok")
