import struct
import json
import os
import time

def cube_glb(size=1.0, color=(0.55, 0.42, 1.0)):
    s = size / 2.0
    # 24 vertices: 4 per face, with normals
    # Order: +X, -X, +Y, -Y, +Z, -Z
    # Each face: 4 vertices
    # We define positions and normals explicitly to ensure correct winding and normals.
    
    # Face +X (normal 1,0,0)
    # v0: (s, -s, s), v1: (s, s, s), v2: (s, s, -s), v3: (s, -s, -s)
    # Face -X (normal -1,0,0)
    # v4: (-s, -s, -s), v5: (-s, s, -s), v6: (-s, s, s), v7: (-s, -s, s)
    # Face +Y (normal 0,1,0)
    # v8: (-s, s, s), v9: (s, s, s), v10: (s, s, -s), v11: (-s, s, -s)
    # Face -Y (normal 0,-1,0)
    # v12: (-s, -s, -s), v13: (s, -s, -s), v14: (s, -s, s), v15: (-s, -s, s)
    # Face +Z (normal 0,0,1)
    # v16: (-s, -s, s), v17: (s, -s, s), v18: (s, s, s), v19: (-s, s, s)
    # Face -Z (normal 0,0,-1)
    # v20: (-s, -s, -s), v21: (s, -s, -s), v22: (s, s, -s), v23: (-s, s, -s)
    
    positions = [
        s, -s, s,  s, s, s,  s, s, -s,  s, -s, -s,
        -s, -s, -s, -s, s, -s, -s, s, s, -s, -s, s,
        -s, s, s,  s, s, s,  s, s, -s, -s, s, -s,
        -s, -s, -s, s, -s, -s, s, -s, s, -s, -s, s,
        -s, -s, s,  s, -s, s,  s, s, s, -s, s, s,
        -s, -s, -s, s, -s, -s, s, s, -s, -s, s, -s
    ]
    
    normals = [
        1, 0, 0,  1, 0, 0,  1, 0, 0,  1, 0, 0,
        -1, 0, 0, -1, 0, 0, -1, 0, 0, -1, 0, 0,
        0, 1, 0,  0, 1, 0,  0, 1, 0,  0, 1, 0,
        0, -1, 0, 0, -1, 0, 0, -1, 0, 0, -1, 0,
        0, 0, 1,  0, 0, 1,  0, 0, 1,  0, 0, 1,
        0, 0, -1, 0, 0, -1, 0, 0, -1, 0, 0, -1
    ]
    
    # Indices for 12 triangles (2 per face)
    # Face +X: 0,1,2 0,2,3
    # Face -X: 4,5,6 4,6,7
    # Face +Y: 8,9,10 8,10,11
    # Face -Y: 12,13,14 12,14,15
    # Face +Z: 16,17,18 16,18,19
    # Face -Z: 20,21,22 20,22,23
    indices = [
        0, 1, 2, 0, 2, 3,
        4, 5, 6, 4, 6, 7,
        8, 9, 10, 8, 10, 11,
        12, 13, 14, 12, 14, 15,
        16, 17, 18, 16, 18, 19,
        20, 21, 22, 20, 22, 23
    ]
    
    # Calculate min/max for positions
    min_pos = [min(positions[i::3]) for i in range(3)]
    max_pos = [max(positions[i::3]) for i in range(3)]
    
    # Pack binary data
    # Positions: 24 * 3 * 4 = 288 bytes
    # Normals: 24 * 3 * 4 = 288 bytes
    # Indices: 36 * 2 = 72 bytes
    pos_bytes = struct.pack('<72f', *positions)
    norm_bytes = struct.pack('<72f', *normals)
    idx_bytes = struct.pack('<36H', *indices)
    
    bin_data = pos_bytes + norm_bytes + idx_bytes
    bin_len = len(bin_data)
    
    # JSON structure
    gltf = {
        "asset": {"version": "2.0", "generator": "Parametric Studio"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0}],
        "meshes": [{
            "primitives": [{
                "attributes": {"POSITION": 0, "NORMAL": 1},
                "indices": 2,
                "material": 0
            }]
        }],
        "materials": [{
            "pbrMetallicRoughness": {
                "baseColorFactor": [color[0], color[1], color[2], 1.0],
                "metallicFactor": 0.0,
                "roughnessFactor": 1.0
            }
        }],
        "accessors": [
            {
                "bufferView": 0,
                "componentType": 5126, # FLOAT
                "count": 24,
                "type": "VEC3",
                "min": min_pos,
                "max": max_pos
            },
            {
                "bufferView": 1,
                "componentType": 5126, # FLOAT
                "count": 24,
                "type": "VEC3"
            },
            {
                "bufferView": 2,
                "componentType": 5123, # UNSIGNED_SHORT
                "count": 36,
                "type": "SCALAR"
            }
        ],
        "bufferViews": [
            {
                "buffer": 0,
                "byteOffset": 0,
                "byteLength": len(pos_bytes),
                "target": 34962 # ARRAY_BUFFER
            },
            {
                "buffer": 0,
                "byteOffset": len(pos_bytes),
                "byteLength": len(norm_bytes),
                "target": 34962 # ARRAY_BUFFER
            },
            {
                "buffer": 0,
                "byteOffset": len(pos_bytes) + len(norm_bytes),
                "byteLength": len(idx_bytes),
                "target": 34963 # ELEMENT_ARRAY_BUFFER
            }
        ],
        "buffers": [{
            "byteLength": bin_len
        }]
    }
    
    json_bytes = json.dumps(gltf, separators=(',', ':')).encode('utf-8')
    
    # Pad JSON with spaces to 4-byte alignment
    json_padded_len = (len(json_bytes) + 3) & ~3
    json_padded = json_bytes + b' ' * (json_padded_len - len(json_bytes))
    
    # Pad BIN with zeros to 4-byte alignment
    bin_padded_len = (bin_len + 3) & ~3
    bin_padded = bin_data + b'\0' * (bin_padded_len - bin_len)
    
    total_len = 12 + 8 + json_padded_len + 8 + bin_padded_len
    
    # GLB Header
    header = struct.pack('<4sII', b'glTF', 2, total_len)
    
    # JSON Chunk
    json_chunk_header = struct.pack('<II', json_padded_len, 0x4E4F534A) # 'JSON'
    json_chunk = json_chunk_header + json_padded
    
    # BIN Chunk
    bin_chunk_header = struct.pack('<II', bin_padded_len, 0x004E4942) # 'BIN\0'
    bin_chunk = bin_chunk_header + bin_padded
    
    return header + json_chunk + bin_chunk

