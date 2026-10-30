"""Tests for psn_nodes.gen.n_4_technical_schematic_overlay."""

import json
import math

import pytest

from psn_nodes.gen.n_4_technical_schematic_overlay import (
    PSN_Schematic_Overlay,
    PSN_Schematic_Annotation,
    _build_overlay_payload,
    _build_annotation_payload,
    _normalize_color,
    _validate_hex_color,
)


class TestColorValidation:
    def test_valid_hex_colors(self):
        assert _validate_hex_color("#FFF")
        assert _validate_hex_color("#0000FF")
        assert _validate_hex_color("#a1b2c3")

    def test_invalid_hex_colors(self):
        assert not _validate_hex_color("FFF")
        assert not _validate_hex_color("#GGG")
        assert not _validate_hex_color("#12345")
        assert not _validate_hex_color("")
        assert not _validate_hex_color(None)

    def test_normalize_expands_short_hex(self):
        assert _normalize_color("#F00") == "#ff0000"

    def test_normalize_named_color(self):
        assert _normalize_color("blue") == "blue"

    def test_normalize_rejects_bad_color(self):
        with pytest.raises(ValueError):
            _normalize_color("not-a-color")


class TestOverlayPayload:
    def test_blueprint_payload(self):
        p = _build_overlay_payload("blueprint", "#0000FF", 0.5)
        assert p["overlay_type"] == "blueprint"
        assert p["line_color"] == "#0000ff"
        assert p["opacity"] == 0.5
        assert p["invert_colors"] is True
        assert p["grid"]["enabled"] is True

    def test_wireframe_payload(self):
        p = _build_overlay_payload("wireframe", "white", 1.0)
        assert p["overlay_type"] == "wireframe"
        assert p["line_color"] == "white"
        assert p["edge_detection"]["enabled"] is True

    def test_grid_payload(self):
        p = _build_overlay_payload("grid", "#123456", 0.25)
        assert p["overlay_type"] == "grid"
        assert p["grid"]["enabled"] is True

    def test_opacity_clamped(self):
        p = _build_overlay_payload("grid", "black", 5.0)
        assert p["opacity"] == 1.0
        p2 = _build_overlay_payload("grid", "black", -1.0)
        assert p2["opacity"] == 0.0

    def test_invalid_overlay_type(self):
        with pytest.raises(ValueError):
            _build_overlay_payload("neon", "white", 0.5)

    def test_invalid_opacity_nan(self):
        with pytest.raises(ValueError):
            _build_overlay_payload("grid", "white", float("nan"))


class TestAnnotationPayload:
    def test_basic_annotation(self):
        p = _build_annotation_payload("Label", 10.0, 20.0, 16)
        assert p["text"] == "Label"
        assert p["position"] == {"x": 10.0, "y": 20.0}
        assert p["font_size"] == 16
        assert p["leader_line"]["enabled"] is True

    def test_empty_text_rejected(self):
        with pytest.raises(ValueError):
            _build_annotation_payload("", 0.0, 0.0, 16)

    def test_too_long_text_rejected(self):
        with pytest.raises(ValueError):
            _build_annotation_payload("x" * 513, 0.0, 0.0, 16)

    def test_font_size_out_of_range(self):
        with pytest.raises(ValueError):
            _build_annotation_payload("A", 0.0, 0.0, 0)
        with pytest.raises(ValueError):
            _build_annotation_payload("A", 0.0, 0.0, 513)

    def test_non_finite_position_rejected(self):
        with pytest.raises(ValueError):
            _build_annotation_payload("A", float("inf"), 0.0, 16)


class TestNodeRun:
    def test_overlay_node_returns_json(self):
        node = PSN_Schematic_Overlay()
        (payload_str,) = node.run("blueprint", "#0000FF", 0.5)
        data = json.loads(payload_str)
        assert data["node"] == "PSN_Schematic_Overlay"
        assert data["overlay_type"] == "blueprint"

    def test_annotation_node_returns_json(self):
        node = PSN_Schematic_Annotation()
        (payload_str,) = node.run("Spec", 100.0, 200.0, 24)
        data = json.loads(payload_str)
        assert data["node"] == "PSN_Schematic_Annotation"
        assert data["text"] == "Spec"
        assert data["font_size"] == 24

    def test_overlay_node_bad_color_raises(self):
        node = PSN_Schematic_Overlay()
        with pytest.raises(ValueError):
            node.run("grid", "invalid-color", 0.5)

    def test_annotation_node_bad_font_raises(self):
        node = PSN_Schematic_Annotation()
        with pytest.raises(ValueError):
            node.run("A", 0.0, 0.0, 9999)
