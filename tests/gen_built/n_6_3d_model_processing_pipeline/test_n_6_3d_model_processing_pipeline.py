import torch
import n_6_3d_model_processing_pipeline as mod


def test_module_structure():
    """Check module-level mappings and node class attributes."""
    assert hasattr(mod, "NODE_CLASS_MAPPINGS"), "NODE_CLASS_MAPPINGS missing"
    assert hasattr(mod, "NODE_DISPLAY_NAME_MAPPINGS"), "NODE_DISPLAY_NAME_MAPPINGS missing"
    assert "PSN_Load_3D_Mesh" in mod.NODE_CLASS_MAPPINGS
    assert "PSN_3D_To_Image" in mod.NODE_CLASS_MAPPINGS
    assert mod.NODE_DISPLAY_NAME_MAPPINGS["PSN_Load_3D_Mesh"] == "Load 3D Mesh"
    assert mod.NODE_DISPLAY_NAME_MAPPINGS["PSN_3D_To_Image"] == "3D Mesh to Image"

    # Check INPUT_TYPES classmethod
    it = mod.PSN_Load_3D_Mesh.INPUT_TYPES()
    assert "required" in it
    assert "mesh_path" in it["required"]
    assert "normalize" in it["required"]

    it2 = mod.PSN_3D_To_Image.INPUT_TYPES()
    assert "mesh" in it2["required"]
    assert "camera_angle" in it2["required"]
    assert "lighting" in it2["required"]

    # Check RETURN_TYPES and FUNCTION
    assert mod.PSN_Load_3D_Mesh.RETURN_TYPES == ("MESH", "IMAGE")
    assert mod.PSN_Load_3D_Mesh.RETURN_NAMES == ("mesh", "uv_map")
    assert mod.PSN_Load_3D_Mesh.FUNCTION == "run"
    assert mod.PSN_Load_3D_Mesh.CATEGORY == "ParametricStudio/3D"

    assert mod.PSN_3D_To_Image.RETURN_TYPES == ("IMAGE",)
    assert mod.PSN_3D_To_Image.RETURN_NAMES == ("image",)
    assert mod.PSN_3D_To_Image.FUNCTION == "run"
    assert mod.PSN_3D_To_Image.CATEGORY == "ParametricStudio/3D"


def test_load_cube_mesh():
    """Load default cube and verify vertices/faces."""
    node = mod.PSN_Load_3D_Mesh()
    mesh, uv = node.run("cube", True)

    assert isinstance(mesh, dict)
    assert "vertices" in mesh
    assert "faces" in mesh

    v = mesh["vertices"]
    f = mesh["faces"]
    assert v.shape == (8, 3), f"Expected 8 vertices, got {v.shape}"
    assert f.shape == (12, 3), f"Expected 12 faces, got {f.shape}"
    assert v.dtype == torch.float32
    assert f.dtype == torch.long

    # After normalization, max |coord| should be 1
    assert v.abs().max().item() <= 1.0 + 1e-6
    # Center should be near origin
    assert v.mean(dim=0).abs().max().item() < 1e-5

    # UV map should be [1, 64, 64, 4]
    assert uv.shape == (1, 64, 64, 4), f"Expected UV shape (1,64,64,4), got {uv.shape}"
    assert uv.min().item() >= 0.0
    assert uv.max().item() <= 1.0


def test_load_obj_text():
    """Load a simple triangle from inline OBJ text."""
    obj_text = "obj:v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3"
    node = mod.PSN_Load_3D_Mesh()
    mesh, uv = node.run(obj_text, False)

    v = mesh["vertices"]
    f = mesh["faces"]
    assert v.shape == (3, 3)
    assert f.shape == (1, 3)
    # Without normalization, vertices should be as given
    assert v[0].tolist() == [0.0, 0.0, 0.0]
    assert v[1].tolist() == [1.0, 0.0, 0.0]
    assert v[2].tolist() == [0.0, 1.0, 0.0]
    assert f[0].tolist() == [0, 1, 2]


