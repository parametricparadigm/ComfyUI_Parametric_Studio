# Long-form video

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


## What is true on this box (research 2026-10-12)
No model here renders minutes in one pass. H3 tops out at 15.1 s per shot, Wan 2.2 at 81 frames (5 s), LongCat Avatar
at one 3.72 s segment as wired. **Every long video is a chain of short segments.** "300 min with any model" is not true:
the guard checks at most 30 min per file, and on most models the chain is untested past one clip.

| Entry / family | One render | Long-form method | Tested? | Evidence | Render s per video s | VRAM |
|---|---|---|---|---|---|---|
| H3 cinematic / continue / i2va (h3:*, h3p:i2va) | 5-10 s (max 15.1) | chain: last frame -> I2V | partial | Format Lab AB7: 2-clip continuation, clip 2 identity 0.03 vs 0.54 | ~8-11 (single clip) | 39-46 GB |
| H3 t2va / handheld | 5-10 s | segment 1 T2V, then h3:continue / h3p:i2va | untested | as above | ~10 | 46-48 GB |
| H3 product / stylised / ugc | 5-10 s | chain | untested | ugc's voice changes per clip | ~10 | 46 GB |
| H3LongVideos (h3p:longvideo) | 2-4 shots | native auto-chain | **tested** 20.5 s | LTX_H3_BATCH §9-fix: 4 shots in 181 s, seams SSIM 0.87-0.89 | 8.8 | 41 GB |
| H3 fl / template / l2va / multishot / meridian / keyframes | 2-10 s | none: needs keys / a source / ends on a still | — | capped with the reason | — | — |
| Wan 2.2 I2V / T2V (wan:*) | 81 f = 5.06 s | chain (T2V continues on I2V) | untested | the Wan chain that IS tested is SVI (prev latents); without SVI that chain fell apart | ~4.7 warm (KB) | 65-72 GB |
| Wan SVI 2.0 PRO (vid:svi) | 3 x 81 f = 14.6 s | native SVI chain; longer = runs chained by last frame | **tested** to 14.6 s | e_wsp_svipro_lora 66 s warm | 4.5 | 75 GB |
| LightWan 2.2 I2V / T2V 720p | 81 f = 5.06 s | chain | **smoke 2026-10-12** (below) | 4 segments accepted before the pause | ~40 wall (measured) | 35 GB |
| TurboWan 2.2 720p (sidecar  a local port) | 81 f | chain | untested | 85-90 s per clip | ~18 (KB) | 28 GB |
| Wan fast preview | 49 f | chain | untested | 13 s warm | ~4.3 | 64 GB |
| LongCat Avatar 1.5 | 93 f = 3.72 s | voice track sliced per 3.72 s + last frame | untested | 5 single-segment rows, 88-296 s each | ~24-80 | 41-62 GB |
| Animate 2 / SCAIL-2 / edits / foley / upscale | source length | none (follows the source clip) | — | — | — | — |

Installed but **not usable** (no weights on disk, or a failed proof): FramePack (nodes, no weights), SkyReels-V2
diffusion forcing (`WanVideoDiffusionForcingSampler`, no DF weights), InfiniteTalk (core `WanInfiniteTalkToVideo`, no
weights), Wan context windows (the June try rendered black), LTX extend / looping (LTX weights deleted 2026-10-10),
the dlqueue; nothing was downloaded.

