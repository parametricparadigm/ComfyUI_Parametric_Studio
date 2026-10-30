import json
import torch

from n_6_metadata_archival_pipeline import (
    PSN_Meta_Extractor,
    PSN_Archive_Logger,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def make_image(b=1, h=4, w=4, c=3, lo=0.0, hi=1.0):
    return torch.linspace(lo, hi, b * h * w * c).reshape(b, h, w, c)


# 1. Module-level mappings exist and are consistent.
assert set(NODE_CLASS_MAPPINGS) == {"PSN_Meta_Extractor", "PSN_Archive_Logger"}
assert set(NODE_DISPLAY_NAME_MAPPINGS) == set(NODE_CLASS_MAPPINGS)
assert NODE_CLASS_MAPPINGS["PSN_Meta_Extractor"] is PSN_Meta_Extractor

# 2. INPUT_TYPES / RETURN_TYPES / FUNCTION / CATEGORY contract.
for cls in (PSN_Meta_Extractor, PSN_Archive_Logger):
    it = cls.INPUT_TYPES()
    assert "required" in it
    assert cls.FUNCTION == "run"
    assert cls.CATEGORY.startswith("ParametricStudio/")
    assert isinstance(cls.RETURN_TYPES, tuple) and len(cls.RETURN_TYPES) >= 1

# 3. Meta_Extractor happy path: dict structure + JSON round-trip.
img = make_image()
meta, js = PSN_Meta_Extractor().run(
    run_id="r1", image=img, prompt="a cat", seed=42, model="sd_xl", steps=20
)
assert isinstance(meta, dict)
assert meta["run_id"] == "r1"
assert meta["prompt"] == "a cat"
assert meta["seed"] == 42
assert meta["model"] == "sd_xl"
assert meta["steps"] == 20
assert meta["image"]["batch"] == 1
assert meta["image"]["height"] == 4
assert meta["image"]["width"] == 4
assert meta["image"]["channels"] == 3
assert abs(meta["image"]["mean"] - img.mean().item()) < 1e-6
parsed = json.loads(js)
assert parsed == meta

# 4. Meta_Extractor edge case: empty image tensor (zero elements).
empty = torch.empty(1, 0, 4, 3)
meta_e, js_e = PSN_Meta_Extractor().run(run_id="r2", image=empty)
assert meta_e["image"]["height"] == 0
assert meta_e["image"]["mean"] == 0.0
assert json.loads(js_e) == meta_e

# 5. Meta_Extractor bad input: wrong dimensionality must raise.
try:
    PSN_Meta_Extractor().run(run_id="r3", image=torch.zeros(4, 4, 3))
    raise AssertionError("expected ValueError for 3-D image")
except ValueError:
    pass

# 6. Meta_Extractor bad input: out-of-range values must raise.
try:
    PSN_Meta_Extractor().run(run_id="r4", image=torch.full((1, 2, 2, 3), 1.5))
    raise AssertionError("expected ValueError for out-of-range image")
except ValueError:
    pass

# 7. Meta_Extractor bad input: non-tensor must raise TypeError.
try:
    PSN_Meta_Extractor().run(run_id="r5", image="not a tensor")
    raise AssertionError("expected TypeError for non-tensor image")
except TypeError:
    pass

# 8. Archive_Logger happy path: JSONL line is valid JSON and carries run_id.
status, line = PSN_Archive_Logger().run(
    metadata_dict=meta, run_id="r1", output_path="out.jsonl"
)
assert status.startswith("ok:")
assert "r1" in status
entry = json.loads(line)
assert entry["run_id"] == "r1"
assert entry["output_path"] == "out.jsonl"
assert entry["prompt"] == "a cat"
# The original dict must not be mutated.
assert "output_path" not in meta

# 9. Archive_Logger bad input: non-dict must raise TypeError.
try:
    PSN_Archive_Logger().run(metadata_dict=[1, 2, 3], run_id="r6")
    raise AssertionError("expected TypeError for non-dict metadata")
except TypeError:
    pass

# 10. Archive_Logger bad input: empty dict must raise ValueError.
try:
    PSN_Archive_Logger().run(metadata_dict={}, run_id="r7")
    raise AssertionError("expected ValueError for empty metadata")
except ValueError:
    pass

# 11. Archive_Logger does not mutate the input dict.
before = json.dumps(meta, sort_keys=True)
PSN_Archive_Logger().run(metadata_dict=meta, run_id="r8", output_path="x.jsonl")
assert json.dumps(meta, sort_keys=True) == before

print("ok")
