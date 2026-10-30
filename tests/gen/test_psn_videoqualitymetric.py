import pytest
from psn_nodes.gen.psn_videoqualitymetric import (
    PSN_VideoQualityMetric,
    compute_metric,
    _normalize_frame,
    METRICS,
)

def test_psnr_identical_frames():
    """PSNR should be very high (100) for identical frames."""
    frame = [[0.5, 0.5], [0.5, 0.5]]
    ref = [[0.5, 0.5], [0.5, 0.5]]
    avg, heatmap = compute_metric([frame], [ref], "psnr")
    assert avg == 100.0
    assert len(heatmap) == 1
    assert heatmap[0] == [[0.0, 0.0], [0.0, 0.0]]

def test_psnr_different_frames():
    """PSNR should be lower for different frames."""
    frame = [[1.0, 0.0], [0.0, 1.0]]
    ref = [[0.0, 1.0], [1.0, 0.0]]
    avg, heatmap = compute_metric([frame], [ref], "psnr")
    # MSE = ((1-0)^2 + (0-1)^2 + (0-1)^2 + (1-0)^2) / 4 = 4/4 = 1.0
    # PSNR = 10 * log10(1/1) = 0
    assert abs(avg - 0.0) < 1e-6

def test_ssim_identical_frames():
    """SSIM should be 1.0 for identical frames."""
    frame = [[0.5, 0.5], [0.5, 0.5]]
    ref = [[0.5, 0.5], [0.5, 0.5]]
    avg, heatmap = compute_metric([frame], [ref], "ssim")
    assert abs(avg - 1.0) < 1e-6

def test_lpips_identical_frames():
    """LPIPS should be 0.0 for identical frames."""
    frame = [[0.5, 0.5], [0.5, 0.5]]
    ref = [[0.5, 0.5], [0.5, 0.5]]
    avg, heatmap = compute_metric([frame], [ref], "lpips")
    assert abs(avg - 0.0) < 1e-6

def test_invalid_metric_raises():
    """Should raise ValueError for unknown metric."""
    frame = [[0.5]]
    ref = [[0.5]]
    with pytest.raises(ValueError, match="Unknown metric"):
        compute_metric([frame], [ref], "unknown_metric")

def test_mismatched_frame_count_raises():
    """Should raise ValueError if frame counts don't match."""
    frames = [[[0.5]], [[0.5]]]
    ref = [[[0.5]]]
    with pytest.raises(ValueError, match="Number of frames"):
        compute_metric(frames, ref, "psnr")

def test_empty_frames():
    """Should handle empty frames gracefully."""
    avg, heatmap = compute_metric([], [], "psnr")
    assert avg == 0.0
    assert heatmap == []

def test_normalization_255_range():
    """Frames with values in [0, 255] should be normalized to [0, 1]."""
    frame = [[255.0, 0.0]]
    ref = [[0.0, 255.0]]
    avg, heatmap = compute_metric([frame], [ref], "psnr")
    # After normalization: frame = [[1.0, 0.0]], ref = [[0.0, 1.0]]
    # Same as test_psnr_different_frames, so PSNR = 0
    assert abs(avg - 0.0) < 1e-6

def test_node_run_interface():
    """Test the node's run method directly."""
    node = PSN_VideoQualityMetric()
    frame = [[0.5, 0.5]]
    ref = [[0.5, 0.5]]
    avg, heatmap = node.run([frame], [ref], "psnr")
    assert avg == 100.0
    assert len(heatmap) == 1

def test_multiple_frames_average():
    """Average should be computed across multiple frames."""
    frame1 = [[1.0]]
    ref1 = [[0.0]]
    frame2 = [[0.0]]
    ref2 = [[1.0]]
    avg, heatmap = compute_metric([frame1, frame2], [ref1, ref2], "psnr")
    # Each frame has MSE = 1.0, PSNR = 0.0
    assert abs(avg - 0.0) < 1e-6
    assert len(heatmap) == 2
