"""PSN_RES4LYF_Sampler: pure-logic configuration, validation, and step-schedule
planning for a RES4LYF-style fast sampler.

This module does NOT perform any GPU/torch/ComfyUI sampling.  It implements the
secure-by-design, pure-logic parts of the spec:

  * allow-list validation of solver and scheduler names,
  * range validation of the step count,
  * construction of a deterministic step-schedule (sigma values) for the
    chosen scheduler,
  * a lightweight "quality estimate" heuristic that reports whether the
    configured step count is within the recommended fast-sampling band.

All functions and the node wrapper take plain values (numbers, strings) and
return plain values (numbers, strings, tuples).  No file, network, subprocess,
or torch access is performed.
"""

import math

# ---------------------------------------------------------------------------
# Allow-lists
# ---------------------------------------------------------------------------

_SOLVERS = ("RES4LYF", "BongMath")
_SCHEDULERS = ("Linear", "Karras")

_MIN_STEPS = 1
_MAX_STEPS = 100
_RECOMMENDED_MIN = 10
_RECOMMENDED_MAX = 20

_CAT = "ParametricStudio/Sampling"


# ---------------------------------------------------------------------------
# Pure-logic helpers
# ---------------------------------------------------------------------------

def psn_validate_solver(solver):
    """Return (ok, reason).  ok is True only if solver is in the allow-list."""
    if not isinstance(solver, str):
        return False, "solver must be a string"
    if solver not in _SOLVERS:
        return False, "solver '%s' not in allow-list %s" % (solver, list(_SOLVERS))
    return True, "ok"


def psn_validate_scheduler(scheduler):
    """Return (ok, reason).  ok is True only if scheduler is in the allow-list."""
    if not isinstance(scheduler, str):
        return False, "scheduler must be a string"
    if scheduler not in _SCHEDULERS:
        return False, "scheduler '%s' not in allow-list %s" % (scheduler, list(_SCHEDULERS))
    return True, "ok"


def psn_validate_steps(steps):
    """Return (ok, reason).  ok is True only if steps is an int in [1, 100]."""
    if not isinstance(steps, int) or isinstance(steps, bool):
        return False, "steps must be an integer"
    if steps < _MIN_STEPS or steps > _MAX_STEPS:
        return False, "steps must be in [%d, %d]" % (_MIN_STEPS, _MAX_STEPS)
    return True, "ok"


def psn_build_schedule(steps, scheduler):
    """Build a list of *steps* sigma values in (0, 1] for the given scheduler.

    Linear:   sigma_i = 1 - (i / steps)          for i in 0..steps-1
    Karras:   sigma_i = (sigma_max^(1/rho) - sigma_min^(1/rho)
                         * (i / (steps-1)))^(1/rho)   with rho=7.0,
              sigma_max=1.0, sigma_min=0.001

    Returns a list of floats, each in (0, 1].
    """
    if steps <= 0:
        raise ValueError("steps must be positive")

    if scheduler == "Linear":
        return [1.0 - (i / steps) for i in range(steps)]

    if scheduler == "Karras":
        rho = 7.0
        sigma_max = 1.0
        sigma_min = 0.001
        if steps == 1:
            return [sigma_max]
        sigmas = []
        for i in range(steps):
            t = i / (steps - 1)
            val = (sigma_max ** (1.0 / rho) - t * (sigma_max ** (1.0 / rho) - sigma_min ** (1.0 / rho))) ** rho
            sigmas.append(val)
        return sigmas

    raise ValueError("unknown scheduler: %s" % scheduler)


def psn_quality_estimate(steps, solver):
    """Return (in_band, reason).

    in_band is True when steps falls within the recommended fast-sampling
    band for the given solver.  RES4LYF is tuned for 10-20 steps; BongMath
    is slightly more forgiving (8-24).
    """
    if solver == "RES4LYF":
        lo, hi = _RECOMMENDED_MIN, _RECOMMENDED_MAX
    elif solver == "BongMath":
        lo, hi = 8, 24
    else:
        return False, "unknown solver for quality estimate"

    if lo <= steps <= hi:
        return True, "steps=%d within recommended [%d, %d] for %s" % (steps, lo, hi, solver)
    if steps < lo:
        return False, "steps=%d below recommended minimum %d for %s" % (steps, lo, solver)
    return False, "steps=%d above recommended maximum %d for %s" % (steps, hi, solver)


# ---------------------------------------------------------------------------
# ComfyUI-style node
# ---------------------------------------------------------------------------

class PSN_RES4LYF_Sampler:
    """Validate and plan a RES4LYF fast-sampling configuration.

    This node does NOT run a diffusion model.  It validates the solver,
    scheduler, and step count against allow-lists and ranges, builds the
    step-schedule, and reports a quality-band estimate.  The outputs are
    plain values that a downstream (GPU) node could consume.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "steps": ("INT", {"default": 15, "min": _MIN_STEPS, "max": _MAX_STEPS, "step": 1}),
                "solver": (list(_SOLVERS),),
                "scheduler": (list(_SCHEDULERS),),
            },
            "optional": {},
        }

    RETURN_TYPES = ("BOOLEAN", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("valid", "schedule_json", "quality_in_band", "reason")
    FUNCTION = "run"
    CATEGORY = _CAT

    def run(self, steps, solver, scheduler):
        # Validate each field
        ok_s, why_s = psn_validate_solver(solver)
        ok_sc, why_sc = psn_validate_scheduler(scheduler)
        ok_st, why_st = psn_validate_steps(steps)

        if not (ok_s and ok_sc and ok_st):
            reasons = []
            if not ok_s:
                reasons.append(why_s)
            if not ok_sc:
                reasons.append(why_sc)
            if not ok_st:
                reasons.append(why_st)
            return (False, "", "no", "; ".join(reasons))

        # Build schedule
        schedule = psn_build_schedule(steps, scheduler)
        schedule_json = "[" + ", ".join("%.6f" % s for s in schedule) + "]"

        # Quality estimate
        in_band, quality_reason = psn_quality_estimate(steps, solver)

        return (True, schedule_json, "yes" if in_band else "no", quality_reason)


# ---------------------------------------------------------------------------
# Module-level mappings
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_RES4LYF_Sampler": PSN_RES4LYF_Sampler,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_RES4LYF_Sampler": "RES4LYF Fast Sampler (Config)",
}
