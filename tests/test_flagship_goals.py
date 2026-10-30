"""Flagship apps (recast, vfx_ltx, reshoot, director): the goal fields, the prompt composition and the fixed workflow templates. No GPU, no ComfyUI: the probe of the uploaded clip is stubbed."""
import json, os
import pytest
from fastapi import HTTPException
from studio import goals as Go
from studio.goals import GOALS, WF, values_for, h3_ref_frames, ltx_ref_frames, director_prompt, DIRECTOR_DEFAULTS
from studio.graph_template import fill, placeholders

CLIP_16_9 = {"width": 1216, "height": 672, "duration": 5.17}
@pytest.fixture(autouse=True)
def no_real_probe(monkeypatch): monkeypatch.setattr(Go, "probe_input", lambda name: dict(CLIP_16_9))
def filled(goal, req, image=None):
    v, o = values_for(goal, req, image); tpl = json.load(open(os.path.join(WF, GOALS[goal]["template"])))
    assert not (placeholders(tpl) - set(v)), "template wants a value the goal does not set"
    return fill(tpl, v), v, o
def by_class(g, cls): return [n for n in g.values() if n["class_type"] == cls]

def test_every_flagship_goal_declares_the_standard_and_new_fields():
    for name in Go.FLAGSHIP:
        g = GOALS[name]
        for k in ("label", "tagline", "template", "family", "kind", "license", "license_class", "gated", "needs_image", "needs_video", "needs_last_image", "prompt_optional", "fields", "options", "defaults", "negative"): assert k in g, (name, k)
        assert g["kind"] == "video" and g["license_class"] in ("community", "open") and os.path.exists(os.path.join(WF, g["template"]))
        for k, v in g["defaults"].items(): assert v in g["options"][k], (name, k, v)

def test_older_goals_keep_working_and_gain_false_flags():
    assert GOALS["h3_animate"]["needs_video"] is False and GOALS["h3_animate"]["needs_image"] is True
    v, _ = values_for("h3_video", {"prompt": "a fox", "seed": 1}); assert v["prompt"] == "a fox" and v["seconds"] == 4.0

# Copied from the live ResolutionSelector (ComfyUI 0.43 object_info), so no test talks to a running server.
RESOLUTION_SELECTOR_LABELS = ["1:1 (Square)", "2:3 (Portrait Photo)", "3:2 (Photo)", "3:4 (Portrait Standard)", "4:3 (Standard)", "9:16 (Portrait Widescreen)", "16:9 (Widescreen)", "21:9 (Ultrawide)"]
def test_every_h3_aspect_is_a_real_resolution_selector_label():
    for short, label in Go.H3_ASPECTS.items(): assert label in RESOLUTION_SELECTOR_LABELS, short

@pytest.mark.parametrize("goal,extra,image", [("h3_video", {}, None), ("h3_animate", {}, "a.png"), ("director", {}, None), ("director_keyframes", {"last_image": "b.png"}, "a.png")])
def test_portrait_h3_goals_send_the_label_the_selector_accepts(goal, extra, image):
    g, v, _ = filled(goal, {"prompt": "x", "options": {"aspect": "9:16"}, **extra}, image)
    assert by_class(g, "ResolutionSelector")[0]["inputs"]["aspect_ratio"] == "9:16 (Portrait Widescreen)"

@pytest.mark.parametrize("goal,image", [("recast", "a.png"), ("reshoot", None)])
def test_clip_goals_use_explicit_sizes_not_the_selector(goal, image):
    g, v, _ = filled(goal, {"video": "clip.mp4", "options": {"aspect": "9:16"}}, image)
    assert not by_class(g, "ResolutionSelector") and (v["width"], v["height"]) == (768, 1344)

def test_recast_is_h3_core_with_the_swap_lora_and_the_source_audio():
    g, v, o = filled("recast", {"video": "clip.mp4", "target": "the chef in white", "prompt": "she keeps smiling", "seed": 7}, "hero.png")
    assert by_class(g, "UNETLoader")[0]["inputs"]["unet_name"].endswith("minimax_h3_ref2va_pruned_int8_convrot.safetensors")
    lora = by_class(g, "LoraLoaderModelOnly")[0]["inputs"]; assert lora["lora_name"].endswith("h3_character_swap_pro4500_1000.safetensors") and lora["strength_model"] == 1.0
    assert by_class(g, "BasicScheduler")[0]["inputs"]["steps"] == 12                    # owner: never below 12
    ref = by_class(g, "MiniMaxH3ReferenceToVideo")[0]["inputs"]; assert ref["ref_images.ref_image_0"][0] == "char" and ref["ref_videos.ref_video_0"][0] == "scale"
    assert "the chef in white" in ref["prompt"] and "<Picture 1>" in ref["prompt"] and "<Video 1>" in ref["prompt"] and ref["prompt"].endswith("she keeps smiling")
    mk = by_class(g, "CreateVideo")[0]["inputs"]; assert mk["audio"] == ["comp", 1]     # original audio, not H3's
    assert (v["width"], v["height"], v["frames"]) == (1344, 768, 124) and o["seconds"] == 5