def inspect_glb(data: bytes) -> dict:
    result = {
        "ok": True,
        "problems": [],
        "meshes": 0,
        "primitives": 0,
        "vertices": 0,
        "triangles": 0,
        "bytes": len(data)
    }
    
    if len(data) < 12:
        result["ok"] = False
        result["problems"].append("File too short for GLB header")
        return result
        
    magic, version, total_length = struct.unpack_from('<4sII', data, 0)
    
    if magic != b'glTF':
        result["ok"] = False
        result["problems"].append("Invalid magic number")
        return result
        
    if version != 2:
        result["ok"] = False
        result["problems"].append(f"Unsupported version: {version}")
        return result
        
    if total_length != len(data):
        result["ok"] = False
        result["problems"].append(f"Length mismatch: header says {total_length}, actual {len(data)}")
        return result
        
    offset = 12
    
    # Parse JSON Chunk
    if offset + 8 > len(data):
        result["ok"] = False
        result["problems"].append("Truncated JSON chunk header")
        return result
        
    json_len, json_type = struct.unpack_from('<II', data, offset)
    offset += 8
    
    if json_type != 0x4E4F534A:
        result["ok"] = False
        result["problems"].append("Invalid JSON chunk type")
        return result
        
    if offset + json_len > len(data):
        result["ok"] = False
        result["problems"].append("Truncated JSON chunk data")
        return result
        
    json_data = data[offset:offset + json_len]
    offset += json_len
    
    # Align to 4 bytes
    offset = (offset + 3) & ~3
    
    # Parse BIN Chunk
    if offset + 8 > len(data):
        result["ok"] = False
        result["problems"].append("Truncated BIN chunk header")
        return result
        
    bin_len, bin_type = struct.unpack_from('<II', data, offset)
    offset += 8
    
    if bin_type != 0x004E4942:
        result["ok"] = False
        result["problems"].append("Invalid BIN chunk type")
        return result
        
    if offset + bin_len > len(data):
        result["ok"] = False
        result["problems"].append("Truncated BIN chunk data")
        return result
        
    bin_data = data[offset:offset + bin_len]
    
    try:
        gltf = json.loads(json_data)
    except json.JSONDecodeError as e:
        result["ok"] = False
        result["problems"].append(f"Invalid JSON: {e}")
        return result
        
    # Validate structure
    if "meshes" not in gltf:
        result["ok"] = False
        result["problems"].append("Missing meshes")
        return result
        
    if "accessors" not in gltf:
        result["ok"] = False
        result["problems"].append("Missing accessors")
        return result
        
    if "bufferViews" not in gltf:
        result["ok"] = False
        result["problems"].append("Missing bufferViews")
        return result
        
    if "buffers" not in gltf:
        result["ok"] = False
        result["problems"].append("Missing buffers")
        return result
        
    # Check buffer length
    if len(gltf["buffers"]) > 0:
        buf_len = gltf["buffers"][0].get("byteLength", 0)
        if buf_len > bin_len:
            result["ok"] = False
            result["problems"].append("Buffer length exceeds BIN chunk size")
            return result
            
    # Count meshes and primitives
    meshes = gltf.get("meshes", [])
    result["meshes"] = len(meshes)
    
    total_vertices = 0
    total_triangles = 0
    
    for mesh in meshes:
        primitives = mesh.get("primitives", [])
        result["primitives"] += len(primitives)
        
        for prim in primitives:
            attrs = prim.get("attributes", {})
            pos_accessor_idx = attrs.get("POSITION")
            
            if pos_accessor_idx is not None:
                if pos_accessor_idx >= len(gltf["accessors"]):
                    result["ok"] = False
                    result["problems"].append("Invalid POSITION accessor index")
                    return result
                    
                accessor = gltf["accessors"][pos_accessor_idx]
                count = accessor.get("count", 0)
                total_vertices += count
                
                # Validate bufferView
                bv_idx = accessor.get("bufferView")
                if bv_idx is not None:
                    if bv_idx >= len(gltf["bufferViews"]):
                        result["ok"] = False
                        result["problems"].append("Invalid bufferView index")
                        return result
                        
                    bv = gltf["bufferViews"][bv_idx]
                    byte_offset = bv.get("byteOffset", 0)
                    byte_length = bv.get("byteLength", 0)
                    
                    # Check if bufferView fits in bin
                    if byte_offset + byte_length > bin_len:
                        result["ok"] = False
                        result["problems"].append("BufferView exceeds BIN chunk size")
                        return result
                        
            idx_accessor_idx = prim.get("indices")
            if idx_accessor_idx is not None:
                if idx_accessor_idx >= len(gltf["accessors"]):
                    result["ok"] = False
                    result["problems"].append("Invalid indices accessor index")
                    return result
                    
                accessor = gltf["accessors"][idx_accessor_idx]
                count = accessor.get("count", 0)
                total_triangles += count // 3
                
                # Validate bufferView
                bv_idx = accessor.get("bufferView")
                if bv_idx is not None:
                    if bv_idx >= len(gltf["bufferViews"]):
                        result["ok"] = False
                        result["problems"].append("Invalid bufferView index for indices")
                        return result
                        
                    bv = gltf["bufferViews"][bv_idx]
                    byte_offset = bv.get("byteOffset", 0)
                    byte_length = bv.get("byteLength", 0)
                    
                    if byte_offset + byte_length > bin_len:
                        result["ok"] = False
                        result["problems"].append("Indices BufferView exceeds BIN chunk size")
                        return result
                        
    result["vertices"] = total_vertices
    result["triangles"] = total_triangles
    
    return result

