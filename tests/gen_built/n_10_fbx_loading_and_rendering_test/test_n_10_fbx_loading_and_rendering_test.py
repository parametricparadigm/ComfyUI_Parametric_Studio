import torch
import n_10_fbx_loading_and_rendering_test as mod


def test_node_class_exists():
    assert hasattr(mod, "PSN_FBXLoad_Render"), "PSN_FBXLoad_Render class must exist"
    assert hasattr(mod, "NODE_CLASS_MAPPINGS"), "NODE_CLASS_MAPPINGS must exist"
    assert hasattr(mod, "NODE_DISPLAY_NAME_MAPPINGS"), "NODE_DISPLAY_NAME_MAPPINGS must exist"
    assert "PSN_FBXLoad_Render" in mod.NODE_CLASS_MAPPINGS
    assert "PSN_FBXLoad_Render" in mod.NODE_DISPLAY_NAME_MAPPINGS


def test_input_types():
    it = mod.PSN_FBXLoad_Render.INPUT_TYPES()
    assert "required" in it
    req = it["required"]
    assert "fbx_path" in req
    assert "render_mode" in req
    assert "camera_angle" in req
    # render_mode should be a tuple of valid modes
    assert isinstance(req["render_mode"], tuple)
    # The combo value is a tuple of strings
    combo = req["render_mode"]
    assert "clay" in combo[0]
    assert "shaded" in combo[0]


def test_return_types():
    assert mod.PSN_FBXLoad_Render.RETURN_TYPES == ("IMAGE", "STRING")
    assert mod.PSN_FBXLoad_Render.RETURN_NAMES == ("rendered_image", "mesh_data")
    assert mod.PSN_FBXLoad_Render.FUNCTION == "run"
    assert mod.PSN_FBXLoad_Render.CATEGORY.startswith("ParametricStudio/")


def test_run_basic():
    node = mod.PSN_FBXLoad_Render()
    img, mesh_data = node.run(fbx_path="", render_mode="clay", camera_angle=0.0)
    # img should be a torch tensor [1, H, W, 3] in 0..1
    assert isinstance(img, torch.Tensor)
    assert img.dim() == 4
    assert img.shape[0] == 1
    assert img.shape[3] == 3
    assert img.min() >= 0.0
    assert img.max() <= 1.0
    # mesh_data should be a string
    assert isinstance(mesh_data, str)
    assert len(mesh_data) > 0


def test_run_shaded_mode():
    node = mod.PSN_FBXLoad_Render()
    img, mesh_data = node.run(fbx_path="some/path.fbx", render_mode="shaded", camera_angle=1.57)
    assert isinstance(img, torch.Tensor)
    assert img.shape[0] == 1
    assert img.shape[3] == 3
    assert img.min() >= 0.0
    assert img.max() <= 1.0
    assert isinstance(mesh_data, str)
    assert "some/path.fbx" in mesh_data


def test_run_bad_render_mode_falls_back():
    node = mod.PSN_FBXLoad_Render()
    img, mesh_data = node.run(fbx_path="", render_mode="invalid_mode", camera_angle=0.0)
    # Should not crash; falls back to clay
    assert isinstance(img, torch.Tensor)
    assert img.shape[0] == 1
    assert img.shape[3] == 3


def test_run_different_camera_angles():
    node = mod.PSN_FBXLoad_Render()
    img1, _ = node.run(fbx_path="", render_mode="clay", camera_angle=0.0)
    img2, _ = node.run(fbx_path="", render_mode="clay", camera_angle=3.14)
    # Different angles should produce different images (at least some pixels differ)
    diff = (img1 - img2).abs().sum().item()
    assert diff > 0, "Different camera angles should produce different renders"


def test_no_in_place_modification():
    node = mod.PSN_FBXLoad_Render()
    # Run twice with same inputs; outputs should be independent tensors
    img1, _ = node.run(fbx_path="", render_mode="clay", camera_angle=0.0)
    img2, _ = node.run(fbx_path="", render_mode="clay", camera_angle=0.0)
    # Modify img1, img2 should be unaffected
    img1[0, 0, 0, 0] = 0.999
    assert img2[0, 0, 0, 0] != 0.999 or img2[0, 0, 0, 0].item() < 0.999


def test_image_not_all_black():
    node = mod.PSN_FBXLoad_Render()
    img, _ = node.run(fbx_path="", render_mode="clay", camera_angle=0.0)
    # The rendered image should have some non-background pixels (the cube)
    # Background for clay is 0.15; cube is ~0.85
    max_val = img.max().item()
    assert max_val > 0.2, "Image should contain rendered geometry, not just background"


if __name__ == "__main__":
    test_node_class_exists()
    test_input_types()
    test_return_types()
    test_run_basic()
    test_run_shaded_mode()
    test_run_bad_render_mode_falls_back()
    test_run_different_camera_angles()
    test_no_in_place_modification()
    test_image_not_all_black()
    print("ok")
