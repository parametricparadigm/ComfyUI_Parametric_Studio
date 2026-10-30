import torch
import torch.nn.functional as F

CAT = "ParametricStudio/VR"


def _s(x):
    """Extract tensor from a ComfyUI LATENT or IMAGE input."""
    if isinstance(x, dict):
        return x["samples"]
    return x


def _out(latent, samples):
    """Wrap samples back into a ComfyUI LATENT dict."""
    return {"samples": samples}


class PSN_VR180_Convert:
    """Convert a rectilinear image to VR180 (cylindrical) projection.

    Warps the input image into a cylindrical projection and crops to the
    180-degree horizontal range, producing a VR180-compatible image.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "fov": ("FLOAT", {"default": 90.0, "min": 10.0, "max": 180.0}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("vr180_image",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, fov):
        """Convert rectilinear image to VR180 cylindrical projection.

        Args:
            image: IMAGE tensor [B, H, W, C] in 0..1
            fov: Horizontal field of view in degrees (10..180)

        Returns:
            vr180_image: IMAGE tensor [B, H_out, W_out, C] in 0..1
        """
        img = _s(image)
        if img.dim() != 4:
            raise ValueError(f"Expected 4D tensor [B,H,W,C], got {img.dim()}D")

        B, H, W, C = img.shape
        device = img.device
        dtype = img.dtype

        # Output dimensions: VR180 is typically 2:1 aspect ratio
        # For a 180-degree horizontal FOV, width = 2 * height
        H_out = H
        W_out = 2 * H

        # Convert FOV to radians
        fov_rad = torch.tensor(fov, dtype=dtype, device=device) * (torch.pi / 180.0)

        # Create output grid in normalized coordinates [-1, 1]
        # For cylindrical projection:
        #   theta = (x / W_out - 0.5) * 2 * pi  (horizontal angle, -pi to pi)
        #   phi = (y / H_out - 0.5) * 2 * pi  (vertical angle, -pi to pi)
        #
        # We want to map each output pixel to a direction in 3D space,
        # then project that direction back to the rectilinear image.

        # Output pixel coordinates (normalized to [-1, 1] for grid_sample)
        # x ranges from -1 to 1 across W_out pixels
        # y ranges from -1 to 1 across H_out pixels
        xs = torch.linspace(-1.0, 1.0, W_out, dtype=dtype, device=device)
        ys = torch.linspace(-1.0, 1.0, H_out, dtype=dtype, device=device)
        grid_x, grid_y = torch.meshgrid(xs, ys, indexing='xy')

        # Convert normalized output coords to angles
        # theta: horizontal angle from -pi to pi (180 degrees total)
        theta = grid_x * torch.pi  # -pi to pi
        # phi: vertical angle, scaled by aspect ratio
        # For a 2:1 image, vertical FOV is 90 degrees (pi/2)
        phi = grid_y * (torch.pi / 2.0)  # -pi/2 to pi/2

        # Direction vectors in 3D (cylindrical projection)
        # x_dir = sin(theta) * cos(phi)
        # y_dir = sin(phi)
        # z_dir = cos(theta) * cos(phi)
        x_dir = torch.sin(theta) * torch.cos(phi)
        y_dir = torch.sin(phi)
        z_dir = torch.cos(theta) * torch.cos(phi)

        # Project to rectilinear image plane
        # The rectilinear image has a horizontal FOV of `fov` degrees
        # focal length f = (W / 2) / tan(fov/2)
        fov_half = fov_rad / 2.0
        f = (W / 2.0) / torch.tan(fov_half)

        # Normalize by z_dir to get image plane coordinates
        # Avoid division by zero
        z_safe = torch.where(torch.abs(z_dir) < 1e-6, torch.full_like(z_dir, 1e-6), z_dir)

        # Image plane coordinates (in pixels, centered)
        u = f * x_dir / z_safe
        v = f * y_dir / z_safe

        # Convert to normalized coordinates for grid_sample [-1, 1]
        # u is in pixels from center, so normalized = u / (W/2)
        # v is in pixels from center, so normalized = v / (H/2)
        u_norm = u / (W / 2.0)
        v_norm = v / (H / 2.0)

        # grid_sample expects [B, H, W, 2] with (x, y) in [-1, 1]
        grid = torch.stack([u_norm, v_norm], dim=-1)  # [H_out, W_out, 2]
        grid = grid.unsqueeze(0).expand(B, -1, -1, -1)  # [B, H_out, W_out, 2]

        # Reshape image for grid_sample: [B, C, H, W]
        img_4d = img.permute(0, 3, 1, 2)  # [B, C, H, W]

        # Perform the warp
        warped = F.grid_sample(
            img_4d, grid, mode='bilinear', padding_mode='zeros', align_corners=True
        )

        # Convert back to [B, H, W, C]
        result = warped.permute(0, 2, 3, 1)  # [B, H_out, W_out, C]

        # Clamp to 0..1
        result = torch.clamp(result, 0.0, 1.0)

        return (result,)


NODE_CLASS_MAPPINGS = {
    "PSN_VR180_Convert": PSN_VR180_Convert,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_VR180_Convert": "VR180 Projection Conversion",
}
