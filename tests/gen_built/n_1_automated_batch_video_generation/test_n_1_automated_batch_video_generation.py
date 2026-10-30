import torch

from n_1_automated_batch_video_generation import (
    PSN_MergeImageBatches,
    PSN_AssembleVideoFromBatch,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def make_batch(n, h=4, w=4, c=3, seed=0):
    g = torch.Generator().manual_seed(seed)
    return torch.rand(n, h, w, c, generator=g)


def test_module_mappings():
    assert "PSN_MergeImageBatches" in NODE_CLASS_MAPPINGS
    assert "PSN_AssembleVideoFromBatch" in NODE_CLASS_MAPPINGS
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_MergeImageBatches"] == "Merge Image Batches"
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_AssembleVideoFromBatch"] == "Assemble Video From Batch"


def test_merge_concat():
    node = PSN_MergeImageBatches()
    a = make_batch(2)
    b = make_batch(2, seed=1)
    (merged,) = node.run(a, b, "concat")
    assert merged.shape == (4, 4, 4, 3)
    # first two frames equal a, last two equal b
    assert torch.equal(merged[:2], a)
    assert torch.equal(merged[2:], b)
    # inputs not modified
    assert a.shape == (2, 4, 4, 3)


def test_merge_interleave():
    node = PSN_MergeImageBatches()
    a = make_batch(3)
    b = make_batch(3, seed=1)
    (merged,) = node.run(a, b, "interleave")
    assert merged.shape == (6, 4, 4, 3)
    assert torch.equal(merged[0], a[0])
    assert torch.equal(merged[1], b[0])
    assert torch.equal(merged[2], a[1])
    assert torch.equal(merged[3], b[1])
    assert torch.equal(merged[4], a[2])
    assert torch.equal(merged[5], b[2])


def test_merge_interleave_uneven():
    node = PSN_MergeImageBatches()
    a = make_batch(3)
    b = make_batch(1, seed=1)
    (merged,) = node.run(a, b, "interleave")
    assert merged.shape == (4, 4, 4, 3)
    assert torch.equal(merged[0], a[0])
    assert torch.equal(merged[1], b[0])
    assert torch.equal(merged[2], a[1])
    assert torch.equal(merged[3], a[2])


def test_merge_bad_mode():
    node = PSN_MergeImageBatches()
    a = make_batch(1)
    b = make_batch(1, seed=1)
    try:
        node.run(a, b, "bogus")
        raise AssertionError("expected ValueError for bad mode")
    except ValueError:
        pass


def test_merge_shape_mismatch():
    node = PSN_MergeImageBatches()
    a = make_batch(2, h=4)
    b = make_batch(2, h=8, seed=1)
    try:
        node.run(a, b, "concat")
        raise AssertionError("expected ValueError for shape mismatch")
    except ValueError:
        pass


def test_assemble_video():
    node = PSN_AssembleVideoFromBatch()
    frames = make_batch(4)
    (video,) = node.run(frames, 24.0, "mp4")
    assert video["num_frames"] == 4
    assert video["fps"] == 24.0
    assert video["format"] == "mp4"
    assert video["frames"].shape == (4, 4, 4, 3)
    assert abs(video["duration"] - 4 / 24.0) < 1e-9
    assert video["audio"] is None
    # frames in 0..1
    assert video["frames"].min() >= 0.0
    assert video["frames"].max() <= 1.0


def test_assemble_video_bad_fps():
    node = PSN_AssembleVideoFromBatch()
    frames = make_batch(2)
    try:
        node.run(frames, 0.0, "mp4")
        raise AssertionError("expected ValueError for fps=0")
    except ValueError:
        pass


def test_assemble_video_bad_format():
    node = PSN_AssembleVideoFromBatch()
    frames = make_batch(2)
    try:
        node.run(frames, 24.0, "avi")
        raise AssertionError("expected ValueError for bad format")
    except ValueError:
        pass


def test_assemble_video_empty_batch():
    node = PSN_AssembleVideoFromBatch()
    empty = torch.zeros(0, 4, 4, 3)
    try:
        node.run(empty, 24.0, "mp4")
        raise AssertionError("expected ValueError for empty batch")
    except ValueError:
        pass


def test_assemble_video_with_audio():
    node = PSN_AssembleVideoFromBatch()
    frames = make_batch(2)
    audio = torch.rand(1, 16000, 2)
    (video,) = node.run(frames, 30.0, "webm", audio_track=audio)
    assert video["audio"] is audio
    assert video["format"] == "webm"
    assert video["fps"] == 30.0


def test_input_types_present():
    it = PSN_MergeImageBatches.INPUT_TYPES()
    assert "required" in it
    assert "batch_a" in it["required"]
    assert "batch_b" in it["required"]
    assert "mode" in it["required"]
    it2 = PSN_AssembleVideoFromBatch.INPUT_TYPES()
    assert "image_batch" in it2["required"]
    assert "fps" in it2["required"]
    assert "format" in it2["required"]
    assert "audio_track" in it2["optional"]


def test_no_inplace_modification():
    node = PSN_MergeImageBatches()
    a = make_batch(2)
    b = make_batch(2, seed=1)
    a_copy = a.clone()
    b_copy = b.clone()
    node.run(a, b, "concat")
    assert torch.equal(a, a_copy)
    assert torch.equal(b, b_copy)


if __name__ == "__main__":
    test_module_mappings()
    test_merge_concat()
    test_merge_interleave()
    test_merge_interleave_uneven()
    test_merge_bad_mode()
    test_merge_shape_mismatch()
    test_assemble_video()
    test_assemble_video_bad_fps()
    test_assemble_video_bad_format()
    test_assemble_video_empty_batch()
    test_assemble_video_with_audio()
    test_input_types_present()
    test_no_inplace_modification()
    print("ok")