def test_render_cube():
    """Render a cube and verify image properties."""
    load_node = mod.PSN_Load_3D_Mesh()
    mesh, _ = load_node.run("cube", True)

    render_node = mod.PSN_3D_To_Image()
    img = render_node.run(mesh, 0.0, "studio")[0]

    assert img.shape == (1, 128, 128, 3), f"Expected (1,128,128,3), got {img.shape}"
    assert img.dtype == torch.float32
    assert img.min().item() >= 0.0
    assert img.max().item() <= 1.0

    # Image should not be entirely black (some pixels rendered)
    assert img.sum().item() > 0.0, "Rendered image is entirely black"


def test_render_different_angles():
    """Different camera angles should produce different images."""
    load_node = mod.PSN_Load_3D_Mesh()
    mesh, _ = load_node.run("cube", True)

    render_node = mod.PSN_3D_To_Image()
    img0 = render_node.run(mesh, 0.0, "studio")[0]
    img45 = render_node.run(mesh, 0.7854, "studio")[0]  # ~45 degrees

    # Images should differ
    diff = (img0 - img45).abs().sum().item()
    assert diff > 0.0, "Different camera angles produced identical images"


def test_render_lighting_modes():
    """Studio and natural lighting should produce different images."""
    load_node = mod.PSN_Load_3D_Mesh()
    mesh, _ = load_node.run("cube", True)

    render_node = mod.PSN_3D_To_Image()
    img_studio = render_node.run(mesh, 0.0, "studio")[0]
    img_natural = render_node.run(mesh, 0.0, "natural")[0]

    diff = (img_studio - img_natural).abs().sum().item()
    assert diff > 0.0, "Different lighting modes produced identical images"


def test_bad_mesh_input():
    """Invalid mesh inputs should raise errors."""
    render_node = mod.PSN_3D_To_Image()

    # Not a dict
    try:
        render_node.run("not a dict", 0.0, "studio")
        assert False, "Should have raised TypeError"
    except TypeError:
        pass

    # Missing keys
    try:
        render_node.run({"vertices": torch.zeros(4, 3)}, 0.0, "studio")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass

    # Bad vertex shape
    try:
        render_node.run({"vertices": torch.zeros(4, 2), "faces": torch.zeros(1, 3, dtype=torch.long)}, 0.0, "studio")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass

    # Out-of-range face indices
    try:
        render_node.run({"vertices": torch.zeros(4, 3), "faces": torch.tensor([[0, 1, 99]], dtype=torch.long)}, 0.0, "studio")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_bad_lighting():
    """Invalid lighting mode should raise ValueError."""
    load_node = mod.PSN_Load_3D_Mesh()
    mesh, _ = load_node.run("cube", True)

    render_node = mod.PSN_3D_To_Image()
    try:
        render_node.run(mesh, 0.0, "invalid_lighting")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_normalize_false():
    """With normalize=False, vertices should not be centered/scaled."""
    obj_text = "obj:v 10 20 30\nv 11 20 30\nv 10 21 30\nf 1 2 3"
    node = mod.PSN_Load_3D_Mesh()
    mesh, _ = node.run(obj_text, False)
    v = mesh["vertices"]
    # Vertices should be as given (not normalized)
    assert v[0].tolist() == [10.0, 20.0, 30.0]
    assert v[1].tolist() == [11.0, 20.0, 30.0]
    assert v[2].tolist() == [10.0, 21.0, 30.0]


def test_no_in_place_modification():
    """Ensure inputs are not modified in place."""
    v_orig = torch.tensor([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    f_orig = torch.tensor([[0, 1, 2], [0, 1, 3], [0, 2, 3], [1, 2, 3]], dtype=torch.long)
    v_copy = v_orig.clone()
    f_copy = f_orig.clone()

    mesh = {"vertices": v_orig, "faces": f_orig}
    render_node = mod.PSN_3D_To_Image()
    render_node.run(mesh, 0.0, "studio")

    assert torch.equal(v_orig, v_copy), "Vertices were modified in place"
    assert torch.equal(f_orig, f_copy), "Faces were modified in place"


if __name__ == "__main__":
    test_module_structure()
    test_load_cube_mesh()
    test_load_obj_text()
    test_render_cube()
    test_render_different_angles()
    test_render_lighting_modes()
    test_bad_mesh_input()
    test_bad_lighting()
    test_normalize_false()
    test_no_in_place_modification()
    print("ok")
