"""Goal presets: what the user wants to MAKE, mapped to a verified workflow template. Everything a preset sets is a ${placeholder} value; nothing else in the graph changes.
Each goal states the licence of the model behind it. License class 'open' = OSI-style permissive (Apache-2.0); 'community' = open weights under the model author's own terms (non-commercial, gated, or revenue-capped):
those tiles say so, and the installer only fetches them when asked."""
import json, math, os, random, re, subprocess
from fastapi import HTTPException
from psn import paths
from studio.anime import STYLES, strict_prompt
WF = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "workflows")
NEG_VIDEO = "worst quality, inconsistent motion, blurry, jittery, distorted, watermark, text"
WAN_NEG = "色调艳丽，过曝，静态，细节模糊不清，字幕，风格，作品，画作，画面，静止，整体发灰，最差质量，低质量，JPEG压缩残留，丑陋的，残缺的，多余的手指，画得不好的手部，画得不好的脸部，畸形的，毁容的，形态畸形的肢体，手指融合，静止不动的画面，杂乱的背景，三条腿，背景人很多，倒着走"
IMG_SIZES = {"1:1": (1024, 1024), "3:2": (1216, 832), "2:3": (832, 1216), "16:9": (1344, 768), "9:16": (768, 1344)}
LTX_SIZES = {"16:9": (960, 544), "9:16": (544, 960), "1:1": (704, 704)}
WAN_SIZES = {"480p": {"16:9": (832, 480), "9:16": (480, 832), "1:1": (640, 640)}, "720p": {"16:9": (1280, 704), "9:16": (704, 1280), "1:1": (704, 704)}}
def frames_ltx(seconds, fps=24): return 8 * max(1, round(seconds * fps / 8)) + 1      # LTX wants 8k+1 frames
def frames_wan(seconds, fps=24): return 4 * max(1, round(seconds * fps / 4)) + 1      # Wan 2.2 5B: 4k+1 frames
KLEIN_MODES = {"fast": {"unet": "flux-2-klein-4b.safetensors", "steps": 4, "cfg": 1.0}, "quality": {"unet": "flux-2-klein-base-4b.safetensors", "steps": 20, "cfg": 5.0}}   # distilled vs base, per the model card and ComfyUI's template
ANIME_MODES = {"quality": {"unet": "anima/anima-aesthetic-v1.1.safetensors", "steps": 30, "cfg": 3.0, "negative": "worst quality, low quality, blurry, jpeg artifacts, artist name, chromatic aberration"},
               "fast": {"unet": "anima/anima-turbo-v1.1.safetensors", "steps": 10, "cfg": 1.0, "negative": ""}}   # settings from the box's own successful Anima runs (model library notes)
ANIME_PREFIX = "masterpiece, best quality, safe, "
SECONDS = [2, 3, 4, 5]
H3_ASPECTS = {"16:9": "16:9 (Widescreen)", "1:1": "1:1 (Square)", "9:16": "9:16 (Portrait Widescreen)"}   # ResolutionSelector's exact labels on ComfyUI 0.43 (object_info); a wrong label is a 400 "Value not in list" on node 115
H3_QUALITY = {"standard": 0.4, "high": 0.8}   # megapixels
MUSIC_SECONDS = [30, 60, 90, 120]
def G(label, tagline, template, family, kind, lic, lic_class, options, defaults, needs_image=False, negative="", gated=False, needs_video=False, needs_last_image=False, prompt_optional=False, fields=None, image_label="", video_label=""):
    return {"label": label, "tagline": tagline, "template": template, "family": family, "kind": kind, "license": lic, "license_class": lic_class, "gated": gated, "needs_image": needs_image, "options": options, "defaults": defaults, "negative": negative,
            "needs_video": needs_video, "needs_last_image": needs_last_image, "prompt_optional": prompt_optional, "fields": fields or {}, "image_label": image_label, "video_label": video_label}
