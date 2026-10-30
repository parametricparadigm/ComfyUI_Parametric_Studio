# Character batch

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Untested.


## Purpose / when to use it
"up to 10 characters with full sheets in a batch". Each character ends up in the library, usable at once, with its own status.

## Step-by-step in the studio UI
1. **Character** page, shelf bar: press **👥 Batch**.
2. Shared settings: **Sheet model** (Klein 9B anchor + Qwen 2.1 edits, default; or Qwen 2.1 for both), **Candidates** (2 default), **Shared outfit** (empty = the standard
   default "a plain fitted black t-shirt and blue jeans").
   An empty row outfit uses the shared outfit; an empty shared outfit uses the standard default.
   Optional helpers that only fill rows (you can still edit them): the **persona** picker (the ready-made personas under
   the single path uses) and the **paste area** (several PROFILE.md blocks, one description per line, or `name | description | outfit`).
4. **Explore looks first** is OFF for a batch. If you tick it you choose which explore-looks models run (default: only the one that matches the sheet model),
   the pictures per model, and the form shows models x pictures x rows = total pictures before anything starts (warning above 40, refused above 120).
5. **Check the plan**: every row accepted or refused with its reasons, the number of pictures, the estimated minutes, the stages. **Start the batch** is enabled only when the plan can start.
6. Watch the rows: `queued` -> `anchor` -> `edits n/9` -> `checking` -> `ready` / `unverified` / `withheld` / `failed` (a refused row says why and is skipped). **Cancel batch**,
   **Resume** (after a restart, cancel or failure) and **Retry failed rows** are under the table.

## What is saved, and what is not started
A row's character is **saved in the character library** the moment its sheet job starts, and takes its final status when the sheet finishes (ready, unverified, withheld, failed).
A ready or unverified one is usable at once (👤 picker, **Use**). The batch starts **nothing else**: no voice design, no Signature 10, no outfit sheets, no hair or nails. Those are made by hand from the shelf later.

## How it is built (the seam)
Every sheet is an ordinary `character` studio job whose runner is `characters.build_sheet`, so the text guard, the age/face checks, the output guard, the VRAM wait
(`queue_when_free`), cancel and the guard's auto-reroll are the single path's own. The batch is a coordinator thread plus one JSON file per run.

**Staged (the model-swap saving).** `klein_generate` and `qwen21_generate` name their files by a hash of (prompt, size, seed), and return "reused" without touching the GPU when the files exist.
So:
1. **Anchors job** (one studio job): renders every row's anchor candidates back to back through the sheet's own anchor tool with the new `free_after=False` (one Klein 9B load, or one Qwen 2.1 load), then frees once (Klein only; for a Qwen sheet the model stays loaded for the edits).
2. **Sheet jobs**, one per row, one after another: each calls `build_sheet` unchanged; its anchor step is a cache hit (the same prompt, seed and takes: `character_batch.sheet_args` computes them the way `build_sheet` does and a test pins the equality), so it goes straight to the 9 Qwen 2.1 edits.
   All but the last sheet job carry `keep_loaded`, so the edit model is freed once at the end, not after every sheet. The face scoring and the output guard run per sheet as before.
3. If the anchors job fails or is cancelled, each sheet renders its own anchor as it always did. Only the saving is lost (the run says so in its notes).

**Saving (an estimate).** Sequential, a sheet loads the anchor model and then Qwen for its edits: 2 loads per sheet. Staged: 2 loads for the whole batch (1 for a Qwen sheet).
At an assumed 30 s (Klein) and 45 s (Qwen) per cold load, a batch of 10 saves about 9 x 75 s = 11 min of about 42 min (that is about 30 min staged). The load times are **guesses**; the first proof run's job timings (`load_s`) replace them.
The face scoring (CPU) is not staged: it happens inside each sheet, as in the single path.

**Not saved.** With **explore looks** on there is no staging: the anchor is the look you pick, so each sheet is built through the normal pick path (Looks panel, "Build sheet from this look") when you pick it. Explore runs **one row at a time**
(row 1's models, then row 2's, ...), never all rows x all models at once; the batch finishes its part when every row's looks are rendered, and the rows then follow their characters' status. Other sheet models (the generated-anchor builders) are not offered in a batch.

