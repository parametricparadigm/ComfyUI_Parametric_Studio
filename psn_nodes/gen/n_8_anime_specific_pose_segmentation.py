"""ParametricStudio - Anime-Specific Pose & Segmentation (torch-only core).

Implements the core of the idea using only torch + stdlib:

* PSN_Anime_Pose_Estimator: deterministic anime-flavoured pose estimator.
  No trained weights (none available in sandbox). Derives a heat-map pose
  map and keypoints from image statistics (luminance centre-of-mass).

* PSN_Anime_Segmentor: rule-based segmentation of anime features
  (hair / eyes / mouth / body) using colour thresholds on RGB.

NOT implemented (needs heavy models / onnxruntime):
  * Real anime-specific pose model inference (DWPose / anime-pose weights).
  * Learned segmentation networks.
  * onnxruntime backend.
"""

import torch

CAT = "ParametricStudio/AnimePose"


def _as_image(image):
    if not isinstance(image, torch.Tensor):
        raise TypeError("image must be a torch.Tensor")
    x = image.detach().clone().float()
    if x.dim() != 4:
        raise ValueError("image must be [B,H,W,C], got %s" % (tuple(x.shape),))
    if x.shape[-1] not in (1, 3, 4):
        raise ValueError("image channels must be 1, 3 or 4, got %d" % x.shape[-1])
    return x.clamp_(0.0, 1.0)


def _resize_bilinear(x, h, w):
    if x.shape[-2] == h and x.shape[-1] == w:
        return x
    if x.dim() == 3:
        xi = x.unsqueeze(-1)
    else:
        xi = x
    xi = xi.permute(0, 3, 1, 2)
    xi = torch.nn.functional.interpolate(xi, size=(h, w), mode="bilinear", align_corners=False)
    xi = xi.permute(0, 2, 3, 1)
    if xi.shape[-1] == 1:
        return xi.squeeze(-1)
    return xi


_POSE_KEYPOINTS = [
    "nose", "left_eye", "right_eye", "left_ear", "right_ear",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_ankle", "right_ankle",
]


