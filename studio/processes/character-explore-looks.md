# Explore a character's looks

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Untested.


## Purpose / when to use it
Before a sheet is built, render the character's anchor headshot on every usable image model with the same 10 fixed seeds,
then pick the look you want. The picked image becomes the sheet's anchor; the other 9 shots are edits of it. Use it when
the look matters more than time: it is a multi-hour run.

## Step-by-step in the studio UI
1. Character tab: write or paste the profile, fill name/outfit, leave **🔍 explore looks first** ticked.
2. Press **Generate**. A dry-run estimate appears (models, images, minutes, refusals); press OK to start.
3. The Looks panel opens. Results appear per model as each finishes (refreshes every 5 s while running).
4. Filter by family, status, model name, "picks only", "hide unverified".
5. Click an image to make it the **primary**; ☆ marks up to 3 **favourites**.
6. **Build sheet from this look** (starts the sheet job) or **Save pick** (keep the choice, build later).
7. Re-open later with 🔍 on the shelf. **Retry** a failed model; **Cancel run** stops what is queued.

## Optimal settings
| Setting | Value | Source |
|---|---|---|
| Seeds | 10 fixed (`looks.SEEDS`, first 10 of 20) | `looks.DEFAULT_COUNT` |
| Models | every usable t2i model in capability_run `models.json`, main arm (its best settings) | looks.py docstring |
| Excluded | skipped/`skip` entries, models not landed, non-t2i builders (Z-Image Fun CN), Ideogram 4 (filter blocks personas), deleted families (Mage-Flow, PixelDiT, TinyBreaker) | looks.py; the author's build notes "Removals" |
| Big models | one model over 20 GB on the box at a time | `looks.BIG_GB` |
| Keep | unpicked images deleted 7 days after the run | `COMFY_LOOKS_KEEP_DAYS` default 7 |
| Prompt style | per model (prose/tags/mixed, its own prefix and negatives) | models.json via looks.py |

## Prompting rules
- Each model's composed prompt (its fixed prefix included) is re-checked by the text guard; a model whose prefix trips it
  sits out (e.g. `flux1_3d_realistic`: "3D rendering" read as an age, LOCAL_MOE_REFERENCE §15).

## Guards and gates
- Text guard on the profile before anything queues, and on every model's prompt.
- Output guard on **every image, one per call**: a face under 20 deletes that image (counted "removed"); anything withheld
- Explore images are never job artifacts, so they cannot be published; downloads are scrubbed exports.

## Time and VRAM
- Estimate (not measured end to end): **~217 min (3.6 h)** per character for 45 models × 10, excluding GPU waits; formula
  `est_s` + 20 s + 1.6 s/GB load + 8 s/image overhead (includes ~4.6 s CPU face check). Peak ~45 GB (flux2_dev_nvfp4).
- One studio job per model, `queue_when_free` set: a busy GPU means wait, never skip. Small models go first.  a local port is
  `/free`d after each model when idle.

## Known pitfalls / failure modes
- It occupies the single studio worker for hours; other studio jobs queue behind it. Start it when you will not need the
  studio GPU.
- A model that runs out of the job store's 30-min wait budget is re-queued only the next time the run is viewed.
- Never rendered end to end on the GPU in the evidence read here (dry run 450/450 valid). Treat the estimate as rough.
- Ideogram 4 never appears (by design).

## Evidence
- Dry run `scripts/chatbox/looks_check.py`: 45 models × 10 = 450 graphs valid on  a local port (2026-10-10).
- Tests: `tests/studio/test_looks.py`, `tests/chatbox/test_looks_routes.py`, `tests/chatbox/js/looks_helpers.test.mjs`.
