import torch

CAT = "ParametricStudio/3D"

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _as_tensor(x):
    if isinstance(x, torch.Tensor):
        return x
    return torch.as_tensor(x, dtype=torch.float32)


def _mesh_from_dict(m):
    """Validate/normalize a MESH dict. Returns (vertices, faces) as float32/long tensors."""
    if not isinstance(m, dict):
        raise TypeError("MESH must be a dict with 'vertices' and 'faces' keys")
    if "vertices" not in m or "faces" not in m:
        raise ValueError("MESH dict must contain 'vertices' and 'faces'")
    v = _as_tensor(m["vertices"]).float()
    f = _as_tensor(m["faces"]).long()
    if v.dim() != 2 or v.shape[1] != 3:
        raise ValueError("vertices must be [N,3]")
    if f.dim() != 2 or f.shape[1] != 3:
        raise ValueError("faces must be [M,3]")
    if f.numel() and (f.min() < 0 or f.max() >= v.shape[0]):
        raise ValueError("face indices out of range")
    return v, f


def _normalize_mesh(v, f):
    """Center at origin and scale so max |coord| == 1. Returns new tensors."""
    center = v.mean(dim=0)
    v2 = v - center
    scale = v2.abs().max()
    if scale > 0:
        v2 = v2 / scale
    return v2, f


def _parse_obj_text(text):
    """Minimal OBJ parser: v / f lines. Returns (vertices, faces) tensors."""
    verts = []
    faces = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if parts[0] == "v" and len(parts) >= 4:
            try:
                verts.append([float(parts[1]), float(parts[2]), float(parts[3])])
            except ValueError:
                continue
        elif parts[0] == "f" and len(parts) >= 4:
            idx = []
            ok = True
            for p in parts[1:4]:
                first = p.split("/")[0]
                try:
                    idx.append(int(first) - 1)
                except ValueError:
                    ok = False
                    break
            if ok:
                faces.append(idx)
    if not verts or not faces:
        raise ValueError("OBJ text contains no valid vertices/faces")
    v = torch.tensor(verts, dtype=torch.float32)
    f = torch.tensor(faces, dtype=torch.long)
    return v, f


def _cube_mesh():
    """Unit cube centered at origin, 8 verts, 12 triangles."""
    v = torch.tensor([
        [-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],
        [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1],
    ], dtype=torch.float32)
    f = torch.tensor([
        [0, 2, 1], [0, 3, 2],
        [4, 5, 6], [4, 6, 7],
        [0, 1, 5], [0, 5, 4],
        [2, 3, 7], [2, 7, 6],
        [0, 4, 7], [0, 7, 3],
        [1, 2, 6], [1, 6, 5],
    ], dtype=torch.long)
    return v, f


def _uv_from_vertices(v):
    """Planar (x,y) UV projection -> [1, H, W, 4] float tensor in 0..1."""
    H = W = 64
    xs = torch.linspace(0.0, 1.0, W)
    ys = torch.linspace(0.0, 1.0, H)
    gx, gy = torch.meshgrid(xs, ys, indexing="xy")
    img = torch.zeros(1, H, W, 4, dtype=torch.float32)
    img[0, :, :, 0] = gx
    img[0, :, :, 1] = gy
    img[0, :, :, 3] = 1.0
    return img


