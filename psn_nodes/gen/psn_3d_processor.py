"""
PSN 3D Processor Nodes.

This module provides pure-logic nodes for processing 3D mesh data structures.
It does NOT load files or render images using GPU libraries. Instead, it:
1. Validates and normalizes mesh data provided as JSON text.
2. Projects 3D vertices to 2D using orthographic camera math.

Inputs are plain values (strings, numbers, booleans).
Outputs are structured data (JSON strings, lists) suitable for further processing.
"""

import json
import math
from typing import Any, Dict, List, Tuple

def _safe_json_loads(text: str) -> Any:
    """Safely parse JSON, returning None on failure."""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None

def _normalize_mesh(vertices: List[List[float]], faces: List[List[int]]) -> Tuple[List[List[float]], List[List[int]], str]:
    """
    Normalize mesh vertices to center at origin and scale to fit within [-1, 1].
    Returns: (normalized_vertices, faces, status_message)
    """
    if not vertices:
        return vertices, faces, "Empty mesh"
    
    # Calculate bounds
    min_x = min(v[0] for v in vertices)
    max_x = max(v[0] for v in vertices)
    min_y = min(v[1] for v in vertices)
    max_y = max(v[1] for v in vertices)
    min_z = min(v[2] for v in vertices)
    max_z = max(v[2] for v in vertices)
    
    center_x = (min_x + max_x) / 2.0
    center_y = (min_y + max_y) / 2.0
    center_z = (min_z + max_z) / 2.0
    
    # Calculate scale (max extent)
    extent_x = max_x - min_x
    extent_y = max_y - min_y
    extent_z = max_z - min_z
    max_extent = max(extent_x, extent_y, extent_z)
    
    if max_extent == 0:
        scale = 1.0
    else:
        scale = 2.0 / max_extent  # Scale to fit in [-1, 1]
        
    normalized_vertices = []
    for v in vertices:
        nx = (v[0] - center_x) * scale
        ny = (v[1] - center_y) * scale
        nz = (v[2] - center_z) * scale
        normalized_vertices.append([nx, ny, nz])
        
    return normalized_vertices, faces, "Normalized"

def _validate_mesh_structure(vertices: List[List[float]], faces: List[List[int]]) -> Tuple[bool, str]:
    """
    Validate that faces reference valid vertex indices and have correct arity.
    """
    if not vertices:
        return False, "No vertices provided"
        
    num_vertices = len(vertices)
    
    for i, face in enumerate(faces):
        if not isinstance(face, list):
            return False, f"Face {i} is not a list"
        if len(face) < 3:
            return False, f"Face {i} has less than 3 vertices"
        for idx in face:
            if not isinstance(idx, int):
                return False, f"Face {i} contains non-integer index {idx}"
            if idx < 0 or idx >= num_vertices:
                return False, f"Face {i} references out-of-bounds vertex index {idx}"
                
    return True, "Valid"

def _project_orthographic(vertices: List[List[float]], camera_angle_deg: float) -> List[List[float]]:
    """
    Project 3D vertices to 2D using orthographic projection.
    Camera looks down Z-axis, rotated around Y-axis by camera_angle_deg.
    """
    angle_rad = math.radians(camera_angle_deg)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    
    projected = []
    for v in vertices:
        x, y, z = v
        # Rotate around Y axis
        x_rot = x * cos_a - z * sin_a
        y_rot = y
        # Orthographic projection: drop Z (or use it for depth if needed, but here we just take X, Y)
        projected.append([x_rot, y_rot])
        
    return projected

