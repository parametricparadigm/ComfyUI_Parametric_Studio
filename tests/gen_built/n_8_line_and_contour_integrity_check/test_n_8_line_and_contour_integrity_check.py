import torch

from n_8_line_and_contour_integrity_check import (
    PSN_CV_LineIntegrity,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def make_image(mask):
    """(H,W) 0/1 -> IMAGE [1,H,W,3] float 0..1."""
    m = (mask > 0).to(torch.float32)
    return m[None, :, :, None].repeat(1, 1, 1, 3)


def broken_square(size=64, gap=6):
    """64x64 square outline with a gap of `gap` pixels in the middle of the top edge."""
    m = torch.zeros(size, size, dtype=torch.float32)
    m[5, 5:-5] = 1.0      # top
    m[-5, 5:-5] = 1.0     # bottom
    m[5:-5, 5] = 1.0      # left
    m[5:-5, -5] = 1.0     # right
    # punch a gap in the top edge
    c = size // 2
    m[5, c - gap // 2:c + gap // 2] = 0.0
    return m


def test_module_mappings():
    assert "PSN_CV_LineIntegrity" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_CV_LineIntegrity"] is PSN_CV_LineIntegrity
    assert "PSN_CV_LineIntegrity" in NODE_DISPLAY_NAME_MAPPINGS
    assert isinstance(NODE_DISPLAY_NAME_MAPPINGS["PSN_CV_LineIntegrity"], str)


def test_input_types_schema():
    it = PSN_CV_LineIntegrity.INPUT_TYPES()
    assert "required" in it
    req = it["required"]
    assert req["image"] == ("IMAGE",)
    assert req["gap_threshold"][0] == "INT"
    assert req["min_line_length"][0] == "INT"
    assert PSN_CV_LineIntegrity.RETURN_TYPES == ("IMAGE", "INT", "FLOAT")
    assert PSN_CV_LineIntegrity.RETURN_NAMES == ("cleaned_image", "line_count", "integrity_score")
    assert PSN_CV_LineIntegrity.FUNCTION == "run"
    assert PSN_CV_LineIntegrity.CATEGORY.startswith("ParametricStudio/")


def test_broken_square_gap_closed_and_lines():
    node = PSN_CV_LineIntegrity()
    img = make_image(broken_square(gap=6))
    cleaned, lines, score = node.run(img, gap_threshold=8, min_line_length=10)
    # output shapes
    assert cleaned.shape == (1, 64, 64, 3)
    assert cleaned.dtype == torch.float32
    assert cleaned.min() >= 0.0 and cleaned.max() <= 1.0
    # gap in the top edge must be closed: the previously-zero pixels are now 1
    c = 32
    top = cleaned[0, 5, c - 3:c + 3, 0]
    assert top.min() >= 0.99, f"gap not closed: {top.tolist()}"
    # 4 sides of the square -> at least 4 straight lines detected
    assert lines >= 4, f"expected >=4 lines, got {lines}"
    # all endpoints bridged -> integrity 1.0
    assert abs(score - 1.0) < 1e-9, f"score {score}"


def test_intact_square_no_bridging_needed():
    node = PSN_CV_LineIntegrity()
    m = torch.zeros(64, 64, dtype=torch.float32)
    m[5, 5:-5] = 1.0
    m[-5, 5:-5] = 1.0
    m[5:-5, 5] = 1.0
    m[5:-5, -5] = 1.0
    img = make_image(m)
    cleaned, lines, score = node.run(img, gap_threshold=8, min_line_length=10)
    assert lines >= 4
    # no endpoints -> integrity 1.0 by definition
    assert score == 1.0


def test_gap_too_large_not_bridged():
    node = PSN_CV_LineIntegrity()
    img = make_image(broken_square(gap=20))
    cleaned, lines, score = node.run(img, gap_threshold=4, min_line_length=10)
    c = 32
    top = cleaned[0, 5, c - 8:c + 8, 0]
    # with gap_threshold=4 the 20px gap must remain open
    assert top.max() < 0.5, f"gap should stay open: {top.tolist()}"
    # endpoints exist but none bridged -> score 0.0
    assert score == 0.0


def test_bad_input_raises():
    node = PSN_CV_LineIntegrity()
    # wrong rank
    try:
        node.run(torch.zeros(64, 64, 3), 4, 10)
        raise AssertionError("expected ValueError for wrong rank")
    except ValueError:
        pass
    # non-tensor
    try:
        node.run("not a tensor", 4, 10)
        raise AssertionError("expected TypeError for non-tensor")
    except TypeError:
        pass


def test_empty_image_edge_case():
    node = PSN_CV_LineIntegrity()
    img = make_image(torch.zeros(32, 32, dtype=torch.float32))
    cleaned, lines, score = node.run(img, gap_threshold=4, min_line_length=10)
    assert cleaned.shape == (1, 32, 32, 3)
    assert lines == 0
    assert score == 1.0  # no endpoints -> vacuously intact
    assert cleaned.max() == 0.0


def test_input_not_modified_in_place():
    node = PSN_CV_LineIntegrity()
    m = broken_square(gap=6)
    img = make_image(m)
    before = img.clone()
    node.run(img, gap_threshold=8, min_line_length=10)
    assert torch.equal(img, before), "input image was modified in place"


def test_grayscale_canny_path():
    """A soft (non-binary) line drawing should go through the Canny path."""
    node = PSN_CV_LineIntegrity()
    m = torch.zeros(64, 64, dtype=torch.float32)
    # soft horizontal line with varying intensity (not binary)
    for j in range(10, 54):
        m[32, j] = 0.3 + 0.5 * (j % 7) / 7.0
    img = make_image(m)
    cleaned, lines, score = node.run(img, gap_threshold=4, min_line_length=10)
    assert cleaned.shape == (1, 64, 64, 3)
    assert isinstance(lines, int)
    assert 0.0 <= score <= 1.0


if __name__ == "__main__":
    test_module_mappings()
    test_input_types_schema()
    test_broken_square_gap_closed_and_lines()
    test_intact_square_no_bridging_needed()
    test_gap_too_large_not_bridged()
    test_bad_input_raises()
    test_empty_image_edge_case()
    test_input_not_modified_in_place()
    test_grayscale_canny_path()
    print("ok")
