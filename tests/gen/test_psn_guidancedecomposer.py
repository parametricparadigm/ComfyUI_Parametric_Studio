"""Tests for PSN_GuidanceDecomposer."""

import json
import math
import pytest

from psn_nodes.gen.psn_guidancedecomposer import (
    PSN_GuidanceDecomposer,
    _parse_vector,
    _parse_axis,
    _magnitude,
    _angle,
    _direction,
    _scale,
    _projection,
    _residual,
    _composite,
)


class TestParseVector:
    def test_valid_json_string(self):
        x, y = _parse_vector("[3.0, 4.0]")
        assert x == 3.0
        assert y == 4.0

    def test_valid_list(self):
        x, y = _parse_vector([1.5, -2.5])
        assert x == 1.5
        assert y == -2.5

    def test_invalid_json_string(self):
        with pytest.raises(ValueError):
            _parse_vector("not json")

    def test_wrong_length(self):
        with pytest.raises(ValueError):
            _parse_vector("[1.0, 2.0, 3.0]")

    def test_non_numeric_component(self):
        with pytest.raises(ValueError):
            _parse_vector("[1.0, 'abc']")

    def test_non_finite_component(self):
        with pytest.raises(ValueError):
            _parse_vector("[inf, 0.0]")


class TestParseAxis:
    def test_valid_json_string(self):
        ax, ay = _parse_axis("[0.0, 1.0]")
        assert ax == 0.0
        assert ay == 1.0

    def test_invalid_axis(self):
        with pytest.raises(ValueError):
            _parse_axis("[1.0]")


class TestMagnitude:
    def test_basic(self):
        assert _magnitude(3.0, 4.0) == pytest.approx(5.0)

    def test_zero(self):
        assert _magnitude(0.0, 0.0) == 0.0

    def test_negative(self):
        assert _magnitude(-3.0, -4.0) == pytest.approx(5.0)


class TestAngle:
    def test_positive_x(self):
        assert _angle(1.0, 0.0) == pytest.approx(0.0)

    def test_positive_y(self):
        assert _angle(0.0, 1.0) == pytest.approx(math.pi / 2)

    def test_negative_x(self):
        assert _angle(-1.0, 0.0) == pytest.approx(math.pi)

    def test_negative_y(self):
        assert _angle(0.0, -1.0) == pytest.approx(-math.pi / 2)


class TestDirection:
    def test_unit_vector(self):
        dx, dy = _direction(3.0, 4.0, 5.0)
        assert dx == pytest.approx(0.6)
        assert dy == pytest.approx(0.8)

    def test_zero_magnitude(self):
        dx, dy = _direction(0.0, 0.0, 0.0)
        assert dx == 0.0
        assert dy == 0.0


class TestScale:
    def test_absolute(self):
        assert _scale(5.0, 10.0, "absolute") == pytest.approx(0.5)

    def test_normalized(self):
        assert _scale(5.0, 5.0, "normalized") == pytest.approx(0.5)

    def test_clamped(self):
        assert _scale(15.0, 10.0, "clamped") == pytest.approx(1.0)

    def test_absolute_bad_reference(self):
        with pytest.raises(ValueError):
            _scale(5.0, 0.0, "absolute")

    def test_unknown_mode(self):
        with pytest.raises(ValueError):
            _scale(5.0, 1.0, "unknown")


class TestProjection:
    def test_parallel(self):
        assert _projection(3.0, 0.0, 1.0, 0.0) == pytest.approx(3.0)

    def test_perpendicular(self):
        assert _projection(0.0, 3.0, 1.0, 0.0) == pytest.approx(0.0)

    def test_zero_axis(self):
        assert _projection(1.0, 1.0, 0.0, 0.0) == 0.0


class TestResidual:
    def test_parallel_residual_zero(self):
        rx, ry = _residual(3.0, 0.0, 1.0, 0.0)
        assert rx == pytest.approx(0.0)
        assert ry == pytest.approx(0.0)

    def test_perpendicular_residual_full(self):
        rx, ry = _residual(0.0, 3.0, 1.0, 0.0)
        assert rx == pytest.approx(0.0)
        assert ry == pytest.approx(3.0)

    def test_zero_axis_returns_original(self):
        rx, ry = _residual(1.0, 2.0, 0.0, 0.0)
        assert rx == pytest.approx(1.0)
        assert ry == pytest.approx(2.0)


