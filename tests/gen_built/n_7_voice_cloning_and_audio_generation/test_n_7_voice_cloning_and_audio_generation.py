"""Tests for n_7_voice_cloning_and_audio_generation.

Run with:  python3 -B test_n_7_voice_cloning_and_audio_generation.py
Must print 'ok' and exit 0.
"""

import torch

from n_7_voice_cloning_and_audio_generation import (
    PSN_Load_Voice_Reference,
    PSN_Generate_Speech,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    EMBED_DIM,
    SAMPLE_RATE,
)


def test_module_mappings():
    """NODE_CLASS_MAPPINGS and display names are present and consistent."""
    assert "PSN_Load_Voice_Reference" in NODE_CLASS_MAPPINGS
    assert "PSN_Generate_Speech" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_Load_Voice_Reference"] is PSN_Load_Voice_Reference
    assert NODE_CLASS_MAPPINGS["PSN_Generate_Speech"] is PSN_Generate_Speech
    assert "PSN_Load_Voice_Reference" in NODE_DISPLAY_NAME_MAPPINGS
    assert "PSN_Generate_Speech" in NODE_DISPLAY_NAME_MAPPINGS


def test_input_types_schema():
    """Both nodes expose a valid INPUT_TYPES classmethod with required keys."""
    lt = PSN_Load_Voice_Reference.INPUT_TYPES()
    assert "required" in lt
    assert "audio_path" in lt["required"]
    assert "speaker_id" in lt["required"]

    gt = PSN_Generate_Speech.INPUT_TYPES()
    assert "required" in gt
    assert "text" in gt["required"]
    assert "voice_embedding" in gt["required"]
    assert "speed" in gt["required"]


def test_embedding_shape_and_determinism():
    """Embedding has correct shape and is deterministic for the same inputs."""
    node = PSN_Load_Voice_Reference()
    emb1 = node.run("ref.wav", "alice")[0]
    emb2 = node.run("ref.wav", "alice")[0]
    assert isinstance(emb1, torch.Tensor)
    assert emb1.shape == (EMBED_DIM,)
    assert emb1.dtype == torch.float32
    assert torch.allclose(emb1, emb2, atol=1e-6), "same inputs must give same embedding"


def test_embedding_differs_for_different_speakers():
    """Different speaker ids (or paths) yield different embeddings."""
    node = PSN_Load_Voice_Reference()
    emb_a = node.run("ref.wav", "alice")[0]
    emb_b = node.run("ref.wav", "bob")[0]
    assert not torch.allclose(emb_a, emb_b, atol=1e-4), "different speakers should differ"


def test_generate_speech_basic():
    """Basic speech generation returns a valid AUDIO tuple."""
    loader = PSN_Load_Voice_Reference()
    emb = loader.run("ref.wav", "alice")[0]
    gen = PSN_Generate_Speech()
    audio, sr = gen.run("Hello world", emb, 1.0)
    assert isinstance(audio, torch.Tensor)
    assert audio.dim() == 3, f"expected 3D tensor, got {audio.dim()}D"
    assert audio.shape[0] == 1, "batch dim must be 1"
    assert audio.shape[2] == 1, "mono channel"
    assert audio.shape[1] > 0, "must have at least one sample"
    assert sr == SAMPLE_RATE
    # Values should be in a reasonable range.
    assert audio.abs().max().item() <= 1.0 + 1e-5


def test_generate_speech_speed_affects_duration():
    """Faster speed should produce fewer samples (shorter audio)."""
    loader = PSN_Load_Voice_Reference()
    emb = loader.run("ref.wav", "alice")[0]
    gen = PSN_Generate_Speech()
    audio_slow, _ = gen.run("Hello world this is a test", emb, 0.5)
    audio_fast, _ = gen.run("Hello world this is a test", emb, 2.0)
    n_slow = audio_slow.shape[1]
    n_fast = audio_fast.shape[1]
    assert n_slow > n_fast, f"slower speed should be longer: {n_slow} vs {n_fast}"


def test_generate_speech_empty_text():
    """Empty text should still produce a valid (short) audio tensor."""
    loader = PSN_Load_Voice_Reference()
    emb = loader.run("ref.wav", "alice")[0]
    gen = PSN_Generate_Speech()
    audio, sr = gen.run("", emb, 1.0)
    assert isinstance(audio, torch.Tensor)
    assert audio.dim() == 3
    assert audio.shape[1] > 0
    assert sr == SAMPLE_RATE


def test_bad_input_types():
    """Non-string / non-tensor inputs must raise TypeError."""
    loader = PSN_Load_Voice_Reference()
    try:
        loader.run(12345, "alice")
        raise AssertionError("expected TypeError for non-string audio_path")
    except TypeError:
        pass

    gen = PSN_Generate_Speech()
    emb = loader.run("ref.wav", "alice")[0]
    try:
        gen.run(42, emb, 1.0)
        raise AssertionError("expected TypeError for non-string text")
    except TypeError:
        pass

    try:
        gen.run("hi", "not_a_tensor", 1.0)
        raise AssertionError("expected TypeError for non-tensor embedding")
    except TypeError:
        pass


def test_bad_embedding_dim():
    """An embedding with the wrong number of dims must raise ValueError."""
    gen = PSN_Generate_Speech()
    bad_emb = torch.randn(16)  # wrong dim
    try:
        gen.run("hi", bad_emb, 1.0)
        raise AssertionError("expected ValueError for wrong embedding dim")
    except ValueError:
        pass


def test_no_in_place_mutation():
    """The embedding tensor passed in must not be modified by the node."""
    loader = PSN_Load_Voice_Reference()
    emb = loader.run("ref.wav", "alice")[0]
    emb_before = emb.clone()
    gen = PSN_Generate_Speech()
    gen.run("Hello world", emb, 1.0)
    assert torch.allclose(emb, emb_before), "embedding must not be mutated in place"


def main():
    test_module_mappings()
    test_input_types_schema()
    test_embedding_shape_and_determinism()
    test_embedding_differs_for_different_speakers()
    test_generate_speech_basic()
    test_generate_speech_speed_affects_duration()
    test_generate_speech_empty_text()
    test_bad_input_types()
    test_bad_embedding_dim()
    test_no_in_place_mutation()
    print("ok")


if __name__ == "__main__":
    main()