"""Tests for the PSN 2.5D Parallax Video Effect pure-logic nodes."""

import json
import math

import pytest

from psn_nodes.gen.n_3_2_5d_parallax_video_effect import (
    PSN_Depth_Parallax_Generator,
    PSN_Parallax_Video_Assembler,
    CAMERA_PATHS,
    CODECS,
)


def _make_depth_json(rows, cols, value=0.5):
    """Build a JSON string for a uniform depth map."""
    grid = [[value] * cols for _ in range(rows)]
    return json.dumps(grid)


def _make_gradient_depth_json(rows, cols):
    """Build a JSON string for a depth map that increases left-to-right."""
    grid = []
    for r in range(rows):
        row = []
        for c in range(cols):
            row.append(c / max(cols - 1, 1))
        grid.append(row)
    return json.dumps(grid)


class TestDepthParallaxGenerator:
    def test_produces_correct_frame_count(self):
        gen = PSN_Depth_Parallax_Generator()
        depth = _make_depth_json(4, 4, 0.5)
        frames_json, masks_json = gen.run(depth, 1.0, 10, "pan_left")
        frames = json.loads(frames_json)
        masks = json.loads(masks_json)
        assert len(frames) == 10
        assert len(masks) == 10

    def test_high_depth_moves_more_than_low_depth(self):
        gen = PSN_Depth_Parallax_Generator()
        # Depth map: left half is 0.0, right half is 1.0.
        grid = [[0.0, 0.0, 1.0, 1.0] for _ in range(2)]
        depth = json.dumps(grid)
        frames_json, _ = gen.run(depth, 1.0, 5, "pan_right")
        frames = json.loads(frames_json)
        # Use the last frame (max displacement).
        last = frames[-1]
        # Pixel (0, 0) has depth 0.0 -> displacement should be 0.
        assert last[0][0][0] == 0.0
        assert last[0][0][1] == 0.0
        # Pixel (0, 2) has depth 1.0 -> displacement should be > 0.
        assert last[0][2][0] > 0.0
        # High-depth displacement should be strictly greater than low-depth.
        assert last[0][2][0] > last[0][0][0]

    def test_frame_zero_has_zero_displacement(self):
        gen = PSN_Depth_Parallax_Generator()
        depth = _make_depth_json(3, 3, 0.8)
        frames_json, _ = gen.run(depth, 1.0, 5, "pan_left")
        frames = json.loads(frames_json)
        first = frames[0]
        for r in range(3):
            for c in range(3):
                assert first[r][c][0] == 0.0
                assert first[r][c][1] == 0.0

    def test_zoom_in_displaces_outward_from_center(self):
        gen = PSN_Depth_Parallax_Generator()
        # 3x3 grid, all depth 1.0.
        depth = _make_depth_json(3, 3, 1.0)
        frames_json, _ = gen.run(depth, 1.0, 5, "zoom_in")
        frames = json.loads(frames_json)
        last = frames[-1]
        # Center pixel (1,1) should have near-zero displacement.
        assert abs(last[1][1][0]) < 1e-9
        assert abs(last[1][1][1]) < 1e-9
        # Corner pixel (0,0) should move up-left (negative dx, negative dy).
        assert last[0][0][0] < 0.0
        assert last[0][0][1] < 0.0
        # Corner pixel (2,2) should move down-right (positive dx, positive dy).
        assert last[2][2][0] > 0.0
        assert last[2][2][1] > 0.0

    def test_motion_strength_scales_displacement(self):
        gen = PSN_Depth_Parallax_Generator()
        depth = _make_depth_json(2, 2, 1.0)
        frames_weak, _ = gen.run(depth, 0.5, 5, "pan_right")
        frames_strong, _ = gen.run(depth, 2.0, 5, "pan_right")
        weak_last = json.loads(frames_weak)[-1]
        strong_last = json.loads(frames_strong)[-1]
        # Strong should be 4x the weak (2.0 / 0.5).
        assert abs(strong_last[0][0][0] - 4.0 * weak_last[0][0][0]) < 1e-9

    def test_invalid_depth_map_raises(self):
        gen = PSN_Depth_Parallax_Generator()
        with pytest.raises(ValueError):
            gen.run("not json", 1.0, 5, "pan_left")
        with pytest.raises(ValueError):
            gen.run("[]", 1.0, 5, "pan_left")
        with pytest.raises(ValueError):
            gen.run("[[1, 2], [3]]", 1.0, 5, "pan_left")  # ragged rows
        with pytest.raises(ValueError):
            gen.run("[[1, 'a'], [0, 0]]", 1.0, 5, "pan_left")  # non-number

    def test_invalid_camera_path_raises(self):
        gen = PSN_Depth_Parallax_Generator()
        depth = _make_depth_json(2, 2, 0.5)
        with pytest.raises(ValueError):
            gen.run(depth, 1.0, 5, "fly_through")

    def test_invalid_frame_count_raises(self):
        gen = PSN_Depth_Parallax_Generator()
        depth = _make_depth_json(2, 2, 0.5)
        with pytest.raises(ValueError):
            gen.run(depth, 1.0, 0, "pan_left")

    def test_negative_motion_strength_raises(self):
        gen = PSN_Depth_Parallax_Generator()
        depth = _make_depth_json(2, 2, 0.5)
        with pytest.raises(ValueError):
            gen.run(depth, -1.0, 5, "pan_left")

    def test_out_of_range_depth_is_clamped(self):
        gen = PSN_Depth_Parallax_Generator()
        # Depth values outside [0, 1] should be clamped.
        grid = [[-1.0, 2.0], [0.5, 0.5]]
        depth = json.dumps(grid)
        frames_json, _ = gen.run(depth, 1.0, 3, "pan_right")
        frames = json.loads(frames_json)
        last = frames[-1]
        # -1.0 clamped to 0.0 -> no displacement.
        assert last[0][0][0] == 0.0
        # 2.0 clamped to 1.0 -> full displacement.
        assert last[0][1][0] > 0.0

    def test_mask_marks_zero_depth_as_background(self):
        gen = PSN_Depth_Parallax_Generator()
        grid = [[0.0, 1.0], [0.5, 0.0]]
        depth = json.dumps(grid)
        _, masks_json = gen.run(depth, 1.0, 3, "pan_left")
        masks = json.loads(masks_json)
        # All masks should be identical.
        for m in masks:
            assert m == [[0, 1], [1, 0]]