class TestComposite:
    def test_json_structure(self):
        comp = _composite(5.0, 0.0, 1.0, 0.0, 0.5, 3.0, 0.0, 4.0)
        data = json.loads(comp)
        assert data["Magnitude"] == 5.0
        assert data["Angle"] == 0.0
        assert data["Direction"] == [1.0, 0.0]
        assert data["Scale"] == 0.5
        assert data["Projection"] == 3.0
        assert data["Residual"] == [0.0, 4.0]


class TestNodeRun:
    def test_basic_run(self):
        node = PSN_GuidanceDecomposer()
        mag, ang, dir_str, scale, proj, res_str, comp = node.run(
            vec_json="[3.0, 4.0]",
            axis_json="[1.0, 0.0]",
            reference=10.0,
            scale_mode="absolute",
        )
        assert mag == pytest.approx(5.0)
        assert ang == pytest.approx(math.atan2(4.0, 3.0))
        dir_data = json.loads(dir_str)
        assert dir_data[0] == pytest.approx(0.6)
        assert dir_data[1] == pytest.approx(0.8)
        assert scale == pytest.approx(0.5)
        assert proj == pytest.approx(3.0)
        res_data = json.loads(res_str)
        assert res_data[0] == pytest.approx(0.0)
        assert res_data[1] == pytest.approx(4.0)
        comp_data = json.loads(comp)
        assert comp_data["Magnitude"] == pytest.approx(5.0)

    def test_zero_vector(self):
        node = PSN_GuidanceDecomposer()
        mag, ang, dir_str, scale, proj, res_str, comp = node.run(
            vec_json="[0.0, 0.0]",
            axis_json="[1.0, 0.0]",
            reference=1.0,
            scale_mode="absolute",
        )
        assert mag == 0.0
        dir_data = json.loads(dir_str)
        assert dir_data == [0.0, 0.0]
        assert scale == 0.0
        assert proj == 0.0
        res_data = json.loads(res_str)
        assert res_data == [0.0, 0.0]

    def test_bad_vec_json(self):
        node = PSN_GuidanceDecomposer()
        with pytest.raises(ValueError):
            node.run(
                vec_json="invalid",
                axis_json="[1.0, 0.0]",
                reference=1.0,
                scale_mode="absolute",
            )

    def test_bad_axis_json(self):
        node = PSN_GuidanceDecomposer()
        with pytest.raises(ValueError):
            node.run(
                vec_json="[1.0, 0.0]",
                axis_json="bad",
                reference=1.0,
                scale_mode="absolute",
            )

    def test_bad_scale_mode(self):
        node = PSN_GuidanceDecomposer()
        with pytest.raises(ValueError):
            node.run(
                vec_json="[1.0, 0.0]",
                axis_json="[1.0, 0.0]",
                reference=1.0,
                scale_mode="invalid_mode",
            )

    def test_normalized_scale_mode(self):
        node = PSN_GuidanceDecomposer()
        mag, ang, dir_str, scale, proj, res_str, comp = node.run(
            vec_json="[3.0, 4.0]",
            axis_json="[1.0, 0.0]",
            reference=5.0,
            scale_mode="normalized",
        )
        assert scale == pytest.approx(5.0 / (5.0 + 5.0))

    def test_clamped_scale_mode(self):
        node = PSN_GuidanceDecomposer()
        mag, ang, dir_str, scale, proj, res_str, comp = node.run(
            vec_json="[3.0, 4.0]",
            axis_json="[1.0, 0.0]",
            reference=2.0,
            scale_mode="clamped",
        )
        assert scale == pytest.approx(1.0)

    def test_negative_vector(self):
        node = PSN_GuidanceDecomposer()
        mag, ang, dir_str, scale, proj, res_str, comp = node.run(
            vec_json="[-3.0, -4.0]",
            axis_json="[-1.0, 0.0]",
            reference=5.0,
            scale_mode="absolute",
        )
        assert mag == pytest.approx(5.0)
        assert proj == pytest.approx(3.0)
