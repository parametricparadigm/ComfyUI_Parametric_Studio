"""ParametricStudio step-reduction sampling nodes.

Implements a step-skip accelerator that patches a ComfyUI MODEL with a
forecasting hook so that a fraction of the diffusion steps can be skipped.
Skipped steps are predicted from the previous step outputs using either a
linear or a Chebyshev polynomial approximation.

Only the core logic that torch/stdlib can do is implemented here.  The
actual KSampler loop is not reimplemented; instead the node returns a
patched model whose ``model_options`` carry the skip schedule and whose
``_psn_step_skip_state`` dict is updated by the hook each time the model is
called.  A downstream sampler that respects ``model_options['psn_step_skip']``
will consult the hook to decide whether to run the real forward pass or to
use the predicted output.
"""

import math

import torch

CAT = "ParametricStudio/Sampling"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _as_tensor(x):
    """Return x as a torch tensor (no copy if already a tensor)."""
    if isinstance(x, torch.Tensor):
        return x
    return torch.as_tensor(x)


def _linear_forecast(history, step_idx):
    """Linear extrapolation from the last two history entries.

    history: list of tensors (most recent last).
    step_idx: the index of the step we are predicting (0-based).
    Returns a tensor of the same shape as the last entry.
    """
    if len(history) < 2:
        return history[-1].clone()
    y1 = history[-1]
    y0 = history[-2]
    # slope between the two most recent points
    slope = y1 - y0
    return y1 + slope


def _chebyshev_forecast(history, step_idx, order=3):
    """Chebyshev polynomial extrapolation from the last ``order+1`` entries.

    We fit a Chebyshev polynomial of the given order to the most recent
    ``order+1`` points (using their indices as x) and evaluate it at
    ``step_idx``.
    """
    n = min(order + 1, len(history))
    if n < 2:
        return history[-1].clone()
    pts = history[-n:]
    xs = torch.arange(n, dtype=torch.float32)
    # map xs to [-1, 1] for Chebyshev stability
    if n > 1:
        x_norm = (2.0 * xs - (n - 1)) / (n - 1)
    else:
        x_norm = torch.zeros(1)
    # target x for prediction
    x_target = float(step_idx - (n - 1) + (n - 1))  # = step_idx
    # map x_target to the same normalisation
    x_t_norm = (2.0 * x_target - (n - 1)) / (n - 1) if n > 1 else 0.0

    # Build Chebyshev basis values at the data points
    # T_k(x) = cos(k * arccos(x))
    def cheb_vals(x, k):
        return torch.cos(k * torch.acos(x.clamp(-1.0, 1.0)))

    # We solve for coefficients c_0..c_{n-1} such that
    #   sum_k c_k T_k(x_i) = y_i
    # Build the Vandermonde-like matrix V[i,k] = T_k(x_i)
    V = torch.stack([cheb_vals(x_norm, k) for k in range(n)], dim=1)  # [n, n]
    # Stack y values (each is a tensor of some shape); flatten for solve
    shapes = pts[0].shape
    flat = [p.reshape(-1) for p in pts]
    Y = torch.stack(flat, dim=0)  # [n, prod(shapes)]
    # Solve V c = Y  ->  c = V^{-1} Y
    try:
        C = torch.linalg.solve(V, Y)  # [n, prod(shapes)]
    except Exception:
        # fallback to linear
        return _linear_forecast(history, step_idx)
    # Evaluate at x_t_norm
    basis_t = torch.stack([cheb_vals(torch.tensor(x_t_norm), k) for k in range(n)])  # [n]
    pred_flat = basis_t @ C  # [prod(shapes)]
    return pred_flat.reshape(shapes)


# ---------------------------------------------------------------------------
# node
# ---------------------------------------------------------------------------

class PSN_Step_Skip_Accelerator:
    """Patch a MODEL so that a fraction of diffusion steps are skipped.

    The patched model carries:
      * ``model_options['psn_step_skip']`` – dict with skip_ratio, method,
        and a mutable ``state`` dict.
      * ``_psn_step_skip_hook`` – a callable that the sampler (or a wrapper)
        can invoke before each forward pass.  It returns ``True`` if the step
        should be skipped (use the predicted output) and ``False`` otherwise.

    The hook maintains a short history of the last few step outputs so that
    the forecast can be computed when a skip is triggered.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
                "skip_ratio": ("FLOAT", {"default": 0.25, "min": 0.0, "max": 0.5, "step": 0.05}),
                "forecast_method": ("chebyshev,linear".split(","),),
            }
        }

    RETURN_TYPES = ("MODEL",)
    RETURN_NAMES = ("model",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, model, skip_ratio, forecast_method):
        if not isinstance(model, dict):
            raise TypeError("model must be a dict (ComfyUI MODEL)")
        if not (0.0 <= skip_ratio <= 0.5):
            raise ValueError("skip_ratio must be in [0.0, 0.5]")
        if forecast_method not in ("chebyshev", "linear"):
            raise ValueError("forecast_method must be 'chebyshev' or 'linear'")

        # Build a patched copy – never mutate the input.
        patched = dict(model)
        opts = dict(patched.get("model_options", {}))

        state = {
            "skip_ratio": float(skip_ratio),
            "method": forecast_method,
            "step": 0,
            "history": [],       # list of tensors (step outputs)
            "skipped": 0,
            "total": 0,
        }
        opts["psn_step_skip"] = state

        def _hook(step_output):
            """Called by the sampler with the current step output.

            Returns (should_skip, predicted_or_none).
            """
            state["total"] += 1
            state["step"] = state["total"]
            state["history"].append(step_output.detach().clone())
            # Keep only the last 8 entries to bound memory.
            if len(state["history"]) > 8:
                state["history"] = state["history"][-8:]

            # Decide whether to skip the *next* step.
            # We skip with probability skip_ratio, but only after we have
            # at least 2 history entries (needed for forecasting).
            if len(state["history"]) < 2:
                return False, None
            # Deterministic skip schedule: skip every k-th step where
            # k = round(1 / skip_ratio) if skip_ratio > 0 else never.
            if state["skip_ratio"] <= 0.0:
                return False, None
            k = max(2, int(round(1.0 / state["skip_ratio"])))
            if state["step"] % k == 0:
                if state["method"] == "chebyshev":
                    pred = _chebyshev_forecast(state["history"], state["step"] + 1)
                else:
                    pred = _linear_forecast(state["history"], state["step"] + 1)
                state["skipped"] += 1
                return True, pred
            return False, None

        patched["_psn_step_skip_hook"] = _hook
        patched["model_options"] = opts
        return (patched,)


# ---------------------------------------------------------------------------
# module-level mappings
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_Step_Skip_Accelerator": PSN_Step_Skip_Accelerator,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Step_Skip_Accelerator": "Step Skip Accelerator (ParametricStudio)",
}
