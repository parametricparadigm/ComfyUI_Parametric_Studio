# Timelapse

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Untested.


## What it does
A 5-30 s video (9:16 by default, 16:9 and 1:1 too) of something changing over time, made from the studio's own engines. Every picture and clip is an **ordinary studio job** through
as for a composer request. The CPU work is published as a `videofinish` job so the output guard sees it too. One model loads at a time (edit model, then video engine, then RIFE); the 4 GiB floor is the jobs' own.

| Mode | Presets | How it is made |
|---|---|---|
| **Scene change** | 13 (day to night, golden to blue hour, sunrise room, storm, snow arrives, four seasons (4 keyframes), flower bloom, seed to sapling, ice melting, a house goes up, traffic trails, tide, starry night) | the START picture (yours, a finished studio picture, or made from words on a text-to-image model) is changed by an edit model into 2-4 keyframes ("Change the scene to dusk ...", each an edit of the START picture); the video engine fills each gap: **H3 first + last frame** (both ends pinned, 8 s per clip), **Wan 2.2 first + last frame** (`wan:flf`, both ends pinned, 5 s per clip; author 2026-10-17) or, as the fallback, **Wan 2.2 image-to-video** (`wan:i2v`: start pinned; the first 3.6 s of each clip kept, 0.5 s crossfades) |
| **Build-up** ("watch it get made") | 13 (painting, sketch to colour, makeup, hair, nails, tattoo, cosplay, outfit, room makeover, cooking, cake, garden bed, **get ready with me** (a character)) | the FINAL picture is the source; an edit model makes 4-11 earlier stages from it ("Remove the painting completely", "Show only the pencil lines"), each an edit of the FINAL; the stages **dissolve on the CPU** (default, no video model) or **morph** pair by pair with H3 first + last frame |
| **Photo effect** | 8 (day to night, golden hour, blue hour, sunrise glow, lights on, hyperlapse push-in: CPU; clouds drift, fog rolls in: Wan 2.2) | one picture: a smoothstep push-in with a graded copy of the picture blended in (ffmpeg), or a Wan 2.2 clip with the grade over it. A grade darkens and tints what is there; it makes no new lights or sky (the plan says so) |

Finishing (all optional except the ramp): **RIFE x2 before the speed ramp** (default on for video-engine routes), **speed ramp + hold** (`ease` none / gentle / strong, the last frame frozen 0-5 s, default 1.5 s),
**upscale to 4K** and **Realism grain** (opt-in, the shared `video_finish.py`, a second pass after the ramp), **music** from the song library (trending sounds are library songs; `post:export` with a `song`: mux
only, no lip-sync) and **captions** (`post:captions`).

## Step by step
1. Pick a mode, then a preset. 2. Say where the picture comes from: words (optionally a saved character, a model, and design picks that join the prompt), a finished picture from the feed, an upload, or (build-ups with a
design kind) a saved hair / nails / cosplay / tattoo design on a character (its Apply picture is the final). 3. Read the plan (it is redrawn as you change things): the models, the clips, the speed, the estimate by
phase, every refusal. Open "The keyframe states / stage instructions" to edit the texts that go to the picture model. 4. **Make the timelapse.** 5. Watch the sheet: each made picture has check chips and reasons;
**Re-render** one (its clips and the video are made again) or **Keep** a flagged one. 6. The final video has Download clean, Send and Wipe; the cut before music / captions / polish stays listed.

