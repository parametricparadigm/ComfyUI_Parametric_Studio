# FLUX.3 Klein

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested here.


## What it is
FLUX.3 Image Klein (5.6B, Black Forest Labs, released 2026-10-15): text to image and multi-reference editing. Until 2026-10-19 the live patched core could not load it (the architecture arrived in ComfyUI v0.41.x), so the studio attached it as a lane (`model-lanes.md`): the vanilla v0.41.2 tree on  a local port in a transient unit. v0.42.1 is live on  a local port/ a local port/ a local port and `UNETLoader` lists the six `flux3_image_klein_*` files, `CLIPLoader` has type `flux3`, so **FLUX.3 now runs on a normal studio port lane** and the  a local port lane is only the rollback.

## Where it runs and how the port is picked
- The tool reaches ComfyUI only through `video_edit_tools`' seams, so everything (`/prompt`, `/history`, `/free`, the staged references) follows the lane's port. The studio's output guard and character binding are unchanged (they run in the JobStore around the runner).
- **Admission** is the usual `ports.fit` inside `video_edit_tools._lane_admit`: the estimate below + the 4 GiB floor must fit in free VRAM + what the job's own port already holds + minus other studio reservations; a vram-mcp reservation is written while the job runs. Short = the job waits (VramBusy), nothing is evicted for it.
- **One FLUX.3 checkpoint resident per port**: when the last checkpoint this process left on the port differs from the one wanted, it is freed first (idle port only). After the job the model is freed through the existing idle-free rule (`_free_if_idle`: queue empty, no other claim on the port), and the free is confirmed once (the first live run once left the model loaded after the /free; a second /free took it). A character sheet keeps the model between shots (`free_after=False`) and the sheet job frees the port once at the end.

## VRAM estimates (GiB, the process's own peak; the planner adds the 4 GiB floor)
Derived from the 2026-10-17 lane trial (lane process 19.6-22.0 GiB at bf16, 20.9 with three references, 14.3 at nvfp4) plus about 10 % margin; the Qwen3-VL-4B bf16 text encoder (8.9 GiB) is in every figure. int8 is inferred (nvfp4 + the 2.3 GiB the int8 file adds), never measured alone. Code: `image_flux3_tools.LIVE_PEAK_GIB`, `peak_gib()`.

| Precision | Distilled t2i, 1 MP | Base t2i, 1 MP (CFG 3.5, +1.5 for the second pass) |
|---|---|---|
| bf16 | 24.0 | 25.5 |
| int8 | 19.0 | 20.5 |
| nvfp4 | 16.0 | 17.5 |

Edit: the same base figure (distilled by default) + 0.75 GiB per reference per megapixel of reference size (chip 0.5 / 1 / 2 MP) + 1.5 GiB per megapixel of output above 1 MP. Examples: 1 reference at 1 MP = 24.8, 2 references at 2 MP = 28.5, 4 references at 2 MP (distilled bf16) = 31.5. Text to image above about 1.1 MP adds 1.5 GiB per extra megapixel.

## Rollback
`COMFY_FLUX3_LANE=on` in the studio server's environment restores the earlier behaviour exactly: FLUX.3 is an exclusive engine again, renders on the separate  a local port lane (vanilla v0.41.2 tree, transient unit `comfyui-lane-flux3-a local port`, started and stopped around each job only with `COMFY_STUDIO_SIDECAR_AUTOSTART=1`), with the earlier 26 / 20 / 20 GiB estimates, and the catalogue offers it only when the lane's tree, launcher and files are there. Read per call, so a studio restart with the variable set is all it takes. Unset or anything else = the live ports. The trial scripts (`scripts/flux3_edit_trial.py`, `scripts/negative_ab.py`, `scripts/sheet_engine_ab.py --flux3`) were written for the lane: set `COMFY_FLUX3_LANE=on` to run them as before. No FLUX.3 path starts, probes or waits for  a local port unless this switch is on (regression test `test_default_runs_on_the_current_ports_seams_and_never_touches_the_local_lane`).

## Checking the graphs against a live port
`.venv/bin/python scripts/lanes/validate_flux3_graphs.py --port a local port` does read-only GETs (`/system_stats`, `/object_info/<class>`) and compares the t2i (distilled, base) and edit (2 refs) graphs with the port's node definitions: classes, input names including the V3 dynamic ones (`resolution.megapixels`, `images.imageN`), required inputs, listed model files, the `flux3` CLIP type, number ranges. 2026-10-19: all three graphs OK against  a local port and  a local port (v0.42.1), no builder change was needed. Without `--port` it still runs the offline validator on a ComfyUI tree.