# ---------- flagship apps: recast, vfx_ltx, reshoot, director. Video inputs are uploaded with /api/upload and sent as {"video": name}; a second still as {"last_image": name}.
H3_LICENCE = "MiniMax H3 community licence"; LTX_LICENCE = "LTX-2.x community licence (gated download)"
# Owner's prompting rules for H3: camera = action + amplitude + speed + start/end framing; one main action; one continuous shot, no cuts.
CAMERA_MOVES = {
 "locked": "The camera stays locked off on one framing for the whole shot.",
 "dolly_in": "The camera dollies in slowly and smoothly, from a wide framing to a close framing of the subject.",
 "dolly_out": "The camera dollies back slowly and smoothly, from a close framing to a wide framing that reveals the surroundings.",
 "orbit_left": "The camera orbits the subject to the left in a smooth quarter circle at a steady pace, keeping the subject centred, and ends on a side view of the subject in profile.",
 "orbit_right": "The camera orbits the subject to the right in a smooth quarter circle at a steady pace, keeping the subject centred, and ends on a side view of the subject in profile.",
 "crane_up": "The camera cranes up smoothly from low to high, ending in a high angle looking down on the subject.",
 "crane_down": "The camera cranes down smoothly from high to low, ending in a low angle looking up at the subject.",
 "pan_left": "The camera pans slowly to the left at a steady speed from a fixed position.",
 "pan_right": "The camera pans slowly to the right at a steady speed from a fixed position.",
 "tilt_up": "The camera tilts up slowly from the ground to the top of the frame.",
 "tracking": "The camera tracks sideways alongside the subject at walking speed, keeping the same framing.",
 "handheld": "Handheld camera with a light natural sway that follows the subject.",
 "dolly_zoom": "A slow dolly zoom: the subject stays the same size while the background stretches away behind it.",
}
LENSES = {"auto": "", "wide_24mm": "Shot on a 24mm wide lens with deep perspective.", "standard_35mm": "Shot on a 35mm lens with natural perspective.", "normal_50mm": "Shot on a 50mm lens.", "portrait_85mm": "Shot on an 85mm lens with shallow depth of field and soft background.", "telephoto_135mm": "Shot on a 135mm telephoto lens with compressed perspective.", "macro": "Shot on a macro lens in extreme close detail.", "anamorphic": "Shot on an anamorphic lens with oval bokeh and horizontal flares."}
SHOTS = {"auto": "", "extreme_wide": "Extreme wide shot.", "wide": "Wide shot.", "medium": "Medium shot.", "close_up": "Close-up.", "extreme_close_up": "Extreme close-up."}
LIGHTING = {"auto": "", "golden_hour": "Warm low golden hour sun with long soft shadows.", "blue_hour": "Cool blue hour dusk light.", "overcast": "Soft even overcast daylight.", "noir": "High contrast low-key noir light with hard shadows.", "neon": "Saturated neon light with coloured reflections.", "candlelight": "Warm flickering candlelight in a dark room.", "volumetric": "Hazy air with volumetric shafts of light.", "studio_rim": "Dark background with a clean studio rim light."}
MOODS = {"auto": "", "epic": "The mood is epic and grand.", "tense": "The mood is tense and uneasy.", "serene": "The mood is calm and serene.", "romantic": "The mood is warm and tender.", "melancholy": "The mood is quiet and melancholy.", "playful": "The mood is light and playful.", "dreamlike": "The mood is soft and dreamlike."}
CONTINUOUS = "One continuous shot, no cuts."
def director_prompt(idea, o):
    parts = [str(idea or "").strip().rstrip(".") + ".", SHOTS[o["shot"]], CAMERA_MOVES[o["camera"]], LENSES[o["lens"]], LIGHTING[o["lighting"]], MOODS[o["mood"]], CONTINUOUS]
    return " ".join(p for p in parts if p)