def test_draft_quality_is_a_smaller_h3_size_on_the_32_grid():
    _, v, _ = filled("recast", {"video": "clip.mp4", "options": {"quality": "draft"}}, "hero.png"); assert (v["width"], v["height"]) == (832, 480)
    for sizes in (Go.H3_VIDEO_SIZES, Go.H3_DRAFT_SIZES):
        for w, h in sizes.values(): assert w % 32 == 0 and h % 32 == 0
    _, v, _ = filled("reshoot", {"video": "clip.mp4", "options": {"quality": "draft", "aspect": "9:16"}}); assert (v["width"], v["height"]) == (480, 832)

def test_recast_refuses_without_its_inputs():
    with pytest.raises(HTTPException): values_for("recast", {"prompt": "x"}, "hero.png")
    with pytest.raises(HTTPException): values_for("recast", {"video": "clip.mp4"}, None)
    with pytest.raises(HTTPException): values_for("recast", {"video": "../../etc/passwd.mp4"}, "hero.png")
    with pytest.raises(HTTPException): values_for("recast", {"video": "notes.txt"}, "hero.png")

def test_frame_rules():
    assert h3_ref_frames(5) == 124 and h3_ref_frames(3) == 73 and h3_ref_frames(5, 3.5) == 73       # 17k+5, never past the clip
    assert ltx_ref_frames(4) == 97 and ltx_ref_frames(5, 2.1) == 49                                 # 8k+1, never past the clip

def test_recast_picks_the_clip_shape(monkeypatch):
    monkeypatch.setattr(Go, "probe_input", lambda n: {"width": 720, "height": 1280, "duration": 10.0})
    _, v, _ = filled("recast", {"video": "tall.mp4"}, "hero.png"); assert (v["width"], v["height"]) == (768, 1344)
    _, v, _ = filled("recast", {"video": "tall.mp4", "options": {"aspect": "1:1"}}, "hero.png"); assert (v["width"], v["height"]) == (1024, 1024)

def test_recast_without_a_probe_trusts_the_options(monkeypatch):
    monkeypatch.setattr(Go, "probe_input", lambda n: None)
    _, v, _ = filled("recast", {"video": "clip.mp4"}, "hero.png"); assert v["frames"] == 124

def test_vfx_ltx_is_ltx_core_with_an_ic_lora_guided_by_the_clip():
    g, v, _ = filled("vfx_ltx", {"video": "clip.mp4", "scene": "a temple in a jungle", "prompt": "a flash flood", "options": {"effect": "water"}})
    assert "ltx-2.5" in by_class(g, "UNETLoader")[0]["inputs"]["unet_name"]
    assert "water-simulation" in by_class(g, "LTXICLoRALoaderModelOnly")[0]["inputs"]["lora_name"] and by_class(g, "LTXICLoRALoaderModelOnly")[0]["inputs"]["strength_model"] == 1.45
    assert by_class(g, "LTXAddVideoICLoRAGuide")[0]["inputs"]["image"][0] == "scale"
    assert "ADD WATER a flash flood." in v["prompt"] and "a temple in a jungle" in v["prompt"] and (v["frames"] - 1) % 8 == 0
    assert by_class(g, "ComfySwitchNode")[0]["inputs"]["switch"] is True and by_class(g, "CreateVideo")[0]["inputs"]["audio"] == ["sound", 0]

def test_vfx_defaults_are_the_rendered_flood_recipe():
    d = GOALS["vfx_ltx"]["defaults"]; assert (d["effect"], d["intensity"], d["seconds"]) == ("water", "max", 5)

def test_vfx_intensity_moves_water_and_night_only():
    assert values_for("vfx_ltx", {"video": "c.mp4", "options": {"effect": "water", "intensity": "max"}})[0]["strength"] == 1.45
    assert values_for("vfx_ltx", {"video": "c.mp4", "options": {"effect": "day_to_night", "intensity": "natural"}})[0]["strength"] == 1.0
    assert values_for("vfx_ltx", {"video": "c.mp4", "options": {"effect": "clean_plate", "intensity": "max"}})[0]["strength"] == 1.0

def test_a_matte_keeps_the_source_audio_and_the_rest_steer_their_sound():
    assert values_for("vfx_ltx", {"video": "c.mp4", "options": {"effect": "matte"}})[0]["new_sound"] is False
    for effect in ("clean_plate", "water", "day_to_night"):
        v = values_for("vfx_ltx", {"video": "c.mp4", "options": {"effect": effect}})[0]; assert v["new_sound"] is True and "no music" in v["prompt"]

