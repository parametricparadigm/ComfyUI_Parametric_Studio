"""Tests for psn_nodes.gen.n_4_fbx_to_video_motion_transfer (pure-logic core)."""

import json
import math

import pytest

from psn_nodes.gen.n_4_fbx_to_video_motion_transfer import (
    PSN_FBX_Pose_Extractor,
    PSN_Pose_Video_Driver,
    OPENPOSE_KEYPOINTS,
)


def _make_fbx_payload(frames):
    return json.dumps({"frames": frames})


def _make_bone_mapping():
    return json.dumps({
        "Spine": "neck",
        "Head": "nose",
        "R_UpperArm": "R_shoulder",
        "L_UpperArm": "L_shoulder",
    })


class TestFBXPoseExtractor:
    def test_two_frames_produces_two_keypoint_sets(self):
        frames = [
            {"bones": {"Spine": [0, 0, 0], "Head": [0, 100, 0]}},
            {"bones": {"Spine": [10, 0, 0], "Head": [10, 100, 0]}},
        ]
        node = PSN_FBX_Pose_Extractor()
        kps_json, reason, count = node.run(
            _make_fbx_payload(frames), 30, _make_bone_mapping()
        )
        assert reason == "ok"
        assert count == 2
        data = json.loads(kps_json)
        assert data["frame_count"] == 2
        assert len(data["keypoints"]) == 2
        # Each frame has 18 keypoints.
        for kps in data["keypoints"]:
            assert len(kps) == len(OPENPOSE_KEYPOINTS)

    def test_projection_coordinates_are_finite_and_in_bounds(self):
        frames = [{"bones": {"Spine": [50, 50, 0], "Head": [-50, 200, 0]}}]
        node = PSN_FBX_Pose_Extractor()
        kps_json, reason, _ = node.run(
            _make_fbx_payload(frames), 24, _make_bone_mapping(),
            focal=500.0, z_cam=1000.0, frame_width=512, frame_height=512,
        )
        assert reason == "ok"
        data = json.loads(kps_json)
        kps = data["keypoints"][0]
        for px, py in kps:
            assert math.isfinite(px) and math.isfinite(py)
            assert 0.0 <= px <= 512.0
            assert 0.0 <= py <= 512.0

    def test_unmapped_bones_yield_zero_keypoints(self):
        frames = [{"bones": {"UnknownBone": [1, 2, 3]}}]
        node = PSN_FBX_Pose_Extractor()
        kps_json, reason, _ = node.run(
            _make_fbx_payload(frames), 30, _make_bone_mapping()
        )
        assert reason == "ok"
        data = json.loads(kps_json)
        # All keypoints should be (0, 0) since no mapped bones present.
        for px, py in data["keypoints"][0]:
            assert px == 0.0 and py == 0.0

    def test_invalid_bone_mapping_index_raises_error(self):
        bad_mapping = json.dumps({"Spine": 99})  # out of range
        frames = [{"bones": {"Spine": [0, 0, 0]}}]
        node = PSN_FBX_Pose_Extractor()
        kps_json, reason, count = node.run(
            _make_fbx_payload(frames), 30, bad_mapping
        )
        assert count == 0
        assert "validation error" in reason
        data = json.loads(kps_json)
        assert "error" in data

    def test_invalid_json_payload_returns_error(self):
        node = PSN_FBX_Pose_Extractor()
        kps_json, reason, count = node.run(
            "not valid json {", 30, _make_bone_mapping()
        )
        assert count == 0
        assert "validation error" in reason
        data = json.loads(kps_json)
        assert "error" in data

    def test_non_numeric_bone_position_returns_error(self):
        frames = [{"bones": {"Spine": ["a", "b", "c"]}}]
        node = PSN_FBX_Pose_Extractor()
        kps_json, reason, count = node.run(
            _make_fbx_payload(frames), 30, _make_bone_mapping()
        )
        assert count == 0
        assert "validation error" in reason
        data = json.loads(kps_json)
        assert "error" in data

    def test_empty_frames_list_returns_error(self):
        node = PSN_FBX_Pose_Extractor()
        kps_json, reason, count = node.run(
            json.dumps({"frames": []}), 30, _make_bone_mapping()
        )
        assert count == 0
        assert "validation error" in reason


class TestPoseVideoDriver:
    def _valid_pose(self, frame_count=2):
        kps = [[(0.0, 0.0)] * len(OPENPOSE_KEYPOINTS) for _ in range(frame_count)]
        return json.dumps({"frame_count": frame_count, "keypoints": kps})

    def _valid_ref(self, w=512, h=512):
        return json.dumps({"width": w, "height": h})

    def test_valid_inputs_produce_latent_plan(self):
        node = PSN_Pose_Video_Driver()
        plan_json, reason, valid = node.run(
            self._valid_pose(3), self._valid_ref(512, 512),
            latent_channels=4, latent_scale=8.0,
        )
        assert valid is True
        assert reason == "ok"
        plan = json.loads(plan_json)
        assert plan["frame_count"] == 3
        assert plan["latent_channels"] == 4
        assert plan["latent_width"] == 64
        assert plan["latent_height"] == 64
        assert plan["shape"] == [1, 4, 3, 64, 64]

    def test_keypoints_length_mismatch_returns_invalid(self):
        bad_pose = json.dumps({"frame_count": 2, "keypoints": [[(0, 0)] * 18]})
        node = PSN_Pose_Video_Driver()
        plan_json, reason, valid = node.run(bad_pose, self._valid_ref())
        assert valid is False
        assert "keypoints length mismatch" in reason

    def test_bad_reference_dimensions_returns_invalid(self):
        bad_ref = json.dumps({"width": -1, "height": 512})
        node = PSN_Pose_Video_Driver()
        plan_json, reason, valid = node.run(self._valid_pose(1), bad_ref)
        assert valid is False
        assert "bad reference dimensions" in reason

    def test_invalid_json_returns_invalid(self):
        node = PSN_Pose_Video_Driver()
        plan_json, reason, valid = node.run("not json", self._valid_ref())
        assert valid is False
        assert "parse error" in reason

    def test_zero_frame_count_returns_invalid(self):
        bad_pose = json.dumps({"frame_count": 0, "keypoints": []})
        node = PSN_Pose_Video_Driver()
        plan_json, reason, valid = node.run(bad_pose, self._valid_ref())
        assert valid is False
        assert "bad frame_count" in reason

    def test_latent_scale_division_produces_min_one(self):
        node = PSN_Pose_Video_Driver()
        plan_json, reason, valid = node.run(
            self._valid_pose(1), self._valid_ref(16, 16),
            latent_channels=4, latent_scale=8.0,
        )
        assert valid is True
        plan = json.loads(plan_json)
        assert plan["latent_width"] == 2
        assert plan["latent_height"] == 2
