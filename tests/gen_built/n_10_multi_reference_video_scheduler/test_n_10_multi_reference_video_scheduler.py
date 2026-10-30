import torch
import n_10_multi_reference_video_scheduler as mod


def make_refs(n, h=8, w=8, c=3):
    """Create n distinct reference images [n,h,w,c] in 0..1."""
    imgs = []
    for i in range(n):
        v = (i + 1) / (n + 1)
        imgs.append(torch.full((1, h, w, c), v))
    return torch.cat(imgs, dim=0)


def test_scheduler_basic():
    """Cat in segment 1, Dog in segment 2."""
    refs = make_refs(2)
    prompt = "A cat sits on a mat. A dog runs in the park."
    keywords = "cat\ndog"
    node = mod.PSN_MultiRefScheduler()
    (plan,) = node.run(prompt, refs, keywords, 1.0)
    assert isinstance(plan, list) and len(plan) == 2, f"expected 2 segments, got {len(plan)}"
    # Segment 0 should reference cat (index 0), segment 1 should reference dog (index 1).
    assert 0 in plan[0]["reference_indices"], f"seg0 refs: {plan[0]['reference_indices']}"
    assert 1 in plan[1]["reference_indices"], f"seg1 refs: {plan[1]['reference_indices']}"
    # Cat should NOT be in segment 1 (dog segment) and dog NOT in segment 0.
    assert 1 not in plan[0]["reference_indices"], f"dog leaked into seg0: {plan[0]['reference_indices']}"
    assert 0 not in plan[1]["reference_indices"], f"cat leaked into seg1: {plan[1]['reference_indices']}"
    # Weights default to 1.0.
    assert plan[0]["reference_weights"] == [1.0]
    assert plan[1]["reference_weights"] == [1.0]


def test_scheduler_fallback():
    """When no keyword matches, all references are assigned (fallback)."""
    refs = make_refs(2)
    prompt = "A bird flies. A fish swims."
    keywords = "cat\ndog"
    node = mod.PSN_MultiRefScheduler()
    (plan,) = node.run(prompt, refs, keywords, 1.0)
    assert len(plan) == 2
    # No match -> fallback assigns all refs.
    assert plan[0]["reference_indices"] == [0, 1]
    assert plan[1]["reference_indices"] == [0, 1]


def test_scheduler_segment_duration():
    """Larger segment_duration groups more sentences per segment."""
    refs = make_refs(1)
    prompt = "One. Two. Three. Four."
    keywords = ""
    node = mod.PSN_MultiRefScheduler()
    # duration=1.0 -> 1 sentence per segment -> 4 segments
    (plan1,) = node.run(prompt, refs, keywords, 1.0)
    assert len(plan1) == 4, f"expected 4, got {len(plan1)}"
    # duration=2.0 -> 1 sentence per segment (ceil(1/2.0)=1) -> 4 segments
    (plan2,) = node.run(prompt, refs, keywords, 2.0)
    assert len(plan2) == 4, f"expected 4, got {len(plan2)}"
    # duration=0.5 -> 2 sentences per segment (ceil(1/0.5)=2) -> 2 segments
    (plan3,) = node.run(prompt, refs, keywords, 0.5)
    assert len(plan3) == 2, f"expected 2, got {len(plan3)}"


def test_scheduler_bad_inputs():
    """Bad inputs raise ValueError."""
    refs = make_refs(1)
    node = mod.PSN_MultiRefScheduler()
    # Empty prompt
    try:
        node.run("", refs, "", 1.0)
        assert False, "empty prompt should raise"
    except ValueError:
        pass
    # Non-tensor references
    try:
        node.run("A cat.", "not a tensor", "", 1.0)
        assert False, "non-tensor refs should raise"
    except ValueError:
        pass
    # Bad image shape
    bad = torch.zeros(2, 8, 8)  # 3D, not 4D
    try:
        node.run("A cat.", bad, "", 1.0)
        assert False, "bad shape should raise"
    except ValueError:
        pass
    # Out-of-range values
    bad2 = torch.full((1, 8, 8, 3), 5.0)
    try:
        node.run("A cat.", bad2, "", 1.0)
        assert False, "out-of-range should raise"
    except ValueError:
        pass
    # Too many keyword lines
    try:
        node.run("A cat.", refs, "a\nb\nc", 1.0)
        assert False, "too many keyword lines should raise"
    except ValueError:
        pass
    # Zero duration
    try:
        node.run("A cat.", refs, "", 0.0)
        assert False, "zero duration should raise"
    except ValueError:
        pass


def test_weight_adjuster_basic():
    """Strength scales weights."""
    plan = [
        {"segment_index": 0, "reference_indices": [0, 1], "reference_weights": [1.0, 1.0]},
        {"segment_index": 1, "reference_indices": [0], "reference_weights": [0.5]},
    ]
    node = mod.PSN_RefWeightAdjuster()
    (out,) = node.run(plan, 0.5)
    assert out[0]["reference_weights"] == [0.5, 0.5]
    assert out[1]["reference_weights"] == [0.25]
    # Input not mutated
    assert plan[0]["reference_weights"] == [1.0, 1.0]
    assert plan[1]["reference_weights"] == [0.5]


def test_weight_adjuster_clamp_and_bad():
    """Weights clamped to [0,2]; bad inputs raise."""
    plan = [{"segment_index": 0, "reference_indices": [0], "reference_weights": [1.5]}]
    node = mod.PSN_RefWeightAdjuster()
    (out,) = node.run(plan, 2.0)
    assert out[0]["reference_weights"] == [2.0], f"expected clamp to 2.0, got {out[0]['reference_weights']}"
    # Bad plan type
    try:
        node.run("not a list", 1.0)
        assert False, "non-list plan should raise"
    except ValueError:
        pass
    # Bad strength
    try:
        node.run(plan, 5.0)
        assert False, "strength > 2 should raise"
    except ValueError:
        pass
    try:
        node.run(plan, -1.0)
        assert False, "strength < 0 should raise"
    except ValueError:
        pass


def test_module_mappings():
    """Module-level mappings exist and are correct."""
    assert "PSN_MultiRefScheduler" in mod.NODE_CLASS_MAPPINGS
    assert "PSN_RefWeightAdjuster" in mod.NODE_CLASS_MAPPINGS
    assert mod.NODE_DISPLAY_NAME_MAPPINGS["PSN_MultiRefScheduler"] == "Multi-Reference Video Scheduler"
    assert mod.NODE_DISPLAY_NAME_MAPPINGS["PSN_RefWeightAdjuster"] == "Reference Weight Adjuster"
    # INPUT_TYPES classmethod works
    it = mod.PSN_MultiRefScheduler.INPUT_TYPES()
    assert "long_prompt" in it["required"]
    assert "reference_images" in it["required"]
    assert "segment_duration" in it["required"]
    it2 = mod.PSN_RefWeightAdjuster.INPUT_TYPES()
    assert "segment_plan" in it2["required"]
    assert "strength" in it2["required"]


if __name__ == "__main__":
    test_scheduler_basic()
    test_scheduler_fallback()
    test_scheduler_segment_duration()
    test_scheduler_bad_inputs()
    test_weight_adjuster_basic()
    test_weight_adjuster_clamp_and_bad()
    test_module_mappings()
    print("ok")
