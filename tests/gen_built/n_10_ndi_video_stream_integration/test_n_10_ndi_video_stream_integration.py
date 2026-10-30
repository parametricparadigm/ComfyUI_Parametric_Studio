"""Tests for n_10_ndi_video_stream_integration.py"""

import torch
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from n_10_ndi_video_stream_integration import (
    PSN_NDI_Source,
    image_to_rgb_bytes,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def test_module_structure():
    """Verify module-level mappings and node class structure."""
    assert "PSN_NDI_Source" in NODE_CLASS_MAPPINGS
    assert "PSN_NDI_Source" in NODE_DISPLAY_NAME_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_NDI_Source"] is PSN_NDI_Source

    # Check INPUT_TYPES
    it = PSN_NDI_Source.INPUT_TYPES()
    assert "required" in it
    assert "image" in it["required"]
    assert "ndi_name" in it["required"]
    assert "fps" in it["required"]

    # Check RETURN_TYPES and FUNCTION
    assert PSN_NDI_Source.RETURN_TYPES == ("BOOLEAN",)
    assert PSN_NDI_Source.FUNCTION == "run"
    assert PSN_NDI_Source.CATEGORY == "ParametricStudio/NDI"


def test_image_to_rgb_bytes_basic():
    """Test basic RGB conversion."""
    # Create a 1x2x2x3 image (1 frame, 2x2 pixels, RGB)
    img = torch.tensor([[[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
                         [[0.0, 0.0, 1.0], [1.0, 1.0, 1.0]]]])
    frames = image_to_rgb_bytes(img)
    assert len(frames) == 1
    assert len(frames[0]) == 2 * 2 * 3  # 12 bytes
    # First pixel should be (255, 0, 0)
    assert frames[0][0] == 255
    assert frames[0][1] == 0
    assert frames[0][2] == 0
    # Second pixel should be (0, 255, 0)
    assert frames[0][3] == 0
    assert frames[0][4] == 255
    assert frames[0][5] == 0


def test_image_to_rgb_bytes_rgba():
    """Test RGBA conversion (alpha channel should be dropped)."""
    img = torch.tensor([[[[1.0, 0.5, 0.0, 0.8]]]])  # 1x1x1x4
    frames = image_to_rgb_bytes(img)
    assert len(frames) == 1
    assert len(frames[0]) == 1 * 1 * 3  # 3 bytes (RGB only)
    assert frames[0][0] == 255
    assert frames[0][1] == 128  # 0.5 * 255 = 127.5, rounds to 128
    assert frames[0][2] == 0


def test_image_to_rgb_bytes_clamping():
    """Test that values outside 0..1 are clamped."""
    img = torch.tensor([[[[2.0, -1.0, 0.5]]]])
    frames = image_to_rgb_bytes(img)
    assert frames[0][0] == 255  # clamped to 1.0
    assert frames[0][1] == 0    # clamped to 0.0
    assert frames[0][2] == 128  # 0.5 * 255 = 127.5


def test_run_dry_run():
    """Test run without a sender (dry run)."""
    node = PSN_NDI_Source()
    img = torch.rand(1, 4, 4, 3)
    result = node.run(img, "TestNDI", 30)
    assert result == (True,)


def test_run_with_sender():
    """Test run with a mock sender."""
    node = PSN_NDI_Source()
    img = torch.rand(2, 4, 4, 3)  # 2 frames

    sent_data = {}

    def mock_sender(ndi_name, fps, frames):
        sent_data["name"] = ndi_name
        sent_data["fps"] = fps
        sent_data["frames"] = frames
        return True

    result = node.run(img, "MyStream", 60, ndi_sender=mock_sender)
    assert result == (True,)
    assert sent_data["name"] == "MyStream"
    assert sent_data["fps"] == 60
    assert len(sent_data["frames"]) == 2
    assert len(sent_data["frames"][0]) == 4 * 4 * 3


def test_run_sender_returns_false():
    """Test that sender returning False propagates."""
    node = PSN_NDI_Source()
    img = torch.rand(1, 2, 2, 3)

    def failing_sender(ndi_name, fps, frames):
        return False

    result = node.run(img, "Test", 30, ndi_sender=failing_sender)
    assert result == (False,)


def test_bad_input_not_tensor():
    """Test that non-tensor input raises TypeError."""
    node = PSN_NDI_Source()
    try:
        node.run("not a tensor", "Test", 30)
        assert False, "Should have raised TypeError"
    except TypeError:
        pass


def test_bad_input_wrong_dims():
    """Test that wrong-dimension tensor raises ValueError."""
    node = PSN_NDI_Source()
    img = torch.rand(4, 4, 3)  # 3D, not 4D
    try:
        node.run(img, "Test", 30)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_bad_input_empty_name():
    """Test that empty ndi_name raises ValueError."""
    node = PSN_NDI_Source()
    img = torch.rand(1, 2, 2, 3)
    try:
        node.run(img, "", 30)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_bad_input_bad_fps():
    """Test that invalid fps raises ValueError."""
    node = PSN_NDI_Source()
    img = torch.rand(1, 2, 2, 3)
    try:
        node.run(img, "Test", 0)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_bad_input_non_callable_sender():
    """Test that non-callable sender raises TypeError."""
    node = PSN_NDI_Source()
    img = torch.rand(1, 2, 2, 3)
    try:
        node.run(img, "Test", 30, ndi_sender="not callable")
        assert False, "Should have raised TypeError"
    except TypeError:
        pass


if __name__ == "__main__":
    test_module_structure()
    test_image_to_rgb_bytes_basic()
    test_image_to_rgb_bytes_rgba()
    test_image_to_rgb_bytes_clamping()
    test_run_dry_run()
    test_run_with_sender()
    test_run_sender_returns_false()
    test_bad_input_not_tensor()
    test_bad_input_wrong_dims()
    test_bad_input_empty_name()
    test_bad_input_bad_fps()
    test_bad_input_non_callable_sender()
    print("ok")
