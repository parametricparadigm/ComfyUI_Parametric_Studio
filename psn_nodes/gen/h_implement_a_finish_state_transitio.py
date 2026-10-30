"""ComfyUI custom node: finish a pipeline stage with auto-approval vs manual review.

Implements a `finish` state-transition function for pipeline stages. The node
accepts a stage name, a mode (auto or manual), and an optional quality score,
and returns the resulting stage state (approved / pending_review / rejected)
along with a human-readable status string.
"""

import torch

CATEGORY = "ParametricStudio/Pipeline"

# Valid stage states
STATE_APPROVED = "approved"
STATE_PENDING = "pending_review"
STATE_REJECTED = "rejected"

# Valid modes
MODE_AUTO = "auto"
MODE_MANUAL = "manual"


def _finish(stage_name: str, mode: str, score: float = 1.0, threshold: float = 0.5) -> dict:
    """Core finish state-transition logic.

    Args:
        stage_name: name of the pipeline stage being finished.
        mode: "auto" or "manual".
        score: quality score in [0, 1].
        threshold: minimum score for auto-approval.

    Returns:
        dict with keys: stage, state, mode, score, message
    """
    if not isinstance(stage_name, str) or not stage_name.strip():
        raise ValueError("stage_name must be a non-empty string")
    if mode not in (MODE_AUTO, MODE_MANUAL):
        raise ValueError(f"mode must be '{MODE_AUTO}' or '{MODE_MANUAL}', got {mode!r}")
    if not isinstance(score, (int, float)):
        raise TypeError("score must be a number")
    score = float(score)
    if score < 0.0 or score > 1.0:
        raise ValueError(f"score must be in [0, 1], got {score}")
    if not isinstance(threshold, (int, float)):
        raise TypeError("threshold must be a number")
    threshold = float(threshold)
    if threshold < 0.0 or threshold > 1.0:
        raise ValueError(f"threshold must be in [0, 1], got {threshold}")

    if mode == MODE_AUTO:
        if score >= threshold:
            state = STATE_APPROVED
            message = f"Stage '{stage_name}' auto-approved (score {score:.2f} >= threshold {threshold:.2f})"
        else:
            state = STATE_REJECTED
            message = f"Stage '{stage_name}' auto-rejected (score {score:.2f} < threshold {threshold:.2f})"
    else:
        state = STATE_PENDING
        message = f"Stage '{stage_name}' pending manual review (score {score:.2f})"

    return {
        "stage": stage_name.strip(),
        "state": state,
        "mode": mode,
        "score": score,
        "message": message,
    }


class PSN_StageFinish:
    """Finish a pipeline stage: auto-approve or queue for manual review based on mode."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "stage_name": ("STRING", {"default": "stage_1", "multiline": False}),
                "mode": ([MODE_AUTO, MODE_MANUAL], {"default": MODE_AUTO}),
                "score": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "threshold": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "FLOAT")
    RETURN_NAMES = ("state", "message", "score")
    FUNCTION = "run"
    CATEGORY = CATEGORY

    def run(self, stage_name: str, mode: str, score: float, threshold: float):
        result = _finish(stage_name, mode, score, threshold)
        return (result["state"], result["message"], result["score"])


class PSN_StageFinishBatch:
    """Finish multiple pipeline stages at once; returns a summary tensor of states.

    Accepts a list of stage names (one per line), a mode, and a score tensor
    [N] (one score per stage). Returns the list of states as a string and a
    float tensor of per-stage scores.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "stage_names": ("STRING", {"default": "stage_1\nstage_2", "multiline": True}),
                "mode": ([MODE_AUTO, MODE_MANUAL], {"default": MODE_AUTO}),
                "scores": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "threshold": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
            }
        }

    RETURN_TYPES = ("STRING", "FLOAT")
    RETURN_NAMES = ("states_summary", "scores_tensor")
    FUNCTION = "run"
    CATEGORY = CATEGORY

    def run(self, stage_names: str, mode: str, scores: float, threshold: float):
        names = [ln.strip() for ln in stage_names.split("\n") if ln.strip()]
        if not names:
            raise ValueError("stage_names must contain at least one non-empty line")

        states = []
        score_list = []
        for name in names:
            result = _finish(name, mode, scores, threshold)
            states.append(f"{name}: {result['state']}")
            score_list.append(result["score"])

        summary = "\n".join(states)
        scores_tensor = torch.tensor(score_list, dtype=torch.float32)
        return (summary, scores_tensor)


NODE_CLASS_MAPPINGS = {
    "PSN_StageFinish": PSN_StageFinish,
    "PSN_StageFinishBatch": PSN_StageFinishBatch,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_StageFinish": "Stage Finish (Auto/Manual)",
    "PSN_StageFinishBatch": "Stage Finish Batch",
}
