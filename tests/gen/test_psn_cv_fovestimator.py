import pytest
import json
import math
from psn_nodes.gen.psn_cv_fovestimator import PSN_CV_FOVEstimator

class TestPSN_CV_FOVEstimator:
    def setup_method(self):
        self.node = PSN_CV_FOVEstimator()

    def test_empty_lines_returns_defaults(self):
        """Test that empty lines return default FOV values."""
        fov_h, fov_v, tilt = self.node.run("[]", 1024.0, 1024.0)
        assert fov_h == 60.0
        assert fov_v == 45.0
        assert tilt == 0.0

    def test_invalid_json_returns_defaults(self):
        """Test that invalid JSON returns default FOV values."""
        fov_h, fov_v, tilt = self.node.run("invalid json", 1024.0, 1024.0)
        assert fov_h == 60.0
        assert fov_v == 45.0
        assert tilt == 0.0

    def test_single_line_returns_defaults(self):
        """Test that a single line (no intersections) returns defaults."""
        lines = [[0, 0, 100, 0]]
        fov_h, fov_v, tilt = self.node.run(json.dumps(lines), 1024.0, 1024.0)
        assert fov_h == 60.0
        assert fov_v == 45.0
        assert tilt == 0.0

    def test_horizontal_lines_tilt_zero(self):
        """Test that horizontal lines result in zero tilt."""
        lines = [
            [0, 512, 1024, 512],
            [0, 512, 1024, 512],
            [0, 512, 1024, 512]
        ]
        fov_h, fov_v, tilt = self.node.run(json.dumps(lines), 1024.0, 1024.0)
        assert abs(tilt) < 1e-6

    def test_tilt_angle_estimation(self):
        """Test tilt angle estimation with tilted horizontal lines."""
        # Lines tilted by 10 degrees
        angle_rad = math.radians(10)
        x1, y1 = 0, 512
        x2, y2 = 1024, 512 + 1024 * math.tan(angle_rad)
        lines = [
            [x1, y1, x2, y2],
            [x1, y1 + 10, x2, y2 + 10],
            [x1, y1 + 20, x2, y2 + 20]
        ]
        fov_h, fov_v, tilt = self.node.run(json.dumps(lines), 1024.0, 1024.0)
        assert abs(tilt - 10.0) < 1.0  # Allow 1 degree tolerance

    def test_vanishing_point_fov_estimation(self):
        """Test FOV estimation with lines converging to a vanishing point."""
        # Lines converging to VP at (1024, 512) - right edge center
        vp_x, vp_y = 1024, 512
        lines = [
            [0, 0, vp_x, vp_y],
            [0, 1024, vp_x, vp_y],
            [512, 0, vp_x, vp_y],
            [512, 1024, vp_x, vp_y]
        ]
        fov_h, fov_v, tilt = self.node.run(json.dumps(lines), 1024.0, 1024.0)
        # VP at right edge center: dx = 512, dy = 0
        # fov_h = 2 * atan(512/512) = 2 * 45 = 90 degrees
        assert abs(fov_h - 90.0) < 5.0  # Allow 5 degree tolerance
        assert abs(fov_v - 90.0) < 5.0

    def test_bad_input_types(self):
        """Test that bad input types are handled gracefully."""
        # Test with non-numeric values in lines
        lines = [[0, 0, "a", 0]]
        fov_h, fov_v, tilt = self.node.run(json.dumps(lines), 1024.0, 1024.0)
        assert fov_h == 60.0
        assert fov_v == 45.0
        assert tilt == 0.0

    def test_parallel_lines_no_vp(self):
        """Test that parallel lines (no VP) return defaults."""
        lines = [
            [0, 0, 1024, 0],
            [0, 100, 1024, 100],
            [0, 200, 1024, 200]
        ]
        fov_h, fov_v, tilt = self.node.run(json.dumps(lines), 1024.0, 1024.0)
        # Parallel lines have no VP, so defaults should be returned
        assert fov_h == 60.0
        assert fov_v == 45.0