def list_glb(root, limit=50):
    results = []
    root = os.path.abspath(root)
    
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        # Filter out symlinked directories to prevent traversal out of root
        dirnames[:] = [d for d in dirnames if not os.path.islink(os.path.join(dirpath, d))]
        
        for filename in filenames:
            if not filename.lower().endswith('.glb'):
                continue
                
            filepath = os.path.join(dirpath, filename)
            
            # Skip symlinks
            if os.path.islink(filepath):
                continue
                
            # Ensure file is within root
            real_path = os.path.realpath(filepath)
            if not real_path.startswith(root + os.sep) and real_path != root:
                continue
                
            try:
                stat = os.stat(filepath)
                rel_path = os.path.relpath(filepath, root)
                results.append({
                    "path": rel_path,
                    "bytes": stat.st_size,
                    "mtime": stat.st_mtime
                })
            except OSError:
                continue
                
    # Sort by mtime descending
    results.sort(key=lambda x: x["mtime"], reverse=True)
    
    return results[:limit]


def knot_glb():
    """Built-in sample: a polished gold torus knot around a glowing emerald core, a real PBR glTF made from numbers."""
    import numpy as np
    def tube(P, r, V=20):
        T = np.roll(P, -1, 0) - np.roll(P, 1, 0); T /= np.linalg.norm(T, axis=1, keepdims=True); N = np.cross(T, [0.31, 0.87, 0.38]); N /= np.linalg.norm(N, axis=1, keepdims=True); B = np.cross(T, N); a = np.linspace(0, 2 * np.pi, V, endpoint=False); n = (N[:, None] * np.cos(a)[None, :, None] + B[:, None] * np.sin(a)[None, :, None]); U = len(P)
        i, j = np.meshgrid(np.arange(U), np.arange(V), indexing="ij"); i2, j2 = (i + 1) % U, (j + 1) % V; q = lambda a, b: a * V + b; f = np.stack([q(i, j), q(i2, j), q(i, j2), q(i, j2), q(i2, j), q(i2, j2)], -1).reshape(-1)
        return (P[:, None] + r * n).reshape(-1, 3), n.reshape(-1, 3), f
    t = np.linspace(0, 2 * np.pi, 480, endpoint=False); p, q = 2, 3; R = 2 + np.cos(q * t); knot = tube(np.stack([R * np.cos(p * t), R * np.sin(p * t), np.sin(q * t)], 1) * 0.42, 0.13)
    lat = np.linspace(0.001, np.pi - 0.001, 40); lon = np.linspace(0, 2 * np.pi, 72, endpoint=False); la, lo = np.meshgrid(lat, lon, indexing="ij"); n = np.stack([np.sin(la) * np.cos(lo), np.cos(la), np.sin(la) * np.sin(lo)], -1).reshape(-1, 3); i, j = np.meshgrid(np.arange(39), np.arange(72), indexing="ij"); j2 = (j + 1) % 72; g = lambda a, b: a * 72 + b; core = (n * 0.34, n, np.stack([g(i, j), g(i + 1, j), g(i, j2), g(i, j2), g(i + 1, j), g(i + 1, j2)], -1).reshape(-1))
    blob, views, acc, prims = b"", [], [], []
    def add(arr, ctype, kind, target):
        nonlocal blob
        data = arr.astype("<f4" if ctype == 5126 else "<u4").tobytes(); views.append({"buffer": 0, "byteOffset": len(blob), "byteLength": len(data), "target": target}); blob += data + b"\0" * (-len(data) % 4); a = {"bufferView": len(views) - 1, "componentType": ctype, "count": len(arr), "type": kind}
        if kind == "VEC3": a.update(min=arr.min(0).tolist(), max=arr.max(0).tolist())
        acc.append(a); return len(acc) - 1
    for m, (v, nr, f) in enumerate((knot, core)): prims.append({"attributes": {"POSITION": add(v, 5126, "VEC3", 34962), "NORMAL": add(nr, 5126, "VEC3", 34962)}, "indices": add(f, 5125, "SCALAR", 34963), "material": m})
    gltf = {"asset": {"version": "2.0", "generator": "Parametric Studio"}, "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"mesh": 0, "name": "Parametric knot"}], "meshes": [{"primitives": prims}], "materials": [{"name": "gold", "pbrMetallicRoughness": {"baseColorFactor": [0.96, 0.74, 0.1, 1], "metallicFactor": 1.0, "roughnessFactor": 0.24}}, {"name": "emerald", "pbrMetallicRoughness": {"baseColorFactor": [0.05, 0.8, 0.42, 1], "metallicFactor": 0.1, "roughnessFactor": 0.12}, "emissiveFactor": [0.03, 0.55, 0.28]}], "accessors": acc, "bufferViews": views, "buffers": [{"byteLength": len(blob)}]}
    j_ = json.dumps(gltf, separators=(",", ":")).encode(); j_ += b" " * (-len(j_) % 4)
    return struct.pack("<III", 0x46546C67, 2, 28 + len(j_) + len(blob)) + struct.pack("<II", len(j_), 0x4E4F534A) + j_ + struct.pack("<II", len(blob), 0x004E4942) + blob
