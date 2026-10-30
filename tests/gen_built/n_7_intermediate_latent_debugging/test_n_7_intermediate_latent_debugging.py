import torch

from n_7_intermediate_latent_debugging import (
    PSN_Peek_Sampler,
    PSN_Peek_Visualizer,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _parse_peek_steps,
)


def _mock_denoise(model, conditioning, x, step, total_steps, cfg):
    """Mock denoiser: subtract a step-dependent constant so the latent changes."""
    return x - (step * 0.1)


def _mock_decode(samples):
    """Mock decode: [B,C,H,W] -> [B,H,W,3] by taking the first channel."""
    b, c, h, w = samples.shape
    img = samples[:, 0:1, :, :].permute(0, 2, 3, 1).repeat(1, 1, 1, 3)
    return img


def test_module_mappings():
    assert "PSN_Peek_Sampler" in NODE_CLASS_MAPPINGS
    assert "PSN_Peek_Visualizer" in NODE_CLASS_MAPPINGS
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_Peek_Sampler"] == "PSN Peek Sampler"
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_Peek_Visualizer"] == "PSN Peek Visualizer"


def test_input_types():
    it = PSN_Peek_Sampler.INPUT_TYPES()
    assert "latent" in it["required"]
    assert "steps" in it["required"]
    assert "peek_steps" in it["required"]
    assert PSN_Peek_Sampler.RETURN_TYPES == ("LATENT", "IMAGE")
    assert PSN_Peek_Sampler.FUNCTION == "run"
    assert PSN_Peek_Sampler.CATEGORY.startswith("ParametricStudio/")

    it2 = PSN_Peek_Visualizer.INPUT_TYPES()
    assert "peeks" in it2["required"]
    assert PSN_Peek_Visualizer.RETURN_TYPES == ("IMAGE",)


def test_sampler_produces_3_peeks():
    """Mock sampler: 10 steps, peeks at 1,5,10 -> 3 images."""
    node = PSN_Peek_Sampler()
    latent = {"samples": torch.randn(1, 4, 8, 8)}
    out_latent, peeks = node.run(
        model=None, positive=None, negative=None, latent=latent,
        seed=42, steps=10, cfg=7.0,
        sampler_name="euler", scheduler="normal",
        peek_steps="1,5,10",
        denoise_fn=_mock_denoise, decode_fn=_mock_decode,
    )
    assert isinstance(out_latent, dict)
    assert "samples" in out_latent
    assert out_latent["samples"].shape == (1, 4, 8, 8)
    # 3 peeks, each [1,8,8,3] -> stacked [3,8,8,3]
    assert peeks.shape == (3, 8, 8, 3)


def test_sampler_no_peeks():
    """Empty peek_steps -> empty image tensor."""
    node = PSN_Peek_Sampler()
    latent = {"samples": torch.randn(1, 4, 8, 8)}
    out_latent, peeks = node.run(
        model=None, positive=None, negative=None, latent=latent,
        seed=0, steps=5, cfg=1.0,
        peek_steps="",
        denoise_fn=_mock_denoise, decode_fn=_mock_decode,
    )
    assert peeks.shape[0] == 0


def test_sampler_does_not_mutate_input():
    """Input latent must not be modified in place."""
    node = PSN_Peek_Sampler()
    orig = torch.randn(1, 4, 8, 8)
    latent = {"samples": orig}
    snapshot = orig.clone()
    node.run(
        model=None, positive=None, negative=None, latent=latent,
        seed=1, steps=3, cfg=1.0, peek_steps="1,2,3",
        denoise_fn=_mock_denoise, decode_fn=_mock_decode,
    )
    assert torch.equal(latent["samples"], snapshot)


def test_visualizer_grid_1x3():
    """3 peek images [3,8,8,3] -> grid [1,8,24,3] (1 row, 3 cols)."""
    node = PSN_Peek_Visualizer()
    peeks = torch.randn(3, 8, 8, 3)
    grid = node.run(peeks=peeks)[0]
    assert grid.shape == (1, 8, 24, 3)


def test_visualizer_single_image():
    node = PSN_Peek_Visualizer()
    peeks = torch.randn(1, 4, 4, 3)
    grid = node.run(peeks=peeks)[0]
    assert grid.shape == (1, 4, 4, 3)


def test_parse_peek_steps_bad_input():
    """Non-integer token should raise."""
    try:
        _parse_peek_steps("1,abc,10", 10)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_parse_peek_steps_out_of_range():
    try:
        _parse_peek_steps("1,99", 10)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_sampler_bad_latent():
    """Latent without 'samples' key should raise."""
    node = PSN_Peek_Sampler()
    try:
        node.run(
            model=None, positive=None, negative=None, latent={},
            seed=0, steps=1, cfg=1.0, peek_steps="1",
            denoise_fn=_mock_denoise, decode_fn=_mock_decode,
        )
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_visualizer_empty_peeks():
    """Empty peeks tensor should raise."""
    node = PSN_Peek_Visualizer()
    try:
        node.run(peeks=torch.zeros((0, 8, 8, 3)))
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_visualizer_bad_dim():
    """3D tensor should raise."""
    node = PSN_Peek_Visualizer()
    try:
        node.run(peeks=torch.randn(8, 8, 3))
        assert False, "expected ValueError"
    except ValueError:
        pass


if __name__ == "__main__":
    test_module_mappings()
    test_input_types()
    test_sampler_produces_3_peeks()
    test_sampler_no_peeks()
    test_sampler_does_not_mutate_input()
    test_visualizer_grid_1x3()
    test_visualizer_single_image()
    test_parse_peek_steps_bad_input()
    test_parse_peek_steps_out_of_range()
    test_sampler_bad_latent()
    test_visualizer_empty_peeks()
    test_visualizer_bad_dim()
    print("ok")
