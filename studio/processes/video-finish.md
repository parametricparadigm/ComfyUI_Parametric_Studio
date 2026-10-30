# Video finish

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Untested.


## What happens
The moment a maker has joined its scenes into one file, this stage runs on that file, by itself:

1. **Smooth motion (2x frames)**: studio entry `edit:interpolate` (RIFE 4.26 x2, `interpolate_frames`). Skipped, with a note,
   when the source is already 48 fps or more.
2. **Upscale**: studio entry `vupscale:2x`. Method by the clip: **quality** (SeedVR2 7B) while the frame is inside its tested
   envelope (480x832), else **fast** (RealESRGAN per frame, takes H3 768p). If neither tool accepts the clip the step is
   skipped with the tool's own refusal text in the run note.
3. **Final render**: the last step's file, source audio kept. The tools mux the audio back; the stage probes the result and lays
   the source's audio on again if a tool dropped it.

Every step is an ordinary studio job (`queue_when_free`, all request checks, the tool's VRAM preflight, the output guard). The
run **never fails because finishing failed**: a refused or failed step keeps the previous file as the final and adds a run note
(a job failure is retried once; a refusal is not). The plain join is kept (`original` / "Original join") and the smooth / 2x files
stay listed next to the final.

## Upscale target (4K)
Request option `finish: {interpolate, upscale, target}`, `target` `"4k"` (default) or `"2x"`; `target: "off"` = `upscale: false`.
- `4k` = true UHD, 3840x2160 landscape / 2160x3840 vertical. What the upscaler really does for `target="4k"` (its own doc block in
  `video_upscale_tools.py`): the method's native 2x pass, then one CPU lanczos scale + centre crop to exactly UHD (1.6-2.5 % of one
  axis is cropped), H.264 CRF 18. **The extra pixels are interpolated, not model detail.**
- **The one switch**: `video_finish.native_4k_available()` is true only when `inspect.signature(video_upscale_tools.upscale_video)`
  has a `target` parameter **and** the studio entry `vupscale:2x` (`media_more.ENTRIES` chips) has a `target` chip that passes it
  through (`UPSCALE_TARGET_PARAM = "target"`). Both exist as of 2026-10-16, so the plan sends `settings.target = "4k"`; if either
  goes missing it falls back to 2x and the run note says "native 4K target not available yet: upscaling 2x".
- A 4K the tool refuses before any part exists is redone at 2x (the best allowed result) with the refusal text in the notes.
- [wired, unproven live: no 4K output has been made through this stage]

## Order, parts, and why
- **Order** (`plan()["order"]`): upscale first, then smooth, when the upscaled frame stays inside the size RIFE was run at after
  SeedVR2 (`RIFE_TESTED_PX` = 1664x960: a Wan 480x832 clip at 2x). Otherwise (H3 1344x768, and every 4K target) smooth first, at the
  clip's own size where RIFE was measured, and the upscaler then sees the doubled frames. Upscale-first is cheaper (the upscaler is the
  expensive step per frame).
- **Parts**: RIFE holds every frame of a call in memory (float32), so a long clip goes in chunks sized by a pixel budget
  (`RIFE_BUDGET`, 1344x768 -> 290 frames); each chunk carries one extra frame of the next so the join has no missing in-between frame,
  and the extra output frame is trimmed (total frames = 2N - 1). The upscale runs in parts of at most `UPSCALE_PART_FRAMES` (1440), under
  the tool's `MAX_LONG_FRAMES` (7200), so the doubled frame count is never a limit. The joins re-lay the source audio (copy of video,
  AAC audio, `apad` + `-shortest`: no frame is cut).
- **Publishing**: a multi-part join is a local file; it becomes the run's result through a CPU-lane studio job (engine `videofinish`,
  `runners._run_videofinish`) so the output guard checks it like any render.
- **Resume**: the state (`run.finish`) is saved after every change. After a restart the stage continues at the unfinished step and
  part; a job in flight is looked up, not resubmitted.
- **Known limit**: RIFE blends the two frames either side of a hard cut into one in-between frame (21 ms at 48 fps). Not detected or
  patched.

## Estimates (labelled estimates everywhere)
| Constant | Value | Source |
|---|---|---|
| RIFE | 0.033 s/frame at 1344x768, scaled by pixels | measured: 4 s per 124 frames incl. model load (H3_ADDONS_AB_2026-10-09) |
| Upscale fast | 0.236 s/frame at 480x832, scaled by pixels | measured 14-28 s per 81-97 frames (docs/processes/video-upscale.md) |
| Upscale quality | 1.01 s/frame at 480x832 | measured 67-114 s per 81-97 frames |
| 4K target | the 2x GPU time + 0.12 s/frame CPU scale and encode | **assumed** (no 4K timing exists) |
| Job path | 20 s per job | assumed |
| Output guard | 6 s per video second per checked file | assumed (smoke 2026-10-12, guard sampling cut to 1/s on 2026-10-13) |
The Long video planner shows the finishing time next to the render time and adds the finishing GPU time to the "over an hour needs
confirm" check.

## Where it is wired
| Maker | Default | Change |
|---|---|---|
| Long video | on (`finish` default `{interpolate, upscale, target 4k}`); chips "Smooth motion (2x frames)" and "Upscale to 4K" | `Manager._finish_run` after the join; statuses `interpolating` / `upscaling` / `finishing`; `run.final` becomes the finished render, `run.original` the plain join |
| Music video | on; chip "Smooth + upscale to 4K" | `Service._finish` inside the assemble stage; `run.original` |
| Deliverables | on only for templates ending `_long` or of 60 s or more; chip "Finish: smooth + upscale" | `Service._finish`; plain join in `finals` as "Original join" |
Not wired: Anime and Song recreate finals (not asked); the Recreate video maker.

`finish.realism: true` (request field; Long video chip "Realism grain (opt-in)", Music video checkbox "Realism (opt-in)") adds ONE CPU step after everything
else: `realism.post_video` (temporal luma-weighted grain, metadata dropped, audio copied; it never resizes here, the upscale step already chose the size).
It is the last step so no later scale smooths it away. A failure keeps the previous file and adds a note ("Realism grain step failed (...); keeping the
un-grained file"); a finished pass is reused on resume. Cost ~4.5 fps at 3840x2160 (the plan estimate adds `realism_s`). `finish: {"realism": false}` or no key =
the finishing state and result are byte-identical to before. It restores a camera noise floor, not detail (ESRGAN 4K is smoother than the original at 100%);
proxy-tested on 5 phone photos and one clip, not a guarantee. Deliverables take `realism: true` in their start request (the checkbox "Realism (opt-in)"): it joins the run's `finish` option (a short video then runs a
finishing pass with only the grain) and sets `settings.realism = "on"` on each shot job (wording where the H3 mode has the chip). Content Studio passes the same option.

## Tests
`tests/studio/test_video_finish.py` (plan, parts, run, cancel, resume, 4K switch), `tests/studio/test_realism_wiring.py` (the Realism grain step), `tests/studio/test_longvideo_finish.py`,
`tests/studio/test_musicvideo.py` (finishing block), `tests/studio/test_deliverables_finish.py`, `tests/chatbox/js/longvideo.test.mjs`,
`musicvideo.test.mjs`, `deliverables.test.mjs`. **Not proven live:** RIFE on a clip with no audio track, RIFE chunk joins on real H3 output,
the fast upscaler at 1344x768 (untested above 480x832), any 4K output.
