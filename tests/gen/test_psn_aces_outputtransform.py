"""
Tests for psn_nodes.gen.psn_aces_outputtransform
"""

import math
import pytest

from psn_nodes.gen.psn_aces_outputtransform import (
    PSN_ACES_OutputTransform,
    OUTPUT_SPACES,
    TONE_MAPPINGS,
    validate_config,
    parse_config_json,
    apply_tone_mapping,
    tone_map_reinhard,
    tone_map_narkowicz,
    tone_map_aces_rrt,
    dither_quantize,
    transform_pixel,
    aces_to_srgb_linear,
    srgb_linear_to_aces,
    _srgb_to_linear,
    _linear_to_srgb,
)


class TestValidateConfig:
    def test_valid_config(self):
        ok, reason = validate_config("sRGB", "None", 0.0)
        assert ok is True
        assert reason == "ok"

    def test_invalid_output_space(self):
        ok, reason = validate_config("Invalid", "None", 0.0)
        assert ok is False
        assert "output_space" in reason

    def test_invalid_tone_mapping(self):
        ok, reason = validate_config("sRGB", "Invalid", 0.0)
        assert ok is False
        assert "tone_mapping" in reason

    def test_exposure_out_of_range(self):
        ok, reason = validate_config("sRGB", "None", 100.0)
        assert ok is False
        assert "exposure" in reason

    def test_exposure_nan(self):
        ok, reason = validate_config("sRGB", "None", float("nan"))
        assert ok is False
        assert "finite" in reason

    def test_exposure_inf(self):
        ok, reason = validate_config("sRGB", "None", float("inf"))
        assert ok is False
        assert "finite" in reason


class TestParseConfigJson:
    def test_valid_json(self):
        ok, config, reason = parse_config_json('{"output_space": "sRGB", "tone_mapping": "Reinhard", "exposure": 0.5}')
        assert ok is True
        assert config["output_space"] == "sRGB"
        assert config["tone_mapping"] == "Reinhard"
        assert config["exposure"] == 0.5

    def test_invalid_json(self):
        ok, config, reason = parse_config_json("not json")
        assert ok is False
        assert config is None
        assert "invalid JSON" in reason

    def test_json_not_object(self):
        ok, config, reason = parse_config_json("[1, 2, 3]")
        assert ok is False
        assert "object" in reason

    def test_json_invalid_space(self):
        ok, config, reason = parse_config_json('{"output_space": "Bad", "tone_mapping": "None", "exposure": 0}')
        assert ok is False
        assert "output_space" in reason


class TestToneMapping:
    def test_reinhard_identity_at_zero(self):
        assert tone_map_reinhard(0.0) == 0.0

    def test_reinhard_compresses_highlights(self):
        assert tone_map_reinhard(10.0) < 10.0
        assert tone_map_reinhard(10.0) > 0.0

    def test_narkowicz_identity_at_zero(self):
        assert abs(tone_map_narkowicz(0.0)) < 1e-10

    def test_aces_rrt_compresses_highlights(self):
        assert tone_map_aces_rrt(10.0) < 10.0
        assert tone_map_aces_rrt(10.0) > 0.0

    def test_apply_tone_mapping_none(self):
        assert apply_tone_mapping(0.5, "None", 0.0) == 0.5

    def test_apply_tone_mapping_with_exposure(self):
        # Exposure of 1 stop doubles the value
        result = apply_tone_mapping(0.5, "None", 1.0)
        assert abs(result - 1.0) < 1e-10

    def test_apply_tone_mapping_invalid(self):
        with pytest.raises(ValueError):
            apply_tone_mapping(0.5, "Invalid", 0.0)


class TestDitherQuantize:
    def test_quantize_8bit(self):
        result = dither_quantize(0.5, bit_depth=8, seed=0)
        assert 0.0 <= result <= 1.0
        # Should be close to 0.5
        assert abs(result - 0.5) < 0.01

    def test_quantize_clamps(self):
        assert dither_quantize(2.0, bit_depth=8, seed=0) == 1.0
        assert dither_quantize(-1.0, bit_depth=8, seed=0) == 0.0

    def test_invalid_bit_depth(self):
        with pytest.raises(ValueError):
            dither_quantize(0.5, bit_depth=0)
        with pytest.raises(ValueError):
            dither_quantize(0.5, bit_depth=33)


