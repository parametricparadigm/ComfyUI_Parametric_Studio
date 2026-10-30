"""Tests for n_2_dynamic_prompt_refinement_loop.py"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from n_2_dynamic_prompt_refinement_loop import (
    PSN_Prompt_Refiner_Loop,
    PSN_Prompt_Structure_Enforcer,
    _heuristic_score,
    _parse_mock_handle,
    _extract_components,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)

# ---------------------------------------------------------------------------
# 1. Module-level registration
# ---------------------------------------------------------------------------
assert "PSN_Prompt_Refiner_Loop" in NODE_CLASS_MAPPINGS, "Refiner not in NODE_CLASS_MAPPINGS"
assert "PSN_Prompt_Structure_Enforcer" in NODE_CLASS_MAPPINGS, "Enforcer not in NODE_CLASS_MAPPINGS"
assert NODE_DISPLAY_NAME_MAPPINGS["PSN_Prompt_Refiner_Loop"] == "PSN Prompt Refiner Loop"
assert NODE_DISPLAY_NAME_MAPPINGS["PSN_Prompt_Structure_Enforcer"] == "PSN Prompt Structure Enforcer"

# ---------------------------------------------------------------------------
# 2. INPUT_TYPES / RETURN_TYPES / FUNCTION / CATEGORY
# ---------------------------------------------------------------------------
rt = PSN_Prompt_Refiner_Loop.INPUT_TYPES()
assert "initial_prompt" in rt["required"]
assert "llm_handle" in rt["required"]
assert "max_iterations" in rt["required"]
assert "quality_threshold" in rt["required"]
assert PSN_Prompt_Refiner_Loop.RETURN_TYPES == ("STRING", "INT", "FLOAT")
assert PSN_Prompt_Refiner_Loop.RETURN_NAMES == ("refined_prompt", "iteration_count", "final_score")
assert PSN_Prompt_Refiner_Loop.FUNCTION == "run"
assert PSN_Prompt_Refiner_Loop.CATEGORY == "ParametricStudio/Prompt"

rt2 = PSN_Prompt_Structure_Enforcer.INPUT_TYPES()
assert "prompt" in rt2["required"]
assert "template" in rt2["required"]
assert PSN_Prompt_Structure_Enforcer.RETURN_TYPES == ("STRING",)
assert PSN_Prompt_Structure_Enforcer.FUNCTION == "run"

# ---------------------------------------------------------------------------
# 3. Heuristic scorer: empty prompt -> 0.0
# ---------------------------------------------------------------------------
assert _heuristic_score("") == 0.0
assert _heuristic_score("   ") == 0.0

# ---------------------------------------------------------------------------
# 4. Heuristic scorer: short prompt scores low, detailed prompt scores higher
# ---------------------------------------------------------------------------
short_score = _heuristic_score("a cat")
detailed_score = _heuristic_score(
    "a cat sitting in a sunlit forest, warm cinematic lighting, detailed fur texture, dramatic mood, soft shadows, rich color palette"
)
assert short_score < 0.5, f"short prompt should score < 0.5, got {short_score}"
assert detailed_score > short_score, f"detailed prompt should score higher, got {detailed_score} vs {short_score}"

# ---------------------------------------------------------------------------
# 5. Mock handle parsing
# ---------------------------------------------------------------------------
handle = "mock:score=0.4,rewrite=a more detailed cat;score=0.9,rewrite=final beautiful cat"
turns = _parse_mock_handle(handle)
assert len(turns) == 2
assert turns[0] == (0.4, "a more detailed cat")
assert turns[1] == (0.9, "final beautiful cat")

# empty handle -> no turns
assert _parse_mock_handle("") == []
assert _parse_mock_handle("not a mock") == []

# ---------------------------------------------------------------------------
# 6. Refiner loop: mock LLM returns low score first, then high score -> 2 iterations
# ---------------------------------------------------------------------------
node = PSN_Prompt_Refiner_Loop()
refined, iters, score = node.run(
    initial_prompt="a cat",
    llm_handle="mock:score=0.4,rewrite=a more detailed cat;score=0.9,rewrite=final beautiful cat",
    max_iterations=5,
    quality_threshold=0.7,
)
assert iters == 2, f"expected 2 iterations, got {iters}"
assert score == 0.9, f"expected final score 0.9, got {score}"
assert refined == "final beautiful cat", f"unexpected refined prompt: {refined}"

# ---------------------------------------------------------------------------
# 7. Refiner loop: max_iterations reached without meeting threshold
# ---------------------------------------------------------------------------
refined2, iters2, score2 = node.run(
    initial_prompt="a cat",
    llm_handle="mock:score=0.2,rewrite=still bad;score=0.3,rewrite=still bad 2;score=0.4,rewrite=still bad 3",
    max_iterations=3,
    quality_threshold=0.9,
)
assert iters2 == 3, f"expected 3 iterations (max), got {iters2}"
assert score2 == 0.4, f"expected final score 0.4, got {score2}"

# ---------------------------------------------------------------------------
# 8. Refiner loop: empty prompt -> immediate return
# ---------------------------------------------------------------------------
refined3, iters3, score3 = node.run(
    initial_prompt="",
    llm_handle="",
    max_iterations=5,
    quality_threshold=0.7,
)
assert refined3 == ""
assert iters3 == 0
assert score3 == 0.0

# ---------------------------------------------------------------------------
# 9. Refiner loop: threshold already met on first iteration
# ---------------------------------------------------------------------------
refined4, iters4, score4 = node.run(
    initial_prompt="a cat",
    llm_handle="mock:score=0.95,rewrite=already great",
    max_iterations=5,
    quality_threshold=0.7,
)
assert iters4 == 1, f"expected 1 iteration, got {iters4}"
assert score4 == 0.95
assert refined4 == "already great"

# ---------------------------------------------------------------------------
# 10. Structure Enforcer: basic template filling
# ---------------------------------------------------------------------------
node2 = PSN_Prompt_Structure_Enforcer()
result = node2.run(
    prompt="a cat in a forest, warm lighting, oil painting style",
    template="{subject}, {env}, {light}, {style}",
)
structured = result[0]
assert "a cat" in structured, f"subject missing: {structured}"
assert "forest" in structured, f"env missing: {structured}"
assert "lighting" in structured.lower(), f"light missing: {structured}"
assert "oil painting" in structured.lower(), f"style missing: {structured}"

# ---------------------------------------------------------------------------
# 11. Structure Enforcer: empty prompt
# ---------------------------------------------------------------------------
result_empty = node2.run(prompt="", template="{subject}, {env}, {light}, {style}")
assert result_empty[0] == "", f"expected empty string, got {result_empty[0]!r}"

# ---------------------------------------------------------------------------
# 12. Structure Enforcer: custom template with subset of fields
# ---------------------------------------------------------------------------
result_sub = node2.run(
    prompt="a dog in a city, neon lighting, 3d render style",
    template="{subject} | {light}",
)
assert "a dog" in result_sub[0]
assert "neon" in result_sub[0].lower()

# ---------------------------------------------------------------------------
# 13. _extract_components: verify component extraction
# ---------------------------------------------------------------------------
comps = _extract_components("a cat in a forest, warm lighting, oil painting style")
assert comps["subject"], f"subject should not be empty: {comps}"
assert "lighting" in comps["light"].lower(), f"light component wrong: {comps['light']}"
assert "oil" in comps["style"].lower(), f"style component wrong: {comps['style']}"

# ---------------------------------------------------------------------------
# 14. Bad input: non-string llm_handle should not crash (treated as empty)
# ---------------------------------------------------------------------------
refined5, iters5, score5 = node.run(
    initial_prompt="a cat",
    llm_handle=None,
    max_iterations=2,
    quality_threshold=0.7,
)
# None is falsy so _parse_mock_handle returns [] and heuristic is used
assert isinstance(refined5, str)
assert isinstance(iters5, int)
assert isinstance(score5, float)

print('ok')
