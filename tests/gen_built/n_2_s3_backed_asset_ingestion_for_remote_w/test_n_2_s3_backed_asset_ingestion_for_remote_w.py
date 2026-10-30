"""Tests for PSN_S3_Asset_Loader node."""

import torch
from n_2_s3_backed_asset_ingestion_for_remote_w import (
    PSN_S3_Asset_Loader,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _validate_bucket,
    _validate_key,
    _validate_region,
    _validate_credentials,
    _simulate_download,
    _bytes_to_image_tensor,
    _simulate_video_tensor,
    _simulate_cache_path,
)


def test_node_class_mappings():
    """Verify module-level mappings exist and are correct."""
    assert "PSN_S3_Asset_Loader" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_S3_Asset_Loader"] is PSN_S3_Asset_Loader
    assert "PSN_S3_Asset_Loader" in NODE_DISPLAY_NAME_MAPPINGS
    assert isinstance(NODE_DISPLAY_NAME_MAPPINGS["PSN_S3_Asset_Loader"], str)


def test_input_types():
    """Verify INPUT_TYPES classmethod returns proper structure."""
    it = PSN_S3_Asset_Loader.INPUT_TYPES()
    assert "required" in it
    assert "optional" in it
    assert "bucket" in it["required"]
    assert "key" in it["required"]
    assert "region" in it["optional"]
    assert "credentials" in it["optional"]
    assert "cache_local" in it["optional"]


def test_return_types():
    """Verify RETURN_TYPES and RETURN_NAMES."""
    assert PSN_S3_Asset_Loader.RETURN_TYPES == ("IMAGE", "IMAGE", "STRING")
    assert PSN_S3_Asset_Loader.RETURN_NAMES == ("image", "video", "local_path")
    assert PSN_S3_Asset_Loader.FUNCTION == "run"
    assert PSN_S3_Asset_Loader.CATEGORY == "ParametricStudio/S3"


def test_basic_run():
    """Run the node with basic inputs and verify output shapes."""
    node = PSN_S3_Asset_Loader()
    image, video, path = node.run(bucket="test-bucket", key="img.png", width=4, height=4, channels=3)
    assert isinstance(image, torch.Tensor)
    assert image.shape == (1, 4, 4, 3)
    assert image.dtype == torch.float32
    assert image.min() >= 0.0
    assert image.max() <= 1.0
    assert isinstance(video, torch.Tensor)
    assert video.shape == (1, 1, 4, 4, 3)
    assert path == ""


def test_video_mode():
    """Run with is_video=True and verify video tensor shape."""
    node = PSN_S3_Asset_Loader()
    image, video, path = node.run(
        bucket="test-bucket", key="vid.mp4", is_video=True,
        width=4, height=4, channels=3, frames=3
    )
    assert video.shape == (1, 3, 4, 4, 3)
    assert video.min() >= 0.0
    assert video.max() <= 1.0


def test_cache_local():
    """Verify cache_local produces a path string."""
    node = PSN_S3_Asset_Loader()
    image, video, path = node.run(bucket="test-bucket", key="a/b/c.png", cache_local=True)
    assert isinstance(path, str)
    assert path != ""
    assert "test-bucket" in path
    assert "a_b_c.png" in path


def test_bad_bucket_empty():
    """Empty bucket should raise ValueError."""
    node = PSN_S3_Asset_Loader()
    try:
        node.run(bucket="", key="img.png")
        assert False, "Expected ValueError for empty bucket"
    except ValueError as e:
        assert "bucket" in str(e).lower()


def test_bad_bucket_too_short():
    """Bucket shorter than 3 chars should raise ValueError."""
    try:
        _validate_bucket("ab")
        assert False, "Expected ValueError for short bucket"
    except ValueError:
        pass


def test_bad_bucket_bad_chars():
    """Bucket with invalid characters should raise ValueError."""
    try:
        _validate_bucket("my_bucket!")
        assert False, "Expected ValueError for bad bucket chars"
    except ValueError:
        pass


def test_bad_key_leading_slash():
    """Key starting with / should raise ValueError."""
    try:
        _validate_key("/leading/slash.png")
        assert False, "Expected ValueError for leading slash key"
    except ValueError:
        pass


def test_bad_key_empty():
    """Empty key should raise ValueError."""
    try:
        _validate_key("")
        assert False, "Expected ValueError for empty key"
    except ValueError:
        pass


def test_bad_region():
    """Region with invalid characters should raise ValueError."""
    try:
        _validate_region("us east 1")
        assert False, "Expected ValueError for bad region"
    except ValueError:
        pass


