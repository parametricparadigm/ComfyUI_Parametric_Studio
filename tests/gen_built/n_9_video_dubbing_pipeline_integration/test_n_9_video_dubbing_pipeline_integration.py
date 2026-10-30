"""Tests for n_9_video_dubbing_pipeline_integration."""

import torch
from n_9_video_dubbing_pipeline_integration import (
    PSN_Video_Dubbing,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _validate_video,
    _validate_lang,
    _validate_api_key,
    _apply_dubbing,
)


def _make_video(b=1, h=8, w=8, c=3):
    return torch.rand(b, h, w, c)


def test_basic_run():
    """Basic run returns a video tensor and a status string."""
    node = PSN_Video_Dubbing()
    video = _make_video()
    out_video, status = node.run(video, "en", "es", "sk-test-key-12345", False)
    assert isinstance(out_video, torch.Tensor), "output must be a tensor"
    assert out_video.shape == video.shape, "shape must be preserved"
    assert isinstance(status, str), "status must be a string"
    assert "en -> es" in status, "status should mention the language pair"
    assert out_video.min() >= 0.0 and out_video.max() <= 1.0, "values in [0,1]"


def test_lip_sync_changes_output():
    """Lip-sync on should produce a different (smoothed) output."""
    node = PSN_Video_Dubbing()
    video = _make_video()
    out_no, _ = node.run(video, "en", "es", "sk-test-key-12345", False)
    out_yes, _ = node.run(video, "en", "es", "sk-test-key-12345", True)
    assert not torch.allclose(out_no, out_yes), "lip-sync should change output"


def test_input_not_modified():
    """The input tensor must not be modified in place."""
    node = PSN_Video_Dubbing()
    video = _make_video()
    video_copy = video.clone()
    node.run(video, "en", "fr", "sk-test-key-12345", True)
    assert torch.equal(video, video_copy), "input must not be modified in place"


def test_bad_video_not_tensor():
    """Passing a non-tensor video should raise ValueError."""
    node = PSN_Video_Dubbing()
    try:
        node.run("not a tensor", "en", "es", "sk-test-key-12345", False)
        assert False, "should have raised ValueError"
    except ValueError:
        pass


def test_bad_video_wrong_dims():
    """A 3-D tensor should be rejected."""
    node = PSN_Video_Dubbing()
    bad = torch.rand(8, 8, 3)  # missing batch dim
    try:
        node.run(bad, "en", "es", "sk-test-key-12345", False)
        assert False, "should have raised ValueError"
    except ValueError:
        pass


def test_bad_lang_code():
    """A non-2-letter language code should be rejected."""
    node = PSN_Video_Dubbing()
    video = _make_video()
    try:
        node.run(video, "english", "es", "sk-test-key-12345", False)
        assert False, "should have raised ValueError"
    except ValueError:
        pass


def test_bad_api_key_too_short():
    """An API key shorter than 8 chars should be rejected."""
    node = PSN_Video_Dubbing()
    video = _make_video()
    try:
        node.run(video, "en", "es", "short", False)
        assert False, "should have raised ValueError"
    except ValueError:
        pass


def test_bad_lip_sync_type():
    """A non-boolean lip_sync should be rejected."""
    node = PSN_Video_Dubbing()
    video = _make_video()
    try:
        node.run(video, "en", "es", "sk-test-key-12345", "yes")
        assert False, "should have raised ValueError"
    except ValueError:
        pass


def test_node_registration():
    """NODE_CLASS_MAPPINGS and NODE_DISPLAY_NAME_MAPPINGS must be correct."""
    assert "PSN_Video_Dubbing" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_Video_Dubbing"] is PSN_Video_Dubbing
    assert "PSN_Video_Dubbing" in NODE_DISPLAY_NAME_MAPPINGS
    assert isinstance(NODE_DISPLAY_NAME_MAPPINGS["PSN_Video_Dubbing"], str)


def test_input_types_structure():
    """INPUT_TYPES must return a dict with 'required' key and correct fields."""
    it = PSN_Video_Dubbing.INPUT_TYPES()
    assert "required" in it
    req = it["required"]
    assert "video" in req
    assert "source_lang" in req
    assert "target_lang" in req
    assert "alta_api_key" in req
    assert "lip_sync" in req
    assert req["video"] == ("VIDEO",)
    assert req["lip_sync"][0] == "BOOLEAN"


def test_return_types():
    """RETURN_TYPES and RETURN_NAMES must be correct."""
    assert PSN_Video_Dubbing.RETURN_TYPES == ("VIDEO", "STRING")
    assert PSN_Video_Dubbing.RETURN_NAMES == ("dubbed_video", "status")
    assert PSN_Video_Dubbing.FUNCTION == "run"
    assert PSN_Video_Dubbing.CATEGORY == "ParametricStudio/Video"


def test_small_video_edge():
    """A 1x1x1x1 video should work (edge case)."""
    node = PSN_Video_Dubbing()
    video = torch.rand(1, 1, 1, 1)
    out, status = node.run(video, "en", "ja", "sk-test-key-12345", True)
    assert out.shape == (1, 1, 1, 1)
    assert out.min() >= 0.0 and out.max() <= 1.0


def test_grayscale_video():
    """A 1-channel (grayscale) video should work."""
    node = PSN_Video_Dubbing()
    video = torch.rand(1, 4, 4, 1)
    out, _ = node.run(video, "en", "de", "sk-test-key-12345", False)
    assert out.shape == (1, 4, 4, 1)


def test_different_langs_different_gains():
    """Different target languages should produce different gains."""
    node = PSN_Video_Dubbing()
    video = torch.ones(1, 4, 4, 3)
    out_es, _ = node.run(video, "en", "es", "sk-test-key-12345", False)
    out_fr, _ = node.run(video, "en", "fr", "sk-test-key-12345", False)
    # es gain = 1.05, fr gain = 0.95, so outputs should differ
    assert not torch.allclose(out_es, out_fr), "different langs should differ"


if __name__ == "__main__":
    test_basic_run()
    test_lip_sync_changes_output()
    test_input_not_modified()
    test_bad_video_not_tensor()
    test_bad_video_wrong_dims()
    test_bad_lang_code()
    test_bad_api_key_too_short()
    test_bad_lip_sync_type()
    test_node_registration()
    test_input_types_structure()
    test_return_types()
    test_small_video_edge()
    test_grayscale_video()
    test_different_langs_different_gains()
    print("ok")
