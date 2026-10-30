"""ParametricStudio: scripted headless smoke test for ComfyUI workflows.

This module provides a single ComfyUI custom node that runs a small, scripted
"smoke test" against a workflow description (a plain Python dict) and a set of
minimal inputs.  The node simulates the workflow steps in-process (headless,
no network, no subprocess) and reports pass/fail plus per-step diagnostics.

The workflow dict format (kept deliberately simple):

    {
        "steps": [
            {
                "id": "step_1",
                "op": "identity" | "scale" | "add" | "mean" | "threshold",
                "inputs": {"a": "input_name" | "step_id", ...},
                "expect": {"min": 0.0, "max": 1.0, "mean": 0.5, "tol": 0.05}
            },
            ...
        ],
        "inputs": {"input_name": "tensor_key"}
    }

Supported ops (all pure torch, CPU):
  - identity:  out = a
  - scale:     out = a * k          (k from "k" in inputs, default 1.0)
  - add:       out = a + b
  - mean:      out = a.mean(dim=(1,2), keepdim=True) broadcast back to a's shape
  - threshold: out = (a > t).float()  (t from "t" in inputs, default 0.5)

Each step's "expect" dict may contain any of: min, max, mean, tol.
  - min/max:  out.min() >= min - tol, out.max() <= max + tol
  - mean:     abs(out.mean() - mean) <= tol
  - tol:      tolerance used for all checks (default 1e-4)

The node returns:
  - result:  (STRING)  "PASS" or "FAIL"
  - report:  (STRING)  human-readable multi-line report
  - output:  (IMAGE)   the tensor produced by the last step (or empty if FAIL)
"""

import torch

CAT = "ParametricStudio/SmokeTest"


def _as_tensor(x):
    """Coerce to a float32 CPU tensor; raise TypeError on bad input."""
    if isinstance(x, torch.Tensor):
        return x.detach().float().cpu()
    raise TypeError("expected a torch.Tensor, got %s" % type(x).__name__)


def _resolve_input(name, inputs_map, step_outputs):
    """Resolve an input reference to a tensor.

    name may be:
      - a key in inputs_map (top-level named inputs)
      - a step id (output of a previous step)
    """
    if name in inputs_map:
        return _as_tensor(inputs_map[name])
    if name in step_outputs:
        return _as_tensor(step_outputs[name])
    raise KeyError("unresolved input reference: %r" % name)


def _apply_op(op, a, b, k, t):
    """Apply a single op.  All tensors are float32 CPU."""
    if op == "identity":
        return a.clone()
    if op == "scale":
        return a * k
    if op == "add":
        return a + b
    if op == "mean":
        # spatial mean, broadcast back to original shape
        m = a.mean(dim=tuple(range(1, a.dim())), keepdim=True)
        return m.expand_as(a).clone()
    if op == "threshold":
        return (a > t).float()
    raise ValueError("unknown op: %r" % op)


def _check_expect(out, expect):
    """Return (ok, list_of_messages)."""
    tol = float(expect.get("tol", 1e-4))
    msgs = []
    ok = True

    if "min" in expect:
        lo = float(expect["min"])
        actual_min = float(out.min())
        if actual_min < lo - tol:
            ok = False
            msgs.append("min check failed: got %.6f < %.6f (tol %.6f)" % (actual_min, lo, tol))
        else:
            msgs.append("min ok: %.6f >= %.6f" % (actual_min, lo))

    if "max" in expect:
        hi = float(expect["max"])
        actual_max = float(out.max())
        if actual_max > hi + tol:
            ok = False
            msgs.append("max check failed: got %.6f > %.6f (tol %.6f)" % (actual_max, hi, tol))
        else:
            msgs.append("max ok: %.6f <= %.6f" % (actual_max, hi))

    if "mean" in expect:
        target = float(expect["mean"])
        actual_mean = float(out.mean())
        if abs(actual_mean - target) > tol:
            ok = False
            msgs.append("mean check failed: got %.6f, expected %.6f (tol %.6f)" % (actual_mean, target, tol))
        else:
            msgs.append("mean ok: %.6f ~ %.6f" % (actual_mean, target))

    return ok, msgs


