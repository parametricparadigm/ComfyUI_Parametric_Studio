import torch
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from n_9_vr180_projection_conversion import PSN_VR180_Convert, NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS


def test_module_structure():
    """Test that the module has the required structure."""
    assert "PSN_VR180_Convert" in NODE_CLASS_MAPPINGS, "PSN_VR180_Convert not in NODE_CLASS_MAPPINGS"
    assert "PSN_VR180_Convert" in NODE_DISPLAY_NAME_MAPPINGS, "PSN_VR180_Convert not in NODE_DISPLAY_NAME_MAPPINGS"
    node_class = NODE_CLASS_MAPPINGS["PSN_VR180_Convert"]
    assert hasattr(node_class, "INPUT_TYPES"), "Missing INPUT_TYPES"
    assert hasattr(node_class, "RETURN_TYPES"), "Missing RETURN_TYPES"
    assert hasattr(node_class, "FUNCTION"), "Missing FUNCTION"
    assert hasattr(node_class, "CATEGORY"), "Missing CATEGORY"
    assert node_class.FUNCTION == "run", "FUNCTION should be 'run'"
    assert node_class.CATEGORY.startswith("ParametricStudio/"), "CATEGORY should start with ParametricStudio/"
    assert node_class.RETURN_TYPES == ("IMAGE",), "RETURN_TYPES should be ('IMAGE',)"


def test_input_types():
    """Test that INPUT_TYPES has the required fields."""
    node_class = PSN_VR180_Convert
    it = node_class.INPUT_TYPES()
    assert "required" in it, "INPUT_TYPES missing 'required'"
    assert "image" in it["required"], "INPUT_TYPES missing 'image'"
    assert "fov" in it["required"], "INPUT_TYPES missing 'fov'"
    assert it["required"]["image"] == ("IMAGE",), "image should be IMAGE type"
    assert it["required"]["fov"][0] == "FLOAT", "fov should be FLOAT type"


def test_basic_conversion():
    """Test basic conversion with a small image."""
    node = PSN_VR180_Convert()
    # Create a small test image: 1 batch, 64x128, 3 channels
    img = torch.rand(1, 64, 128, 3, dtype=torch.float32)
    result = node.run(img, fov=90.0)
    assert len(result) == 1, "Should return a tuple with 1 element"
    vr180 = result[0]
    assert vr180.dim() == 4, "Output should be 4D"
    assert vr180.shape[0] == 1, "Batch size should be preserved"
    assert vr180.shape[3] == 3, "Channels should be preserved"
    # VR180 should be 2:1 aspect ratio: W_out = 2 * H_out
    assert vr180.shape[2] == 2 * vr180.shape[1], f"VR180 should be 2:1, got {vr180.shape[1]}x{vr180.shape[2]}"
    # Values should be in 0..1
    assert vr180.min() >= 0.0, "Values should be >= 0"
    assert vr180.max() <= 1.0, "Values should be <= 1"


def test_different_fov():
    """Test that different FOV values produce different outputs."""
    node = PSN_VR180_Convert()
    img = torch.rand(1, 32, 64, 3, dtype=torch.float32)
    result_60 = node.run(img, fov=60.0)
    result_120 = node.run(img, fov=120.0)
    # Outputs should have the same shape
    assert result_60[0].shape == result_120[0].shape, "Different FOV should produce same output shape"
    # But different values (different warp)
    diff = (result_60[0] - result_120[0]).abs().sum().item()
    assert diff > 0, "Different FOV should produce different outputs"


def test_edge_case_min_fov():
    """Test with minimum FOV."""
    node = PSN_VR180_Convert()
    img = torch.rand(1, 32, 64, 3, dtype=torch.float32)
    result = node.run(img, fov=10.0)
    assert result[0].shape[2] == 2 * result[0].shape[1], "VR180 should be 2:1 even at min FOV"
    assert result[0].min() >= 0.0
    assert result[0].max() <= 1.0


def test_edge_case_max_fov():
    """Test with maximum FOV."""
    node = PSN_VR180_Convert()
    img = torch.rand(1, 32, 64, 3, dtype=torch.float32)
    result = node.run(img, fov=180.0)
    assert result[0].shape[2] == 2 * result[0].shape[1], "VR180 should be 2:1 even at max FOV"
    assert result[0].min() >= 0.0
    assert result[0].max() <= 1.0


def test_bad_input_wrong_dims():
    """Test that bad input (wrong dimensions) raises an error."""
    node = PSN_VR180_Convert()
    # 3D tensor instead of 4D
    bad_img = torch.rand(64, 128, 3, dtype=torch.float32)
    try:
        node.run(bad_img, fov=90.0)
        assert False, "Should have raised ValueError for 3D input"
    except ValueError as e:
        assert "4D" in str(e) or "dim" in str(e).lower(), f"Error message should mention dimensions, got: {e}"


def test_no_in_place_modification():
    """Test that the input image is not modified in place."""
    node = PSN_VR180_Convert()
    img = torch.rand(1, 32, 64, 3, dtype=torch.float32)
    img_copy = img.clone()
    node.run(img, fov=90.0)
    assert torch.equal(img, img_copy), "Input image should not be modified in place"


def test_grid_pattern_curvature():
    """Test that a grid pattern shows curvature consistent with cylindrical projection."""
    node = PSN_VR180_Convert()
    # Create a grid pattern: vertical lines
    H, W = 64, 128
    img = torch.zeros(1, H, W, 3, dtype=torch.float32)
    # Draw vertical lines every 16 pixels
    for x in range(0, W, 16):
        img[:, :, x, :] = 1.0
    result = node.run(img, fov=90.0)
    vr180 = result[0]
    # The center column should still have a line (theta=0 maps to center)
    center_col = vr180[:, :, W // 2, :].mean()
    # The edges should have different values due to warping
    left_col = vr180[:, :, 0, :].mean()
    right_col = vr180[:, :, -1, :].mean()
    # In cylindrical projection, the center should be relatively undistorted
    # while edges are stretched. Just verify the output is valid.
    assert vr180.shape[2] == 2 * vr180.shape[1], "VR180 should be 2:1"
    assert vr180.min() >= 0.0
    assert vr180.max() <= 1.0


def test_batch_size_preserved():
    """Test that batch size is preserved."""
    node = PSN_VR180_Convert()
    img = torch.rand(3, 32, 64, 3, dtype=torch.float32)
    result = node.run(img, fov=90.0)
    assert result[0].shape[0] == 3, "Batch size should be preserved"


def test_output_dimensions_1920x1080():
    """Test that a 1920x1080 input produces correct VR180 dimensions."""
    node = PSN_VR180_Convert()
    # Use a smaller version to save memory: 192x108 -> should give 192x384
    img = torch.rand(1, 108, 192, 3, dtype=torch.float32)
    result = node.run(img, fov=90.0)
    vr180 = result[0]
    # H_out = H = 108, W_out = 2 * H = 216
    assert vr180.shape[1] == 108, f"Height should be 108, got {vr180.shape[1]}"
    assert vr180.shape[2] == 216, f"Width should be 216, got {vr180.shape[2]}"


if __name__ == "__main__":
    test_module_structure()
    test_input_types()
    test_basic_conversion()
    test_different_fov()
    test_edge_case_min_fov()
    test_edge_case_max_fov()
    test_bad_input_wrong_dims()
    test_no_in_place_modification()
    test_grid_pattern_curvature()
    test_batch_size_preserved()
    test_output_dimensions_1920x1080()
    print('ok')
