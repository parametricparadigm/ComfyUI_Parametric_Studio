"""Civitai-compatible image saver for community sharing.

Saves a ComfyUI IMAGE tensor as a PNG whose metadata carries a JSON
structure that Civitai's auto-detection can read.  The JSON is stored in
the PNG ``parameters`` text chunk (the field Civitai looks for first)
and, for maximum compatibility, also in a ``prompt`` chunk.

Only stdlib + torch + Pillow are used.  No network, no subprocess.
"""

import json

import torch

from PIL import Image
from PIL.PngImagePlugin import PngInfo

CAT = "ParametricStudio/Save"

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _build_civitai_metadata(
    prompt: str,
    negative_prompt: str,
    model_name: str,
    extra: dict | None = None,
) -> dict:
    """Return the metadata dict that Civitai expects.

    Civitai's auto-detection looks for a JSON object in the PNG metadata
    (``parameters`` or ``prompt`` text chunk) that contains at least a
    ``prompt`` key.  We include the common fields so the image is fully
    self-describing.
    """
    meta: dict = {
        "prompt": prompt or "",
        "negative_prompt": negative_prompt or "",
        "model": model_name or "",
        "source": "ComfyUI",
    }
    if extra:
        for k, v in extra.items():
            meta.setdefault(k, v)
    return meta


def _tensor_to_pil(image: torch.Tensor) -> Image.Image:
    """Convert a ComfyUI IMAGE tensor [B,H,W,C] 0..1 to a PIL image.

    Only the first batch element is saved (single-image saver).
    """
    if not isinstance(image, torch.Tensor):
        raise TypeError("image must be a torch.Tensor")
    if image.dim() != 4:
        raise ValueError(f"expected [B,H,W,C] tensor, got shape {tuple(image.shape)}")
    if image.shape[3] not in (1, 3, 4):
        raise ValueError(f"expected C in (1,3,4), got {image.shape[3]}")

    img = image[0].detach().cpu().clamp(0.0, 1.0)
    # [H,W,C] -> [H,W] for single channel
    if img.shape[2] == 1:
        arr = (img[:, :, 0] * 255).to(torch.uint8).numpy()
        return Image.fromarray(arr, mode="L")
    arr = (img * 255).to(torch.uint8).numpy()
    if img.shape[2] == 3:
        return Image.fromarray(arr, mode="RGB")
    return Image.fromarray(arr, mode="RGBA")


def _write_png_with_metadata(
    pil_img: Image.Image,
    path: str,
    metadata: dict,
) -> None:
    """Write *pil_img* to *path* as PNG with Civitai metadata chunks.

    The JSON is stored in BOTH the ``parameters`` and ``prompt`` text
    chunks so that whichever key a parser checks first, it finds valid
    JSON.
    """
    json_str = json.dumps(metadata, ensure_ascii=False)
    info = PngInfo()
    info.add_text("parameters", json_str)
    info.add_text("prompt", json_str)
    pil_img.save(path, format="PNG", pnginfo=info)


# ---------------------------------------------------------------------------
# node
# ---------------------------------------------------------------------------


class PSN_Civitai_Compat_Save:
    """Save an image as PNG with Civitai-compatible metadata.

    The PNG will contain a ``parameters`` text chunk (and a ``prompt``
    chunk) holding a JSON object with at least ``prompt``,
    ``negative_prompt`` and ``model`` keys, which is what Civitai's
    auto-detection expects.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "prompt": ("STRING", {"default": "", "multiline": True}),
                "negative_prompt": ("STRING", {"default": "", "multiline": True}),
                "model_name": ("STRING", {"default": ""}),
                "filename_prefix": ("STRING", {"default": "civitai_save"}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("saved_path",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(
        self,
        image: torch.Tensor,
        prompt: str,
        negative_prompt: str,
        model_name: str,
        filename_prefix: str,
    ) -> tuple[str]:
        """Save *image* (first batch element) as a Civitai-compatible PNG.

        Returns the absolute path of the written file.
        """
        pil_img = _tensor_to_pil(image)
        meta = _build_civitai_metadata(prompt, negative_prompt, model_name)

        prefix = (filename_prefix or "civitai_save").strip() or "civitai_save"
        # sanitise: keep only safe filename characters
        safe = "".join(c if (c.isalnum() or c in "-_ ") else "_" for c in prefix)
        safe = safe.strip() or "civitai_save"
        path = f"{safe}.png"

        _write_png_with_metadata(pil_img, path, meta)
        return (path,)


# ---------------------------------------------------------------------------
# module-level mappings (ComfyUI convention)
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_Civitai_Compat_Save": PSN_Civitai_Compat_Save,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Civitai_Compat_Save": "Civitai-Compatible Image Saver",
}