## How it works
1. **Length chip** on every video entry: one clip (the entry's own length) or 0:30 … 30:00, capped at what the entry's
   method supports; a capped length shows disabled with the reason. Untested chains say "(untested)".
2. **Plan + estimate** (`POST /api/studio/longvideo/plan`): segments, render s per video s (measured on this box's
   finished runs once there are some, else the KB single-clip proof), +15 % rerolls, one cold load → GPU hours. Over
   1 h the start needs `confirm: true` (the composer asks).
3. **Segments** are ordinary studio jobs through `_studio_generate` (every request check, text guard, enhancer, GPU
   turn, lanes, the tool's VRAM preflight, output guard, ComfyUI visibility), queued `queue_when_free` (they wait for
   gaps, nothing is evicted). Segment 1 renders from your inputs; segment k from the last frame of the last accepted
   segment, new seed. T2V entries continue on their I2V sibling.
4. **Script / shot list** (optional): split into one prompt + spoken line per segment by the content LLM
   The split must not add camera directions (the smoke's split added "medium shot" and framing drifted to knee height).
5. **Drift checks** per segment: output guard (withheld / pending never used); ArcFace median of first/mid/last frames
   vs the character's headshot (bar 0.45; no face = not judged); brightness / colour drift vs segment 1 (28 / 14);
   black or blown-out frames. A failing segment is rerolled from the same frame with a new seed (2 rerolls), then the
   best try is kept and flagged (`strict` stops instead). **Drift the conditioning frame already had is not rerolled**
   (a reroll from that frame cannot fix it) — it is kept, flagged and noted.
6. **Join** (`longvideo:join`, CPU lane): duplicate first frame of each continuation dropped; a cut when the seam is
   close (mean grey diff ≤ 22), else a 0.4 s crossfade (new shots always); pieces normalised to the first segment's
   size/fps with an audio track; concat demuxer + one CFR re-encode; trimmed to ≤ 30:00; music bed from
   `longvideo.MUSIC_BED_PROVIDER` (hook for an earlier branch; None = no bed). The joined file and a seam contact sheet
   go through the output guard as a normal result.
7. **Robust**: state in `<studio jobs>/longvideo/<run>/run.json` after every step; a chatbox restart resumes running
   runs (`COMFY_STUDIO_LONGVIDEO_AUTORESUME`, default on; a segment job the restart interrupted is submitted again);
   Cancel stops the run and its job; Resume continues a paused / failed / cancelled run from the first segment not
   accepted. The long-video panel shows progress, ETA, rerolls, notes, and the result.

Characters: on entries with an identity input (H3 image modes) every segment carries the character. On entries
without one (Wan, LightWan, TurboWan, H3 pipelines) the character's description leads every prompt, segment 1 starts
on the sheet's full-body still, and every segment is ArcFace-checked against the sheet.

Run `(earlier commit)`, 15 segments planned by the LLM split. Paused by the coordinator at segment 5 (author using the
studio); state on disk, to be resumed with `longvideo_smoke.py --resume (earlier commit) --render`.

| seg | wall s | tries | ArcFace median | luma / chroma drift | seam diff | join |
|---|---|---|---|---|---|---|
| 1 | 207.6 (cold) | 1 | 0.749 | — | — | — |
| 2 | 230.6 | 1 | 0.644 | 1.9 / 4.2 | 3.0 | cut |
| 3 | 181.9 | 1 | 0.541 | 5.7 / 6.0 | 3.2 | cut |
| 4 | 331.5 (*) | 1 | 0.501 | 7.2 / 7.5 | 2.8 | cut |
| 5 | try 1 rejected | 2+ | 0.387 (try 1) | 8.9 / 8.7 | 2.4 | — |

(*) inflated by a guard-timing probe of mine competing for the box-wide classifier slot.
Studio job time per segment 175-223 s, of which ComfyUI execution 67-80 s; the other ~105-145 s are the job path
(preflight, staging, the output guard on 81 frames at 720p, publish, /free) — the guard is the bulk.

Findings: seams are invisible (cut joins, diff 2.4-3.2); identity decays ~0.06-0.1 per segment along a last-frame chain
(it crosses the 0.45 bar at segment 5, ~25 s); colour drifts ~2 luma per segment; framing crept tighter when the split
prompts named shot sizes. Contact sheets: `seams_partial_4segments.jpg`, `segments_first_last_4segments.jpg`; the
4-segment join `partial_4segments_joined.mp4` (20.06 s, 16 fps, 720x1280).

## Honest 30-min extrapolation (LightWan I2V 720p)
- 360 segments x ~200 s wall = **~20 h**, +20 % rerolls (1 in 5 so far) = **~24 h**; GPU-busy time ~360 x 75 s ≈ 7.5 h,
  the rest is the per-segment job path (mostly the output guard on the CPU) — serial, because segment k+1 needs k's
  last frame.
- The final 30-min file is new bytes, so the guard checks it whole again (CPU, same density) — several more hours.
- **A character will not hold for 30 min** with last-frame chaining alone: identity was under the bar after ~25 s.
  Without a character (scenery, product, abstract) identity does not apply, but colour drift reaches the 28 luma bar
  around segment 14 (~70 s) at the measured rate; from there every segment is flagged.
- Other entries: H3 chains ~10-11 GPU s per video s (~5-6 h GPU for 30 min, plus the same job-path overhead), Wan 2.2
  box stack ~4.7 (but 72 GB peak), LongCat ~24-80 (13-40 h). All untested past one clip except what is listed above.

## What would make 30 min real (next steps, untested)
1. An identity re-anchor every N segments: refresh the conditioning frame with a two-image identity edit (frame +
   headshot) before continuing — needs a two-image edit graph (the studio's qwen21 / Klein edits take one image).
2. Colour anchoring: transfer the conditioning frame's colour statistics back to segment 1's before continuing.
3. Pipelining: start segment k+1 from k's last frame while k's output guard runs (discard k+1.. if k is withheld) —
   halves wall time at the same safety (nothing unguarded is ever served).
4. Native long models with context (SVI prev-latents for Wan, H3LongVideos with more shots) tested past their proofs.

## Continuity modes and the H3LongVideos chain (2026-10-15)
The Continuity chip (shown once a Length over one clip is picked) sets how segments connect:

| Mode | Segment k starts from | Join | Good for | Trade-off |
|---|---|---|---|---|
| 🔗 Continuous (`chain`, default) | the last frame of segment k-1 | cut (or crossfade when the seam jumps) | one unbroken take | identity decays ~0.06-0.1 per segment (under the bar at ~25 s on the 2026-10-12 smoke) |
| 🔁 Continuous + re-anchor (`reanchor`) | the last frame, except every 3rd segment, which starts from your inputs again | hard cut at each re-anchor | long takes that must keep the face | a visible cut every ~15 s |
| 🎬 Independent shots (`shots`) | your inputs (the character sheet / start still) every time | hard cuts | edits, montages, anything over ~30 s with a character | no continuous motion across shots |

**H3LongVideos** (`h3p:longvideo`) now takes lengths past 20.5 s: each run is the scene paragraph + 4 shot paragraphs
(planned from the script, 5 s per shot, quoted lines kept), and each further run starts from the last frame of the one
before (or from your still in `shots` / `reanchor`). One run is tested (4 shots / 20.5 s); chaining runs is untested.

**Wan SVI 2.0 PRO past 3 clips** (`vid:svi`) was already a chain of 3-clip runs (each 14.6 s, continued from the
previous run's last frame); the continuity modes apply to it too.

Not wired yet: joeygambino's `context_pin` (re-use the last ~22 latent frames; needs the H3-Motion-Context nodes and an
A/B against the last-frame chain) — the next long-form test.

## Finishing (2026-10-16)
As soon as the last scene is accepted and the join is made, the joined video is finished by itself (`studio/video_finish.py`, full
detail in [video-finish.md](video-finish.md)): **upscale (4K target, 2x until the upscaler can) and smooth (RIFE x2)**, in the order the
clip's size allows, as ordinary studio jobs, then put together as the run's final render with the source audio kept.
- On by default; request field `finish: {interpolate, upscale, target}`, UI chips "Smooth motion (2x frames)" and "Upscale to 4K".
- Opt-in, OFF by default: `finish.realism` (chip "Realism grain (opt-in)") adds a light camera grain as the last step (CPU, ~4.5 fps at 4K; see [video-finish.md](video-finish.md), [realism-4k.md](realism-4k.md)). The prompt wording is the entry's own `Realism` chip; `h3:continue` segments do not offer it.
- Run statuses `interpolating` / `upscaling` / `finishing` (the progress text names the part, e.g. "Upscaling 2x: part 2 of 5").
- `run.final` is the finished render; the plain join stays as `run.original` ("Original join" link), the smooth / 2x files are listed.
- The planner estimate adds the finishing time (labelled an estimate) and counts its GPU time toward the "over an hour needs confirm" check.
- Finishing never fails the run: a refused or failed step keeps the previous file and writes a note. Cancel stops the finishing job;
  a restart or Resume continues at the unfinished step.
- A video over 5 min at 24 fps is upscaled in parts (the tool's 5 min cap is per call). RIFE blends the frames either side of a hard cut.

## Relationship to the Deliverables Wan engine (2026-10-17)
Deliverables on Wan ([wan22-deliverables.md](wan22-deliverables.md)) renders each template shot as its own 5 s clip (or a 2-3 clip SVI chain with `wan_long: svi`) and joins
them: independent shots from one template. Long video chains one continuous story by last frame / latents (`vid:svi` tested to 3 clips; `wan:i2v` chaining untested).
They share the SVI entry only. Music video stays H3 (audio-locked sung shots; Wan has no audio input).

## Batch phases for Deliverables long-form runs (2026-10-17)
Long-form Deliverables templates (a `*_long` id or a minute or more) have many shots per run, so they get the same option as the music video: `batch_phases` `auto` (default; on from 3 shots of a long-form run) | `on` | `off`, select "Batch phases" in the Deliverables options. On: the existing prepare stage writes every shot's long H3 prompt first (one writer load), then the renders follow by themselves with those prompts, then the join / finishing as before. Not for Wan runs. This is the Long video **chain** maker's sibling, not the same maker: the Long video chain (last-frame segments) writes each segment from the previous one and is **not** batched. See [batch-phases.md](batch-phases.md) for the limits, the timings (`prep_s`, `render_stage_s`) and the measurement protocol.
