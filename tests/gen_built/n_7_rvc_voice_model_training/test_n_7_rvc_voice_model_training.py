import torch

from n_7_rvc_voice_model_training import (
    PSN_RVC_Preprocess,
    PSN_RVC_Train_Model,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


# 1. module-level mappings exist and are consistent
assert set(NODE_CLASS_MAPPINGS) == {"PSN_RVC_Preprocess", "PSN_RVC_Train_Model"}
assert set(NODE_DISPLAY_NAME_MAPPINGS) == set(NODE_CLASS_MAPPINGS)

# 2. INPUT_TYPES / RETURN_TYPES / FUNCTION / CATEGORY present
for cls in (PSN_RVC_Preprocess, PSN_RVC_Train_Model):
    it = cls.INPUT_TYPES()
    assert "required" in it
    assert cls.FUNCTION == "run"
    assert cls.CATEGORY.startswith("ParametricStudio/")
    assert isinstance(cls.RETURN_TYPES, tuple) and len(cls.RETURN_TYPES) > 0

# 3. preprocess: correct number of segments for a known length
sr = 40000
seg_s = 5.0
seg_len = int(sr * seg_s)  # 200000
audio = torch.randn(1, seg_len * 2 + 12345)  # 2 full + 1 tail
out = PSN_RVC_Preprocess().run(audio, sr, seg_s, keep_tail=True)
segments, num_segments, got_seg_len = out
assert got_seg_len == seg_len
assert num_segments == 3
assert segments.shape[0] == 3
assert segments.shape[1] == seg_len  # padded

# 4. preprocess: keep_tail=False drops the short tail
out2 = PSN_RVC_Preprocess().run(audio, sr, seg_s, keep_tail=False)
assert out2[1] == 2

# 5. preprocess: peak normalisation -> max abs == 0.95 (non-silent)
assert abs(segments[0].abs().max().item() - 0.95) < 1e-4

# 6. preprocess: silent input stays silent (no NaN/Inf)
silent = torch.zeros(1, seg_len)
out_s = PSN_RVC_Preprocess().run(silent, sr, seg_s, keep_tail=True)
assert torch.isfinite(out_s[0]).all()
assert out_s[0].abs().max().item() == 0.0

# 7. preprocess: bad input (3-D tensor) raises ValueError
try:
    PSN_RVC_Preprocess().run(torch.randn(2, 3, 4), sr, seg_s, True)
    raise AssertionError("expected ValueError for 3-D audio")
except ValueError:
    pass

# 8. preprocess: non-tensor input raises ValueError
try:
    PSN_RVC_Preprocess().run("not a tensor", sr, seg_s, True)
    raise AssertionError("expected ValueError for non-tensor audio")
except ValueError:
    pass

# 9. train: runs, returns finite loss, model dict has 'samples'
seg = torch.randn(4, 4096)
model_out, final_loss, index = PSN_RVC_Train_Model().run(seg, epochs=2, batch_size=2, lr=1e-3, seed=7)
assert isinstance(model_out, dict) and "samples" in model_out
assert torch.isfinite(torch.tensor(final_loss))
assert index.shape == (1,)

# 10. train: deterministic with same seed
_, l1, _ = PSN_RVC_Train_Model().run(seg, epochs=2, batch_size=2, lr=1e-3, seed=42)
_, l2, _ = PSN_RVC_Train_Model().run(seg, epochs=2, batch_size=2, lr=1e-3, seed=42)
assert abs(l1 - l2) < 1e-6

# 11. train: bad epochs raises ValueError
try:
    PSN_RVC_Train_Model().run(seg, epochs=0, batch_size=2, lr=1e-3, seed=1)
    raise AssertionError("expected ValueError for epochs=0")
except ValueError:
    pass

# 12. train: bad batch_size raises ValueError
try:
    PSN_RVC_Train_Model().run(seg, epochs=1, batch_size=0, lr=1e-3, seed=1)
    raise AssertionError("expected ValueError for batch_size=0")
except ValueError:
    pass

print("ok")
