"""Tests for PSN_ValueAnimationMask node."""

import pytest
from psn_nodes.gen.psn_valueanimationmask import (
    PSN_ValueAnimationMask,
    _compute_brightness,
    _compute_color_deviation,
    _analyze_frame,
    _apply_threshold,
)


def _make_pixel(r, g, b):
    """Helper to create a pixel as a list of channel values."""
    return [r, g, b]


def _make_frame(pixels_2d):
    """Helper to create a frame from a 2D list of pixels."""
    return pixels_2d


def _make_video(frames):
    """Helper to create a video from a list of frames."""
    return frames


class TestComputeBrightness:
    def test_grayscale_pixel(self):
        """Brightness of a gray pixel should equal the channel value."""
        pixel = _make_pixel(0.5, 0.5, 0.5)
        assert _compute_brightness(pixel) == pytest.approx(0.5)

    def test_white_pixel(self):
        """Brightness of a white pixel should be 1.0."""
        pixel = _make_pixel(1.0, 1.0, 1.0)
        assert _compute_brightness(pixel) == pytest.approx(1.0)

    def test_black_pixel(self):
        """Brightness of a black pixel should be 0.0."""
        pixel = _make_pixel(0.0, 0.0, 0.0)
        assert _compute_brightness(pixel) == pytest.approx(0.0)

    def test_colored_pixel(self):
        """Brightness of a colored pixel is the mean of channels."""
        pixel = _make_pixel(1.0, 0.0, 0.0)
        assert _compute_brightness(pixel) == pytest.approx(1.0 / 3.0)

    def test_empty_pixel(self):
        """Empty pixel should return 0.0."""
        assert _compute_brightness([]) == 0.0


class TestComputeColorDeviation:
    def test_gray_pixel(self):
        """Gray pixel should have zero color deviation."""
        pixel = _make_pixel(0.5, 0.5, 0.5)
        assert _compute_color_deviation(pixel) == pytest.approx(0.0)

    def test_pure_red_pixel(self):
        """Pure red pixel should have high color deviation."""
        pixel = _make_pixel(1.0, 0.0, 0.0)
        # Mean = 1/3, deviations: |1-1/3|=2/3, |0-1/3|=1/3, |0-1/3|=1/3
        # Max deviation = 2/3
        assert _compute_color_deviation(pixel) == pytest.approx(2.0 / 3.0)

    def test_white_pixel(self):
        """White pixel should have zero color deviation."""
        pixel = _make_pixel(1.0, 1.0, 1.0)
        assert _compute_color_deviation(pixel) == pytest.approx(0.0)

    def test_empty_pixel(self):
        """Empty pixel should return 0.0."""
        assert _compute_color_deviation([]) == 0.0


class TestAnalyzeFrame:
    def test_brightness_frame(self):
        """Analyze a simple frame for brightness."""
        frame = _make_frame([
            [_make_pixel(0.0, 0.0, 0.0), _make_pixel(1.0, 1.0, 1.0)],
            [_make_pixel(0.5, 0.5, 0.5), _make_pixel(0.25, 0.25, 0.25)],
        ])
        result = _analyze_frame(frame, "brightness")
        assert len(result) == 2
        assert len(result[0]) == 2
        assert result[0][0] == pytest.approx(0.0)
        assert result[0][1] == pytest.approx(1.0)
        assert result[1][0] == pytest.approx(0.5)
        assert result[1][1] == pytest.approx(0.25)

    def test_color_frame(self):
        """Analyze a simple frame for color deviation."""
        frame = _make_frame([
            [_make_pixel(0.5, 0.5, 0.5), _make_pixel(1.0, 0.0, 0.0)],
        ])
        result = _analyze_frame(frame, "color")
        assert result[0][0] == pytest.approx(0.0)
        assert result[0][1] == pytest.approx(2.0 / 3.0)

    def test_invalid_value_type(self):
        """Invalid value_type should raise ValueError."""
        frame = _make_frame([[_make_pixel(0.5, 0.5, 0.5)]])
        with pytest.raises(ValueError, match="value_type must be"):
            _analyze_frame(frame, "invalid_type")


class TestApplyThreshold:
    def test_basic_threshold(self):
        """Values above threshold become 1.0, below become 0.0."""
        values = [[0.3, 0.7], [0.5, 0.9]]
        mask = _apply_threshold(values, 0.5)
        assert mask == [[0.0, 1.0], [1.0, 1.0]]

    def test_threshold_at_boundary(self):
        """Value exactly at threshold should be 1.0 (>= comparison)."""
        values = [[0.5]]
        mask = _apply_threshold(values, 0.5)
        assert mask == [[1.0]]

    def test_all_below_threshold(self):
        """All values below threshold should produce all zeros."""
        values = [[0.1, 0.2], [0.3, 0.4]]
        mask = _apply_threshold(values, 0.5)
        assert mask == [[0.0, 0.0], [0.0, 0.0]]

    def test_all_above_threshold(self):
        """All values above threshold should produce all ones."""
        values = [[0.6, 0.7], [0.8, 0.9]]
        mask = _apply_threshold(values, 0.5)
        assert mask == [[1.0, 1.0], [1.0, 1.0]]


