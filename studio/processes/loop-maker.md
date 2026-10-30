# Loop maker

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Untested.


## The three methods (a chip with an honest trade-off line each)
| Method | How | Trade-off (also shown in the UI) |
|---|---|---|
| **Generate a loop** | a still (a finished studio picture, an upload, or a start frame made from words on a text-to-image model, optionally of a saved character) becomes ONE first + last frame clip with the SAME picture at both ends: `h3:fl` (5 / 8 / 10 s) or `wan:flf` (5 s), with a cyclic-motion prompt | new motion from a still, but the engines land NEAR the first frame, not on it: a CPU step picks the best cut near both ends (usually "drop the final frame, which repeats the first") and can crossfade. Costs a GPU clip. Faces and big moves drift most |
| **Find a loop** | CPU only: an existing video (a finished studio video or an upload, at most 120 s) is searched for the start / end pair that wraps best, cut by source frame number | free and quick, keeps real footage and motion; only works if the video already repeats. A one-way motion has no good loop and the seam score says so |
| **Ping-pong** | CPU only: a window of any clip (up to 30 s; a clip of more than 96 frames is reversed in chunks of 96, so memory stays bounded) played forward then backward, neither turning frame twice; optional ease (the Timelapse maker's closed-form curve) so it slows into and out of each turn | seamless at the cut by construction, but the motion visibly reverses: water, hair, smoke, lights, cloth; not walking, speech, text or anything with a direction |

### Generate: how it is submitted (read from `timelapse.py`, same rules)
- **Both slots hold the same reference**: `h3:fl` gets `still` = `last_frame` = the start picture (job reference or workspace path); `wan:flf` gets `image` = `last_frame`. `tests/chatbox/test_loops_routes.py` pins this against the real checks.
- **Never a character on a first + last frame clip, and no person is described** (author decision 2026-10-17: both frames pin who is there; the studio would otherwise prefix "<name>, <description>."). A start picture made from words MAY carry a saved character (an identity edit of her sheet); the clip does not.
- Prompts (`loop_prompts.py`): `write: "template"` = the official H3 FL2VA form (alignment line naming Picture 2 as "the same picture as Picture 1", ONE shot, fixed camera, one full cycle that ends where it began, soundscape, `non_diegetic_music: N/A`), linted by `lint_h3_prompt` in a test;
  `write: "writer"` (default) = an `h3_brief` for the studio's long-prompt enhancer whose rules say the pictures are one picture and forbid describing a person or moving the camera. Wan: motion + "Fixed camera." + "One smooth, even cycle that ends exactly where it began, a seamless loop", or a `wan_brief`.
  The camera is always fixed (a camera move or a one-way change cannot loop). You may type your own one-cycle motion (guarded).
  Each carries an honest note (rain and steam are chaotic and will show a reset unless crossfaded; the turntable is the least reliable: neither engine is built for a measured 360 degree turn). All texts pass the text guard in both modes (a test).
- A generated clip's own soundtrack is **not loop-safe**, so it is dropped; use a sound bed or leave it silent.

### Find: the algorithm (`loop_media.find_loops`)
Frames are decoded to 72x72 RGB (every n-th source frame, at most 1800). For every pair (i, j) (the loop plays frames i .. j-1 and wraps to i) three scale-free distances between frame i and frame j (the frame that would come next): **pixel** RMS (gram matrix, all pairs at once),
**perceptual hash** (8x8 difference hash, Hamming) and **colour histogram** (16 bins x RGB, L1), each divided by its median over all pairs (1.0 = an average pair), weighted 0.55 / 0.20 / 0.25. The best 200 pairs get a **motion-continuity** term (optical-flow free: the velocity image before the wrap against the one after it, against the clip's typical step, weight 0.25),
and a small bonus for longer loops (0.04) breaks ties. Five ranked, distinct candidates are kept; the UI can re-cut at another one without re-searching (`POST runs/{id}/pick`). The cut is by frame number (nothing re-timed); an optional crossfade fades the last k frames into the first k (the loop is k frames shorter).
Restricting the start and end windows is what the generate method's tighten step uses (start within the first 0.4 s, end within the last second).

## Seam QC (a craft check, not a prediction; the thresholds are first guesses)
Measured on the finished loop file (`loop_media.seam_report`), each check `pass | warn | fail`, score 0-100 = 50% wrap step + 25% motion + 25% tone:
| Check | What | pass / warn |
|---|---|---|
| wrap step | the step from the last frame to the first, against the loop's own median frame-to-frame step (so a fast clip and a calm one are judged alike) | up to 1.6x / 3.0x |
| motion continuity | the velocity just before the wrap against just after it, against the loop's typical change of velocity | up to 1.8x / 3.5x |
| brightness / colour step | mean luma step and strongest colour-channel mean step across the wrap, of 255 | up to 2 / 5 |
| sound (when the file has sound) | `sound_dsp.loop_seam` (slope-aware click, level step, spectral match; read-only import): fail when 2 of its 3 limits are crossed | click < 4, level < 6 dB, match > 0.8 |
A video that barely moves reads `still`: almost any cut loops, the score is high and there is little to see (the run says so). The UI prints "A craft check, not a prediction" next to the score and the grade-D theory note beside the form.
**Preview:** the final page plays the loop 1 / 3 / 5 / 10 times and stops, with "Watch the wrap" to replay it. **Repeat x N:** a second file with the loop played N times (2-10, at most 60 s), published as its own studio video.

## Audio
| Option | What |
|---|---|
| Silent (default) | the loop has no sound |
| Keep the video's own sound (find, ping-pong) | find: the sound of the loop window with an equal-power blend into the sound that FOLLOWED the window (`fold_tail`, 80 ms), or, with a crossfade, `sound_dsp.make_loop` over the same window (same length as the video); ping-pong: the sound forward then mirrored (continuous at both turns; it does not follow the ease) |
| A library song as a bed (all methods) | `sound_dsp.make_loop` on the song cut to the loop length (tiled when the song is shorter), levelled to about -16 LUFS with a 0.89 peak cap, muxed to the exact length; the audio seam is then checked |
| Sound cues (shared) | the same `SoundCueSelect` + `sound_cues.plan_for_scenes` as Timelapse / Recreate: off by default, a post `export` job lays Trending noises on the published loop (they play once per loop) |

## The run (plan, start, runs, cancel, resume)
`POST /api/studio/loops/plan` (and `GET .../plan?...`) shows every check, the steps, the prompts and the **estimate** (labelled: KB numbers scaled, cold loads, CPU and guard times assumed) and refuses before anything is queued;
`POST .../start` makes the run; `GET .../runs`, `GET .../runs/{id}`; `POST .../runs/{id}/cancel | resume | reroll {what: "clip" | "stage", index} | pick {pick}`; `GET .../runs/{id}/export/gif|webp?session_id=` (served through `publish_file`, the output guard, then `_serve_studio_file`).
One JSON file per run (`<guard state>/loops/runs/lp<12 hex>.json`), a thread per run. States: rendering, done, failed, cancelled, interrupted (the studio restarted: the saved file says rendering, nothing is running and it has been quiet 20 s; **it waits for Resume, nothing starts on boot and no GPU job is queued by itself**).
Steps `loop -> audio -> publish -> sound_cues -> repeat -> publish_repeat -> export`: a step done with its file on disk is not redone on Resume; an optional step that fails keeps the previous file and says so in the notes. The loop and the repeat render are published as `videofinish` studio jobs, so the **output guard reads every file**, the card appears in the feed and the Post steps (Send, Wipe, captions, export) work on them. The gif / webp copies are made from the published loop.

## Content Studio (wired 2026-10-17)
The **🔁 Loops** tab adds the Loop maker as a package item: `{kind: 'loop', method: generate | find | pingpong, preset (generate), source, prompt, motion, ratio, write, video_engine, seg_s, crossfade_s, ease, min_s, max_s, start_s, end_s, audio (none | keep | bed), song, repeat, formats {gif, webp}}`.
`generate` takes `source` `{text: true}` (the preset's own words, or `prompt`, once per package character), `{from_item: 'all' | 'iN'}` / `{from_template}` (the first finished picture of each earlier picture unit) or `{job_ref}` (a chosen picture); `find` and `pingpong` take `{job_ref}` (a chosen finished video) or `{from_item: 'all' | 'iN'}` (the first finished VIDEO of each earlier video unit, known when that unit has run).
The plan asks the maker for each unit's estimate and plan lines (`content_studio.make_env` -> `loops.Service.plan`; a refusal is a blocker; a found / ping-pong loop of a video that does not exist yet gets a labelled guess), counts `loops` in the totals and reserves disk. The unit starts the maker with the same body as `POST /api/studio/loops/start`, is polled like a timelapse (interrupted detection, resume, cancel), and its finished loop is numbered in the package, given per-platform post text like a video and pre-post checked before Send.

## Guards (all kept)

## Estimates (labelled estimates)
| Run | GPU | All in (guard + CPU) | Peak | Basis |
|---|---|---|---|---|
| Find / ping-pong, 6 s source | 0 | ~25-45 s | none | CPU analysis ~4 s + 0.15 s per source second (assumed), tail 6 s, guard 6 s per video second |
| Generate on H3, a given picture, 5 s | ~2.5 min | ~3.2 min | 42 GiB | 5 s x 7.5 s/s warm (KB) + 120 s cold load (assumed) |
| Generate on Wan flf, a given picture | ~2.3 min | ~3 min | 66 GiB | ~24 s warm per clip like `wan:i2v` (assumed) + 165 s cold load |
| + start picture from words | + ~1 min | + ~1 min | 36 GiB | 14 s + 45 s load |

## Live proof (NOT run; do not run until the author approves GPU time)
| # | Case | Method | What to look at |
|---|---|---|---|
| 1 | `h3_candle` | generate on `h3:fl`, Candle flame, start frame from words | last frame vs first, the flame cycle, the tighten step's cut, seam score, loop it 3x in the preview |
| 2 | `h3_breathing` | generate on `h3:fl`, Slow breathing, a library persona's picture | the face and pose return to the first frame, no drift, no mouth/eye artefacts at the wrap |
| 3 | `h3_rain` | generate on `h3:fl`, Rain on a window, 8 s, with a 0.3 s crossfade | rain is chaotic: does the crossfade hide the reset, is the seam score honest about it |
| 4 | `wan_ripples` | generate on `wan:flf`, Water ripples | the pinned end really is the first frame (no jump), the ripples cycle |
| 5 | `wan_steam` | generate on `wan:flf`, Steam from a cup, a given picture | same, plus the plume shape at the end |
| 6 | `find_clip` x3 | find on three finished studio videos (a calm scene, a cyclic move, a one-way move) | the cut lands on a repeat, the one-way move is flagged by the seam score, the candidates are sensible, a crossfade changes the seam score the right way |
Judging (by eye, record who judged: only the author's verdict can make a level "verified"): (1) the wrap is not noticed over three plays; (2) the seam score agrees with the eye (a calibration, not a prediction); (3) guards (every picture and clip has its job card and guard result, nothing withheld); (4) sound has no click at the wrap.

## Known limits
- Nothing has been generated on the GPU: both engines may land visibly off their first frame, and a face or a large motion will drift; the CPU tighten step cannot fix a clip that ended elsewhere.
- Rain, steam and other chaotic motion cannot repeat exactly; a crossfade hides, it does not remove.
- The find step compares 72x72 frames: a small fast object in a large still frame barely moves the distances, so the seam ratio is less sensitive to it (the first-guess thresholds are not calibrated).
- Ping-pong windows are at most 30 s. A clip of up to 98 frames is reversed in one go (the old path); a longer one is reversed chunk by chunk (`PINGPONG_CHUNK` = 96 frames: each chunk is trimmed, reversed and encoded on its own, the last chunk first, then the forward clip and the chunks are joined), so ffmpeg never holds more than 96 frames. The chunk files are removed afterwards. The ease re-times the video only, not the sound.
- A crossfade shortens the loop by its length. The gif / webp copies are plain palette / libwebp encodes at 480 px.
- The seam score and its thresholds are a craft check; there is no evidence they predict replays.