DIRECTOR_OPTIONS = {"camera": list(CAMERA_MOVES), "shot": list(SHOTS), "lens": list(LENSES), "lighting": list(LIGHTING), "mood": list(MOODS)}
DIRECTOR_DEFAULTS = {"camera": "dolly_in", "shot": "auto", "lens": "auto", "lighting": "auto", "mood": "auto"}
# The swap prompt is the akatz-ai card's example with the blanks filled; the owner's rule: prompt = the TARGET, not a scene.
SWAP_PROMPT = "Replace only {target} in <Video 1> with the character in <Picture 1>. Keep the replacement character's identity, outfit, and art style from <Picture 1>. Preserve the source video's camera, background, lighting, objects, and all other people. Match the target person's position, scale, pose, and movement. Do not show the reference sheet or its background."
RESHOOT_DEFAULT = "The scene continues naturally, with the same subject, the same place and the same light."
RESHOOT_CAMERA = {k: v for k, v in CAMERA_MOVES.items() if k not in ("locked", "dolly_zoom")}
WAN_CAMERA_POSES = {"zoom_in": "Zoom In", "zoom_out": "Zoom Out", "pan_left": "Pan Left", "pan_right": "Pan Right", "pan_up": "Pan Up", "pan_down": "Pan Down", "roll_left": "Anti Clockwise (ACW)", "roll_right": "ClockWise (CW)"}   # WanCameraEmbedding's own presets
H3_VIDEO_SIZES = {"16:9": (1344, 768), "9:16": (768, 1344), "1:1": (1024, 1024)}          # recipes: proven at 1344x768 x 124; the others are the same pixel budget
H3_DRAFT_SIZES = {"16:9": (832, 480), "9:16": (480, 832), "1:1": (640, 640)}              # H3 takes multiples of 32; a reference clip costs about 40 s a step at the full size, so this is the quick look
VFX_EFFECTS = {  # lora file, strength, prompt, negative, new sound? Prompts: each IC-LoRA card's dual-panel convention, as in the owner's l2_iclora batch, with the sound steered so the AV track is not left to chance.
 "clean_plate": ("ltx/_ic_Clean-Plate/ltx-2.5-22b-ic-lora-clean-plate-1.0.safetensors", 1.0, "An empty clean plate of the exact same location: {scene}, identical background, environment, structures and lighting as the source video, with no people, no humans, no figures, and no body parts such as arms, hands or legs anywhere in the frame. Static photorealistic footage, natural light, high detail. Quiet natural ambient sound of the empty place, no music, no speech.", "people, person, man, woman, human, figure, body parts, arms, hands, legs, crowd", True),
 "water": ("ltx/_ic_Water-Simulation/ltx-2.5-22b-ic-lora-water-simulation-0.9.safetensors", 1.3, "Reference shows {scene}. Edited shows the same scene with water added. ADD WATER {effect} Sound of rushing, splashing water, no music, no speech.", NEG_VIDEO, True),
 "day_to_night": ("ltx/_ic_Day-To-Night/ltx-2.5-22b-ic-lora-day-to-night-0.9.safetensors", 1.2, "A realistic nighttime scene of {scene}. Photorealistic moonlight, deep natural shadows, the sky is dark, practical lamps glow. Only the lighting changes from day to night; identical composition, framing, camera movement and motion. Quiet night ambience, no music, no speech.", "daytime, bright sunlight, blue sky, overexposed, worst quality, inconsistent motion", True),
 "matte": ("ltx/_ic_Alpha-Gen/ltx-2.5-22b-ic-lora-alpha-gen-0.9.safetensors", 1.0, "", "", False),     # a matte is a pass for compositing: it keeps the source audio, if any
}
VFX_INTENSITY = {"natural": 1.0, "strong": 1.3, "max": 1.45}   # Water-Simulation card: 1.0-1.05 natural, 1.25-1.45 max drama, 1.5 and over warps faces. Night takes the same scale; clean plate and matte stay at their proven strength.
VFX_DEFAULT_SCENE = "the scene"; VFX_DEFAULT_WATER = "a rising flood of clear water that surges across the ground and splashes around everything it touches."
def h3_ref_frames(want_seconds, have_seconds=None):
    """H3 lengths are 17k+5 at 24 fps, snapped up (5 s -> 124, the proven length), then down to what the clip really has."""
    k = math.ceil((round(want_seconds * 24) - 5) / 17)
    if have_seconds is not None: k = min(k, math.floor((math.floor(have_seconds * 24) - 5) / 17))
    return 17 * max(k, 1) + 5
def ltx_ref_frames(want_seconds, have_seconds=None):
    """LTX lengths are 8k+1 at 24 fps; never more than the clip has."""
    k = max(1, round(want_seconds * 24 / 8))
    if have_seconds is not None: k = min(k, math.floor((math.floor(have_seconds * 24) - 1) / 8))
    return 8 * max(k, 1) + 1
