import torch

from n_10_scene_detection_segmentation import (
    PSN_SceneDetector,
    PSN_SegmentExtractor,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def make_video(frames):
    """Build a [B,H,W,C] float tensor in 0..1 from a list of per-frame colors."""
    t = torch.zeros(len(frames), 8, 8, 3)
    for i, c in enumerate(frames):
        t[i] = torch.tensor(c, dtype=torch.float32)
    return t


def test_mappings():
    assert "PSN_SceneDetector" in NODE_CLASS_MAPPINGS
    assert "PSN_SegmentExtractor" in NODE_CLASS_MAPPINGS
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_SceneDetector"]
    assert PSN_SceneDetector.FUNCTION == "run"
    assert PSN_SceneDetector.CATEGORY.startswith("ParametricStudio/")


def test_detector_known_change():
    # frames 0-1 identical, frame 2 very different -> change at index 2
    vid = make_video([[0.1, 0.1, 0.1], [0.1, 0.1, 0.1], [0.9, 0.9, 0.9]])
    idx, marked = PSN_SceneDetector().run(vid, 0.3)
    assert idx == [2], idx
    assert marked.shape == vid.shape
    # marked frame 2 has red border
    assert marked[2, 0, 0, 0].item() == 1.0
    # unmarked frames untouched
    assert torch.equal(marked[0], vid[0])


def test_detector_no_change():
    vid = make_video([[0.2, 0.2, 0.2], [0.2, 0.2, 0.2], [0.2, 0.2, 0.2]])
    idx, marked = PSN_SceneDetector().run(vid, 0.3)
    assert idx == []
    assert torch.equal(marked, vid)


def test_detector_threshold_edge():
    # small difference: 0.1 vs 0.2 -> low diff; high threshold -> no change
    vid = make_video([[0.1, 0.1, 0.1], [0.2, 0.2, 0.2]])
    idx, _ = PSN_SceneDetector().run(vid, 0.9)
    assert idx == []
    idx2, _ = PSN_SceneDetector().run(vid, 0.0)
    assert idx2 == [1]


def test_detector_bad_input():
    try:
        PSN_SceneDetector().run(torch.zeros(3, 8, 8), 0.3)
        raise AssertionError("expected ValueError for 3D input")
    except ValueError:
        pass
    try:
        PSN_SceneDetector().run(make_video([[0.5, 0.5, 0.5]]), 1.5)
        raise AssertionError("expected ValueError for bad threshold")
    except ValueError:
        pass
    try:
        PSN_SceneDetector().run(make_video([[0.5, 0.5, 0.5]]), "x")
        raise AssertionError("expected TypeError for bad threshold")
    except TypeError:
        pass


def test_extractor_segments():
    vid = make_video([[0.1, 0.1, 0.1], [0.1, 0.1, 0.1],
                      [0.9, 0.9, 0.9], [0.9, 0.9, 0.9],
                      [0.5, 0.5, 0.5]])
    segs = PSN_SegmentExtractor().run(vid, [2, 4])[0]
    assert len(segs) == 3
    assert segs[0].shape[0] == 2
    assert segs[1].shape[0] == 2
    assert segs[2].shape[0] == 1
    # content preserved
    assert torch.equal(segs[0][0], vid[0])
    assert torch.equal(segs[1][0], vid[2])
    assert torch.equal(segs[2][0], vid[4])


def test_extractor_edge_cases():
    vid = make_video([[0.1, 0.1, 0.1], [0.2, 0.2, 0.2], [0.3, 0.3, 0.3]])
    # no scene changes -> single segment of whole video
    segs = PSN_SegmentExtractor().run(vid, [])[0]
    assert len(segs) == 1 and segs[0].shape[0] == 3
    # duplicate + unsorted indices handled
    segs = PSN_SegmentExtractor().run(vid, [2, 1, 1])[0]
    assert [s.shape[0] for s in segs] == [1, 1, 1]
    # out of range
    try:
        PSN_SegmentExtractor().run(vid, [5])
        raise AssertionError("expected ValueError for out-of-range index")
    except ValueError:
        pass
    # non-int entry
    try:
        PSN_SegmentExtractor().run(vid, [1.5])
        raise AssertionError("expected TypeError for non-int index")
    except TypeError:
        pass
    # not a list
    try:
        PSN_SegmentExtractor().run(vid, 3)
        raise AssertionError("expected TypeError for non-list indices")
    except TypeError:
        pass


def test_no_inplace():
    vid = make_video([[0.1, 0.1, 0.1], [0.9, 0.9, 0.9]])
    snap = vid.clone()
    PSN_SceneDetector().run(vid, 0.3)
    PSN_SegmentExtractor().run(vid, [1])
    assert torch.equal(vid, snap)


def test_input_types():
    it = PSN_SceneDetector.INPUT_TYPES()
    assert "image" in it["required"] and "threshold" in it["required"]
    it2 = PSN_SegmentExtractor.INPUT_TYPES()
    assert "image" in it2["required"] and "scene_indices" in it2["required"]


if __name__ == "__main__":
    test_mappings()
    test_detector_known_change()
    test_detector_no_change()
    test_detector_threshold_edge()
    test_detector_bad_input()
    test_extractor_segments()
    test_extractor_edge_cases()
    test_no_inplace()
    test_input_types()
    print("ok")