def run_smoke_test(workflow, inputs):
    """Core smoke-test engine (pure Python + torch, no side effects).

    Args:
        workflow: dict with "steps" (list) and optional "inputs" (dict mapping
                  logical input names to keys in `inputs`).
        inputs:   dict mapping tensor names to torch tensors.

    Returns:
        (passed: bool, report: str, last_output: torch.Tensor or None)
    """
    if not isinstance(workflow, dict):
        return False, "ERROR: workflow must be a dict", None
    steps = workflow.get("steps", [])
    if not isinstance(steps, list) or len(steps) == 0:
        return False, "ERROR: workflow must have a non-empty 'steps' list", None

    # Resolve top-level input mapping
    wf_inputs = workflow.get("inputs", {})
    if not isinstance(wf_inputs, dict):
        return False, "ERROR: workflow 'inputs' must be a dict", None

    # Build the resolved input map: logical_name -> tensor
    inputs_map = {}
    for logical_name, tensor_key in wf_inputs.items():
        if tensor_key not in inputs:
            return False, "ERROR: input tensor %r not provided" % tensor_key, None
        inputs_map[logical_name] = inputs[tensor_key]

    step_outputs = {}
    report_lines = []
    last_output = None
    all_ok = True

    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            all_ok = False
            report_lines.append("step %d: ERROR not a dict" % i)
            continue

        step_id = step.get("id", "step_%d" % i)
        op = step.get("op", "identity")
        step_inputs = step.get("inputs", {})
        expect = step.get("expect", {})

        try:
            # Resolve inputs for this step
            a = None
            b = None
            k = 1.0
            t = 0.5

            for key, ref in step_inputs.items():
                if key == "k":
                    k = float(ref)
                elif key == "t":
                    t = float(ref)
                elif key == "a":
                    a = _resolve_input(ref, inputs_map, step_outputs)
                elif key == "b":
                    b = _resolve_input(ref, inputs_map, step_outputs)
                else:
                    # unknown key, ignore
                    pass

            if a is None:
                raise ValueError("step %r: missing input 'a'" % step_id)
            if op == "add" and b is None:
                raise ValueError("step %r: op 'add' requires input 'b'" % step_id)

            out = _apply_op(op, a, b, k, t)
            step_outputs[step_id] = out
            last_output = out

            # Check expectations
            if expect:
                ok, msgs = _check_expect(out, expect)
                status = "PASS" if ok else "FAIL"
                if not ok:
                    all_ok = False
                report_lines.append("[%s] %s (%s): %s" % (status, step_id, op, "; ".join(msgs)))
            else:
                report_lines.append("[PASS] %s (%s): no expectations" % (step_id, op))

        except Exception as e:
            all_ok = False
            report_lines.append("[FAIL] %s (%s): ERROR %s" % (step_id, op, e))

    report = "\n".join(report_lines) if report_lines else "(no steps)"
    return all_ok, report, last_output


class PSN_SmokeTestWorkflow:
    """Run a scripted headless smoke test against a ComfyUI workflow description.

    Feed in a workflow dict (as a JSON string) and a set of minimal input
    tensors.  The node executes each step in order, checks expectations, and
    returns PASS/FAIL with a detailed report.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "workflow_json": ("STRING", {
                    "multiline": True,
                    "default": '{"steps": [{"id": "s1", "op": "identity", "inputs": {"a": "img"}, "expect": {"min": 0.0, "max": 1.0}}], "inputs": {"img": "img"}}',
                }),
                "image": ("IMAGE",),
            },
            "optional": {
                "mask": ("MASK",),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "IMAGE")
    RETURN_NAMES = ("result", "report", "output")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, workflow_json, image, mask=None):
        import json

        # Parse workflow JSON
        try:
            workflow = json.loads(workflow_json)
        except (json.JSONDecodeError, TypeError) as e:
            return ("FAIL", "ERROR: invalid workflow JSON: %s" % e, image)

        # Build inputs dict
        inputs = {"img": image}
        if mask is not None:
            inputs["mask"] = mask

        passed, report, last_out = run_smoke_test(workflow, inputs)

        result = "PASS" if passed else "FAIL"
        out_tensor = last_out if last_out is not None else image

        return (result, report, out_tensor)


NODE_CLASS_MAPPINGS = {
    "PSN_SmokeTestWorkflow": PSN_SmokeTestWorkflow,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_SmokeTestWorkflow": "Smoke Test Workflow (Headless)",
}
