"""Tests for n_9_batch_scene_generation_queue.

Run with:  python3 -B test_n_9_batch_scene_generation_queue.py
Must print 'ok' and exit 0.
"""

import json
import torch

from n_9_batch_scene_generation_queue import (
    PSN_SceneQueueBuilder,
    PSN_BatchExecutor,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


# ---------------------------------------------------------------------------
# 1. Module-level registration
# ---------------------------------------------------------------------------
assert "PSN_SceneQueueBuilder" in NODE_CLASS_MAPPINGS
assert "PSN_BatchExecutor" in NODE_CLASS_MAPPINGS
assert NODE_DISPLAY_NAME_MAPPINGS["PSN_SceneQueueBuilder"] == "PSN Scene Queue Builder"
assert NODE_DISPLAY_NAME_MAPPINGS["PSN_BatchExecutor"] == "PSN Batch Executor"

# ---------------------------------------------------------------------------
# 2. INPUT_TYPES / RETURN_TYPES / FUNCTION / CATEGORY
# ---------------------------------------------------------------------------
for cls in (PSN_SceneQueueBuilder, PSN_BatchExecutor):
    it = cls.INPUT_TYPES()
    assert "required" in it
    assert cls.RETURN_TYPES == ("LIST[STRING]",) or cls.RETURN_TYPES == ("LIST[IMAGE]",)
    assert cls.FUNCTION == "run"
    assert cls.CATEGORY.startswith("ParametricStudio/")

# ---------------------------------------------------------------------------
# 3. SceneQueueBuilder: 3 variants -> 3 queue items
# ---------------------------------------------------------------------------
builder = PSN_SceneQueueBuilder()
variants = json.dumps(["a forest at dawn", "a city at night", "a beach at sunset"])
(items,) = builder.run(base_prompt="a detailed scene", scene_variants=variants)
assert len(items) == 3, f"expected 3 items, got {len(items)}"
assert all(isinstance(x, str) for x in items)
assert items[0] == "a detailed scene, a forest at dawn"
assert items[1] == "a detailed scene, a city at night"
assert items[2] == "a detailed scene, a beach at sunset"

# ---------------------------------------------------------------------------
# 4. SceneQueueBuilder: single string variant (not a list)
# ---------------------------------------------------------------------------
(items2,) = builder.run(base_prompt="base", scene_variants='"only one"')
assert len(items2) == 1
assert items2[0] == "base, only one"

# ---------------------------------------------------------------------------
# 5. SceneQueueBuilder: bad JSON raises ValueError
# ---------------------------------------------------------------------------
try:
    builder.run(base_prompt="base", scene_variants="not json at all")
    raise AssertionError("expected ValueError for bad JSON")
except ValueError:
    pass

# ---------------------------------------------------------------------------
# 6. SceneQueueBuilder: empty list raises ValueError
# ---------------------------------------------------------------------------
try:
    builder.run(base_prompt="base", scene_variants="[]")
    raise AssertionError("expected ValueError for empty list")
except ValueError:
    pass

# ---------------------------------------------------------------------------
# 7. SceneQueueBuilder: non-string element raises ValueError
# ---------------------------------------------------------------------------
try:
    builder.run(base_prompt="base", scene_variants='["ok", 42]')
    raise AssertionError("expected ValueError for non-string element")
except ValueError:
    pass

# ---------------------------------------------------------------------------
# 8. BatchExecutor: 2 prompts -> 2 IMAGE tensors, correct shape and range
# ---------------------------------------------------------------------------
executor = PSN_BatchExecutor()
(results,) = executor.run(queue_items=["prompt A", "prompt B"], height=16, width=16, channels=3)
assert len(results) == 2, f"expected 2 results, got {len(results)}"
for img in results:
    assert isinstance(img, torch.Tensor), f"expected torch.Tensor, got {type(img)}"
    assert img.shape == (1, 16, 16, 3), f"bad shape {img.shape}"
    assert img.dtype == torch.float32
    assert img.min().item() >= 0.0 and img.max().item() <= 1.0

# ---------------------------------------------------------------------------
# 9. BatchExecutor: different prompts produce different images
# ---------------------------------------------------------------------------
assert not torch.equal(results[0], results[1]), "different prompts should give different images"

# ---------------------------------------------------------------------------
# 10. BatchExecutor: same prompt is deterministic
# ---------------------------------------------------------------------------
(r1,) = executor.run(queue_items=["same prompt"], height=8, width=8, channels=1)
(r2,) = executor.run(queue_items=["same prompt"], height=8, width=8, channels=1)
assert torch.equal(r1[0], r2[0]), "same prompt must be deterministic"

# ---------------------------------------------------------------------------
# 11. BatchExecutor: bad input (None) raises ValueError
# ---------------------------------------------------------------------------
try:
    executor.run(queue_items=None)
    raise AssertionError("expected ValueError for None queue_items")
except ValueError:
    pass

# ---------------------------------------------------------------------------
# 12. BatchExecutor: bad input (non-list) raises ValueError
# ---------------------------------------------------------------------------
try:
    executor.run(queue_items="just a string")
    raise AssertionError("expected ValueError for non-list queue_items")
except ValueError:
    pass

# ---------------------------------------------------------------------------
# 13. BatchExecutor: empty list raises ValueError
# ---------------------------------------------------------------------------
try:
    executor.run(queue_items=[])
    raise AssertionError("expected ValueError for empty queue_items")
except ValueError:
    pass

# ---------------------------------------------------------------------------
# 14. End-to-end: builder -> executor
# ---------------------------------------------------------------------------
(e2e_items,) = builder.run(base_prompt="epic landscape", scene_variants='["mountains", "ocean"]')
(e2e_results,) = executor.run(queue_items=e2e_items, height=8, width=8, channels=3)
assert len(e2e_results) == 2
assert all(img.shape == (1, 8, 8, 3) for img in e2e_results)

print("ok")
