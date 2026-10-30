"""Tests for psn_nodes.gen.n_2_drift_correction_loop."""

import json
import math
import pytest

from psn_nodes.gen.n_2_drift_correction_loop import (
    PSN_IdentityDriftDetector,
    PSN_FaceRepairTrigger,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


# ---------------------------------------------------------------------------
# PSN_IdentityDriftDetector
# ---------------------------------------------------------------------------

class TestPSNIdentityDriftDetector:
    def setup_method(self):
        self.node = PSN_IdentityDriftDetector()

    def test_basic_drift_detection(self):
        """Frame 2 has low similarity; others are fine."""
        scores = json.dumps([0.92, 0.91, 0.45, 0.93, 0.88])
        mask, scores_out, count, reason = self.node.run(scores, 0.85)
        assert mask == [0.0, 0.0, 1.0, 0.0, 0.0]
        assert scores_out == [0.92, 0.91, 0.45, 0.93, 0.88]
        assert count == 1
        assert "1/5" in reason

    def test_no_drift(self):
        """All scores above threshold."""
        scores = json.dumps([0.90, 0.95, 0.86])
        mask, _, count, _ = self.node.run(scores, 0.85)
        assert mask == [0.0, 0.0, 0.0]
        assert count == 0

    def test_all_drift(self):
        """All scores below threshold."""
        scores = json.dumps([0.3, 0.2, 0.1])
        mask, _, count, _ = self.node.run(scores, 0.85)
        assert mask == [1.0, 1.0, 1.0]
        assert count == 3

    def test_boundary_score_equals_threshold(self):
        """Score exactly at threshold should NOT be flagged (>= threshold passes)."""
        scores = json.dumps([0.85, 0.84])
        mask, _, count, _ = self.node.run(scores, 0.85)
        assert mask == [0.0, 1.0]
        assert count == 1

    def test_empty_scores(self):
        """Empty list returns empty results."""
        mask, scores_out, count, reason = self.node.run("[]", 0.85)
        assert mask == []
        assert scores_out == []
        assert count == 0
        assert "No frames" in reason

    def test_invalid_json_raises(self):
        with pytest.raises(ValueError, match="not valid JSON"):
            self.node.run("not json", 0.85)

    def test_non_numeric_score_raises(self):
        with pytest.raises(TypeError, match="must be a number"):
            self.node.run(json.dumps([0.9, "abc"]), 0.85)

    def test_nan_score_raises(self):
        with pytest.raises(ValueError, match="not finite"):
            self.node.run(json.dumps([float("nan")]), 0.85)

    def test_threshold_out_of_range_raises(self):
        with pytest.raises(ValueError, match="must be in \\[0, 1\\]"):
            self.node.run(json.dumps([0.5]), 1.5)

    def test_threshold_negative_raises(self):
        with pytest.raises(ValueError, match="must be in \\[0, 1\\]"):
            self.node.run(json.dumps([0.5]), -0.1)

    def test_single_frame(self):
        mask, scores_out, count, _ = self.node.run(json.dumps([0.5]), 0.85)
        assert mask == [1.0]
        assert scores_out == [0.5]
        assert count == 1


# ---------------------------------------------------------------------------
# PSN_FaceRepairTrigger
# ---------------------------------------------------------------------------

class TestPSNFaceRepairTrigger:
    def setup_method(self):
        self.node = PSN_FaceRepairTrigger()

    def test_basic_repair_plan(self):
        """Two drifted frames produce a valid plan."""
        mask = json.dumps([0.0, 1.0, 0.0, 1.0, 0.0])
        plan_json, count, summary = self.node.run(
            mask, "internal_gfpgan", "semantic", 8.0, 0.7
        )
        plan = json.loads(plan_json)
        assert plan["frames_to_repair"] == [1, 3]
        assert plan["repair_count"] == 2
        assert plan["total_frames"] == 5
        assert plan["repair_model"] == "internal_gfpgan"
        assert plan["blend_mode"] == "semantic"
        assert plan["feather_radius"] == 8.0
        assert plan["strength"] == 0.7
        assert count == 2
        assert "2/5" in summary

    def test_no_repair_needed(self):
        """All-zero mask means no repair."""
        mask = json.dumps([0.0, 0.0, 0.0])
        plan_json, count, summary = self.node.run(
            mask, "internal_codeformer", "feather", 4.0, 0.5
        )
        plan = json.loads(plan_json)
        assert plan["frames_to_repair"] == []
        assert plan["repair_count"] == 0
        assert count == 0
        assert "No drift" in summary

    def test_all_frames_repair(self):
        mask = json.dumps([1.0, 1.0, 1.0])
        plan_json, count, _ = self.node.run(
            mask, "external", "hard", 0.0, 1.0
        )
        plan = json.loads(plan_json)
        assert plan["frames_to_repair"] == [0, 1, 2]
        assert count == 3
        assert plan["repair_model"] == "external"
        assert plan["blend_mode"] == "hard"

    def test_invalid_mask_value_raises(self):
        """Mask values must be exactly 0 or 1."""
        with pytest.raises(ValueError, match="must be 0 or 1"):
            self.node.run(json.dumps([0.5]), "internal_gfpgan", "semantic", 8.0, 0.7)

    def test_invalid_repair_model_raises(self):
        with pytest.raises(ValueError, match="repair_model must be one of"):
            self.node.run(json.dumps([1.0]), "bad_model", "semantic", 8.0, 0.7)

    def test_invalid_blend_mode_raises(self):
        with pytest.raises(ValueError, match="blend_mode must be one of"):
            self.node.run(json.dumps([1.0]), "internal_gfpgan", "warp", 8.0, 0.7)

    def test_negative_feather_radius_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            self.node.run(json.dumps([1.0]), "internal_gfpgan", "semantic", -1.0, 0.7)

    def test_strength_out_of_range_raises(self):
        with pytest.raises(ValueError, match="strength must be in \\[0, 1\\]"):
            self.node.run(json.dumps([1.0]), "internal_gfpgan", "semantic", 8.0, 1.5)

    def test_invalid_json_mask_raises(self):
        with pytest.raises(ValueError, match="not valid JSON"):
            self.node.run("garbage", "internal_gfpgan", "semantic", 8.0, 0.7)

    def test_empty_mask(self):
        plan_json, count, summary = self.node.run(
            "[]", "internal_gfpgan", "semantic", 8.0, 0.7
        )
        plan = json.loads(plan_json)
        assert plan["total_frames"] == 0
        assert plan["frames_to_repair"] == []
        assert count == 0


# ---------------------------------------------------------------------------
# Integration: detector -> trigger pipeline
# ---------------------------------------------------------------------------

class TestPipelineIntegration:
    def test_detector_to_trigger(self):
        """Full data-flow: detect drift, then build repair plan."""
        detector = PSN_IdentityDriftDetector()
        trigger = PSN_FaceRepairTrigger()

        scores = json.dumps([0.92, 0.91, 0.45, 0.93, 0.88])
        mask, scores_out, count, reason = detector.run(scores, 0.85)
        assert count == 1

        mask_json = json.dumps(mask)
        plan_json, repair_count, summary = trigger.run(
            mask_json, "internal_gfpgan", "semantic", 8.0, 0.7
        )
        plan = json.loads(plan_json)
        assert plan["frames_to_repair"] == [2]
        assert repair_count == 1
        assert "1/5" in summary

    def test_no_drift_no_repair(self):
        detector = PSN_IdentityDriftDetector()
        trigger = PSN_FaceRepairTrigger()

        scores = json.dumps([0.95, 0.96, 0.97])
        mask, _, count, _ = detector.run(scores, 0.85)
        assert count == 0

        plan_json, repair_count, summary = trigger.run(
            json.dumps(mask), "internal_gfpgan", "semantic", 8.0, 0.7
        )
        assert repair_count == 0
        assert "No drift" in summary


# ---------------------------------------------------------------------------
# Node mapping sanity
# ---------------------------------------------------------------------------

class TestNodeMappings:
    def test_mappings_present(self):
        assert "PSN_IdentityDriftDetector" in NODE_CLASS_MAPPINGS
        assert "PSN_FaceRepairTrigger" in NODE_CLASS_MAPPINGS

    def test_display_names(self):
        assert NODE_DISPLAY_NAME_MAPPINGS["PSN_IdentityDriftDetector"] == "PSN Identity Drift Detector"
        assert NODE_DISPLAY_NAME_MAPPINGS["PSN_FaceRepairTrigger"] == "PSN Face Repair Trigger"

    def test_input_types_callable(self):
        it = PSN_IdentityDriftDetector.INPUT_TYPES()
        assert "required" in it
        assert "drift_scores" in it["required"]
        assert "drift_threshold" in it["required"]

        it2 = PSN_FaceRepairTrigger.INPUT_TYPES()
        assert "drift_mask" in it2["required"]
        assert "repair_model" in it2["required"]
