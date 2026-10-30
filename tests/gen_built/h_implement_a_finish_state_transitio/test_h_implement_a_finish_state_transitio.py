"""Tests for h_implement_a_finish_state_transitio module."""

import torch
from h_implement_a_finish_state_transitio import (
    _finish,
    PSN_StageFinish,
    PSN_StageFinishBatch,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    STATE_APPROVED,
    STATE_PENDING,
    STATE_REJECTED,
    MODE_AUTO,
    MODE_MANUAL,
)


# 1. Auto mode with high score -> approved
r = _finish("brief", MODE_AUTO, score=0.9, threshold=0.5)
assert r["state"] == STATE_APPROVED, f"Expected approved, got {r['state']}"
assert r["stage"] == "brief"
assert r["mode"] == MODE_AUTO
assert r["score"] == 0.9

# 2. Auto mode with low score -> rejected
r = _finish("copy", MODE_AUTO, score=0.3, threshold=0.5)
assert r["state"] == STATE_REJECTED, f"Expected rejected, got {r['state']}"

# 3. Manual mode -> always pending review regardless of score
r = _finish("style", MODE_MANUAL, score=1.0, threshold=0.5)
assert r["state"] == STATE_PENDING, f"Expected pending_review, got {r['state']}"

# 4. Edge: score exactly at threshold -> approved (>=)
r = _finish("images", MODE_AUTO, score=0.5, threshold=0.5)
assert r["state"] == STATE_APPROVED, f"Expected approved at threshold, got {r['state']}"

# 5. Edge: score 0.0 in auto mode -> rejected
r = _finish("build", MODE_AUTO, score=0.0, threshold=0.5)
assert r["state"] == STATE_REJECTED

# 6. Edge: score 1.0 in manual mode -> still pending
r = _finish("export", MODE_MANUAL, score=1.0, threshold=0.0)
assert r["state"] == STATE_PENDING

# 7. Bad input: empty stage name raises ValueError
try:
    _finish("", MODE_AUTO, score=0.9)
    assert False, "Expected ValueError for empty stage name"
except ValueError:
    pass

# 8. Bad input: invalid mode raises ValueError
try:
    _finish("brief", "invalid_mode", score=0.9)
    assert False, "Expected ValueError for invalid mode"
except ValueError:
    pass

# 9. Bad input: score out of range raises ValueError
try:
    _finish("brief", MODE_AUTO, score=1.5)
    assert False, "Expected ValueError for score > 1"
except ValueError:
    pass

# 10. Bad input: negative score raises ValueError
try:
    _finish("brief", MODE_AUTO, score=-0.1)
    assert False, "Expected ValueError for negative score"
except ValueError:
    pass

# 11. Node class PSN_StageFinish: check INPUT_TYPES structure
it = PSN_StageFinish.INPUT_TYPES()
assert "required" in it
assert "stage_name" in it["required"]
assert "mode" in it["required"]
assert "score" in it["required"]
assert "threshold" in it["required"]

# 12. Node class PSN_StageFinish: check RETURN_TYPES and FUNCTION
assert PSN_StageFinish.RETURN_TYPES == ("STRING", "STRING", "FLOAT")
assert PSN_StageFinish.FUNCTION == "run"
assert PSN_StageFinish.CATEGORY == "ParametricStudio/Pipeline"

# 13. Run PSN_StageFinish node
node = PSN_StageFinish()
state, message, score = node.run("brief", MODE_AUTO, 0.9, 0.5)
assert state == STATE_APPROVED
assert "auto-approved" in message
assert score == 0.9

# 14. Run PSN_StageFinish node with manual mode
state, message, score = node.run("copy", MODE_MANUAL, 0.9, 0.5)
assert state == STATE_PENDING
assert "pending manual review" in message

# 15. PSN_StageFinishBatch: run with multiple stages
batch_node = PSN_StageFinishBatch()
summary, scores_tensor = batch_node.run("brief\ncopy\nstyle", MODE_AUTO, 0.8, 0.5)
assert isinstance(scores_tensor, torch.Tensor)
assert scores_tensor.shape == (3,)
assert scores_tensor.dtype == torch.float32
assert "brief: approved" in summary
assert "copy: approved" in summary
assert "style: approved" in summary

# 16. PSN_StageFinishBatch: mixed scores with threshold
summary, scores_tensor = batch_node.run("a\nb\nc", MODE_AUTO, 0.3, 0.5)
assert "a: rejected" in summary
assert torch.allclose(scores_tensor, torch.tensor([0.3, 0.3, 0.3]))

# 17. PSN_StageFinishBatch: empty stage names raises ValueError
try:
    batch_node.run("\n\n", MODE_AUTO, 0.8, 0.5)
    assert False, "Expected ValueError for empty stage names"
except ValueError:
    pass

# 18. NODE_CLASS_MAPPINGS and NODE_DISPLAY_NAME_MAPPINGS exist and are correct
assert "PSN_StageFinish" in NODE_CLASS_MAPPINGS
assert "PSN_StageFinishBatch" in NODE_CLASS_MAPPINGS
assert NODE_CLASS_MAPPINGS["PSN_StageFinish"] is PSN_StageFinish
assert NODE_CLASS_MAPPINGS["PSN_StageFinishBatch"] is PSN_StageFinishBatch
assert "PSN_StageFinish" in NODE_DISPLAY_NAME_MAPPINGS
assert "PSN_StageFinishBatch" in NODE_DISPLAY_NAME_MAPPINGS

# 19. Whitespace in stage name is stripped
r = _finish("  brief  ", MODE_AUTO, score=0.9)
assert r["stage"] == "brief"

# 20. Threshold edge: threshold 0.0, score 0.0 -> approved
r = _finish("x", MODE_AUTO, score=0.0, threshold=0.0)
assert r["state"] == STATE_APPROVED

print("ok")