class TestParallaxVideoAssembler:
    def test_returns_valid_path_for_mp4(self):
        gen = PSN_Depth_Parallax_Generator()
        depth = _make_depth_json(2, 2, 0.5)
        frames_json, _ = gen.run(depth, 1.0, 5, "pan_left")
        asm = PSN_Parallax_Video_Assembler()
        (path,) = asm.run(frames_json, 30, "mp4")
        assert path.endswith(".mp4")
        assert "5_frames" in path

    def test_returns_valid_path_for_webm(self):
        gen = PSN_Depth_Parallax_Generator()
        depth = _make_depth_json(2, 2, 0.5)
        frames_json, _ = gen.run(depth, 1.0, 3, "zoom_in")
        asm = PSN_Parallax_Video_Assembler()
        (path,) = asm.run(frames_json, 60, "webm")
        assert path.endswith(".webm")
        assert "3_frames" in path

    def test_invalid_fps_raises(self):
        asm = PSN_Parallax_Video_Assembler()
        frames = json.dumps([[[[0.0, 0.0]]]])
        with pytest.raises(ValueError):
            asm.run(frames, 0, "mp4")
        with pytest.raises(ValueError):
            asm.run(frames, 241, "mp4")

    def test_invalid_codec_raises(self):
        asm = PSN_Parallax_Video_Assembler()
        frames = json.dumps([[[[0.0, 0.0]]]])
        with pytest.raises(ValueError):
            asm.run(frames, 30, "avi")

    def test_invalid_frames_json_raises(self):
        asm = PSN_Parallax_Video_Assembler()
        with pytest.raises(ValueError):
            asm.run("not json", 30, "mp4")
        with pytest.raises(ValueError):
            asm.run("[]", 30, "mp4")  # empty list
        with pytest.raises(ValueError):
            asm.run("[1, 2, 3]", 30, "mp4")  # not a list of frames

    def test_frames_must_be_list_of_lists(self):
        asm = PSN_Parallax_Video_Assembler()
        # Each frame must be a list of rows, each row a list.
        bad = json.dumps([42])  # frame is not a list
        with pytest.raises(ValueError):
            asm.run(bad, 30, "mp4")

    def test_path_is_deterministic(self):
        gen = PSN_Depth_Parallax_Generator()
        depth = _make_depth_json(2, 2, 0.5)
        frames_json, _ = gen.run(depth, 1.0, 5, "pan_left")
        asm = PSN_Parallax_Video_Assembler()
        (path1,) = asm.run(frames_json, 30, "mp4")
        (path2,) = asm.run(frames_json, 30, "mp4")
        assert path1 == path2