def test_bad_credentials_type():
    """Credentials that is not a dict should raise ValueError."""
    try:
        _validate_credentials("not-a-dict")
        assert False, "Expected ValueError for non-dict credentials"
    except ValueError:
        pass


def test_credentials_none_ok():
    """None credentials should be accepted (use env vars)."""
    result = _validate_credentials(None)
    assert result == {}


def test_credentials_valid():
    """Valid credentials dict should pass."""
    creds = {"access_key_id": "AKIA123", "secret_access_key": "secret"}
    result = _validate_credentials(creds)
    assert result == creds


def test_credentials_bad_field_type():
    """Credentials with non-string field should raise ValueError."""
    try:
        _validate_credentials({"access_key_id": 12345})
        assert False, "Expected ValueError for non-string access_key_id"
    except ValueError:
        pass


def test_deterministic_download():
    """Same inputs should produce same bytes."""
    d1 = _simulate_download("bucket", "key.png", "us-east-1", {})
    d2 = _simulate_download("bucket", "key.png", "us-east-1", {})
    assert d1 == d2
    assert len(d1) >= 64


def test_different_inputs_different_bytes():
    """Different keys should produce different bytes."""
    d1 = _simulate_download("bucket", "key1.png", "us-east-1", {})
    d2 = _simulate_download("bucket", "key2.png", "us-east-1", {})
    assert d1 != d2


def test_image_tensor_range():
    """Image tensor values must be in [0, 1]."""
    data = bytes([0, 128, 255, 64, 32, 192])
    t = _bytes_to_image_tensor(data, width=2, height=1, channels=3)
    assert t.shape == (1, 1, 2, 3)
    assert t.min() >= 0.0
    assert t.max() <= 1.0


def test_image_tensor_bad_dims():
    """Zero or negative dimensions should raise ValueError."""
    try:
        _bytes_to_image_tensor(b"\x00" * 10, width=0, height=4, channels=3)
        assert False, "Expected ValueError for zero width"
    except ValueError:
        pass


def test_video_tensor_bad_frames():
    """Zero frames should raise ValueError."""
    try:
        _simulate_video_tensor(b"\x00" * 10, frames=0, width=4, height=4, channels=3)
        assert False, "Expected ValueError for zero frames"
    except ValueError:
        pass


def test_cache_path_format():
    """Cache path should contain bucket and sanitized key."""
    p = _simulate_cache_path("my-bucket", "a/b/c.png")
    assert "my-bucket" in p
    assert "a_b_c.png" in p
    assert p.startswith("/tmp/")


def test_no_in_place_modification():
    """Verify the node does not modify input tensors (we pass none, but check output is fresh)."""
    node = PSN_S3_Asset_Loader()
    img1, _, _ = node.run(bucket="bkt", key="k1.png", width=2, height=2, channels=3)
    img2, _, _ = node.run(bucket="bkt", key="k2.png", width=2, height=2, channels=3)
    # Different keys should give different tensors
    assert not torch.equal(img1, img2)


def test_single_channel():
    """Test with 1 channel (grayscale)."""
    node = PSN_S3_Asset_Loader()
    image, video, _ = node.run(bucket="bkt", key="gray.png", width=3, height=3, channels=1)
    assert image.shape == (1, 3, 3, 1)


def test_large_dimensions():
    """Test with larger dimensions."""
    node = PSN_S3_Asset_Loader()
    image, video, _ = node.run(bucket="bkt", key="big.png", width=16, height=16, channels=4)
    assert image.shape == (1, 16, 16, 4)
    assert image.min() >= 0.0
    assert image.max() <= 1.0


if __name__ == "__main__":
    test_node_class_mappings()
    test_input_types()
    test_return_types()
    test_basic_run()
    test_video_mode()
    test_cache_local()
    test_bad_bucket_empty()
    test_bad_bucket_too_short()
    test_bad_bucket_bad_chars()
    test_bad_key_leading_slash()
    test_bad_key_empty()
    test_bad_region()
    test_bad_credentials_type()
    test_credentials_none_ok()
    test_credentials_valid()
    test_credentials_bad_field_type()
    test_deterministic_download()
    test_different_inputs_different_bytes()
    test_image_tensor_range()
    test_image_tensor_bad_dims()
    test_video_tensor_bad_frames()
    test_cache_path_format()
    test_no_in_place_modification()
    test_single_channel()
    test_large_dimensions()
    print("ok")
