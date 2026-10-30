"""Tests for n_2_vram_efficient_video_pipeline.

Run with:  python3 -B test_n_2_vram_efficient_video_pipeline.py
Must print 'ok' and exit 0.
"""

import torch

from n_2_vram_efficient_video_pipeline import (
    PSN_Video_Frame_Generator,
    PSN_Video_Assembler,
    PSN_Video_Frame_Loop,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _latent_samples,
    _make_latent,
    _decode_latent_to_frames,
)


def test_mappings():
    assert "PSN_Video_Frame_Generator" in NODE_CLASS_MAPPINGS
    assert "PSN_Video_Assembler" in NODE_CLASS_MAPPINGS
    assert "PSN_Video_Frame_Loop" in NODE_CLASS_MAPPINGS
    for k in NODE_CLASS_MAPPINGS:
        assert k in NODE_DISPLAY_NAME_MAPPINGS, k
        assert NODE_CLASS_MAPPINGS[k].FUNCTION == "run", k
        assert NODE_CLASS_MAPPINGS[k].CATEGORY.startswith("ParametricStudio"), k
    print("  1. mappings ok")


def test_generator_first_frame():
    gen = PSN_Video_Frame_Generator()
    cur, nxt = gen.run(
        frame_index=0,
        total_frames=4,
        steps=20,
        cfg=7.0,
        sampler_name="euler",
        scheduler="normal",
        seed=42,
    )
    assert isinstance(cur, dict) and "samples" in cur
    assert isinstance(nxt, dict) and "samples" in nxt
    x = cur["samples"]
    assert x.dim() == 4, "expected 4-D latent"
    assert x.shape[0] == 1, "batch should be 1"
    assert x.min() >= 0.0 and x.max() <= 1.0
    assert nxt["samples"] is not cur["samples"]
    assert torch.equal(nxt["samples"], cur["samples"])
    print("  2. generator first frame ok")


def test_generator_temporal():
    gen = PSN_Video_Frame_Generator()
    prev = _make_latent(torch.full((1, 4, 8, 8), 0.5))
    cur, nxt = gen.run(
        frame_index=1,
        total_frames=4,
        steps=20,
        cfg=7.0,
        sampler_name="euler",
        scheduler="normal",
        seed=42,
        prev_latent=prev,
    )
    x = cur["samples"]
    assert x.shape == (1, 4, 8, 8)
    assert x.min() >= 0.0 and x.max() <= 1.0
    assert not torch.equal(x, prev["samples"])
    assert abs(x.mean().item() - 0.5) < 0.3
    print("  3. generator temporal ok")


def test_generator_bad_frame_index():
    gen = PSN_Video_Frame_Generator()
    try:
        gen.run(
            frame_index=5,
            total_frames=4,
            steps=20,
            cfg=7.0,
            sampler_name="euler",
            scheduler="normal",
            seed=42,
        )
        assert False, "should have raised ValueError"
    except ValueError as e:
        assert "frame_index" in str(e)
    print("  4. generator bad frame_index ok")


def test_generator_bad_prev_latent():
    gen = PSN_Video_Frame_Generator()
    try:
        gen.run(
            frame_index=0,
            total_frames=4,
            steps=20,
            cfg=7.0,
            sampler_name="euler",
            scheduler="normal",
            seed=42,
            prev_latent="not a latent",
        )
        assert False, "should have raised ValueError"
    except ValueError:
        pass
    print("  5. generator bad prev_latent ok")


def test_assembler_4_frames():
    loop = PSN_Video_Frame_Loop()
    (latents,) = loop.run(
        total_frames=4,
        steps=20,
        cfg=7.0,
        sampler_name="euler",
        scheduler="normal",
        seed=42,
    )
    assert isinstance(latents, list) and len(latents) == 4
    asm = PSN_Video_Assembler()
    (video,) = asm.run(latents, fps=24.0)
    assert isinstance(video, torch.Tensor)
    assert video.shape == (1, 4, 8, 8, 3), video.shape
    assert video.min() >= 0.0 and video.max() <= 1.0
    assert video.dtype == torch.float32
    print("  6. assembler 4 frames ok")


def test_assembler_single_latent():
    lat = _make_latent(torch.full((1, 4, 8, 8), 0.5))
    asm = PSN_Video_Assembler()
    (video,) = asm.run(lat, fps=30.0)
    assert video.shape == (1, 1, 8, 8, 3), video.shape
    print("  7. assembler single latent ok")


def test_assembler_empty_list():
    asm = PSN_Video_Assembler()
    try:
        asm.run([], fps=24.0)
        assert False, "should have raised ValueError"
    except ValueError as e:
        assert "empty" in str(e)
    print("  8. assembler empty list ok")


def test_assembler_mismatched_shapes():
    lat1 = _make_latent(torch.full((1, 4, 8, 8), 0.5))
    lat2 = _make_latent(torch.full((1, 4, 16, 16), 0.5))
    asm = PSN_Video_Assembler()
    try:
        asm.run([lat1, lat2], fps=24.0)
        assert False, "should have raised ValueError"
    except ValueError as e:
        assert "shape" in str(e)
    print("  9. assembler mismatched shapes ok")


def test_assembler_bad_fps():
    lat = _make_latent(torch.full((1, 4, 8, 8), 0.5))
    asm = PSN_Video_Assembler()
    try:
        asm.run(lat, fps=0.0)
        assert False, "should have raised ValueError"
    except ValueError as e:
        assert "fps" in str(e)
    print(" 10. assembler bad fps ok")


def test_loop_single_frame():
    loop = PSN_Video_Frame_Loop()
    (latents,) = loop.run(
        total_frames=1,
        steps=10,
        cfg=5.0,
        sampler_name="euler",
        scheduler="karras",
        seed=99,
    )
    assert len(latents) == 1
    x = latents[0]["samples"]
    assert x.dim() == 4
    assert x.min() >= 0.0 and x.max() <= 1.0
    print(" 11. loop single frame ok")


def test_no_inplace_mutation():
    gen = PSN_Video_Frame_Generator()
    prev = _make_latent(torch.full((1, 4, 8, 8), 0.5))
    prev_orig = prev["samples"].clone()
    cur, nxt = gen.run(
        frame_index=1,
        total_frames=4,
        steps=20,
        cfg=7.0,
        sampler_name="euler",
        scheduler="normal",
        seed=42,
        prev_latent=prev,
    )
    cur["samples"].fill_(0.0)
    assert torch.equal(prev["samples"], prev_orig)
    assert nxt["samples"].min() > 0.0
    print(" 12. no inplace mutation ok")


def test_input_types():
    for name, cls in NODE_CLASS_MAPPINGS.items():
        it = cls.INPUT_TYPES()
        assert "required" in it, name
        assert isinstance(cls.RETURN_TYPES, tuple), name
        assert isinstance(cls.RETURN_NAMES, tuple), name
        assert len(cls.RETURN_TYPES) == len(cls.RETURN_NAMES), name
    print(" 13. input types ok")


def main():
    test_mappings()
    test_generator_first_frame()
    test_generator_temporal()
    test_generator_bad_frame_index()
    test_generator_bad_prev_latent()
    test_assembler_4_frames()
    test_assembler_single_latent()
    test_assembler_empty_list()
    test_assembler_mismatched_shapes()
    test_assembler_bad_fps()
    test_loop_single_frame()
    test_no_inplace_mutation()
    test_input_types()
    print("ok")


if __name__ == "__main__":
    main()