## Settings and why
| Setting | Value | Why |
|---|---|---|
| Edit model | Qwen-Image 2.1 edit (auto), Klein 9B edit (fallback), Klein + consistency LoRA, Boogu (draft) | the pose set's table: the only measured identity across edits (sheet 0.751) |
| Star, not chain | every keyframe from the START, every stage from the FINAL, one seed family | one edit of drift instead of n (inferred; the sheet's shape) |
| Edit instructions | raw (`enhance: false`), "instruction. Keep ... unchanged." | the `imgedit` rule; Boogu/Klein/Qwen all take it |
| H3 clip | `h3:fl`, 8 s (5 / 8 / 10), turbo v4 default, 9:16 | 60 s for 192 frames is the KB's measured length |
| H3 prompt | `write: "writer"` (default): the studio's long-prompt enhancer from an `h3_brief`; `"template"`: the short official FL2VA form, linted | author rule 2026-10-16 (H3 prompts ~2000 tokens); the template needs no writer model |
| Wan clip | `wan:i2v`, 5 s, decode final (standard) or draft (fast), Wan formula (motion + one camera move + "Time-lapse feel") | `wan22-deliverables.md` |
| Wan first + last frame | `wan:flf`: the I2V stack (A14B fp8 KJ pair, lightx2v 4 steps 2+2, CFG 1, shift 5, 480x832 x81 @16 fps) with the core `WanFirstLastFrameToVideo` node; both pictures by job reference; no LoRA, creative take or preview; the clips share their boundary keyframe, so they are joined without the doubled frame and at their own 16 fps (RIFE then doubles real frames) | the official template `video_wan2_2_14B_flf2v` and the user workflow use the same node; graph validated offline (below) |
| Character on a clip | **never on a first + last frame clip, H3 or Wan** (template or writer; author decision 2026-10-17: both frames pin the person, identity cannot drift, and the studio would prefix "<name>, <description>." to the prompt); the writer brief says not to describe any person (wardrobe or design words only if they differ between the frames). Kept on Wan I2V clips (no end frame to pin her) and on the edit stages | the first + last frames carry identity |
| Ramp | `g(x) = x + k sin(2 pi x)/(2 pi)`, k 0.45 / 0.8, 24 fps, hold by `tpad` | closed form, monotonic, tested on a real clip |
| Audio | none: the timelapse is silent; music is the library mix | re-timing H3's own audio makes no sense |

## Guards (all kept, none weakened)
  same neutral edits (no preset asks for fewer clothes; a test pins the words).

## The run (resume / cancel / reroll / interrupted)
One JSON file per run (`<guard state>/timelapse/runs/tl<12 hex>.json`), a thread per run. States: rendering, done, failed, cancelled, interrupted (the studio restarted: the saved file says rendering, nothing is running
and it has been quiet 20 s; Resume continues at the unfinished picture, clip or step). Stages render in order (the made source first), then the clips, then the steps `join -> smooth -> ramp -> publish -> polish ->
music -> captions` (a step done with its file still on disk is not redone; an optional step that fails keeps the previous file and says so). **Cancel** cancels the running job. **Re-render** a picture or a clip: new
seed, the clips that use the picture and every step after it are made again; re-rendering the made source remakes all its edits. A check that fails rerolls the picture once automatically, then it waits
("needs your review": Keep or Re-render). A build-up also checks that each stage is closer to the finished picture than the one before.

## Estimates (labelled estimates; the planner prints them by phase)
| Run | GPU | All in (guard + CPU) | Peak | Basis |
|---|---|---|---|---|
| CPU photo effect | 0 | ~1.5 min | none | the output guard dominates (assumed 6 s per video second) |
| Build-up, 6 stages dissolved, picture from words | ~4 min | ~6 min | 36 GiB | 14 s + 45 s load, 6 x (12 + 6 + 5) s + 40 s load |
| Scene, 3 keyframes on H3, picture from words, smoothing | ~7.5 min | ~10.5 min | 42 GiB | + 2 x 65 s + 120 s load, RIFE 53 s |
| Scene, 3 keyframes on Wan (crossfade, wan:i2v) | ~6 min | ~9 min | 72 GiB | 3 x (24 + 5) s + 165 s load |
| Scene, 3 keyframes on Wan first + last frame (wan:flf) | ~6.5 min | ~9 min | 66 GiB | 2 x 29 s + 165 s load (25 s per clip assumed like wan:i2v) |
| Build-up painted 6 stages, H3 morph | ~13 min | ~18 min | 42 GiB | 5 x 85 s + load |
| Add Upscale to 4K | + ~4 min | + 1.5 min | 30 GiB | SeedVR2 / RealESRGAN from `video_finish.py` (4K = assumed) |

## GPU proof plan (NOT run; do not run it until the author approves GPU time)
Preconditions: the 3D proof batch finished; >= 46 GiB free on the shared card for the H3 phase (42 + the 4 GiB floor), >= 70 for the Wan flf phase (66 + 4) and >= 40 for the edit phase; the queues of  a local port /  a local port /
 a local port empty; no pip, no download; the studio must be running a build that has `/api/studio/timelapse`, `wan:flf` and the Content Studio item (a studio restart is the author's call: ask, and check

| # | Case (`scripts/timelapse_proof.py`) | Setup | Minutes (GPU / all in) | Peak | What to look at |
|---|---|---|---|---|---|
| 1 | `scene_h3`: `scene_day_to_night_city` (H3 first + last frame) | a start picture made from the preset's words (Qwen t2i), 3 keyframes, `write: writer`, smoothing on, 12 s | 7.5 / 10.5 | 42 GiB | the keyframes: same camera and layout, dusk and night believable? the two clips: do they land on the keyframes, any wobble in the middle where the light changes, the join between clips |
| 3 | `grwm`: `process_get_ready_with_me` (character) | a saved library persona, a final from words with the character bound, 5 stages, 16 s | 3.6 / 5.6 | 36 GiB | the face match chips (ArcFace >= 0.60), fully clothed in every stage, makeup and hair change between stages 2-4, the final matches her sheet |
| 4 | `scene_wan_flf`: `scene_golden_to_blue_coast` on `wan:flf` | a start picture from the preset's words, 2 keyframes (one 5 s clip), `write: writer`, smoothing on, 6 s | 5.6 / 7.3 | 66 GiB | the clip starts on the golden keyframe and ends on the blue one (the pinned end), no flicker in the middle, nothing appears; compare with the same scene on the crossfade route (`video_engine: wan`) |
| 5 | `content_item`: a Content Studio package with ONE Timelapse item (`process_makeup`) for the persona | the package's plan lists the unit with the maker's estimate and lines; run, package, pre-post gate | 4 / 6 | 36 GiB | the unit runs after the plan, the mp4 is numbered in the package with its per-platform post text, the pre-post gate checks it like a video, Send stays the author's press |
Total about 25 GPU minutes (35 all in), one engine at a time (`python scripts/timelapse_proof.py plan` prints the numbers from the planner's tables and the gate right now). Run `run --approved`
(it posts to the studio's own routes; resumable; stops on a shut gate, never forced), or press the buttons.
Judging checklist (per run, by eye; record who judged: only the author's verdict can make a level "verified"): (1) **consistency across stages** (identity, outfit, background, camera, light unchanged except what the
stage changes); (2) **smoothness** (no jumps, the ramp slow at both ends, the join invisible); (3) **no flicker** (watch the light changes and the dissolves frame by frame); (4) **the final matches the target** (the last
**Threshold calibration (author 2026-10-17, "keep as first guesses and add the calibration report"):** the stage checks (layout, changed, step, face) stay at their first-guess lines; `timelapse_proof.py run` records every
stage's readings, you mark each made picture `pic CASE INDEX good|bad --by author`, and `report` prints, for each check, how many good and bad pictures there are, how the CURRENT lines treat them (false fails: good but under
the fail line; missed: bad but over the ok line), the cut that would separate them best and a confusion table of the automatic verdict against yours. Nothing changes a threshold by itself.

## Assumptions (the author gave no detail; change any of them)
timelapse is silent; music and captions are optional post steps. 7. Smoothing on for video-engine routes, 4K and Realism grain off. 8. Content Studio runs it as the `timelapse` item kind (see below).

## Decisions (the author answered "yes all of this" on 2026-10-17: BOTH sides of each are built and selectable)
1. **Prompt mode:** `writer` (H3 long prompt, default) and `template` (short official first + last frame form, no writer model): a per-run selector (UI "Prompts").
2. **Wan 2.2 first + last frame:** built as the catalogue entry `wan:flf` (below); a scene picks "Wan: pin both ends (flf)" or "Wan: crossfade". A preset whose own engine is Wan defaults to the pinned end when the entry is there.
3. **Finishing:** smoothing on, 4K and grain off by default; each is a per-run checkbox (and per Content Studio item).
4. **Build-up:** "CPU dissolve" (default, no video model) and "H3 morph" (5 clips, about 18 minutes all in): a per-run selector.
5. **Check thresholds:** kept as first guesses; the calibration report in `scripts/timelapse_proof.py` records the readings against your picture verdicts.
6. **Content Studio:** the `timelapse` item kind is wired AND the standalone workspace stays.

## Wan 2.2 first + last frame (`wan:flf`, 2026-10-17)
- **Graph:** `earlier_studio/tools/graphs/wan22_flf_4s.api.json` = `wan22_i2v_4s` node for node, with `WanImageToVideo` swapped for the core `WanFirstLastFrameToVideo` (start_image = the first picture, end_image = a second `LoadImage`).
  **Validated offline** with `graphcheck.validate` against GET `/object_info` of the LIVE  a local port and  a local port (both: no errors; the I2V graph the same); the classes it uses are saved as a fixture
  (`tests/studio/data/wan_flf_object_info.json`) so a test re-checks it. Nothing was submitted to ComfyUI.
- **Tool:** `wan_tools.wan22_generate(mode="flf", image, last_frame, ...)` (no preview, creative take or LoRA preset; both pictures staged; the end picture is part of the cache key); the room check is the Wan one
  (`PEAK_GIB` 64 + the shared headroom,  a local port freed afterwards).
- **Entry:** `wan:flf` ("Wan 2.2 · First -> last frame (4-step, both ends pinned)", inputs `image` + `last_frame`, aspect / seconds 5 / decode chips; no LoRA, creative-take or character), runner `runners._run_wan` passes
  `last_frame`; a curated process card `wan22-flf`; peak 66 GiB, ~25 s warm per clip (assumed like `wan:i2v`).
- **Proof level: recipe.** The official ComfyUI template and a user workflow use the same node, Wan 2.1 FLF2V 720p rendered once (167 s, 71 GiB, not judged), nobody has judged a render of THIS graph. Proof case 4 above.
- The timelapse's flf clips are submitted unbound (no `character_id`, no description of the person), exactly like the H3 first + last frame clips.

## Content Studio (wired 2026-10-17)
A package item `{kind: "timelapse", preset, source, prompt?, seconds?, ratio?, write?, video_engine?, assemble?, edit_engine?, finish?, song?, captions?}` ([content-studio.md](content-studio.md) "Timelapses"):
the ⏱ Timelapses tab adds it (made from the preset's own words once per package character, or from the first finished picture of each picture set above, or one chosen picture). The plan runs the maker's own plan
for every unit (its estimate and plan lines; its refusals become blockers), the unit starts the maker with the same body as `POST /api/studio/timelapse/start`, the finished video (the last cut: music / captions /
polish included) is a package file numbered, packaged, pre-post checked and given per-platform post text like a video. Finishing defaults per item: smoothing on, 4K and grain off (the package's Realism option
is the grain). Design picks are not passed from Content Studio yet (use the workspace). The Timelapse tab of Time and loops is unchanged.

## Known limits
- Nothing has been rendered through this; the estimates' cold loads (H3 120 s, Wan 165 s, the start picture) and the guard time are assumed.
- With a saved character a text start picture is an identity edit of her sheet, so its shape follows the sheet; the run notes when it differs from the video's ratio.
- The Wan crossfade fallback pins only the start of a clip; its end state can drift (the crossfade hides it, it does not remove it). `wan:flf` pins both ends, unjudged.
- The photo grades darken and tint; they do not add lights, clouds or motion (use a Wan photo preset for clouds / fog).
- RIFE blends the two frames either side of a hard cut; the dissolves have no cut, the H3 joins share their boundary frame.
- A first + last frame clip is stretched / cropped to the canvas by H3 (first frame stretched, last cover-cropped): keep every keyframe the same shape (they are, as edits of one picture).
