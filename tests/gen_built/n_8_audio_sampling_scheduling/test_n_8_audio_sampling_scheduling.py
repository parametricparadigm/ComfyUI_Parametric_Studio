"""Tests for n_8_audio_sampling_scheduling."""

import torch

from n_8_audio_sampling_scheduling import (
    PSN_AudioScheduler,
    PSN_AudioSampler,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def test_scheduler_linear():
    node = PSN_AudioScheduler()
    (sigmas,) = node.run(steps=10, scheduler_type="Linear", sigma_max=1.0, sigma_min=0.001)
    assert isinstance(sigmas, torch.Tensor)
    assert sigmas.dim() == 1
    assert sigmas.numel() == 11  # steps + 1
    assert sigmas[0].item() == 1.0
    assert sigmas[-1].item() == 0.0
    # Monotonically decreasing
    for i in range(len(sigmas) - 1):
        assert sigmas[i].item() >= sigmas[i + 1].item()


def test_scheduler_karras():
    node = PSN_AudioScheduler()
    (sigmas,) = node.run(steps=20, scheduler_type="Karras", sigma_max=1.0, sigma_min=0.001)
    assert sigmas.numel() == 21
    assert sigmas[0].item() == 1.0
    assert sigmas[-1].item() == 0.0
    for i in range(len(sigmas) - 1):
        assert sigmas[i].item() >= sigmas[i + 1].item()


def test_scheduler_audio_optimized():
    node = PSN_AudioScheduler()
    (sigmas,) = node.run(steps=15, scheduler_type="AudioOptimized", sigma_max=1.0, sigma_min=0.001)
    assert sigmas.numel() == 16
    assert sigmas[0].item() == 1.0
    assert sigmas[-1].item() == 0.0
    for i in range(len(sigmas) - 1):
        assert sigmas[i].item() >= sigmas[i + 1].item()


def test_scheduler_bad_steps():
    node = PSN_AudioScheduler()
    try:
        node.run(steps=0, scheduler_type="Linear", sigma_max=1.0, sigma_min=0.001)
        assert False, "should have raised"
    except ValueError:
        pass


def test_scheduler_bad_sigma():
    node = PSN_AudioScheduler()
    try:
        node.run(steps=10, scheduler_type="Linear", sigma_max=0.5, sigma_min=0.5)
        assert False, "should have raised"
    except ValueError:
        pass


def test_sampler_basic():
    node = PSN_AudioSampler()
    latent = {"samples": torch.randn(1, 4, 8, 16)}
    sigmas = torch.linspace(1.0, 0.0, 11)
    (audio,) = node.run(latent=latent, sigmas=sigmas, sampler="Euler", sample_rate=22050)
    assert isinstance(audio, dict)
    assert "waveform" in audio
    assert "sample_rate" in audio
    assert audio["sample_rate"] == 22050
    wf = audio["waveform"]
    assert isinstance(wf, torch.Tensor)
    assert wf.shape[0] == 1
    assert wf.abs().max().item() <= 1.0 + 1e-6


def test_sampler_with_positive():
    node = PSN_AudioSampler()
    latent = {"samples": torch.randn(1, 4, 8, 16)}
    sigmas = torch.linspace(1.0, 0.0, 11)
    positive = torch.randn(1, 4, 8, 16)
    (audio,) = node.run(latent=latent, sigmas=sigmas, sampler="Euler", sample_rate=16000, positive=positive)
    assert audio["sample_rate"] == 16000
    assert audio["waveform"].shape[0] == 1


def test_sampler_bad_sigmas():
    node = PSN_AudioSampler()
    latent = {"samples": torch.randn(1, 4, 8, 16)}
    sigmas = torch.tensor([1.0])  # too short
    try:
        node.run(latent=latent, sigmas=sigmas, sampler="Euler", sample_rate=22050)
        assert False, "should have raised"
    except ValueError:
        pass


def test_node_mappings():
    assert "PSN_AudioScheduler" in NODE_CLASS_MAPPINGS
    assert "PSN_AudioSampler" in NODE_CLASS_MAPPINGS
    assert "PSN_AudioScheduler" in NODE_DISPLAY_NAME_MAPPINGS
    assert "PSN_AudioSampler" in NODE_DISPLAY_NAME_MAPPINGS


def test_input_types():
    it = PSN_AudioScheduler.INPUT_TYPES()
    assert "required" in it
    assert "steps" in it["required"]
    assert "scheduler_type" in it["required"]

    it2 = PSN_AudioSampler.INPUT_TYPES()
    assert "required" in it2
    assert "latent" in it2["required"]
    assert "sigmas" in it2["required"]


if __name__ == "__main__":
    test_scheduler_linear()
    test_scheduler_karras()
    test_scheduler_audio_optimized()
    test_scheduler_bad_steps()
    test_scheduler_bad_sigma()
    test_sampler_basic()
    test_sampler_with_positive()
    test_sampler_bad_sigmas()
    test_node_mappings()
    test_input_types()
    print("ok")