## Entries
| Entry | What | Proven |
|---|---|---|
| `flux3:distilled` | text to image, 16 steps, CFG 1, euler/simple | the graph rendered 10/10 long captions in the trial (bf16 3.1-4.1 s warm, 12 s cold; NVFP4 about 2x faster); the studio path is not run yet |
| `flux3:base` | the undistilled checkpoint, 25 or 50 steps, CFG 3.5 (empty-text negative) | wired from the model card, not rendered |
| `flux3:edit` | 1-4 references (`image`, `image_2..4`) through `Set Reference Multi Latent`, addressed as `<ref_image_0>` ... | the graph passes ComfyUI v0.41.2's own prompt validator offline (`scripts/lanes/validate_flux3_graphs.py`) and **rendered 15 studio jobs on 2026-10-17 (load-tested / trial results, see Trial 2026-10-17)** |
Chips: aspect (t2i), takes 1-4, precision (`bf16` reference, `nvfp4` fastest, `int8` ComfyUI's default), steps, edit detail (reference size 0.5 / 1 / 2 MP). Not wired: the layout-box nodes (`Create Bounding Boxes`, `FLUX.3 Layout Prompt`), which need a box-drawing UI.

## The prompt (the part BFL says matters)
BFL: do not use Klein without its prompt upsampler; it is trained on the captions the upsampler writes. The upsampler is a 9B LLM (~28 GB) that is not downloaded. BFL publishes its system prompts, which the studio uses verbatim to brief its own local writer (`data/flux3_system_prompts.json`, source URL inside): t2i = one detailed self-contained caption of 100-350 words (medium first, frame-relative layout, observable people, quoted text verbatim); i2i = an instruction or a generation request that names what to take from each reference by number. The writer **cannot see** edit references (BFL's upsampler can): it is told so and keeps your `<ref_image_N>` tokens.

## Files (identify by size or header, not name: BFL may flip the naming)
Unsuffixed `flux3_image_klein_*` = **Base**; `_sd_` = **Distilled** (the `ref_time_in` tensors). Text encoder `qwen3vl_4b_bf16` (CLIPLoader type `flux3`), FLUX.2 VAE. The six checkpoints are symlinks into `a local folder` (via `a local folder`): move them into the model store before cleaning Downloads.

## Using it
1. Image page → FLUX.3 Klein card (or the Edit page for `flux3:edit`). Nothing to start: it uses a live port. The entries are listed when the model store has `text_encoders/qwen/qwen3vl_4b_bf16.safetensors` and `diffusion_models/flux3-klein/flux3_image_klein_sd_bf16.safetensors`.
2. Port chip: Auto, or  a local port /  a local port /  a local port (the sidecar is greyed out for FLUX.3).
3. The job waits rather than evicting when the card is short of room (4 GB floor) or its port is busy; the first load of a checkpoint reads it from disk (about 20 s all in), later ones are faster.

## Licence

## Live proof 2026-10-19 (live port  a local port, v0.42.1; the studio-equivalent path, `scripts/flux3_live_proof.py`)
One job per entry, bf16, 1024 px, seed 7, neutral prompts (a teapot on an oak table; tulips in a glass vase; the edit puts the tulips from the second picture on the table of the first). Run inside `ports.use(a local port)` with the port lock, a vram-mcp reservation and the free-after-job rule, on an idle  a local port (queue empty;  a local port /  a local port idle too; the card had 44.9 GiB free). Card peak is the card's used memory minus its used memory before the job.

| Case | Seconds, all in (load included) | Card peak over baseline | Result |
|---|---|---|---|
| distilled t2i | 23.6 first run (cold files), 11.1 on a second seed | 18.7 GiB | PNG 1024 x 1024, mean 83.6, std 56.8, 2.1 % dark pixels, looked at: sharp, correct teapot, cups, steam, window light |
| base t2i (25 steps, CFG 3.5) | 28.1 | 18.7 GiB | mean 200.0, std 47.5 (bright white wall), looked at: clean tulips in a glass vase |
| edit, 2 references | 19.1 | 18.8 GiB | mean 85.9, std 61.8, looked at: the table, teapot and cups kept, the tulips added in the window light |

Pictures and `results_local.json`: `a local folder`. The estimates above (24 / 25.5 / 24.8) sit about 6 GiB over the measured peaks on purpose (trial max 22, three references and larger sizes grow it). The model was freed after each case (the port read 0.8 GiB, its CUDA context). Once, on the first run, the /free right after the job did not release the model (19.6 GiB stayed); a manual /free did, so the tool now confirms the free and asks once more. The base case ran with `--min-free-after 19` (the planned rule was 20 GiB free after the estimate; the port had 19.4), the 4 GiB floor was never near. This is a load-tested proof (3 jobs), not an author-judged quality verdict.

## Before it becomes the default
FLUX.2 Klein stays the default until this passes a proper A/B (distilled bf16 vs nvfp4 vs int8, base 25/50, with and without the writer), because day-1 reception elsewhere is mixed (eyes, anatomy, multi-reference weakest).

## Trial 2026-10-17 (edit, load-tested / trial results; not author-judged, not "verified"; on the old  a local port lane)
`scripts/flux3_edit_trial.py` drove 15 studio jobs (session `flux3-edit-trial`, raw prompts, seed 7, distilled 16 steps) through `flux3:edit`; the studio started and stopped the lane per job. Full numbers, job ids and sheets: [../research/flux3-edit-trial-2026-10-17.md](../research/flux3-edit-trial-2026-10-17.md), pictures in `a local folder`.
- Works: every job rendered, lane up in about 8 s, 22-33 s per job all in (warm second take bf16 4.3 s, nvfp4 2.8 s), lane process 19.6-22 GiB (nvfp4 14.3 GiB), no grain, hands clean, identity as good as Qwen 2.1 on one-person edits (mean face 0.905 against 0.902 over six poses).
- Better than Qwen 2.1: the saved-outfit swap (it put the real chain-strap dress on; Qwen kept the old neckline). Equal: background change and add-objects edits.
- Worse: 2 of 6 pose changes ignored or misread (Qwen 6 of 6), 3-reference composition went wrong, a consistent warm saturated colour cast and slight retouched skin.
- Precision: nvfp4 looked the same as bf16 at the same seed and is about 1.5x faster warm with about 6 GiB less VRAM (one case).
- Verdict: a plausible edit option, stays non-default; second pick for outfit swap pending a wider garment test, Qwen first for pose sets. Only the author's verdict can mark it verified.
