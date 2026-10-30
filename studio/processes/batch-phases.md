# Batch phases

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


Status (2026-10-17): built and unit-tested with fakes; **nothing has been timed on the GPU yet**, so every saving below is an **estimate**. author request: "make stage batching a shared
service and put a Batch phases: on / off / auto (on from 3+ units) option on every maker that has repeated units; start with Music video and Deliverables long-form."
Plan this comes from: [the author's research notes](../research/batching-plan-2026-10-17.md) (section 5, step 1).

Code: `earlier_studio/studio/batch_phases.py` (the helper), `earlier_studio/studio/timings.py` (`batch_summary`, the `batch_*` keys), `static/studio/batch_phases.js` (the shared
select and lines). Tests: `tests/studio/test_batch_phases.py`, `test_musicvideo_batch.py`, `test_deliverables_batch_phases.py`, `tests/chatbox/js/batch_phases.test.mjs`.

## What it is
The 96 GB card cannot hold the writer LLM (about 33 GiB) and the H3 model (46-66 GiB) together, so a maker that writes a prompt per shot swaps writer, H3, writer, H3 for every shot.
With the option **on**, the run is three phases, each model loaded once:

2. **Renders**: the shots render in order; each carries its written prompt (`pre_enhanced`), so its job skips the writer. The prompt guard in the JobStore still reads the final prompt. Before the first render the writer is dropped through the **existing** room logic (`llm_room.make_room_for_render`: idle content LLMs, biggest first, only until the render fits, never the  a local port MoE or a vLLM / llama.cpp unit). No new eviction code was added; the render's own VRAM preflight is still the backstop.
3. **Finishing**: the maker's own join / smooth / upscale / post text, after all renders, exactly as before.

## The option
`batch_phases`: `"auto"` (default, nothing is stored for it) | `"on"` | `"off"`. UI: a **Batch phases** select next to the other options (Music video, Deliverables).
- **auto**: on from 3 units. Music video: 3+ shots. Deliverables: only **long-form** runs (a `*_long` template or a minute or more) with 3+ shots; a short template stays as it was.
- **on**: any run with at least one unit that needs a written prompt. **off**: the old per-shot behaviour.
- Always off when: the build has no prompt-ahead seam, long prompts are off (nothing to write), the Deliverables engine is Wan 2.2 (it writes at its own render), or the run is a Content Studio unit (the package batches across units: `batch_prompts`, which now uses the same `decide` rule with the same answers).
- The plan and the run header say which mode ran and why ("Batch phases: auto, on (auto: 48 shots, on from 3) · about 35 min to 78 min less dead time over 48 shots (estimate, not measured yet)").

## Honest limits (from the plan, unchanged)
- It does **not** make one render faster: an H3 clip is the same 120-260 s of sampling. It removes dead time between renders (writer load and unload, H3 reload).
- The writer time itself stays: 48 shots at about 50 s each is still about 40 min of writing. Only the swaps go.
- It does not fix quality problems (identity drift, anatomy); a bigger batch only makes more bad pictures faster.
- A long unattended batch holds the card, so it keeps the VRAM floor logic, and cancel / resume work between units and survive a restart (the prompts written so far are kept on the run).
- **Estimate**: 45 to 100 s of dead time per unit after the first (the plan's figure for the writer load + H3 reload). For a 48-shot music video that is 47 x 45 to 47 x 100 s = **about 35 to 78 min** [ESTIMATE, not measured]. The same number is on the plan line, labelled estimate, until the protocol below replaces it.

## Failure isolation
A shot whose prompt cannot be written (writer error, refused, no prompt back) is marked **fallback** with a visible note ("shot 7: the prompt was not written ahead (...); its render writes it"), renders the old way (its job writes the prompt at render time) and is not retried by a resume. It never blocks the other shots. A render failure stops the run exactly as the maker's own loop did.

## Music video specifics
- Option `batch_phases` in the request; shown on the plan (`plan.batch`) and the run header (`run.batch`).
- The prompts are written **before the review** (new stage `prepare`, status `preparing`, chip "Writing the shot prompts"), so the review shows them ("Prepared H3 prompt" under each shot). Nothing renders before your OK. Cost of that choice: re-plan throws the written prompts away (a note says so), and the wait before the review is the writing time (about 40 min for 48 shots) instead of a few minutes. Turning the review off, or choosing **off**, removes that wait.
- Editing a shot at review clears that shot's written prompt; it is written again (that shot only) just before the renders. A **reroll** writes a fresh prompt for that shot only (as the old path always did). A try after a failed judgement writes a fresh prompt in its own job; the planned takes of a shot (best of N) share the written prompt (different seeds).
- A resumed shot that failed on its prompt gets a fresh one; one that failed on the GPU / ComfyUI keeps its prompt.
- **Which shots depend on a previous render?** None. A shot's brief uses the neighbouring shots' *planned* prompts, never a render's result, so every shot can be prepared ahead. (Neighbour context is read as planned: an edit at review changes only that shot's own written prompt.) If a future maker has a prompt that depends on the previous render, mark it `needs_prepare = False` and it stays per-shot.
- With the option **off** the run is the old run: the same requests, the same order (a test compares them).

## Deliverables long-form specifics
A thin adapter over the `prepare` stage Content Studio's `batch_prompts` built: options `batch_phases` / `batch` (only stored when chosen or batched), `_after_edits` goes to `prepare` when batched, and the prepare stage, instead of holding for a package's `release()`, drops the writer (existing room logic) and goes straight on to the renders. The review (edit the lines) still comes first; the long prompts are written after your approval, since the lines feed them. A cancelled prompt phase now reads "cancelled" (Resume carries on and writes only the missing prompts).

## How to read the timings
Every run records its stage clock, batched or not.
- **Music video** (`run.batch`): `stage_s` = wall seconds per stage (`prepare`, `shots`, `assemble`; assemble includes the finishing); `timings` (batched only) = `batch_prep_s` (all prompts), `batch_render_s`, `batch_prepared`, `batch_fallbacks`, `batch_writer_loads` (how many prompt calls had to load the writer; expect 1); `job_timings` = the shot jobs' own numbers summed (studio/timings.py: `enhance_s`, `llm_s`, `render_s`, `load_s`, `llm_loads`, `jobs`). In an unbatched run `llm_loads` is about one per shot and `enhance_s` is the writer time inside the jobs.
- **Deliverables** (`run.timings`): `fill_s`, `prep_s`, `render_stage_s` (the whole render stage), `assemble_s`, `finish_s`; batched adds `batch_prep_s`, `batch_render_s`, `batch_prepared`, `batch_fallbacks`, `batch_writer_loads`.
- The run header prints the summary line ("batch phases: prompts 40.0 min, renders 3.1 h, finishing 90 s (47 prepared, writer loaded 1x)").

## Measurement protocol (replaces the estimate)
Run the **same** request twice on a quiet card (same character, song / template, seed, quality, pace; review off so nobody waits):
1. `batch_phases: "off"`, then 2. `batch_phases: "on"`.
Compare, per run:
- **Music video**: `batch.stage_s.shots` (off) against `stage_s.prepare + stage_s.shots` (on). Same render work, so the difference is the dead time. Then `job_timings.llm_loads` (off about one per shot, on 0 in the render jobs plus `batch_writer_loads` 1) and `job_timings.enhance_s`.
- **Deliverables**: `timings.render_stage_s` (off) against `timings.prep_s + timings.render_stage_s` (on).
Report the per-unit saving = (off total - on total) / (units - 1) and replace `SAVING_PER_UNIT_S` in `batch_phases.py` with the measured range. Check also that identity scores and the flagged-shot count did not move (batching must not change quality). Until two such runs exist, the 35-78 min figure is an estimate.

## Proven vs only wired