## Guards (unchanged)
Each row goes through exactly the single create path's checks (`characters.parse_profile` + `profile_problems`: the text guard over the name, description and outfit and over the exact prompts the model reads;
Checks per sheet are the single path's: ArcFace weak shots (under 0.5) are kept and flagged, a face under 20 is flagged, an unverified sheet (scorer down) and a withheld one are flagged. A flagged row shows **needs review** and stays in the library with its status; it never blocks the others.

## Names
The character store allows two characters with one name (their ids differ), but lookups by name pick the newest. So a name repeated **inside the batch** is saved as "Mara 2", "Mara 3" (shown in the plan); a name that already exists in the library is only warned about.

## Resume, cancel, retry
- State: `<guard state>/character_batches/runs/cb<12 hex>.json` (override `COMFY_CHARBATCH_STATE`), written after every step.
- A run marked running with no live thread and no update for 20 s is **interrupted** (a restart); its in-flight rows go back to the queue. At boot (`server._charbatch_boot`, 30 s after the sockets are up) every interrupted batch the author did not cancel resumes: finished rows are not redone, an unfinished sheet gets a new job for the same character (finished takes are reused).
- **Cancel** stops the current job, marks queued rows cancelled, frees an idle port; a cancelled batch is never resumed at boot (the Resume button still works). **Retry failed rows** re-queues `failed` and `withheld` rows only. One batch runs at a time (a second start answers 409).

## Estimates in the plan view

## API
`GET /api/studio/characterbatch/config | personas | runs?session_id= | runs/{id}?session_id=`; `POST .../parse {text}`, `.../persona {handle}`, `.../plan`, `.../start`, `.../runs/{id}/cancel | resume | retry`.
Plan/start body: `{session_id, rows: [{name, description, outfit}], outfit, sheet_model, candidates, explore, explore_models, explore_count}`.

## Known limits / decisions for the author
- Not rendered end to end as a batch yet; see the proof plan below. The model-load saving is a guess until then.
- No age and no real-person rule is enforced beyond the single path (see Guards).
- The batch is built for the two simple sheet models. A sheet on a generated-anchor builder is not in the batch form.
- Persona rows use only the base prompt block (not the profile's negative), as the request said.

## GPU proof plan (do not run without the author's OK)
Goal: prove a 3-row batch end to end, and measure the real model-load saving.
- **Setup**: Studio on  a local port with no other studio GPU job queued; `vram_status` before: at least 45 GB free on the 96 GB card (Qwen 2.1 bf16 holds about 33-36 GB, Klein 9B about 28 GB peak; the floor of 4 GB free must hold throughout, watch `vram-floor-watch`). Claim the VRAM with the `vram claim` tool for the run and release it after.
- **Expected**: anchors job about 1 min (6 pictures, one Klein load); then three sheets of about 4 min each; the whole batch about **10-13 minutes** including the CPU face checks. Per row: `queued` -> `anchor` -> `edits 1/9..9/9` -> `checking` -> `ready`.
- **Measure**: from the job records (`timings.load_s`, `render_s`) of the anchors job and the three sheet jobs: the real cold-load seconds of Klein and Qwen, whether the second and third sheets show a near-zero `load_s`, the batch's wall time against 3 x 250 s = 12.5 min; peak VRAM during the anchors job and the edits (`nvidia-smi` samples) and that free VRAM stayed above 4 GB.
- **Judge** (by eye, on the contact sheets in the shelf): each sheet's face stays the same person across its 10 shots (consistency about 0.7 or above; weak shots flagged only on side views), the outfit matches (the row outfit on row 3, the standard default on rows 1-2), no sheet withheld; the three characters are clearly different people; the anchor of each sheet is the one the anchors job rendered (same seed in the shelf's candidates list).
- **Also check**: Cancel during sheet 2 leaves sheet 1 ready, marks the rest cancelled and frees the card; (after an approved studio restart, never during the proof) the run resumes and finishes sheet 3 only.
- **Then**: record the measured loads in `character_batch.LOAD_S`, set the readiness entry `character.batch` to verified or load-tested with the author's verdict.
