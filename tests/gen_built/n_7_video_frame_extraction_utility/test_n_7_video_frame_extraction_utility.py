import torch

from n_7_video_frame_extraction_utility import (
    PSN_Video_Frame_Extract,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def make_video(n=10, h=4, w=4, c=3):
    # Each frame has a distinct constant value so we can verify identity.
    t = torch.zeros(n, h, w, c)
    for i in range(n):
        t[i] = float(i)
    return t


def test_basic_extraction():
    node = PSN_Video_Frame_Extract()
    vid = make_video(10)
    out, info = node.run(vid, [0, 5, 9])
    assert out.shape == (3, 4, 4, 3), out.shape
    assert torch.allclose(out[0], torch.full((4, 4, 3), 0.0))
    assert torch.allclose(out[1], torch.full((4, 4, 3), 5.0))
    assert torch.allclose(out[2], torch.full((4, 4, 3), 9.0))
    assert "extracted=3" in info
    assert "total=10" in info


def test_single_int_index():
    node = PSN_Video_Frame_Extract()
    vid = make_video(10)
    out, info = node.run(vid, 7)
    assert out.shape == (1, 4, 4, 3)
    assert torch.allclose(out[0], torch.full((4, 4, 3), 7.0))


def test_negative_index():
    node = PSN_Video_Frame_Extract()
    vid = make_video(10)
    out, _ = node.run(vid, [-1])
    assert out.shape == (1, 4, 4, 3)
    assert torch.allclose(out[0], torch.full((4, 4, 3), 9.0))


def test_string_indices():
    node = PSN_Video_Frame_Extract()
    vid = make_video(10)
    out, info = node.run(vid, "0, 5, 9")
    assert out.shape == (3, 4, 4, 3)
    assert torch.allclose(out[1], torch.full((4, 4, 3), 5.0))


def test_out_of_range_raises():
    node = PSN_Video_Frame_Extract()
    vid = make_video(10)
    try:
        node.run(vid, [0, 10])
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for out-of-range index")


def test_bad_image_dim_raises():
    node = PSN_Video_Frame_Extract()
    bad = torch.zeros(3, 4, 4)  # 3D, not 4D
    try:
        node.run(bad, [0])
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for 3D image")


def test_empty_batch_raises():
    node = PSN_Video_Frame_Extract()
    empty = torch.zeros(0, 4, 4, 3)
    try:
        node.run(empty, [0])
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for empty batch")


def test_fps_metadata():
    node = PSN_Video_Frame_Extract()
    vid = make_video(10)
    _, info = node.run(vid, [0, 5], fps=25.0)
    assert "fps=25.0" in info
    assert "times=" in info


def test_input_not_mutated():
    node = PSN_Video_Frame_Extract()
    vid = make_video(10)
    snapshot = vid.clone()
    node.run(vid, [1, 2])
    assert torch.equal(vid, snapshot)


def test_module_mappings():
    assert "PSN_Video_Frame_Extract" in NODE_CLASS_MAPPINGS
    assert "PSN_Video_Frame_Extract" in NODE_DISPLAY_NAME_MAPPINGS
    cls = NODE_CLASS_MAPPINGS["PSN_Video_Frame_Extract"]
    it = cls.INPUT_TYPES()
    assert "image" in it["required"]
    assert "frame_indices" in it["required"]
    assert cls.FUNCTION == "run"
    assert cls.RETURN_TYPES == ("IMAGE", "STRING")


def main():
    test_basic_extraction()
    test_single_int_index()
    test_negative_index()
    test_string_indices()
    test_out_of_range_raises()
    test_bad_image_dim_raises()
    test_empty_batch_raises()
    test_fps_metadata()
    test_input_not_mutated()
    test_module_mappings()
    print("ok")


if __name__ == "__main__":
    main()
