# Quality sweep

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


## Purpose / when to use it
The grainy pose picture (`stand_hands_clasped`, 19.1 against 5.4 in its input = 3.5x) passed every automatic check of the pose set, and seed 4242 was only one of the ways to get that defect. The sweep goes back over everything already made, measures it on the CPU, and lists what looks bad with the reason and the numbers. You then mark the good ones OK, hide the noise, and queue a new render for the bad ones.

It **flags and suggests**. It never edits, moves or deletes an original, it never starts on its own (not at boot, not after a restart), and it never queues a re-render on its own.

## Step-by-step in the studio UI
1. Open **Quality**. **Start sweep** (Options: face drift on, anatomy off, only results with a job record, videos on, 2 workers). Progress, speed and time left show in the bar; **Pause**, **Resume** and **Cancel** work at any time. What was measured is kept.
2. **Flagged results** is a grid of thumbnails with a Fix / Check / Note badge, the reasons (hover the ⓘ for what that check cannot see), and the measured numbers. Filters: severity, check, character, studio, from / to date, text, and the To review / Marked OK / Hidden / All tabs. The first view shows Fix and Check, not the notes.
3. Per picture: **Mark OK** (it leaves the list and the counts until its file changes), **Hide**, **Open in results** (large view, the file path, a link to the original) and **Queue reroll**.
4. **Summary**: counts per check and severity, the worst offenders, how many Qwen results were made with seed 4242 (and how many of those measure grainy), counts per studio and per character, and what every check can and cannot see.
5. After a studio restart a running sweep shows **Interrupted**; **Resume** continues it (the index keeps everything measured so far).