def _render_mesh(v, f, camera_angle, lighting, size=128):
    """Simple orthographic projection of a triangle mesh to a [1, size, size, 3] image.

    Uses painter's algorithm with flat shading. CPU only.
    """
    H = W = size
    img = torch.zeros(1, H, W, 3, dtype=torch.float32)

    ca = torch.cos(torch.tensor(camera_angle, dtype=torch.float32))
    sa = torch.sin(torch.tensor(camera_angle, dtype=torch.float32))
    R = torch.tensor([
        [ca, 0, sa],
        [0, 1, 0],
        [-sa, 0, ca],
    ], dtype=torch.float32)
    vr = v @ R.T

    vmin = vr.min(dim=0).values
    vmax = vr.max(dim=0).values
    span = vmax - vmin
    span[span == 0] = 1.0
    vr = (vr - vmin) / span * 2.0 - 1.0

    if lighting == "studio":
        light_dir = torch.tensor([0.0, 0.0, 1.0], dtype=torch.float32)
        base_color = torch.tensor([0.8, 0.8, 0.85], dtype=torch.float32)
    else:
        light_dir = torch.tensor([0.5, 0.7, 0.5], dtype=torch.float32)
        base_color = torch.tensor([0.9, 0.85, 0.75], dtype=torch.float32)
    light_dir = light_dir / light_dir.norm()

    v0 = vr[f[:, 0]]
    v1 = vr[f[:, 1]]
    v2 = vr[f[:, 2]]
    e1 = v1 - v0
    e2 = v2 - v0
    normals = torch.cross(e1, e2, dim=-1)
    norms = normals.norm(dim=-1, keepdim=True)
    norms[norms == 0] = 1.0
    normals = normals / norms

    flip = normals[:, 2] < 0
    normals[flip] = -normals[flip]
    f = f.clone()
    f[flip] = f[flip].flip(1)

    diff = (normals * light_dir).sum(dim=-1).clamp(0, 1)
    ambient = 0.3
    shade = (ambient + (1 - ambient) * diff).unsqueeze(-1)
    face_color = (base_color.unsqueeze(0) * shade)

    def to_px(x, y):
        col = ((x + 1) / 2 * (W - 1)).long()
        row = ((1 - y) / 2 * (H - 1)).long()
        col = col.clamp(0, W - 1)
        row = row.clamp(0, H - 1)
        return row, col

    face_z = vr[f, 2].mean(dim=1)
    order = torch.argsort(face_z, dim=0, descending=False)

    depth = torch.full((H, W), float("inf"), dtype=torch.float32)

    for fi in order.tolist():
        tri = f[fi]
        p0 = vr[tri[0]]
        p1 = vr[tri[1]]
        p2 = vr[tri[2]]
        z_avg = face_z[fi].item()

        rows, cols = to_px(
            torch.stack([p0[0], p1[0], p2[0]]),
            torch.stack([p0[1], p1[1], p2[1]]),
        )
        rmin, rmax = rows.min().item(), rows.max().item()
        cmin, cmax = cols.min().item(), cols.max().item()

        col = face_color[fi]

        for r in range(rmin, rmax + 1):
            for c in range(cmin, cmax + 1):
                px = c / (W - 1) * 2 - 1
                py = 1 - r / (H - 1) * 2

                def sign(p1_, p2_, p3_):
                    return (p1_[0] - p3_[0]) * (p2_[1] - p3_[1]) - (p2_[0] - p3_[0]) * (p1_[1] - p3_[1])

                d1 = sign((px, py), (p0[0].item(), p0[1].item()), (p1[0].item(), p1[1].item()))
                d2 = sign((px, py), (p1[0].item(), p1[1].item()), (p2[0].item(), p2[1].item()))
                d3 = sign((px, py), (p2[0].item(), p2[1].item()), (p0[0].item(), p0[1].item()))
                has_neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
                has_pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
                if not (has_neg and has_pos):
                    if z_avg < depth[r, c]:
                        depth[r, c] = z_avg
                        img[0, r, c, 0] = col[0]
                        img[0, r, c, 1] = col[1]
                        img[0, r, c, 2] = col[2]

    return img


# ---------------------------------------------------------------------------
# Node 1: PSN_Load_3D_Mesh
# ---------------------------------------------------------------------------

class PSN_Load_3D_Mesh:
    """Load a 3D mesh from inline OBJ text or generate a default cube.

    Since file I/O is not permitted, `mesh_path` is interpreted as:
    - If it starts with "obj:" the remainder is parsed as inline OBJ text.
    - If it is "cube" a unit cube is generated.
    - Otherwise a default cube is used.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mesh_path": ("STRING", {"default": "cube", "multiline": False}),
                "normalize": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("MESH", "IMAGE")
    RETURN_NAMES = ("mesh", "uv_map")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, mesh_path, normalize):
        if mesh_path is None:
            raise ValueError("mesh_path must not be None")
        path = str(mesh_path).strip()

        if path.startswith("obj:"):
            text = path[4:]
            v, f = _parse_obj_text(text)
        elif path.lower() == "cube":
            v, f = _cube_mesh()
        else:
            try:
                v, f = _parse_obj_text(path)
            except Exception:
                v, f = _cube_mesh()

        if normalize:
            v, f = _normalize_mesh(v, f)

        mesh = {"vertices": v, "faces": f}
        uv = _uv_from_vertices(v)
        return (mesh, uv)


# ---------------------------------------------------------------------------
# Node 2: PSN_3D_To_Image
# ---------------------------------------------------------------------------

class PSN_3D_To_Image:
    """Render a 3D mesh to a 2D image using simple orthographic projection
    with flat shading and painter's algorithm. CPU only.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mesh": ("MESH",),
                "camera_angle": ("FLOAT", {"default": 0.0, "min": -3.14159, "max": 3.14159, "step": 0.01}),
                "lighting": (["studio", "natural"], {"default": "studio"}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, mesh, camera_angle, lighting):
        v, f = _mesh_from_dict(mesh)
        if lighting not in ("studio", "natural"):
            raise ValueError("lighting must be 'studio' or 'natural'")
        img = _render_mesh(v, f, float(camera_angle), lighting, size=128)
        return (img,)


# ---------------------------------------------------------------------------
# Mappings
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_Load_3D_Mesh": PSN_Load_3D_Mesh,
    "PSN_3D_To_Image": PSN_3D_To_Image,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Load_3D_Mesh": "Load 3D Mesh",
    "PSN_3D_To_Image": "3D Mesh to Image",
}