class TestPSNValueAnimationMask:
    def test_brightness_mask_basic(self):
        """Basic brightness mask generation."""
        node = PSN_ValueAnimationMask()
        # Frame with one dark pixel and one bright pixel
        video = _make_video([
            _make_frame([
                [_make_pixel(0.1, 0.1, 0.1), _make_pixel(0.9, 0.9, 0.9)],
            ]),
        ])
        (mask,) = node.run(video, "brightness", 0.5)
        assert len(mask) == 1
        assert mask[0] == [[0.0, 1.0]]

    def test_color_mask_basic(self):
        """Basic color mask generation."""
        node = PSN_ValueAnimationMask()
        # Gray pixel (low color deviation) and red pixel (high color deviation)
        video = _make_video([
            _make_frame([
                [_make_pixel(0.5, 0.5, 0.5), _make_pixel(1.0, 0.0, 0.0)],
            ]),
        ])
        (mask,) = node.run(video, "color", 0.5)
        assert len(mask) == 1
        # Gray: deviation 0.0 < 0.5 -> 0.0
        # Red: deviation 2/3 ≈ 0.667 >= 0.5 -> 1.0
        assert mask[0] == [[0.0, 1.0]]

    def test_multi_frame_video(self):
        """Mask should be generated for each frame in the video."""
        node = PSN_ValueAnimationMask()
        video = _make_video([
            _make_frame([[_make_pixel(0.2, 0.2, 0.2)]]),
            _make_frame([[_make_pixel(0.8, 0.8, 0.8)]]),
            _make_frame([[_make_pixel(0.5, 0.5, 0.5)]]),
        ])
        (mask,) = node.run(video, "brightness", 0.5)
        assert len(mask) == 3
        assert mask[0] == [[0.0]]
        assert mask[1] == [[1.0]]
        assert mask[2] == [[1.0]]

    def test_invalid_value_type(self):
        """Invalid value_type should raise ValueError."""
        node = PSN_ValueAnimationMask()
        video = _make_video([_make_frame([[_make_pixel(0.5, 0.5, 0.5)]])])
        with pytest.raises(ValueError, match="value_type must be"):
            node.run(video, "invalid", 0.5)

    def test_invalid_threshold_type(self):
        """Non-numeric threshold should raise TypeError."""
        node = PSN_ValueAnimationMask()
        video = _make_video([_make_frame([[_make_pixel(0.5, 0.5, 0.5)]])])
        with pytest.raises(TypeError, match="threshold must be a number"):
            node.run(video, "brightness", "high")

    def test_threshold_out_of_range(self):
        """Threshold outside [0, 1] should raise ValueError."""
        node = PSN_ValueAnimationMask()
        video = _make_video([_make_frame([[_make_pixel(0.5, 0.5, 0.5)]])])
        with pytest.raises(ValueError, match="threshold must be between"):
            node.run(video, "brightness", 1.5)

    def test_invalid_video_type(self):
        """Non-list video should raise TypeError."""
        node = PSN_ValueAnimationMask()
        with pytest.raises(TypeError, match="video must be a list"):
            node.run("not a list", "brightness", 0.5)

    def test_empty_video(self):
        """Empty video should return empty mask."""
        node = PSN_ValueAnimationMask()
        (mask,) = node.run([], "brightness", 0.5)
        assert mask == []

    def test_edge_case_threshold_zero(self):
        """Threshold of 0.0 should mask all pixels (all values >= 0)."""
        node = PSN_ValueAnimationMask()
        video = _make_video([
            _make_frame([[_make_pixel(0.0, 0.0, 0.0), _make_pixel(0.5, 0.5, 0.5)]]),
        ])
        (mask,) = node.run(video, "brightness", 0.0)
        assert mask[0] == [[1.0, 1.0]]

    def test_edge_case_threshold_one(self):
        """Threshold of 1.0 should only mask fully bright pixels."""
        node = PSN_ValueAnimationMask()
        video = _make_video([
            _make_frame([[_make_pixel(0.9, 0.9, 0.9), _make_pixel(1.0, 1.0, 1.0)]]),
        ])
        (mask,) = node.run(video, "brightness", 1.0)
        assert mask[0] == [[0.0, 1.0]]
