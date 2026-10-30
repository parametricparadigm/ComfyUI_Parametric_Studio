import pytest
import json
import math
from psn_nodes.gen.psn_3d_processor import PSN_3D_Mesh_Validator, PSN_3D_Camera_Projection

def test_validator_valid_cube():
    """Test that a valid cube mesh is accepted and normalized."""
    node = PSN_3D_Mesh_Validator()
    # Simple cube vertices
    vertices = [
        [0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
        [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]
    ]
    faces = [
        [0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 5, 4], [2, 3, 7, 6], [1, 2, 6, 5], [0, 3, 7, 4]
    ]
    mesh_json = json.dumps({"vertices": vertices, "faces": faces})
    
    mesh_data, status = node.run(mesh_json, normalize=True)
    
    assert "Error" not in status
    assert "Normalized" in status
    
    data = json.loads(mesh_data)
    assert len(data["vertices"]) == 8
    assert len(data["faces"]) == 6
    
    # Check normalization: max extent should be 1.0
    max_coord = max(max(abs(v[0]), abs(v[1]), abs(v[2])) for v in data["vertices"])
    assert abs(max_coord - 1.0) < 1e-5

def test_validator_invalid_face_index():
    """Test that a face referencing a non-existent vertex fails."""
    node = PSN_3D_Mesh_Validator()
    vertices = [[0, 0, 0], [1, 0, 0], [0, 1, 0]]
    faces = [[0, 1, 5]]  # Index 5 does not exist
    mesh_json = json.dumps({"vertices": vertices, "faces": faces})
    
    mesh_data, status = node.run(mesh_json, normalize=False)
    
    assert "Validation Failed" in status
    data = json.loads(mesh_data)
    assert "error" in data

def test_validator_invalid_json():
    """Test that invalid JSON input is handled gracefully."""
    node = PSN_3D_Mesh_Validator()
    mesh_json = "not a json"
    
    mesh_data, status = node.run(mesh_json, normalize=False)
    
    assert "Error" in status
    data = json.loads(mesh_data)
    assert "error" in data

def test_validator_empty_mesh():
    """Test that an empty mesh is handled."""
    node = PSN_3D_Mesh_Validator()
    mesh_json = json.dumps({"vertices": [], "faces": []})
    
    mesh_data, status = node.run(mesh_json, normalize=True)
    
    # The validator should reject empty meshes because _validate_mesh_structure returns False for empty vertices
    assert "Validation Failed" in status
    data = json.loads(mesh_data)
    assert "error" in data

def test_projection_orthographic_front():
    """Test orthographic projection from the front (angle 0)."""
    node = PSN_3D_Camera_Projection()
    # Simple triangle in XY plane
    vertices = [[0, 0, 0], [1, 0, 0], [0, 1, 0]]
    mesh_data = json.dumps({"vertices": vertices, "faces": [[0, 1, 2]]})
    
    projected_str, bbox_str = node.run(mesh_data, camera_angle=0.0)
    projected = json.loads(projected_str)
    bbox = json.loads(bbox_str)
    
    # At angle 0, Z is ignored, X and Y remain
    assert projected[0] == [0, 0]
    assert projected[1] == [1, 0]
    assert projected[2] == [0, 1]
    
    assert bbox["min"] == [0, 0]
    assert bbox["max"] == [1, 1]

def test_projection_orthographic_rotated():
    """Test orthographic projection with rotation."""
    node = PSN_3D_Camera_Projection()
    # Point on Z axis
    vertices = [[0, 0, 1]]
    mesh_data = json.dumps({"vertices": vertices, "faces": []})
    
    # Rotate 90 degrees around Y. 
    # x' = x*cos(90) - z*sin(90) = 0 - 1 = -1
    # y' = y = 0
    projected_str, _ = node.run(mesh_data, camera_angle=90.0)
    projected = json.loads(projected_str)
    
    assert abs(projected[0][0] - (-1.0)) < 1e-5
    assert abs(projected[0][1] - 0.0) < 1e-5

def test_projection_invalid_input():
    """Test projection with invalid mesh data."""
    node = PSN_3D_Camera_Projection()
    mesh_data = "invalid json"
    
    projected_str, bbox_str = node.run(mesh_data, camera_angle=0.0)
    projected = json.loads(projected_str)
    
    assert "error" in projected