class PSN_3D_Mesh_Validator:
    """
    Validates and normalizes 3D mesh data provided as JSON.
    Input: mesh_json (STRING) - JSON string containing {"vertices": [[x,y,z],...], "faces": [[i,j,k],...]}
    Input: normalize (BOOLEAN) - Whether to normalize the mesh to [-1,1] range.
    Output: mesh_data (STRING) - JSON string of the processed mesh.
    Output: status (STRING) - Validation/normalization status.
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mesh_json": ("STRING", {"default": '{"vertices": [[0,0,0],[1,0,0],[0,1,0],[0,0,1]], "faces": [[0,1,2],[0,1,3],[0,2,3],[1,2,3]]}', "multiline": True}),
                "normalize": ("BOOLEAN", {"default": True}),
            },
            "optional": {}
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("mesh_data", "status")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/3D"

    def run(self, mesh_json: str, normalize: bool) -> Tuple[str, str]:
        data = _safe_json_loads(mesh_json)
        if data is None:
            return json.dumps({"error": "Invalid JSON"}), "Error: Invalid JSON"
        
        if not isinstance(data, dict):
            return json.dumps({"error": "Root must be object"}), "Error: Root must be object"
        
        vertices = data.get("vertices", [])
        faces = data.get("faces", [])
        
        if not isinstance(vertices, list) or not isinstance(faces, list):
            return json.dumps({"error": "Vertices and faces must be lists"}), "Error: Invalid types"
            
        # Basic type check for vertices
        for v in vertices:
            if not isinstance(v, list) or len(v) != 3:
                return json.dumps({"error": "Vertices must be lists of 3 numbers"}), "Error: Invalid vertex format"
            for coord in v:
                if not isinstance(coord, (int, float)):
                    return json.dumps({"error": "Vertex coordinates must be numbers"}), "Error: Non-numeric coordinate"
        
        is_valid, msg = _validate_mesh_structure(vertices, faces)
        if not is_valid:
            return json.dumps({"error": msg}), f"Validation Failed: {msg}"
        
        if normalize:
            vertices, faces, norm_msg = _normalize_mesh(vertices, faces)
            status = f"Valid & {norm_msg}"
        else:
            status = "Valid"
            
        output_data = {
            "vertices": vertices,
            "faces": faces
        }
        
        return json.dumps(output_data), status

class PSN_3D_Camera_Projection:
    """
    Projects 3D mesh vertices to 2D using orthographic camera math.
    Input: mesh_data (STRING) - JSON string from PSN_3D_Mesh_Validator.
    Input: camera_angle (FLOAT) - Rotation angle in degrees around Y-axis.
    Output: projected_2d (STRING) - JSON string of 2D projected vertices.
    Output: bounding_box (STRING) - JSON string of the 2D bounding box.
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mesh_data": ("STRING", {"default": '{"vertices": [[0,0,0],[1,0,0],[0,1,0],[0,0,1]], "faces": [[0,1,2],[0,1,3],[0,2,3],[1,2,3]]}', "multiline": True}),
                "camera_angle": ("FLOAT", {"default": 0.0, "min": -360.0, "max": 360.0, "step": 1.0}),
            },
            "optional": {}
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("projected_2d", "bounding_box")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/3D"

    def run(self, mesh_data: str, camera_angle: float) -> Tuple[str, str]:
        data = _safe_json_loads(mesh_data)
        if data is None or not isinstance(data, dict):
            return json.dumps({"error": "Invalid mesh data"}), json.dumps({"error": "Invalid mesh data"})
            
        vertices = data.get("vertices", [])
        if not vertices:
            return json.dumps([]), json.dumps({"min": [0,0], "max": [0,0]})
            
        projected = _project_orthographic(vertices, camera_angle)
        
        # Calculate bounding box
        if projected:
            min_x = min(p[0] for p in projected)
            max_x = max(p[0] for p in projected)
            min_y = min(p[1] for p in projected)
            max_y = max(p[1] for p in projected)
            bbox = {"min": [min_x, min_y], "max": [max_x, max_y]}
        else:
            bbox = {"min": [0, 0], "max": [0, 0]}
            
        return json.dumps(projected), json.dumps(bbox)

NODE_CLASS_MAPPINGS = {
    "PSN_3D_Mesh_Validator": PSN_3D_Mesh_Validator,
    "PSN_3D_Camera_Projection": PSN_3D_Camera_Projection,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_3D_Mesh_Validator": "3D Mesh Validator & Normalizer",
    "PSN_3D_Camera_Projection": "3D Camera Projection (Ortho)",
}
