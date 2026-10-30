"""Tests for h_read_only_http_verifier_probes_for.py"""

import json
import torch

from h_read_only_http_verifier_probes_for import (
    PSN_BuildProbePlan,
    PSN_VerifierProbe,
    PSN_ProbeResultToLatent,
    build_default_plan,
    evaluate_probes,
    report_to_tensor,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)

# 1. build_default_plan returns a valid list of 3 probes
plan = build_default_plan()
assert isinstance(plan, list) and len(plan) == 3, "default plan should have 3 entries"
assert all(isinstance(p, dict) and "name" in p and "path" in p and "expect" in p for p in plan)

# 2. PSN_BuildProbePlan node produces valid JSON plan
node = PSN_BuildProbePlan()
(plan_json,) = node.run(include_comfyui=True, include_vllm=True, timeout=3.0)
plan_list = json.loads(plan_json)
assert len(plan_list) == 3, "full plan should have 3 probes"
assert plan_list[0]["name"] == "comfyui"
assert plan_list[0]["timeout"] == 3.0

# 3. PSN_BuildProbePlan with only comfyui
(plan_json2,) = node.run(include_comfyui=True, include_vllm=False, timeout=2.0)
plan_list2 = json.loads(plan_json2)
assert len(plan_list2) == 1, "comfyui-only plan should have 1 probe"

# 4. evaluate_probes: all pass
results_ok = [
    {"name": "comfyui", "status": 200, "latency_ms": 12.5, "error": None},
    {"name": "vllm", "status": 200, "latency_ms": 8.3, "error": None},
    {"name": "vllm_models", "status": 200, "latency_ms": 15.1, "error": None},
]
report = evaluate_probes(plan, results_ok)
assert report["ready"] is True, "all probes passed -> ready"
assert report["passed"] == 3 and report["failed"] == 0

# 5. evaluate_probes: one fails (wrong status)
results_bad = [
    {"name": "comfyui", "status": 200, "latency_ms": 12.5, "error": None},
    {"name": "vllm", "status": 503, "latency_ms": 200.0, "error": None},
    {"name": "vllm_models", "status": 200, "latency_ms": 15.1, "error": None},
]
report_bad = evaluate_probes(plan, results_bad)
assert report_bad["ready"] is False, "one probe failed -> not ready"
assert report_bad["failed"] == 1 and report_bad["passed"] == 2

# 6. evaluate_probes: missing result
results_missing = [
    {"name": "comfyui", "status": 200, "latency_ms": 12.5, "error": None},
]
report_missing = evaluate_probes(plan, results_missing)
assert report_missing["ready"] is False
assert report_missing["failed"] == 2, "two probes missing -> 2 failed"

# 7. PSN_VerifierProbe node: happy path
vnode = PSN_VerifierProbe()
img, summary, ready = vnode.run(json.dumps(plan), json.dumps(results_ok))
assert ready is True
assert isinstance(img, torch.Tensor) and img.shape == (1, 1, 4, 1)
assert img.dtype == torch.float32
assert "ready=True" in summary
assert "3/3" in summary

# 8. PSN_VerifierProbe node: bad plan JSON
img2, summary2, ready2 = vnode.run("not json", json.dumps(results_ok))
assert ready2 is False
assert "bad plan" in summary2
assert img2.shape == (1, 1, 4, 1)

# 9. PSN_VerifierProbe node: bad results JSON
img3, summary3, ready3 = vnode.run(json.dumps(plan), "{{bad")
assert ready3 is False
assert "bad results" in summary3

# 10. PSN_ProbeResultToLatent: valid conversion
lnode = PSN_ProbeResultToLatent()
(latent_out,) = lnode.run(img)
assert isinstance(latent_out, dict) and "samples" in latent_out
assert latent_out["samples"].shape == (1, 4, 1, 1)

# 11. PSN_ProbeResultToLatent: bad shape raises
try:
    lnode.run(torch.zeros(2, 3, 4, 5))
    assert False, "should have raised"
except ValueError:
    pass

# 12. report_to_tensor values are in [0,1]
img_all = report_to_tensor(report)
assert img_all.min() >= 0.0 and img_all.max() <= 1.0

# 13. NODE_CLASS_MAPPINGS and DISPLAY_NAME_MAPPINGS are consistent
assert set(NODE_CLASS_MAPPINGS.keys()) == set(NODE_DISPLAY_NAME_MAPPINGS.keys())
assert len(NODE_CLASS_MAPPINGS) == 3

# 14. evaluate_probes with empty plan
report_empty = evaluate_probes([], [])
assert report_empty["ready"] is False, "empty plan -> not ready"
assert report_empty["total"] == 0

# 15. evaluate_probes with error in result
results_err = [
    {"name": "comfyui", "status": 200, "latency_ms": 12.5, "error": "timeout"},
    {"name": "vllm", "status": 200, "latency_ms": 8.3, "error": None},
    {"name": "vllm_models", "status": 200, "latency_ms": 15.1, "error": None},
]
report_err = evaluate_probes(plan, results_err)
assert report_err["ready"] is False, "error in result -> not ready even if status matches"
assert report_err["failed"] == 1

print('ok')
