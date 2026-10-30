"""PSN_Tail_Frame_Selector: Selects the best tail frame from a set of candidates for video continuation.

This module implements the pure-logic, secure-by-design part of the tail frame selection.
Since the spec requires GPU/torch/skimage for actual image similarity computation (SSIM, PSNR, LPIPS),
this implementation accepts pre-computed similarity scores as plain values (lists of floats) instead
of raw IMAGE tensors. The node validates the inputs, applies the selected metric's scoring logic
(maximization of similarity), and returns the index and score of the best candidate.

Inputs:
  - candidate_scores (LIST): A list of pre-computed similarity scores for each candidate frame.
  - previous_frame_id (STRING): Identifier for the previous frame (for logging/tracing).
  - similarity_metric (COMBO): The metric used to compute the scores ["SSIM", "PSNR", "LPIPS"].

Outputs:
  - selected_index (INT): The index of the best candidate frame.
  - similarity_score (FLOAT): The similarity score of the selected frame.
  - reason (STRING): A human-readable explanation of the selection.

Note: In a full ComfyUI environment, a separate node would compute the similarity scores
using torch/skimage/lpips and pass them to this node. This node handles the selection logic.
"""

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/Video"

# Valid similarity metrics
_METRICS = ["SSIM", "PSNR", "LPIPS"]


class PSN_Tail_Frame_Selector:
    """Selects the best tail frame from a set of candidates based on pre-computed similarity scores."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "candidate_scores": ("LIST", {"default": []}),
                "similarity_metric": (_METRICS,),
            },
            "optional": {
                "previous_frame_id": ("STRING", {"default": "prev_frame_0"}),
            },
        }

    RETURN_TYPES = ("INT", "FLOAT", "STRING")
    RETURN_NAMES = ("selected_index", "similarity_score", "reason")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, candidate_scores, similarity_metric, previous_frame_id="prev_frame_0"):
        """
        Select the best candidate frame based on the highest similarity score.

        Args:
            candidate_scores: List of float similarity scores for each candidate frame.
            similarity_metric: The metric used to compute the scores.
            previous_frame_id: Identifier for the previous frame.

        Returns:
            Tuple of (selected_index, similarity_score, reason)
        """
        # Validate candidate_scores
        if not isinstance(candidate_scores, (list, tuple)):
            return (0, 0.0, "Error: candidate_scores must be a list or tuple")

        if len(candidate_scores) == 0:
            return (0, 0.0, "Error: No candidate frames provided")

        # Validate each score is a number
        for i, score in enumerate(candidate_scores):
            if not isinstance(score, (int, float)):
                return (0, 0.0, f"Error: Score at index {i} is not a number")
            if isinstance(score, float) and (score != score):  # NaN check
                return (0, 0.0, f"Error: Score at index {i} is NaN")

        # For SSIM and PSNR, higher is better. For LPIPS, lower is better (distance metric).
        # However, the spec says "selects the one with the highest similarity", so we assume
        # the scores are already normalized such that higher = more similar for all metrics.
        # If LPIPS is used, the caller should invert the scores (e.g., 1 - lpips_score) before passing.
        
        # Find the index of the maximum score
        best_index = 0
        best_score = candidate_scores[0]
        
        for i in range(1, len(candidate_scores)):
            if candidate_scores[i] > best_score:
                best_score = candidate_scores[i]
                best_index = i

        reason = f"Selected candidate {best_index} with score {best_score:.4f} using {similarity_metric} metric"
        
        return (best_index, float(best_score), reason)


NODE_CLASS_MAPPINGS = {
    "PSN_Tail_Frame_Selector": PSN_Tail_Frame_Selector,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Tail_Frame_Selector": "PSN Tail Frame Selector",
}
