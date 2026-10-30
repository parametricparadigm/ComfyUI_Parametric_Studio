import json, os
import pytest
from psn import recipes, camera, fallback_prompt as FP, rotation as R
from psn.subagents.runner import Result
from psn.subagents import ROLES
WF = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "workflows")

def test_every_recipe_cites_a_source_and_a_quote():
    assert recipes.recipe_problems() == [] and recipes.recipe_problems({"x": {"source": "a"}}) == ["recipe 'x' has no quote"]

def test_ltx_decode_rule_by_clip_length():
    short = recipes.ltx_decode_settings(121, 24); long = recipes.ltx_decode_settings(241, 24)
    assert not short["long_clip"] and short["temporal_overlap"] == 8 and short["vae"] is None and short["seconds"] == 5.0
    assert long["long_clip"] and long["temporal_overlap"] == 16 and long["tile_size"] == 512 and long["temporal_size"] == 64 and long["vae"] == recipes.LTX_CONV_VAE
    g = {"1": {"class_type": "VAELoader", "inputs": {"vae_name": recipes.LTX_DIFF_VAE}}, "2": {"class_type": "VAEDecodeTiled", "inputs": {"tile_size": 256, "overlap": 8, "temporal_size": 8, "temporal_overlap": 2}}, "3": {"class_type": "KSampler", "inputs": {"steps": 9}}}
    out = recipes.apply_ltx_safe_decode(g, 241, 24)
    assert out["1"]["inputs"]["vae_name"] == recipes.LTX_CONV_VAE and out["2"]["inputs"] == {"tile_size": 512, "overlap": 64, "temporal_size": 64, "temporal_overlap": 16} and out["3"] == g["3"]
    assert g["1"]["inputs"]["vae_name"] == recipes.LTX_DIFF_VAE                                   # the input graph is untouched
    assert recipes.apply_ltx_safe_decode(g, 121, 24)["1"]["inputs"]["vae_name"] == recipes.LTX_DIFF_VAE

def test_workflows_in_the_repo_follow_the_pinned_recipes():
    k = json.load(open(os.path.join(WF, "flux3_klein_core_t2i_api.json"))); ks = next(n for n in k.values() if n["class_type"] == "KSampler")["inputs"]; r = recipes.RECIPES["flux3-klein"]
    assert (ks["sampler_name"], ks["scheduler"], ks["steps"], ks["cfg"]) == (r["sampler"], r["scheduler"], r["steps"], r["cfg"])
    l = json.load(open(os.path.join(WF, "ltx25_core_t2v_api.json"))); assert next(n for n in l.values() if n["class_type"] == "ManualSigmas")["inputs"]["sigmas"] == recipes.RECIPES["ltx25-distilled"]["sigmas"]

def test_camera_moves_and_the_one_move_rule():
    assert camera.camera_moves("slow push in on the fox") == ["push_in"] and camera.camera_moves("a still mountain lake") == []
    assert camera.camera_moves("camera pans left then tilts up while orbiting") == ["orbit", "pan", "tilt"] and "3 camera moves" in camera.one_move_problems("pan left, tilt up and orbit")[0]
    assert camera.one_move_problems("a gentle dolly in on the teapot") == []
    v = ROLES["prompt_enhancer"].verify; ok = {"prompt": "a red fox walking through snow at sunrise, slow push in, soft golden light", "negative": "blurry"}; ctx = {"must_keep": ["fox"], "min_words": 5, "video": True}
    assert v(ok, ctx) == [] and any("camera moves" in p for p in v({**ok, "prompt": ok["prompt"] + ", then orbit around it"}, ctx)) and v({**ok, "prompt": ok["prompt"] + ", then orbit around it"}, {**ctx, "video": False}) == []

def test_fallback_prompt_is_deterministic_sfw_and_well_formed():
    a = FP.build_prompt({"subject": "a red fox", "setting": "fresh snow"}, 3); assert a == FP.build_prompt({"subject": "a red fox", "setting": "fresh snow"}, 3) and a.startswith("a red fox, in fresh snow") and FP.lint(a) == []
    assert any(FP.build_prompt({"subject": "a red fox"}, s) != FP.build_prompt({"subject": "a red fox"}, 0) for s in range(1, 8))
    assert "slow push in" in FP.build_prompt({"subject": "fox", "camera": "slow push in"}, 0, video=True) and "slow push in" not in FP.build_prompt({"subject": "fox", "camera": "slow push in"}, 0, video=False)
    assert FP.fix("a  fox,   fox fox  in   snow") == "a fox, fox in snow" and len(FP.fix(" ".join(["word,"] * 300)).split()) <= 200 and any("non-SFW" in p for p in FP.lint("a nude statue is on display here today"))
    with pytest.raises(ValueError): FP.build_prompt({}, 0)

def test_enhance_or_fallback_uses_the_model_only_when_it_passes():
    good = lambda role, task, ctx=None, **k: Result(True, role, {"prompt": "a red fox in the snow at sunrise, warm light, sharp focus", "negative": "blurry"})
    bad = lambda role, task, ctx=None, **k: Result(False, role, None, problems=["the subject term 'fox' was dropped"])
    boom = lambda role, task, ctx=None, **k: (_ for _ in ()).throw(ConnectionError("server down"))
    assert FP.enhance_or_fallback("a red fox in snow", runner=good)["source"] == "model"
    r = FP.enhance_or_fallback("a red fox in snow", {"subject": "a red fox"}, seed=2, runner=bad); assert r["source"] == "fallback" and "fox" in r["prompt"] and "dropped" in r["problems"][0]
    r = FP.enhance_or_fallback("a red fox", runner=boom); assert r["source"] == "fallback" and "ConnectionError" in r["problems"][0]

def test_rotation_never_repeats_within_a_unit_and_is_stable():
    opts = list("ABCDEFG"); assert R.stride(7) in (4, 5, 6) and R.stride(8) % 2 == 1
    for u in range(5): assert len({R.rotate(opts, u, i) for i in range(7)}) == 7
    assert R.rotate(opts, 3, 2) == R.rotate(opts, 3, 2) and R.rotate(opts, 0, 0) != R.rotate(opts, 1, 0) and R.rotate(opts, 0, 0, offset=1) == opts[1]
    assert len(R.schedule(opts, 4, 3)) == 4 and len({row[0] for row in R.schedule(opts, 7, 3)}) == 7
    with pytest.raises(ValueError): R.rotate([], 0, 0)