## Checks, thresholds and what each can and cannot see
| Check | Looks for | Cannot see | Severity |
|---|---|---|---|
| Obvious failures | undecodable or cut-short file, all black / white / flat, a file under 4 KB, a video that does not open, black sampled frames | a valid but wrong picture | Fix (flat: Check) |
| Grain | `grain.hf_energy` against the edit's own input with the live gate's rule (>= 2.0x and >= 10, `grain.RATIO_MIN` / `ABS_MIN`); with no input left, >= 16 for a Qwen edit; the live gate's own flag on the artifact | grain on purpose; mild random noise; defects that are not high-frequency | Fix with an input or the gate's flag; Check for an absolute reading; Note for another engine's outlier |
| Known-bad seed 4242 | a qwen21 result whose job record (or the gate's record) says seed 4242 and that the studio did not move to 4243 | the picture itself; most 4242 results are fine | Check, a Note when the measurement is clean |
| Blur / low resolution | the sharpest of 8 x 8 Laplacian tiles (768 px copy) under 40; a short side under 512 px | intentional soft focus or bokeh (the sharpest tile is used), motion blur | Check; low resolution and video: Note |
| Near-duplicates | 64-bit difference hash within 3 bits AND 16 x 16 thumbnails within 2 grey levels, or identical bytes; all but the best are flagged (no grain flag, then largest, cleanest, newest) | a wanted pair (an upscale); a pose edit of one source is not caught | Note |
| Face drift (per character) | ArcFace (insightface, CPU) of the face against the character's saved `head_front`: under 0.40 Fix, under 0.50 Check, and a low outlier among that character's results (Note). **Turned or looking-up heads get a lower floor: under 0.25 Fix, under 0.30 Check**, when the record says so: the pose set's own `turn` flag, a turned / looking-up pose (id or text of the pose-set run), a character sheet's profile or 3/4 role, or the job's own instruction ("over the shoulder", "looking up", "profile view" ...). The card says which rule applied | no-face pictures, several characters in one picture (skipped), a head turn the record does not mention (the strict floor applies), a character with no `head_front` | Fix / Check / Note |
| Anatomy (opt-in) | DWPose pair: a hand the input shows that the result lost, a held phone gone, more people than expected (`pose_anatomy.compare`) | missing fingers, an extra arm read as one person, anything but a phone; poses that hide the hands on purpose | Check / Note |
| Video | 5 frames spread over the clip, measured like pictures: black frames, grain, blur | anything between the sampled frames | Fix (black), Note (grain, blur) |

Every threshold is in `data/qsweep_thresholds.json` with its calibration note. Changing one and pressing the **rejudge** route (`POST /api/studio/qsweep/rejudge`) re-applies it without measuring again.

## Calibration (2026-10-17, the author's files, CPU, read-only)
Measured with `scripts/qsweep_calibrate.py` and a full sweep of the real store (the numbers are also in the thresholds file):
- **Qwen edits with their input still on disk: 230.** The ratio to the input is under 2.0x for 202 (one of them 1.75-2.0x) and 2.0x or more for 28: a visible gap, so the live gate's rule is the reference.
- **Seed 4242 is a poor label.** 84 Qwen results are recorded with 4242: 13 measure grainy, 71 measure clean (the metadata alone would be right 15% of the time). **15 grainy results were made with other seeds** (seed 7 x12, 4409 x2, 770912780 x3): a seed list cannot find them, the measurement can. Hence 4242 is a Check that drops to a Note when the picture measures clean.
- **Absolute grain rule (no input left), threshold 16**, against the gate's verdict on the 230: 25 of 28 grainy found (false-negative rate 11%), 6 of 202 clean flagged (false-positive rate 3.0%, precision 81%). At 13 the false positives double. 1 of 174 Qwen edits with no input reads 16 or more.
- **Pose-set proof: 110 pictures read**, 1 grainy (the 3.5x `stand_hands_clasped` the set judged "ok"), 109 clean (at most 8.1).
- **Face drift against the pose-set proof's own face check** (143 pictures with a face): all 17 it failed are flagged here (11 Fix, 6 Check); of 113 it passed, 1 flagged (0.9%). Over the whole library 66 of 455 single-character results are flagged (14.5%): one character, 52 of 244 (21%, mostly Klein edit and pose-control results: real drift or turned heads), every other character 14 of 211 (6.6%). No judged identity labels exist, so these are agreement figures, not accuracy.
- **Turned-head floor** (author 2026-10-17, from the pose proof where turned and looking-up heads read 0.26-0.5 while still looking right): 183 of 1,607 results qualify. Re-run on the real store: that character 52 -> 39 of 244 flagged (21% -> 16%); its Klein edit + pose-control results 40 -> 29 of 136 (29% -> 21%; Klein edit alone 26%, pose control 8%); all single-character results 14.5% -> 10.3%. The strict floor still flags 18% of her non-turn results: that is real drift, not head turns.
- **Blur** (no ground truth): threshold 40 flags 3 of 1,357 pictures as soft (2 truly soft uploaded photos, 1 plain wood texture: one false positive of 3). Synthetic blur on 40 clean pictures: sigma 3 flagged 40/40, sigma 1.5 flagged 18/40, none of the originals.
- **Noise it cannot see:** random noise (sigma 10) added to clean pictures reads 9.3 (max 10.9), under every rule. Only the structured crunch of the bad Qwen runs (17-20) is caught.
- **Duplicates:** a JPEG-60 copy, a half-size copy and a blur of 1.5 are found 40/40; 1 of 780 unrelated pairs passes. A pose or expression edit of one source is deliberately not caught.
- **Videos:** 246 clips, 0 unreadable, 0 black-frame; the thresholds are library percentiles (about the top 1%), with no labelled bad clip, so video findings are Notes.
- **Speed:** a first full sweep on a busy shared box, 3 workers at low priority, face on: 602 s (52 s to read 102,599 job files, 112 s to measure 1,529 files, 437 s for 460 faces). A rescan reads only changed job files and measures only new files.

## Queue reroll
A deliberate click per picture. It calls the ordinary retry path (`server._studio_retry`) with `variation: true`: the original job's entry, prompt (the enhanced prompt it used), settings and re-validated references, a **new random seed** (never 4242 for Qwen), the text guard, the output guard, the grain gate and the VRAM rules all run again. A job with several takes is re-run as **one** take (`takes: 1`, a small addition to the retry route). Pressing again on the same picture asks first (the first reroll is remembered). The original is untouched.
**After a reroll** the sweep watches the new job: when it finishes it measures the new picture (the same checks as a sweep: failure, blur, grain against the same input, seed, face drift; CPU, low priority, it waits while the box is busy), and the card shows **before / after**: a thumbnail of the new picture, the numbers next to the old ones ("grain 6.1 (was 17.5)"), and cleaner / same / worse. It is shown as **pending your look** until you press Mark OK or Hide on the card: **the sweep never marks anything OK for you.** A failed re-render is reported on the card. The watcher exists only for rerolls you queued (it also resumes when you open the page after a restart); anatomy and near-duplicates are left to the next sweep.
Not offered: files with no job record, character sheet shots (their retry keeps the locked seed), post exports, and audio / 3D results. A pose-set picture is rerolled as a plain job: the pose-set run's own record is not updated.

## Index and safety
- Index: `a local folder` (override `COMFY_QSWEEP_STATE`), the only thing the sweep writes. Job files are re-read only when their size or mtime changed; files are measured only when new or changed, keyed by content hash (a copy reuses the numbers); verdicts (OK / Hide / the reroll record) belong to the file content they judged.
- One sweep at a time: an in-process lock plus a `flock` on the state dir (a second start answers 409). Workers default to 2 (max 4), run at low priority, and wait while the load average is over 85% of the cores.
- A studio restart leaves a running sweep `interrupted`; nothing resumes it except the Resume press. There is no boot hook.
- Files with no job record (`outputs/moe_*`, off by default) have no seed, input or reroll; hard links of recorded files are not counted as orphans.

## Known limits
- A flag is a suggestion. Hits on style choices happen (a wood texture reads soft; a film-grain look reads grainy). "Mark OK" is for those.
- A picture with no flag is not proven good: every check lists what it cannot see.
- The face check needs the ComfyUI venv (`COMFY_FACE_PYTHON`, insightface on the CPU) and a saved `head_front`; if it cannot run the sweep says so and records no pass. Anatomy is slower (a pose model) and off by default.
- A turned head is only known from the record (pose-set run, sheet role, the instruction): a head turn it does not mention is judged strictly.
- Thresholds were set on one box's files and one model generation: re-run `scripts/qsweep_calibrate.py` after a model, sampler or LoRA change.

## Evidence
- Code and tests: `tests/studio/test_qsweep.py` (generated clean / grainy / blurry / duplicate / black / broken pictures, tiny ffmpeg clips, seed-4242 job records, incremental index, one-at-a-time, pause / resume / cancel, never auto-started, mark / hide, reroll through a fake retry), `tests/chatbox/test_qsweep_routes.py` (the routes and the real retry route with a fake runner), `tests/chatbox/js/qsweep_helpers.test.mjs`.
- Research behind the grain rule: the earlier studio's grain.py and `seeds.py` (the 2026-10-17 seed sweep: 20 seeds, 60 files).
- Readiness: `finish.quality_sweep` / route `qsweep_cpu` (recipe).
