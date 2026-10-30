"""Tests for psn_nodes.gen.psn_filmemulation (pure-logic film emulation)."""

import json

from psn_nodes.gen.psn_filmemulation import (
    PSN_FilmEmulation,
    validate_film_stock,
    validate_iso,
    validate_grain,
    validate_halation,
    build_lut,
    compute_grain_scale,
    compute_halation_threshold,
    generate_grain_mask,
    generate_halation_mask,
    combine_masks,
    apply_lut_to_pixel,
    FILM_STOCKS,
)


def test_validate_film_stock_allow_list():
    for stock in FILM_STOCKS:
        ok, _ = validate_film_stock(stock)
        assert ok, "expected %s to be valid" % stock
    ok, why = validate_film_stock("Nikon_Film_999")
    assert not ok
    assert "allow-list" in why
    ok, why = validate_film_stock(123)
    assert not ok
    assert "string" in why


def test_validate_iso_clamping_and_bad_input():
    ok, val, _ = validate_iso(400)
    assert ok and val == 400
    ok, val, why = validate_iso(99999)
    assert ok and val == 12800
    assert "clamped" in why
    ok, val, why = validate_iso(10)
    assert ok and val == 25
    ok, val, why = validate_iso("400")
    assert not ok
    assert "integer" in why
    ok, val, why = validate_iso(True)
    assert not ok


def test_validate_grain_and_halation():
    ok, val, _ = validate_grain(0.5)
    assert ok and val == 0.5
    ok, val, why = validate_grain(2.0)
    assert ok and val == 1.0
    assert "clamped" in why
    ok, val, why = validate_grain(-1.0)
    assert ok and val == 0.0
    ok, val, why = validate_grain("0.5")
    assert not ok
    ok, val, why = validate_halation(0.3)
    assert ok and val == 0.3
    ok, val, why = validate_halation(5.0)
    assert ok and val == 1.0


def test_build_lut_is_256_and_monotonic_non_decreasing():
    lut = build_lut("Kodak_Portra_400", 400)
    assert len(lut) == 256
    for i in range(1, 256):
        assert lut[i] >= lut[i - 1] - 1e-9, "LUT must be non-decreasing"
    assert 0.0 <= lut[0] <= 1.0
    assert 0.0 <= lut[255] <= 1.0


def test_grain_scale_increases_with_iso_and_resolution():
    base = compute_grain_scale(100, 0.5, 512, 512)
    high_iso = compute_grain_scale(8000, 0.5, 512, 512)
    assert high_iso > base, "higher ISO should increase grain scale"
    high_res = compute_grain_scale(100, 0.5, 2048, 2048)
    assert high_res > base, "higher resolution should increase grain scale"
    zero = compute_grain_scale(100, 0.0, 512, 512)
    assert zero == 0.0


def test_halation_threshold_decreases_with_intensity():
    t_low = compute_halation_threshold(0.0, 0.05)
    t_high = compute_halation_threshold(1.0, 0.05)
    assert t_high < t_low, "more halation should lower the threshold"
    assert 0.0 <= t_high <= 1.0
    assert 0.0 <= t_low <= 1.0


def test_grain_mask_deterministic_and_bounded():
    m1 = generate_grain_mask(4, 4, 0.5, 12345)
    m2 = generate_grain_mask(4, 4, 0.5, 12345)
    assert m1 == m2, "same seed must produce same mask"
    assert len(m1) == 16
    for v in m1:
        assert 0.0 <= v <= 1.0
    m3 = generate_grain_mask(4, 4, 0.5, 99999)
    assert m1 != m3, "different seeds should differ"


def test_combine_masks_takes_max():
    g = [0.1, 0.9, 0.5]
    h = [0.3, 0.2, 0.7]
    c = combine_masks(g, h)
    assert c == [0.3, 0.9, 0.7]


def test_apply_lut_to_pixel_bounds_and_bad_input():
    lut = build_lut("Fuji_Velvia_50", 100)
    assert apply_lut_to_pixel(0.0, lut) >= 0.0
    assert apply_lut_to_pixel(1.0, lut) <= 1.0
    assert apply_lut_to_pixel(2.0, lut) == apply_lut_to_pixel(1.0, lut)
    assert apply_lut_to_pixel(-1.0, lut) == apply_lut_to_pixel(0.0, lut)
    assert apply_lut_to_pixel("bad", lut) == 0.0


def test_node_run_valid_and_invalid_inputs():
    node = PSN_FilmEmulation()
    lut_json, grain_json, hal_json, grain_scale, hal_thr = node.run(
        "Kodak_Portra_400", 400, 0.5, 0.3, 8, 8
    )
    lut = json.loads(lut_json)
    assert len(lut) == 256
    grain = json.loads(grain_json)
    hal = json.loads(hal_json)
    assert len(grain) == 64
    assert len(hal) == 64
    assert grain_scale > 0.0
    assert 0.0 <= hal_thr <= 1.0

    lut_json2, grain_json2, hal_json2, gs2, ht2 = node.run(
        "Bad_Film", 400, 0.5, 0.3, 8, 8
    )
    assert lut_json2 == "{}"
    assert grain_json2 == "[]"
    assert hal_json2 == "[]"
    assert gs2 == 0.0
    assert ht2 == 0.0

    lut_json3, grain_json3, hal_json3, gs3, ht3 = node.run(
        "Kodak_Portra_400", "not_an_int", 0.5, 0.3, 8, 8
    )
    assert lut_json3 == "{}"
    assert gs3 == 0.0