@pytest.mark.parametrize("effect,needle", [("clean_plate", "clean-plate"), ("day_to_night", "day-to-night"), ("matte", "alpha-gen")])
def test_vfx_effects_choose_their_lora(effect, needle):
    g, v, _ = filled("vfx_ltx", {"video": "clip.mp4", "options": {"effect": effect}}); assert needle in v["lora"] and v["prompt"]      # the server refuses an empty prompt, even a prompt-free LoRA sends a blank

def test_reshoot_is_a_new_take_from_the_first_frame_with_the_move_in_the_prompt():
    g, v, _ = filled("reshoot", {"video": "clip.mp4", "options": {"camera": "crane_up"}, "prompt": "the flames rise"})
    i2v = by_class(g, "MiniMaxH3ImageToVideo")[0]["inputs"]; assert i2v["first_frame"] == ["scale", 0] and "last_frame" not in i2v and i2v["length"] == 124
    assert by_class(g, "ImageFromBatch")[0]["inputs"]["length"] == 1 and not by_class(g, "MiniMaxH3ReferenceToVideo")      # Ref2VA with the clip as <Video 1> copies its camera: rendered and rejected
    assert v["prompt"].startswith("the flames rise. ") and "cranes up" in v["prompt"] and v["prompt"].endswith("no cuts.")
    assert values_for("reshoot", {"video": "clip.mp4"})[0]["prompt"].startswith(Go.RESHOOT_DEFAULT)
    assert "new take" in GOALS["reshoot"]["tagline"] and "new take" in GOALS["reshoot_wan"]["tagline"]

def test_reshoot_wan_drives_the_real_camera_node_from_the_first_frame():
    g, v, _ = filled("reshoot_wan", {"video": "clip.mp4", "options": {"camera": "pan_left", "seconds": 3}})
    assert by_class(g, "WanCameraEmbedding")[0]["inputs"]["camera_pose"] == "Pan Left" and by_class(g, "WanCameraEmbedding")[0]["inputs"]["length"] == 49
    assert (v["width"], v["height"]) == (832, 480) and v["prompt"] and GOALS["reshoot_wan"]["license_class"] == "open" and by_class(g, "ImageFromBatch")[0]["inputs"]["length"] == 1

def test_orbit360_freezes_the_chosen_moment_and_follows_the_lora_card():
    g, v, _ = filled("orbit360", {"video": "clip.mp4", "options": {"moment": "middle"}})
    assert v["frame_index"] == int(5.17 * 24) // 2 and by_class(g, "ImageFromBatch")[0]["inputs"]["batch_index"] == v["frame_index"]
    i2v = by_class(g, "MiniMaxH3ImageToVideo")[0]["inputs"]; assert i2v["first_frame"] == i2v["last_frame"] and (i2v["width"], i2v["height"], i2v["length"]) == (768, 768, 73)
    assert i2v["prompt"].startswith("One frozen instant. Only the camera moves.") and by_class(g, "BasicScheduler")[0]["inputs"]["steps"] == 28
    assert "audio" not in by_class(g, "CreateVideo")[0]["inputs"] and by_class(g, "LoraLoaderBypassModelOnly")[0]["inputs"]["lora_name"].endswith("minimax_h3_flf2v_lora_v1.safetensors")

def test_director_composes_structured_controls():
    _, v, o = filled("director", {"prompt": "A fox runs through snow.", "options": {"camera": "orbit_left", "lens": "portrait_85mm", "lighting": "noir", "mood": "tense", "shot": "close_up"}})
    p = v["prompt"]; assert p.startswith("A fox runs through snow. Close-up. The camera orbits") and "85mm" in p and "noir" in p and "tense" in p and p.endswith("no cuts.") and ".." not in p
    assert director_prompt("x", {**DIRECTOR_DEFAULTS, "camera": "locked"}) == "x. The camera stays locked off on one framing for the whole shot. One continuous shot, no cuts."

def test_unknown_option_falls_back_to_the_default():
    _, _, o = filled("director", {"prompt": "x", "options": {"camera": "barrel_roll"}}); assert o["camera"] == "dolly_in"

def test_director_keyframes_needs_two_frames_and_wires_the_last_one():
    with pytest.raises(HTTPException): values_for("director_keyframes", {"prompt": "x"}, "a.png")
    g, v, _ = filled("director_keyframes", {"prompt": "the door opens", "last_image": "b.png"}, "a.png")
    i2v = by_class(g, "MiniMaxH3ImageToVideo")[0]["inputs"]; assert i2v["first_frame"] and i2v["last_frame"]
    assert sorted(n["inputs"]["image"] for n in by_class(g, "LoadImage")) == ["a.png", "b.png"]
