import torch

import n_5_automated_video_contact_sheet_generati as m


def make_video(f, h, w, c=3, seed=0):
    g = torch.Generator().manual_seed(seed)
    return torch.rand(f, h, w, c, generator=g)


def test_module_mappings():
    assert "PSN_Video_Frame_Sampler" in m.NODE_CLASS_MAPPINGS
    assert "PSN_Contact_Sheet_Assembler" in m.NODE_CLASS_MAPPINGS
    assert m.NODE_DISPLAY_NAME_MAPPINGS["PSN_Video_Frame_Sampler"]
    assert m.NODE_DISPLAY_NAME_MAPPINGS["PSN_Contact_Sheet_Assembler"]
    for cls in m.NODE_CLASS_MAPPINGS.values():
        assert cls.FUNCTION == "run"
        assert cls.CATEGORY.startswith("ParametricStudio/")
        assert isinstance(cls.RETURN_TYPES, tuple)
        assert isinstance(cls.RETURN_NAMES, tuple)
        assert len(cls.RETURN_TYPES) == len(cls.RETURN_NAMES)
        it = cls.INPUT_TYPES()
        assert "required" in it


def test_uniform_sampling():
    vid = make_video(100, 16, 16)
    node = m.PSN_Video_Frame_Sampler()
    frames, idx = node.run(vid, 10, "uniform")
    assert idx == [0, 10, 20, 30, 40, 50, 60, 70, 80, 90]
    assert frames.shape == (10, 16, 16, 3)
    # sampled frames match the source
    for i, k in enumerate(idx):
        assert torch.allclose(frames[i], vid[k])


def test_first_last_sampling():
    vid = make_video(10, 8, 8)
    node = m.PSN_Video_Frame_Sampler()
    frames, idx = node.run(vid, 5, "first_last")
    assert idx[0] == 0
    assert idx[-1] == 9
    assert len(idx) == 5
    assert frames.shape == (5, 8, 8, 3)
    # n == 2 edge case
    _, idx2 = node.run(vid, 2, "first_last")
    assert idx2 == [0, 9]
    # n == 1 edge case
    _, idx1 = node.run(vid, 1, "first_last")
    assert idx1 == [0]


def test_keyframe_sampling():
    # build a video where frame 5 is very different from its neighbours
    vid = torch.zeros(10, 8, 8, 3)
    vid[5] = 1.0
    node = m.PSN_Video_Frame_Sampler()
    frames, idx = node.run(vid, 3, "keyframe")
    assert 5 in idx
    assert len(idx) == 3
    assert frames.shape == (3, 8, 8, 3)


def test_num_frames_clamped():
    vid = make_video(4, 8, 8)
    node = m.PSN_Video_Frame_Sampler()
    frames, idx = node.run(vid, 100, "uniform")
    assert len(idx) == 4
    assert idx == [0, 1, 2, 3]


def test_bad_video_input():
    node = m.PSN_Video_Frame_Sampler()
    try:
        node.run("not a tensor", 4, "uniform")
        assert False, "expected TypeError"
    except TypeError:
        pass
    try:
        node.run(torch.rand(4, 8, 8, 5), 4, "uniform")
        assert False, "expected ValueError for bad channel count"
    except ValueError:
        pass
    # 3D [H, W, C] with a valid channel count is accepted as a single frame
    frames, idx = node.run(torch.rand(8, 8, 3), 4, "uniform")
    assert frames.shape == (1, 8, 8, 3)
    assert idx == [0]


def test_contact_sheet_dimensions():
    vid = make_video(100, 16, 16)
    sampler = m.PSN_Video_Frame_Sampler()
    frames, idx = sampler.run(vid, 10, "uniform")
    asm = m.PSN_Contact_Sheet_Assembler()
    sheet = asm.run(frames, idx, 2, 5, False)[0]
    # 2 cols x 5 rows of 16x16 cells -> 80 x 32
    assert sheet.shape == (80, 32, 3)
    assert sheet.min() >= 0.0 and sheet.max() <= 1.0


def test_contact_sheet_with_timestamps():
    vid = make_video(10, 32, 32)
    sampler = m.PSN_Video_Frame_Sampler()
    frames, idx = sampler.run(vid, 4, "uniform")
    asm = m.PSN_Contact_Sheet_Assembler()
    sheet = asm.run(frames, idx, 2, 2, True)[0]
    assert sheet.shape == (64, 64, 3)
    # labels should have modified the top-left corner of at least one cell
    # compare against a no-timestamp sheet: they must differ
    sheet_plain = asm.run(frames, idx, 2, 2, False)[0]
    assert not torch.allclose(sheet, sheet_plain)


def test_contact_sheet_padding():
    # fewer frames than grid cells -> padded with black
    frames = make_video(3, 16, 16)
    asm = m.PSN_Contact_Sheet_Assembler()
    sheet = asm.run(frames, [0, 1, 2], 2, 2, False)[0]
    assert sheet.shape == (32, 32, 3)
    # bottom-right cell should be all black (padding)
    br = sheet[16:32, 16:32, :]
    assert torch.all(br == 0.0)


def test_no_inplace_modification():
    vid = make_video(10, 16, 16)
    vid_copy = vid.clone()
    sampler = m.PSN_Video_Frame_Sampler()
    frames, idx = sampler.run(vid, 4, "uniform")
    asm = m.PSN_Contact_Sheet_Assembler()
    asm.run(frames, idx, 2, 2, True)
    assert torch.allclose(vid, vid_copy), "input video was modified in place"


def test_single_frame_video():
    vid = make_video(1, 8, 8)
    node = m.PSN_Video_Frame_Sampler()
    frames, idx = node.run(vid, 5, "uniform")
    assert idx == [0]
    assert frames.shape == (1, 8, 8, 3)


def main():
    test_module_mappings()
    test_uniform_sampling()
    test_first_last_sampling()
    test_keyframe_sampling()
    test_num_frames_clamped()
    test_bad_video_input()
    test_contact_sheet_dimensions()
    test_contact_sheet_with_timestamps()
    test_contact_sheet_padding()
    test_no_inplace_modification()
    test_single_frame_video()
    print("ok")


if __name__ == "__main__":
    main()