def _estimate_keypoints(img):
    b, h, w, c = img.shape
    rgb = img[..., :3]
    lum = rgb.mean(dim=-1)
    upper = lum[:, : max(1, h // 2), :]
    total = upper.sum(dim=(1, 2), keepdim=True).clamp_min(1e-6)
    ys = torch.arange(upper.shape[1], device=lum.device, dtype=torch.float32).view(1, -1, 1)
    xs = torch.arange(w, device=lum.device, dtype=torch.float32).view(1, 1, -1)
    cy = (upper * ys).sum(dim=(1, 2), keepdim=True) / total
    cx = (upper * xs).sum(dim=(1, 2), keepdim=True) / total
    cy = cy.clamp(0.0, float(h - 1))
    cx = cx.clamp(0.0, float(w - 1))

    lower = lum[:, h // 2:, :]
    total_l = lower.sum(dim=(1, 2), keepdim=True).clamp_min(1e-6)
    ys_l = torch.arange(h // 2, h, device=lum.device, dtype=torch.float32).view(1, -1, 1)
    by = (lower * ys_l).sum(dim=(1, 2), keepdim=True) / total_l
    bx = (lower * xs).sum(dim=(1, 2), keepdim=True) / total_l
    by = by.clamp(0.0, float(h - 1))
    bx = bx.clamp(0.0, float(w - 1))

    spread = min(h, w) * 0.15

    def kp(x, y, score=0.9):
        return torch.stack([x.squeeze(-1), y.squeeze(-1), torch.full_like(x, score).squeeze(-1)], dim=-1)

    kps = []
    kps.append(kp(cx, cy, 0.95))
    kps.append(kp(cx - spread * 0.5, cy - spread * 0.2, 0.9))
    kps.append(kp(cx + spread * 0.5, cy - spread * 0.2, 0.9))
    kps.append(kp(cx - spread * 0.9, cy, 0.85))
    kps.append(kp(cx + spread * 0.9, cy, 0.85))
    sh_y = cy + spread * 1.2
    kps.append(kp(cx - spread * 1.2, sh_y, 0.8))
    kps.append(kp(cx + spread * 1.2, sh_y, 0.8))
    el_y = sh_y + spread * 1.0
    kps.append(kp(cx - spread * 1.5, el_y, 0.7))
    kps.append(kp(cx + spread * 1.5, el_y, 0.7))
    wr_y = el_y + spread * 0.9
    kps.append(kp(cx - spread * 1.7, wr_y, 0.6))
    kps.append(kp(cx + spread * 1.7, wr_y, 0.6))
    hip_y = by - spread * 0.5
    kps.append(kp(bx - spread * 0.6, hip_y, 0.8))
    kps.append(kp(bx + spread * 0.6, hip_y, 0.8))
    kn_y = by + spread * 0.8
    kps.append(kp(bx - spread * 0.7, kn_y, 0.7))
    kps.append(kp(bx + spread * 0.7, kn_y, 0.7))
    an_y = by + spread * 1.8
    kps.append(kp(bx - spread * 0.8, an_y, 0.6))
    kps.append(kp(bx + spread * 0.8, an_y, 0.6))
    return kps


def _render_pose_map(img, kps):
    b, h, w, _ = img.shape
    canvas = torch.zeros(b, h, w, 3, dtype=torch.float32)
    sigma = max(2.0, min(h, w) * 0.02)
    for i, kp in enumerate(kps):
        col = torch.tensor([
            (i * 47) % 256 / 255.0,
            (i * 97) % 256 / 255.0,
            (i * 151) % 256 / 255.0,
        ], dtype=torch.float32)
        x = kp[..., 0].round().long().clamp(0, w - 1)
        y = kp[..., 1].round().long().clamp(0, h - 1)
        score = kp[..., 2]
        for bi in range(b):
            xi, yi = int(x[bi, 0]), int(y[bi, 0])
            s = float(score[bi, 0])
            r = max(1, int(sigma))
            y0, y1 = max(0, yi - r), min(h, yi + r + 1)
            x0, x1 = max(0, xi - r), min(w, xi + r + 1)
            yy, xx = torch.meshgrid(
                torch.arange(y0, y1, dtype=torch.float32),
                torch.arange(x0, x1, dtype=torch.float32),
                indexing="ij",
            )
            d2 = (xx - xi) ** 2 + (yy - yi) ** 2
            g = torch.exp(-d2 / (2.0 * sigma * sigma)) * s
            for ci in range(3):
                canvas[bi, y0:y1, x0:x1, ci] = torch.clamp(
                    canvas[bi, y0:y1, x0:x1, ci] + g * col[ci], 0.0, 1.0
                )
    return canvas


class PSN_Anime_Pose_Estimator:
    """Estimate anime pose: heat-map pose map + keypoints (torch-only core)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "resolution": ("INT", {"default": 512, "min": 64, "max": 2048}),
            }
        }

    RETURN_TYPES = ("IMAGE", "POSE_KEYPOINT")
    RETURN_NAMES = ("pose_map", "keypoints")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, resolution):
        img = _as_image(image)
        b, h, w, c = img.shape
        scale = resolution / max(h, w)
        nh = max(1, int(round(h * scale)))
        nw = max(1, int(round(w * scale)))
        img_r = _resize_bilinear(img, nh, nw)
        kps = _estimate_keypoints(img_r)
        pose_map = _render_pose_map(img_r, kps)
        kp_tensor = torch.cat(kps, dim=1)
        keypoints = {"names": list(_POSE_KEYPOINTS), "keypoints": kp_tensor}
        return (pose_map, keypoints)


_SEG_CLASSES = ["hair", "eyes", "mouth", "body"]


def _segment_hair(img):
    b, h, w, _ = img.shape
    rgb = img[..., :3]
    r, g, bch = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    lum = (r + g + bch) / 3.0
    mx = torch.max(torch.max(r, g), bch)
    mn = torch.min(torch.min(r, g), bch)
    sat = torch.where(mx > 0, (mx - mn) / mx.clamp_min(1e-6), torch.zeros_like(mx))
    dark = (lum < 0.35).float()
    low_sat = (sat < 0.35).float()
    hair = dark * low_sat
    mask_top = torch.zeros_like(hair)
    cut = max(1, int(h * 0.6))
    mask_top[:, :cut, :] = 1.0
    return (hair * mask_top).clamp(0.0, 1.0)


def _segment_eyes(img):
    b, h, w, _ = img.shape
    rgb = img[..., :3]
    r, g, bch = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    lum = (r + g + bch) / 3.0
    bright = (lum > 0.7).float()
    mask_top = torch.zeros_like(bright)
    cut = max(1, int(h * 0.4))
    mask_top[:, :cut, :] = 1.0
    return (bright * mask_top).clamp(0.0, 1.0)


def _segment_mouth(img):
    b, h, w, _ = img.shape
    rgb = img[..., :3]
    r, g, bch = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    redness = (r - (g + bch) / 2.0)
    mouth = (redness > 0.05).float()
    mask_band = torch.zeros_like(mouth)
    y0 = max(0, int(h * 0.3))
    y1 = min(h, int(h * 0.55))
    mask_band[:, y0:y1, :] = 1.0
    return (mouth * mask_band).clamp(0.0, 1.0)


def _segment_body(img):
    b, h, w, _ = img.shape
    rgb = img[..., :3]
    lum = rgb.mean(dim=-1)
    body = ((lum > 0.15) & (lum < 0.85)).float()
    mask_bot = torch.zeros_like(body)
    y0 = max(0, int(h * 0.3))
    mask_bot[:, y0:, :] = 1.0
    return (body * mask_bot).clamp(0.0, 1.0)


_SEG_FUNCS = {
    "hair": _segment_hair,
    "eyes": _segment_eyes,
    "mouth": _segment_mouth,
    "body": _segment_body,
}


class PSN_Anime_Segmentor:
    """Segment anime features (hair/eyes/mouth/body) into a MASK."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "classes": ("COMBO", {"default": "hair", "options": _SEG_CLASSES}),
            }
        }

    RETURN_TYPES = ("MASK",)
    RETURN_NAMES = ("mask",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, classes):
        img = _as_image(image)
        if classes not in _SEG_FUNCS:
            raise ValueError("unknown class %r" % (classes,))
        mask = _SEG_FUNCS[classes](img)
        return (mask,)


NODE_CLASS_MAPPINGS = {
    "PSN_Anime_Pose_Estimator": PSN_Anime_Pose_Estimator,
    "PSN_Anime_Segmentor": PSN_Anime_Segmentor,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Anime_Pose_Estimator": "Anime Pose Estimator",
    "PSN_Anime_Segmentor": "Anime Segmentor",
}
