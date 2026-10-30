"""Tests for n_5_centralized_parameter_orchestration."""

import json

import torch

from n_5_centralized_parameter_orchestration import (
    PSN_ParamOrchestrator,
    compute_params,
    _model_metadata,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


# ---------------------------------------------------------------------------
# 1. Basic image / fast: steps should be reduced relative to base (30 -> 15)
# ---------------------------------------------------------------------------
params = compute_params("image", "fast", {})
assert params["steps"] == 15, "fast image steps should be 15, got %s" % params["steps"]
assert params["cfg"] == 6.0, "fast image cfg should be 6.0, got %s" % params["cfg"]
assert params["sampler_name"] == "euler", "fast should override sampler to euler"
assert params["scheduler"] == "simple", "fast should override scheduler to simple"
assert params["pipeline_type"] == "image"
assert params["quality"] == "fast"

# ---------------------------------------------------------------------------
# 2. Basic image / high: steps should be increased (30 -> 45)
# ---------------------------------------------------------------------------
params_high = compute_params("image", "high", {})
assert params_high["steps"] == 45, "high image steps should be 45, got %s" % params_high["steps"]
assert params_high["cfg"] == 8.0, "high image cfg should be 8.0, got %s" % params_high["cfg"]
assert params_high["sampler_name"] == "euler_ancestral", "high should keep base sampler"
assert params_high["scheduler"] == "normal", "high should keep base scheduler"

# ---------------------------------------------------------------------------
# 3. Video pipeline: should include video-specific keys
# ---------------------------------------------------------------------------
params_video = compute_params("video", "fast", {})
assert params_video["frame_count"] == 16, "video should have frame_count 16"
assert params_video["temporal_cfg_scale"] == 0.8, "video should have temporal_cfg_scale"
assert params_video["steps"] == 20, "fast video steps should be 20, got %s" % params_video["steps"]

# ---------------------------------------------------------------------------
# 4. 3D pipeline: should include 3d-specific keys
# ---------------------------------------------------------------------------
params_3d = compute_params("3d", "high", {})
assert params_3d["view_count"] == 6, "3d should have view_count 6"
assert params_3d["steps"] == 75, "high 3d steps should be 75, got %s" % params_3d["steps"]

# ---------------------------------------------------------------------------
# 5. Model metadata overrides: metadata cfg/steps should be used as base
# ---------------------------------------------------------------------------
meta = {"cfg": 10.0, "steps": 20, "sampler_name": "dpmpp_2m_sde"}
params_meta = compute_params("image", "fast", meta)
# fast: steps = 20 * 0.5 = 10, cfg = 10.0 - 1.0 = 9.0
assert params_meta["steps"] == 10, "metadata steps 20 * 0.5 should be 10, got %s" % params_meta["steps"]
assert params_meta["cfg"] == 9.0, "metadata cfg 10.0 - 1.0 should be 9.0, got %s" % params_meta["cfg"]
assert params_meta["source"] == "model_metadata", "source should be model_metadata"

# ---------------------------------------------------------------------------
# 6. Node run with a mock model object (has metadata attr)
# ---------------------------------------------------------------------------

class MockModel:
    def __init__(self):
        self.metadata = {"cfg": 5.0, "steps": 10}


node = PSN_ParamOrchestrator()
mock = MockModel()
result_params, result_model = node.run(mock, "image", "fast")
assert result_model is mock, "model should be returned unchanged (same object)"
assert result_params["cfg"] == 4.0, "mock cfg 5.0 - 1.0 should be 4.0, got %s" % result_params["cfg"]
assert result_params["steps"] == 5, "mock steps 10 * 0.5 should be 5, got %s" % result_params["steps"]

# ---------------------------------------------------------------------------
# 7. Node run with a dict model
# ---------------------------------------------------------------------------
dict_model = {"cfg": 12.0, "steps": 40}
result_params2, result_model2 = node.run(dict_model, "video", "high")
assert result_model2 is dict_model, "dict model should be returned unchanged"
# high: steps = 40 * 1.5 = 60, cfg = 12.0 + 1.0 = 13.0
assert result_params2["steps"] == 60, "dict steps 40 * 1.5 should be 60, got %s" % result_params2["steps"]
assert result_params2["cfg"] == 13.0, "dict cfg 12.0 + 1.0 should be 13.0, got %s" % result_params2["cfg"]

# ---------------------------------------------------------------------------
# 8. Bad input: None model should raise ValueError
# ---------------------------------------------------------------------------
try:
    node.run(None, "image", "fast")
    assert False, "None model should raise ValueError"
except ValueError:
    pass

# ---------------------------------------------------------------------------
# 9. Bad input: invalid pipeline_type should raise ValueError
# ---------------------------------------------------------------------------
try:
    compute_params("audio", "fast", {})
    assert False, "invalid pipeline_type should raise ValueError"
except ValueError:
    pass

# ---------------------------------------------------------------------------
# 10. Bad input: invalid quality should raise ValueError
# ---------------------------------------------------------------------------
try:
    compute_params("image", "ultra", {})
    assert False, "invalid quality should raise ValueError"
except ValueError:
    pass

# ---------------------------------------------------------------------------
# 11. Clamping: extreme metadata values should be clamped
# ---------------------------------------------------------------------------
params_clamped = compute_params("image", "high", {"cfg": 100.0, "steps": 1000})
assert params_clamped["cfg"] == 30.0, "cfg should be clamped to 30.0, got %s" % params_clamped["cfg"]
assert params_clamped["steps"] == 512, "steps should be clamped to 512, got %s" % params_clamped["steps"]

# ---------------------------------------------------------------------------
# 12. Node registration: NODE_CLASS_MAPPINGS and display names
# ---------------------------------------------------------------------------
assert "PSN_ParamOrchestrator" in NODE_CLASS_MAPPINGS
assert NODE_CLASS_MAPPINGS["PSN_ParamOrchestrator"] is PSN_ParamOrchestrator
assert NODE_DISPLAY_NAME_MAPPINGS["PSN_ParamOrchestrator"] == "PSN Param Orchestrator"

# ---------------------------------------------------------------------------
# 13. INPUT_TYPES structure
# ---------------------------------------------------------------------------
it = PSN_ParamOrchestrator.INPUT_TYPES()
assert "model" in it["required"]
assert it["required"]["model"] == ("MODEL",)
assert it["required"]["pipeline_type"] == ("image", "video", "3d")
assert it["required"]["quality"] == ("fast", "high")

# ---------------------------------------------------------------------------
# 14. RETURN_TYPES and FUNCTION
# ---------------------------------------------------------------------------
assert PSN_ParamOrchestrator.RETURN_TYPES == ("DICT", "MODEL")
assert PSN_ParamOrchestrator.RETURN_NAMES == ("optimized_params", "adjusted_model")
assert PSN_ParamOrchestrator.FUNCTION == "run"
assert PSN_ParamOrchestrator.CATEGORY == "ParametricStudio/Orchestration"

# ---------------------------------------------------------------------------
# 15. Model with get_metadata method
# ---------------------------------------------------------------------------

class GetterModel:
    def get_metadata(self):
        return {"cfg": 3.0, "steps": 8}


getter = GetterModel()
result_params3, _ = node.run(getter, "image", "fast")
# fast: steps = 8 * 0.5 = 4, cfg = 3.0 - 1.0 = 2.0
assert result_params3["steps"] == 4, "getter steps 8 * 0.5 should be 4, got %s" % result_params3["steps"]
assert result_params3["cfg"] == 2.0, "getter cfg 3.0 - 1.0 should be 2.0, got %s" % result_params3["cfg"]

# ---------------------------------------------------------------------------
# 16. Model with no metadata at all (plain object)
# ---------------------------------------------------------------------------

class BareModel:
    pass


bare = BareModel()
result_params4, _ = node.run(bare, "image", "fast")
assert result_params4["steps"] == 15, "bare model should use default steps 15 for fast"
assert result_params4["source"] == "default", "bare model source should be default"

# ---------------------------------------------------------------------------
# 17. Params dict is JSON-serializable
# ---------------------------------------------------------------------------
json_str = json.dumps(params)
assert isinstance(json_str, str)

print("ok")
