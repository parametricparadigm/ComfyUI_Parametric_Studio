import torch

from n_9_frequency_domain_artifact_detection import (
    PSN_CV_FrequencyArtifact,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _as_image,
    _grayscale,
    _radial_average_amplitude,
    _artifact_score,
)


def make_clean_image(h=64, w=64, c=3, b=1):
    """A smooth gradient image (low frequency content)."""
    ys = torch.linspace(0, 1, h)
    xs = torch.linspace(0, 1, w)
    yy, xx = torch.meshgrid(ys, xs, indexing="ij")
    img = (yy * 0.5 + xx * 0.5).unsqueeze(-1).expand(b, h, w, c).clone()
    return img


def make_artifact_image(h=64, w=64, c=3, b=1):
    """A smooth gradient + high-frequency noise (simulates compression artifacts)."""
    base = make_clean_image(h, w, c, b)
    noise = torch.rand(b, h, w, c) * 0.5 - 0.25  # high-freq noise
    img = (base + noise).clamp(0, 1)
    return img


def test_module_mappings():
    assert "PSN_CV_FrequencyArtifact" in NODE_CLASS_MAPPINGS
    assert "PSN_CV_FrequencyArtifact" in NODE_DISPLAY_NAME_MAPPINGS
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_CV_FrequencyArtifact"] == "Frequency Domain Artifact Detection"


def test_input_types():
    it = PSN_CV_FrequencyArtifact.INPUT_TYPES()
    assert "image" in it["required"]
    assert "artifact_threshold" in it["required"]
    assert PSN_CV_FrequencyArtifact.RETURN_TYPES == ("IMAGE", "FLOAT", "BOOLEAN")
    assert PSN_CV_FrequencyArtifact.FUNCTION == "run"
    assert PSN_CV_FrequencyArtifact.CATEGORY.startswith("ParametricStudio/")


def test_clean_image_low_score():
    node = PSN_CV_FrequencyArtifact()
    img = make_clean_image(64, 64, 3, 1)
    plot, score, has = node.run(img, 0.1)
    assert isinstance(plot, torch.Tensor)
    assert plot.shape == (1, 256, 512, 3)
    assert plot.min() >= 0.0 and plot.max() <= 1.0
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0
    assert isinstance(has, bool)
    # Clean image should have low artifact score
    assert score < 0.5, f"clean image score too high: {score}"


def test_artifact_image_higher_score():
    node = PSN_CV_FrequencyArtifact()
    clean = make_clean_image(64, 64, 3, 1)
    artifact = make_artifact_image(64, 64, 3, 1)
    _, score_clean, _ = node.run(clean, 0.1)
    _, score_art, has_art = node.run(artifact, 0.1)
    # Artifact image should score higher than clean
    assert score_art > score_clean, f"artifact score {score_art} not > clean {score_clean}"
    assert has_art is True or score_art > 0.1


def test_bad_input_type():
    node = PSN_CV_FrequencyArtifact()
    try:
        node.run("not a tensor", 0.1)
        assert False, "should have raised TypeError"
    except TypeError:
        pass


def test_bad_input_shape():
    node = PSN_CV_FrequencyArtifact()
    bad = torch.rand(1, 64, 64)  # missing channel dim
    try:
        node.run(bad, 0.1)
        assert False, "should have raised ValueError"
    except ValueError:
        pass


def test_nan_input():
    node = PSN_CV_FrequencyArtifact()
    img = make_clean_image(32, 32, 3, 1)
    img[0, 0, 0, 0] = float("nan")
    try:
        node.run(img, 0.1)
        assert False, "should have raised ValueError for NaN"
    except ValueError:
        pass


def test_batch_processing():
    node = PSN_CV_FrequencyArtifact()
    img = make_clean_image(32, 32, 3, 4)  # batch of 4
    plot, score, has = node.run(img, 0.1)
    assert plot.shape[0] == 1  # plot is single image
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0


def test_grayscale_conversion():
    img = torch.rand(1, 8, 8, 3)
    g = _grayscale(img)
    assert g.shape == (1, 8, 8)
    assert g.min() >= 0.0 and g.max() <= 1.0


def test_radial_average_shape():
    g = torch.rand(2, 16, 16)
    raas = _radial_average_amplitude(g)
    assert raas.shape == (2, 8)  # min(16,16)//2 = 8
    assert raas.min() >= 0.0


def test_no_inplace_modification():
    node = PSN_CV_FrequencyArtifact()
    img = make_clean_image(32, 32, 3, 1)
    img_copy = img.clone()
    node.run(img, 0.1)
    assert torch.equal(img, img_copy), "input was modified in place"


if __name__ == "__main__":
    test_module_mappings()
    test_input_types()
    test_clean_image_low_score()
    test_artifact_image_higher_score()
    test_bad_input_type()
    test_bad_input_shape()
    test_nan_input()
    test_batch_processing()
    test_grayscale_conversion()
    test_radial_average_shape()
    test_no_inplace_modification()
    print("ok")