class TestColorSpaceConversion:
    def test_srgb_round_trip(self):
        # sRGB -> linear -> sRGB should be near-identity
        for c in [0.0, 0.1, 0.5, 0.9, 1.0]:
            linear = _srgb_to_linear(c)
            back = _linear_to_srgb(linear)
            assert abs(back - c) < 1e-6, f"Round trip failed for {c}: {back}"

    def test_aces_srgb_round_trip(self):
        # ACES -> sRGB linear -> ACES should be near-identity
        # Note: The matrices are approximations, so we use a looser tolerance
        rgb = (0.2, 0.3, 0.4)
        srgb = aces_to_srgb_linear(rgb)
        back = srgb_linear_to_aces(srgb)
        for i in range(3):
            assert abs(back[i] - rgb[i]) < 0.1, f"Round trip failed for channel {i}: {back[i]} vs {rgb[i]}"


class TestTransformPixel:
    def test_srgb_output(self):
        # A mid-gray ACES pixel should produce a valid sRGB output
        rgb_aces = (0.18, 0.18, 0.18)
        result = transform_pixel(rgb_aces, "sRGB", "None", 0.0, bit_depth=32)
        assert len(result) == 3
        for c in result:
            assert 0.0 <= c <= 1.0

    def test_hdr10_output_can_exceed_one(self):
        # A bright ACES pixel with no tone mapping should produce HDR values > 1.0
        rgb_aces = (1.0, 1.0, 1.0)
        result = transform_pixel(rgb_aces, "HDR10_PQ", "None", 0.0, bit_depth=32)
        assert len(result) == 3
        # At least one channel should be > 1.0 for a bright input
        assert any(c > 1.0 for c in result)

    def test_invalid_config_raises(self):
        with pytest.raises(ValueError):
            transform_pixel((0.1, 0.1, 0.1), "Invalid", "None", 0.0)

    def test_tone_mapping_reduces_highlights(self):
        rgb_aces = (1.0, 1.0, 1.0)
        no_tm = transform_pixel(rgb_aces, "sRGB", "None", 0.0, bit_depth=32)
        with_tm = transform_pixel(rgb_aces, "sRGB", "Reinhard", 0.0, bit_depth=32)
        # Reinhard should reduce the output values
        for i in range(3):
            assert with_tm[i] <= no_tm[i] + 1e-6


class TestNode:
    def test_node_valid(self):
        node = PSN_ACES_OutputTransform()
        status, reason, exposure = node.run("sRGB", "None", 0.0)
        assert status == "ok"
        assert reason == "ok"
        assert exposure == 0.0

    def test_node_invalid_space(self):
        node = PSN_ACES_OutputTransform()
        status, reason, exposure = node.run("Invalid", "None", 0.0)
        assert status == "error"
        assert "output_space" in reason

    def test_node_with_config_json(self):
        node = PSN_ACES_OutputTransform()
        config_json = '{"output_space": "Display_P3", "tone_mapping": "ACES_RRT", "exposure": 0.5}'
        status, reason, exposure = node.run("sRGB", "None", 0.0, config_json=config_json)
        assert status == "ok"
        assert exposure == 0.5

    def test_node_with_invalid_config_json(self):
        node = PSN_ACES_OutputTransform()
        status, reason, exposure = node.run("sRGB", "None", 0.0, config_json="bad json")
        assert status == "error"
        assert "invalid JSON" in reason

    def test_node_input_types(self):
        inputs = PSN_ACES_OutputTransform.INPUT_TYPES()
        assert "required" in inputs
        assert "output_space" in inputs["required"]
        assert "tone_mapping" in inputs["required"]
        assert "exposure" in inputs["required"]

    def test_node_return_types(self):
        assert PSN_ACES_OutputTransform.RETURN_TYPES == ("STRING", "STRING", "FLOAT")
        assert PSN_ACES_OutputTransform.RETURN_NAMES == ("status", "reason", "exposure_applied")
        assert PSN_ACES_OutputTransform.FUNCTION == "run"
        assert PSN_ACES_OutputTransform.CATEGORY == "ParametricStudio/Color"
