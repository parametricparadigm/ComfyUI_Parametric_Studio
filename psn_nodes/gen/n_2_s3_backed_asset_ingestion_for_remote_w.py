"""S3-Backed Asset Ingestion for Remote Workflows.

This module provides a ComfyUI custom node that simulates loading assets
from S3-compatible buckets. Since network access and boto3 are not available
in this environment, the node implements the core logic for:
- Validating S3 configuration (bucket, key, region, credentials)
- Simulating the download/decode pipeline with mock data
- Converting raw bytes to ComfyUI IMAGE tensors
- Managing local cache state (simulated)

The node is designed to be a drop-in replacement that can be extended with
real boto3/PIL/FFmpeg calls when those dependencies are available.
"""

import torch

CAT = "ParametricStudio/S3"


def _validate_bucket(bucket: str) -> str:
    """Validate S3 bucket name format."""
    if not isinstance(bucket, str) or not bucket:
        raise ValueError("bucket must be a non-empty string")
    if len(bucket) < 3 or len(bucket) > 63:
        raise ValueError("bucket name must be 3-63 characters")
    if not bucket[0].isalnum():
        raise ValueError("bucket name must start with a letter or digit")
    if not all(c.isalnum() or c in '-.' for c in bucket):
        raise ValueError("bucket name may only contain lowercase letters, digits, hyphens, and dots")
    if '..' in bucket:
        raise ValueError("bucket name must not contain consecutive dots")
    return bucket


def _validate_key(key: str) -> str:
    """Validate S3 object key."""
    if not isinstance(key, str) or not key:
        raise ValueError("key must be a non-empty string")
    if key.startswith('/'):
        raise ValueError("key must not start with a slash")
    return key


def _validate_region(region: str) -> str:
    """Validate AWS region format."""
    if not isinstance(region, str) or not region:
        raise ValueError("region must be a non-empty string")
    if not all(c.isalnum() or c == '-' for c in region):
        raise ValueError("region may only contain letters, digits, and hyphens")
    return region


def _validate_credentials(creds: dict) -> dict:
    """Validate credentials dict structure."""
    if creds is None:
        return {}
    if not isinstance(creds, dict):
        raise ValueError("credentials must be a dict")
    for field in ("access_key_id", "secret_access_key"):
        if field in creds and not isinstance(creds[field], str):
            raise ValueError(f"credentials['{field}'] must be a string")
    return creds


def _simulate_download(bucket: str, key: str, region: str, creds: dict) -> bytes:
    """Simulate downloading an object from S3.

    In a real implementation this would use boto3 to fetch the object.
    Here we return a deterministic mock byte string based on the inputs.
    """
    _validate_bucket(bucket)
    _validate_key(key)
    if region:
        _validate_region(region)
    _validate_credentials(creds)

    # Deterministic mock: hash-like bytes derived from inputs
    seed_str = f"{bucket}/{key}/{region}"
    data = bytearray()
    for i, ch in enumerate(seed_str):
        data.append((ord(ch) * (i + 1)) % 256)
    # Pad to a minimum size to simulate a small image payload
    while len(data) < 64:
        data.append((data[-1] + 7) % 256)
    return bytes(data)


def _bytes_to_image_tensor(data: bytes, width: int = 4, height: int = 4, channels: int = 3) -> torch.Tensor:
    """Convert raw bytes to a ComfyUI IMAGE tensor [B, H, W, C] in 0..1.

    In a real implementation this would use PIL to decode the image.
    Here we deterministically map bytes to pixel values.
    """
    if width < 1 or height < 1 or channels < 1:
        raise ValueError("width, height, channels must be >= 1")
    total_pixels = width * height * channels
    # Use bytes to fill the tensor, cycling if data is shorter
    values = []
    for i in range(total_pixels):
        values.append(data[i % len(data)] / 255.0)
    tensor = torch.tensor(values, dtype=torch.float32).reshape(1, height, width, channels)
    return tensor


def _simulate_video_tensor(data: bytes, frames: int = 2, width: int = 4, height: int = 4, channels: int = 3) -> torch.Tensor:
    """Simulate a video tensor [B, F, H, W, C] in 0..1.

    In a real implementation this would use FFmpeg to decode video frames.
    """
    if frames < 1 or width < 1 or height < 1 or channels < 1:
        raise ValueError("frames, width, height, channels must be >= 1")
    total = frames * width * height * channels
    values = []
    for i in range(total):
        values.append(data[i % len(data)] / 255.0)
    tensor = torch.tensor(values, dtype=torch.float32).reshape(1, frames, height, width, channels)
    return tensor


def _simulate_cache_path(bucket: str, key: str) -> str:
    """Generate a simulated local cache path."""
    safe_key = key.replace('/', '_')
    return f"/tmp/comfyui_s3_cache/{bucket}/{safe_key}"


class PSN_S3_Asset_Loader:
    """Load reference images and videos from S3-compatible buckets.

    Simulates the S3 download and decode pipeline. In production, this
    would use boto3 for S3 access, PIL for image decoding, and FFmpeg
    for video decoding.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "bucket": ("STRING", {"default": "my-bucket"}),
                "key": ("STRING", {"default": "assets/ref.png"}),
            },
            "optional": {
                "region": ("STRING", {"default": "us-east-1"}),
                "credentials": ("DICT", {"default": {}}),
                "cache_local": ("BOOLEAN", {"default": False}),
                "is_video": ("BOOLEAN", {"default": False}),
                "width": ("INT", {"default": 4, "min": 1, "max": 4096}),
                "height": ("INT", {"default": 4, "min": 1, "max": 4096}),
                "channels": ("INT", {"default": 3, "min": 1, "max": 4}),
                "frames": ("INT", {"default": 2, "min": 1, "max": 256}),
            },
        }

    RETURN_TYPES = ("IMAGE", "IMAGE", "STRING")
    RETURN_NAMES = ("image", "video", "local_path")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(
        self,
        bucket: str,
        key: str,
        region: str = "",
        credentials: dict = None,
        cache_local: bool = False,
        is_video: bool = False,
        width: int = 4,
        height: int = 4,
        channels: int = 3,
        frames: int = 2,
    ):
        # Validate inputs
        _validate_bucket(bucket)
        _validate_key(key)
        if region:
            _validate_region(region)
        _validate_credentials(credentials)

        # Simulate download
        data = _simulate_download(bucket, key, region, credentials)

        # Decode to image tensor
        image_tensor = _bytes_to_image_tensor(data, width, height, channels)

        # Decode to video tensor if requested
        if is_video:
            video_tensor = _simulate_video_tensor(data, frames, width, height, channels)
        else:
            # Return a zero video tensor as placeholder
            video_tensor = torch.zeros(1, 1, height, width, channels, dtype=torch.float32)

        # Handle local cache
        if cache_local:
            local_path = _simulate_cache_path(bucket, key)
        else:
            local_path = ""

        return (image_tensor, video_tensor, local_path)


NODE_CLASS_MAPPINGS = {
    "PSN_S3_Asset_Loader": PSN_S3_Asset_Loader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_S3_Asset_Loader": "S3 Asset Loader (Remote Workflows)",
}