def probe_input(name):
    """Facts about an uploaded clip, or None when it cannot be read here (ComfyUI on another machine): the graph then trusts the options."""
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:format=duration", "-of", "json", os.path.join(paths.comfy_input(True), os.path.basename(name))], capture_output=True, text=True, timeout=20)
        d = json.loads(r.stdout); s = d["streams"][0]; return {"width": int(s["width"]), "height": int(s["height"]), "duration": float(d["format"]["duration"])}
    except Exception: return None
def clip_shape(req, sizes):
    """-> (video name, probe, aspect picked for the clip). The 400 comes from here, before the server's generic image message."""
    name = str(req.get("video") or "").strip()
    if not name: raise HTTPException(400, "add a source video first")
    if os.path.basename(name) != name or not re.search(r"\.(mp4|webm|mov|mkv)$", name, re.I): raise HTTPException(400, "the source must be an uploaded mp4, webm, mov or mkv")
    info = probe_input(name); aspect = "16:9"
    if info:
        r = info["width"] / max(1, info["height"]); aspect = min(sizes, key=lambda a: abs(math.log(r / (sizes[a][0] / sizes[a][1]))))
    return name, info, aspect
ASPECTS_AUTO = ["auto", "16:9", "9:16", "1:1"]
def g_negative(goal, req): return req.get("negative") if req.get("negative") is not None else GOALS[goal]["negative"]
def flagship_values(goal, req, image_name, o, seed):
    """Prompt composition and clip handling of the flagship goals. The graph is one fixed template per goal; only ${placeholders} change."""
    text = str(req.get("prompt", "")).strip()
    if goal in ("director", "director_keyframes"):
        if not text: raise HTTPException(400, "describe the shot first")
        v = {"prompt": director_prompt(text, o), "seed": seed, "aspect": H3_ASPECTS[o["aspect"]], "megapixels": H3_QUALITY[o["quality"]], "seconds": float(o["seconds"]), "turbo": o["speed"] == "fast"}
        if goal == "director_keyframes":
            last = str(req.get("last_image") or "").strip()
            if not image_name or not last: raise HTTPException(400, "add a first frame and a last frame")
            v.update(image=image_name, last_image=last)
        return v
    if goal == "orbit360":      # one frozen frame of the clip; the size, length and prompt are fixed by the LoRA's recipe, in the template
        video, info, _ = clip_shape(req, H3_VIDEO_SIZES); total = int((info["duration"] if info else 2.0) * 24)
        return {"video": video, "frame_index": {"start": 0, "middle": total // 2, "end": max(0, total - 2)}[o["moment"]], "seed": seed, "prompt": "Frozen-time 360 orbit"}
    sizes = LTX_SIZES if goal == "vfx_ltx" else WAN_SIZES["480p"] if goal == "reshoot_wan" else H3_VIDEO_SIZES
    video, info, aspect = clip_shape(req, sizes); have = info["duration"] if info else None
    if have is not None and have < (0.5 if goal == "vfx_ltx" else 22 / 24): raise HTTPException(400, "the source clip is too short")
    if goal in ("recast", "reshoot") and o["quality"] == "draft": sizes = H3_DRAFT_SIZES
    w, h = sizes[aspect if o["aspect"] == "auto" else o["aspect"]]
    if goal == "reshoot_wan":      # 16 fps, 4k+1 frames; only the first frame of the clip conditions the render, so the clip may be shorter than the shot
        frames = 4 * round(o["seconds"] * 16 / 4) + 1
        return {"video": video, "width": w, "height": h, "frames": frames, "slice_seconds": round(frames / 16 + 0.1, 3), "seed": seed, "pose": WAN_CAMERA_POSES[o["camera"]], "prompt": text or "The scene continues naturally, the same subject and the same place.", "negative": g_negative(goal, req)}
    if goal == "vfx_ltx": frames = ltx_ref_frames(o["seconds"], have)
    else: frames = h3_ref_frames(o["seconds"], have)
    v = {"video": video, "width": w, "height": h, "frames": frames, "slice_seconds": round(frames / 24 + 0.1, 3), "seed": seed}
    if goal == "recast":
        if not image_name: raise HTTPException(400, "add the character picture")
        target = str(req.get("target") or "").strip() or "the main person"
        v.update(image=image_name, prompt=SWAP_PROMPT.format(target=target) + (" " + text if text else ""))
    elif goal == "reshoot":
        del v["slice_seconds"]; v.update(turbo=True, prompt=" ".join([text.rstrip(".") + "." if text else RESHOOT_DEFAULT, RESHOOT_CAMERA[o["camera"]], CONTINUOUS]))
    else:
        lora, strength, tpl, neg, new_sound = VFX_EFFECTS[o["effect"]]; scene = str(req.get("scene") or "").strip() or VFX_DEFAULT_SCENE
        if o["effect"] == "matte": prompt = " "      # Alpha-Gen is prompt-free (owner's 4e arm); a blank keeps the server's check happy
        elif o["effect"] == "water": prompt = tpl.format(scene=scene, effect=(text.rstrip(".") + "." if text else VFX_DEFAULT_WATER))
        else: prompt = tpl.format(scene=scene) + (" " + text if text else "")
        if o["effect"] in ("water", "day_to_night"): strength = VFX_INTENSITY[o["intensity"]]
        v.update(lora=lora, strength=strength, prompt=prompt, negative=neg, new_sound=new_sound)
    return v
PRODUCT_SET = {"black glass": "on a black glass surface with soft reflections", "wet obsidian": "above wet obsidian with frozen water splashes", "white sweep": "on a seamless white studio sweep", "gold silk": "on folds of gold silk", "emerald moss": "on a bed of emerald moss in morning mist"}
PRODUCT_LIGHT = {"rim light": "dramatic rim light against a dark background", "soft box": "large soft box lighting", "golden hour": "warm golden hour sunlight", "neon": "emerald and gold neon accents"}
def product_prompt(text, o): return f"High end product advertising photograph of {str(text).strip()}, {PRODUCT_SET[o['setting']]}, {PRODUCT_LIGHT[o['light']]}, tack sharp, clean composition, no text, no logos" if str(text).strip() else ""
GOALS = {
 "image": G("Image", "Text to image with FLUX.2 Klein 4B", "flux2_klein4b_t2i_api.json", "FLUX.2 Klein 4B", "image", "Apache-2.0", "open", {"aspect": list(IMG_SIZES), "mode": list(KLEIN_MODES)}, {"aspect": "1:1", "mode": "fast"}),
 "video": G("Video", "Text to video with Wan 2.2 (5B)", "wan22_5b_t2v_api.json", "Wan 2.2 TI2V-5B", "video", "Apache-2.0", "open", {"aspect": list(WAN_SIZES["480p"]), "quality": list(WAN_SIZES), "seconds": SECONDS}, {"aspect": "16:9", "quality": "480p", "seconds": 5}, negative=WAN_NEG),
 "animate": G("Animate", "Bring an image to life with Wan 2.2 (5B)", "wan22_5b_i2v_api.json", "Wan 2.2 TI2V-5B", "video", "Apache-2.0", "open", {"aspect": list(WAN_SIZES["480p"]), "quality": list(WAN_SIZES), "seconds": SECONDS}, {"aspect": "16:9", "quality": "480p", "seconds": 5}, needs_image=True, negative=WAN_NEG),
 "anime": G("Anime", "Anime and illustration with Anima", "anima_core_t2i_api.json", "Anima", "image", "Non-commercial (circlestone-labs licence)", "community", {"aspect": list(IMG_SIZES), "style": list(STYLES), "mode": list(ANIME_MODES)}, {"aspect": "1:1", "style": "tv", "mode": "quality"}),
 "product": G("Product Studio", "FLUX 3: your product, shot like an ad. Pick the set and the light", "flux3_klein_core_t2i_api.json", "FLUX.3 Klein", "image", "FLUX Kommunity licence (gated download)", "community", {"setting": list(PRODUCT_SET), "light": list(PRODUCT_LIGHT), "aspect": list(IMG_SIZES)}, {"setting": "black glass", "light": "rim light", "aspect": "1:1"}, gated=True),
 "flux3": G("Image HQ", "FLUX.3 Klein, highest quality", "flux3_klein_core_t2i_api.json", "FLUX.3 Klein", "image", "FLUX Kommunity licence (gated download)", "community", {"aspect": list(IMG_SIZES)}, {"aspect": "1:1"}, gated=True),
 "video_ltx": G("Video + sound", "Text to video with sound, LTX-2.5", "ltx25_core_t2v_api.json", "LTX-2.5", "video", "LTX-2.x community licence (gated download)", "community", {"aspect": list(LTX_SIZES), "seconds": [2, 3, 4, 5, 6]}, {"aspect": "16:9", "seconds": 5}, negative=NEG_VIDEO, gated=True),
 "animate_ltx": G("Animate + sound", "Image to video with sound, LTX-2.5", "ltx25_core_i2v_api.json", "LTX-2.5", "video", "LTX-2.x community licence (gated download)", "community", {"aspect": list(LTX_SIZES), "seconds": [2, 3, 4, 5, 6]}, {"aspect": "16:9", "seconds": 5}, needs_image=True, negative=NEG_VIDEO, gated=True),
 "h3_video": G("Video H3", "MiniMax H3: text to video with sound", "h3_t2v_api.json", "MiniMax H3", "video", "MiniMax H3 community licence", "community", {"aspect": list(H3_ASPECTS), "quality": list(H3_QUALITY), "seconds": [2, 3, 4, 5, 6, 8], "speed": ["quality", "fast"]}, {"aspect": "16:9", "quality": "standard", "seconds": 4, "speed": "fast"}),
 "h3_animate": G("Animate H3", "MiniMax H3: image to video with sound", "h3_i2v_api.json", "MiniMax H3", "video", "MiniMax H3 community licence", "community", {"aspect": list(H3_ASPECTS), "quality": list(H3_QUALITY), "seconds": [2, 3, 4, 5, 6, 8], "speed": ["quality", "fast"]}, {"aspect": "16:9", "quality": "standard", "seconds": 4, "speed": "fast"}, needs_image=True),
 "music": G("Music", "MiniMax Music 3: full songs with vocals", "music3_api.json", "MiniMax Music 3", "audio", "MiniMax-Music3 community licence", "community", {"seconds": MUSIC_SECONDS}, {"seconds": 60}),
 "recast": G("Recast", "Swap the character in any video: MiniMax H3 keeps the performance, you pick who plays it", "h3_recast_api.json", "MiniMax H3", "video", H3_LICENCE, "community", {"aspect": ASPECTS_AUTO, "quality": ["draft", "high"], "seconds": [3, 4, 5]}, {"aspect": "auto", "quality": "high", "seconds": 5}, needs_image=True, needs_video=True, prompt_optional=True, fields={"target": "Who to replace, by look and position (default: the main person)"}, image_label="Character", video_label="Source video"),
 "vfx_ltx": G("VFX", "LTX-2.5 VFX on a clip: paint people out, flood the scene, turn day to night, pull a matte", "ltx25_vfx_api.json", "LTX-2.5", "video", LTX_LICENCE, "community", {"effect": list(VFX_EFFECTS), "intensity": list(VFX_INTENSITY), "aspect": ASPECTS_AUTO, "seconds": [2, 3, 4, 5]}, {"effect": "water", "intensity": "max", "aspect": "auto", "seconds": 5}, needs_video=True, prompt_optional=True, gated=True, fields={"scene": "What the clip shows, in plain words (the place, for a clean plate)"}, video_label="Source video"),
 "reshoot": G("Reshoot", "A new take of your clip with a new camera move: MiniMax H3 starts from its first frame and regenerates the action", "h3_reshoot_api.json", "MiniMax H3", "video", H3_LICENCE, "community", {"camera": list(RESHOOT_CAMERA), "aspect": ASPECTS_AUTO, "quality": ["draft", "high"], "seconds": [3, 4, 5]}, {"camera": "orbit_right", "aspect": "auto", "quality": "high", "seconds": 5}, needs_video=True, prompt_optional=True, video_label="Source video"),
 "orbit360": G("Frozen orbit", "Freeze one moment of a clip and orbit the camera 360 degrees around it (MiniMax H3)", "h3_orbit360_api.json", "MiniMax H3", "video", H3_LICENCE, "community", {"moment": ["start", "middle", "end"]}, {"moment": "middle"}, needs_video=True, prompt_optional=True, video_label="Source video"),
 "reshoot_wan": G("Reshoot (Wan camera)", "A new take with a real camera path from a clip's first frame, Wan 2.2 Fun Camera; the action is regenerated", "wan_camera_api.json", "Wan 2.2 Fun Camera 14B", "video", "Apache-2.0", "open", {"camera": list(WAN_CAMERA_POSES), "aspect": ASPECTS_AUTO, "seconds": [3, 5]}, {"camera": "zoom_in", "aspect": "auto", "seconds": 5}, needs_video=True, prompt_optional=True, negative=WAN_NEG, video_label="Source video"),
 "director": G("Director", "Direct your shot: camera move, lens, lighting and mood on MiniMax H3", "h3_t2v_api.json", "MiniMax H3", "video", H3_LICENCE, "community", {**DIRECTOR_OPTIONS, "aspect": list(H3_ASPECTS), "quality": list(H3_QUALITY), "seconds": [2, 3, 4, 5, 6, 8], "speed": ["quality", "fast"]}, {**DIRECTOR_DEFAULTS, "aspect": "16:9", "quality": "high", "seconds": 5, "speed": "fast"}),
 "director_keyframes": G("Director: first + last frame", "Direct a shot between two frames you choose on MiniMax H3", "h3_fl2v_api.json", "MiniMax H3", "video", H3_LICENCE, "community", {**DIRECTOR_OPTIONS, "aspect": list(H3_ASPECTS), "quality": list(H3_QUALITY), "seconds": [2, 3, 4, 5, 6, 8], "speed": ["quality", "fast"]}, {**DIRECTOR_DEFAULTS, "camera": "locked", "aspect": "16:9", "quality": "high", "seconds": 5, "speed": "fast"}, needs_image=True, needs_last_image=True, image_label="First frame"),
}
FLAGSHIP = ("recast", "vfx_ltx", "reshoot", "orbit360", "reshoot_wan", "director", "director_keyframes")
def values_for(goal, req, image_name=None):
    g = GOALS[goal]; o = {**g["defaults"], **{k: v for k, v in (req.get("options") or {}).items() if k in g["options"] and v in g["options"][k]}}
    seed = req.get("seed"); seed = random.randint(0, 2**31 - 1) if seed in (None, "") else int(seed)
    fam = g["family"]
    if goal == "product": req = {**req, "prompt": product_prompt(req.get("prompt", ""), o)}
    if goal in FLAGSHIP: return flagship_values(goal, req, image_name, o, seed), o
    if goal == "music":
        v = {"caption": str(req.get("prompt", "")).strip(), "lyrics": str(req.get("lyrics", "") or "").strip(), "duration": int(o["seconds"]), "seed": seed}
        v["prompt"] = v["caption"]; return v, o
    if goal in ("h3_video", "h3_animate"):
        v = {"prompt": str(req.get("prompt", "")).strip(), "seed": seed, "aspect": H3_ASPECTS[o["aspect"]], "megapixels": H3_QUALITY[o["quality"]], "seconds": float(o["seconds"]), "turbo": o["speed"] == "fast"}
        if g["needs_image"]: v["image"] = image_name
        return v, o
    if goal in ("image", "anime", "flux3", "product"): w, h = IMG_SIZES[o["aspect"]]; v = {"width": w, "height": h}
    elif goal in ("video", "animate"): w, h = WAN_SIZES[o["quality"]][o["aspect"]]; v = {"width": w, "height": h, "frames": frames_wan(o["seconds"]), "fps": 24}
    else: w, h = LTX_SIZES[o["aspect"]]; v = {"width": w, "height": h, "frames": frames_ltx(o["seconds"]), "fps": 24.0}
    v.update(prompt=str(req.get("prompt", "")).strip(), negative=req.get("negative") if req.get("negative") is not None else g["negative"], seed=seed)
    if goal == "image": m = KLEIN_MODES[o["mode"]]; v.update(unet=m["unet"], steps=m["steps"], cfg=m["cfg"])
    if goal == "anime":
        m = ANIME_MODES[o["mode"]]; v.update(unet=m["unet"], steps=m["steps"], cfg=m["cfg"])
        if not req.get("negative"): v["negative"] = m["negative"]
        if v["prompt"]: v["prompt"] = ANIME_PREFIX + strict_prompt(v["prompt"], o["style"])[0]
    if g["needs_image"]: v["image"] = image_name
    return v, o
