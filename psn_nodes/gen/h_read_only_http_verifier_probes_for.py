"""Read-only HTTP verifier probes for local service health.

This module provides ComfyUI custom nodes that let a workflow confirm that
local services (ComfyUI, vLLM, etc.) are responsive before heavy processing
starts.  The probes are strictly read-only: they only issue GET-style
requests and never mutate state.

Because the sandbox forbids real network I/O, the nodes operate on a
*probe plan* (a list of named endpoints with expected status codes) and a
*probe result* (a list of observed outcomes).  The verifier node evaluates
the plan against the results and produces a readiness report.  A separate
node can build a default plan for common local services.
"""

import torch

CAT = "ParametricStudio/Health"


def _s(x):
    """Unwrap a ComfyUI tensor/dict input to the underlying tensor."""
    if isinstance(x, dict):
        return x.get("samples", x)
    return x


def _out(latent, samples):
    """Wrap a tensor back into a ComfyUI LATENT dict."""
    return {"samples": samples}


def build_default_plan():
    """Return a default probe plan for common local services.

    Each entry is a dict with keys:
      name   – human-readable service name
      path   – HTTP path to probe (GET only)
      expect – expected HTTP status code (int)
      timeout – timeout in seconds (float)
    """
    return [
        {"name": "comfyui", "path": "/system_stats", "expect": 200, "timeout": 5.0},
        {"name": "vllm", "path": "/health", "expect": 200, "timeout": 5.0},
        {"name": "vllm_models", "path": "/v1/models", "expect": 200, "timeout": 5.0},
    ]


def evaluate_probes(plan, results):
    """Evaluate a probe plan against observed results.

    Args:
        plan: list of dicts (see build_default_plan).
        results: list of dicts with keys:
            name, status (int or None), latency_ms (float or None), error (str or None)

    Returns:
        dict with keys:
            ready (bool) – True if every probe in the plan passed
            total (int)
            passed (int)
            failed (int)
            details – list of per-probe dicts with name, ok, status, expected, latency_ms, error
    """
    details = []
    passed = 0
    failed = 0
    for probe in plan:
        name = probe.get("name", "unknown")
        expect = probe.get("expect", 200)
        # find matching result
        result = None
        for r in results:
            if r.get("name") == name:
                result = r
                break
        if result is None:
            details.append({
                "name": name, "ok": False, "status": None,
                "expected": expect, "latency_ms": None, "error": "no result",
            })
            failed += 1
            continue
        status = result.get("status")
        latency = result.get("latency_ms")
        error = result.get("error")
        ok = (status == expect) and (error is None)
        if ok:
            passed += 1
        else:
            failed += 1
        details.append({
            "name": name, "ok": ok, "status": status,
            "expected": expect, "latency_ms": latency, "error": error,
        })
    total = len(plan)
    return {
        "ready": failed == 0 and total > 0,
        "total": total,
        "passed": passed,
        "failed": failed,
        "details": details,
    }


def report_to_tensor(report):
    """Convert a readiness report into a small float tensor [1, 1, 4, 1].

    Channels: [ready, passed_frac, failed_frac, total_norm]
    where total_norm = min(total, 16) / 16.
    """
    ready = 1.0 if report["ready"] else 0.0
    total = max(report["total"], 1)
    passed_frac = report["passed"] / total
    failed_frac = report["failed"] / total
    total_norm = min(report["total"], 16) / 16.0
    t = torch.tensor([ready, passed_frac, failed_frac, total_norm], dtype=torch.float32)
    return t.reshape(1, 1, 4, 1)


class PSN_BuildProbePlan:
    """Build a default read-only HTTP probe plan for local services."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "include_comfyui": ("BOOLEAN", {"default": True}),
                "include_vllm": ("BOOLEAN", {"default": True}),
                "timeout": ("FLOAT", {"default": 5.0, "min": 0.5, "max": 60.0, "step": 0.5}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("plan_json",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, include_comfyui, include_vllm, timeout):
        plan = []
        if include_comfyui:
            plan.append({"name": "comfyui", "path": "/system_stats", "expect": 200, "timeout": timeout})
        if include_vllm:
            plan.append({"name": "vllm", "path": "/health", "expect": 200, "timeout": timeout})
            plan.append({"name": "vllm_models", "path": "/v1/models", "expect": 200, "timeout": timeout})
        import json
        return (json.dumps(plan),)


class PSN_VerifierProbe:
    """Evaluate read-only HTTP probe results and produce a readiness report.

    Inputs are JSON strings (plan and results) so the node can be wired from
    any text source.  The output is a small IMAGE tensor encoding the report
    plus a human-readable summary string.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "plan_json": ("STRING",),
                "results_json": ("STRING",),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING", "BOOLEAN")
    RETURN_NAMES = ("report_image", "summary", "ready")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, plan_json, results_json):
        import json
        try:
            plan = json.loads(plan_json)
            if not isinstance(plan, list):
                raise ValueError("plan must be a list")
        except Exception as e:
            return (torch.zeros(1, 1, 4, 1, dtype=torch.float32), f"bad plan: {e}", False)
        try:
            results = json.loads(results_json)
            if not isinstance(results, list):
                raise ValueError("results must be a list")
        except Exception as e:
            return (torch.zeros(1, 1, 4, 1, dtype=torch.float32), f"bad results: {e}", False)

        report = evaluate_probes(plan, results)
        img = report_to_tensor(report)
        lines = [f"ready={report['ready']} passed={report['passed']}/{report['total']}"]
        for d in report["details"]:
            status_s = str(d["status"]) if d["status"] is not None else "-"
            lat_s = f"{d['latency_ms']:.1f}ms" if d["latency_ms"] is not None else "-"
            err_s = f" err={d['error']}" if d["error"] else ""
            lines.append(f"  {d['name']}: {status_s}/{d['expected']} {lat_s}{err_s}")
        summary = "\n".join(lines)
        return (img, summary, report["ready"])


class PSN_ProbeResultToLatent:
    """Convert a probe report IMAGE tensor into a LATENT for downstream use.

    The report image [1,1,4,1] is reshaped into a latent [1,4,1,1] so it can
    be fed into latent-conditioning nodes.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "report_image": ("IMAGE",),
            }
        }

    RETURN_TYPES = ("LATENT",)
    RETURN_NAMES = ("latent",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, report_image):
        x = _s(report_image)
        if x.dim() != 4 or x.shape[0] != 1 or x.shape[1] != 1:
            raise ValueError(f"expected [1,1,C,1] tensor, got {list(x.shape)}")
        # [1,1,4,1] -> [1,4,1,1]
        lat = x.permute(0, 2, 1, 3).contiguous()
        return (_out(None, lat),)


NODE_CLASS_MAPPINGS = {
    "PSN_BuildProbePlan": PSN_BuildProbePlan,
    "PSN_VerifierProbe": PSN_VerifierProbe,
    "PSN_ProbeResultToLatent": PSN_ProbeResultToLatent,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_BuildProbePlan": "Build Probe Plan",
    "PSN_VerifierProbe": "Verifier Probe",
    "PSN_ProbeResultToLatent": "Probe Result To Latent",
}
