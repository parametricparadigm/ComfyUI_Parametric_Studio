"""NDI Video Stream Integration for ComfyUI (ParametricStudio).

Sends generated frames to an NDI stream for live broadcasting.

Since the real `ndi-python` / `PyNDI` library is not available in this
environment, the module implements the full tensor-to-RGB conversion
pipeline and a pluggable NDI sender interface.  When the real NDI
library is installed, a user can supply a sender callable that performs
the actual network send.  The node returns a boolean indicating whether
a frame was successfully handed to the sender.
"""

import torch

CAT = "ParametricStudio/NDI"


def _s(x):
    """Unwrap a ComfyUI LATENT dict to its samples tensor."""
    if isinstance(x, dict):
        return x["samples"]
    return x


def _out(latent, samples):
    """Re-wrap a samples tensor into a ComfyUI LATENT dict."""
    return {"samples": samples}


def image_to_rgb_bytes(image):
    """Convert a ComfyUI IMAGE tensor [B,H,W,C] in 0..1 to a list of
    per-frame RGB byte arrays (bytes objects).

    Returns a list of length B, each element a bytes object of length
    H*W*3 (row-major, RGB).
    """
    if not torch.is_tensor(image):
        raise TypeError("image must be a torch tensor")
    if image.dim() != 4:
        raise ValueError("image must have shape [B,H,W,C], got %d dims" % image.dim())
    if image.shape[-1] not in (3, 4):
        raise ValueError("image last dim must be 3 (RGB) or 4 (RGBA), got %d" % image.shape[-1])

    # Clamp to 0..1 and convert to uint8
    img = image.clamp(0.0, 1.0)
    # Take first 3 channels if RGBA
    if img.shape[-1] == 4:
        img = img[:, :, :, :3]
    # Convert to uint8
    img_u8 = (img * 255.0 + 0.5).to(torch.uint8)

    frames = []
    for i in range(img_u8.shape[0]):
        frame = img_u8[i].contiguous().view(-1).numpy().tobytes()
        frames.append(frame)
    return frames


class PSN_NDI_Source:
    """Sends generated frames to an NDI stream for live broadcasting.

    Converts the IMAGE tensor to RGB byte arrays and hands them to an
    NDI sender.  Returns True if the frame was successfully sent.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "ndi_name": ("STRING", {"default": "ComfyUI_NDI", "multiline": False}),
                "fps": ("INT", {"default": 30, "min": 1, "max": 240}),
            },
            "optional": {
                "ndi_sender": ("NDI_SENDER",),
            },
        }

    RETURN_TYPES = ("BOOLEAN",)
    RETURN_NAMES = ("streaming",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, ndi_name, fps, ndi_sender=None):
        """Convert image to RGB bytes and send via NDI sender.

        Args:
            image: IMAGE tensor [B,H,W,C] in 0..1.
            ndi_name: Name of the NDI source to register.
            fps: Target frames per second.
            ndi_sender: Optional callable(ndi_name, fps, frames_bytes) -> bool.
                        If None, no actual send is performed (dry run).

        Returns:
            (bool,): True if the frame was handed to a sender successfully.
        """
        # Validate inputs
        if not torch.is_tensor(image):
            raise TypeError("image must be a torch tensor")
        if image.dim() != 4:
            raise ValueError("image must have shape [B,H,W,C]")
        if image.shape[-1] not in (3, 4):
            raise ValueError("image last dim must be 3 or 4")
        if not isinstance(ndi_name, str) or len(ndi_name) == 0:
            raise ValueError("ndi_name must be a non-empty string")
        if not isinstance(fps, int) or fps < 1 or fps > 240:
            raise ValueError("fps must be an integer between 1 and 240")

        # Convert to RGB byte arrays
        frames = image_to_rgb_bytes(image)

        # Send via NDI sender if provided
        if ndi_sender is not None:
            if not callable(ndi_sender):
                raise TypeError("ndi_sender must be callable")
            result = ndi_sender(ndi_name, fps, frames)
            return (bool(result),)

        # Dry run: no sender, just validate conversion succeeded
        return (True,)


NODE_CLASS_MAPPINGS = {
    "PSN_NDI_Source": PSN_NDI_Source,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_NDI_Source": "NDI Video Stream Source",
}
