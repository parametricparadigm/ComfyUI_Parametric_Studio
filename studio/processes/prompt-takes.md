# Prompt takes

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


## Purpose / when to use it
The enhancer writes the same idea N different ways (N = 2-4) and every take renders with the same seed, so the
differences you see come from the prompt alone. Use it to find which wording a model responds to before you commit to
one, or to get a spread of looks (literal, cinematic, stylised, unusual angle) from a single idea in one click.

It is not the same as:
- **✦ Variations** (card action): the same prompt again with a new seed. Differences come from the seed.
- **Creative take** (`creative_take` chip on Wan entries): the same prompt and seed, rendered with and without the
  concept LoRAs. Differences come from the LoRA.
- The **takes** chip on some image entries: N images of one prompt in one job, consecutive seeds.

## Step-by-step in the studio UI
1. Pick an Image/Video/Music/3D entry and leave **✨ enhance** on. The selector is disabled while enhance is off.
2. Set **Prompt takes: 2, 3 or 4** (default 1, which is the normal single job).
3. Type the idea. The button counts the renders one click will queue when that is more than one: "Generate · 3
   renders" for 3 takes, "Generate · 8 renders" for 4 takes with creative take on (and a LoRA to drop). Press it. The feed shows one set ("Prompt takes · N ways of the same prompt · seed S")
   with one card per take. Each card says which take it is ("Take 2/3 · Cinematic") and shows its final prompt open.
4. Like a result? Use that card's **↺ Remix** (puts its final prompt in the composer) or **✦ Variations** (that
   prompt, new seed). A Retry/Variations of a take keeps its direction label but is a single card, not a new set.

Takes use the directions in this order (2 takes = the first two):

| # | Direction | Lane (what only this take may use) | Kept out |
|---|---|---|---|
| 1 | Faithful | Your words, clarified, plus literal detail they already imply and what the model needs | Any style, medium, mood, palette, camera, lens, lighting or composition you did not write |
| 2 | Cinematic | Camera and light only: format, lens mm, aperture/depth of field, shot size, camera height and movement, key/fill/practicals, contrast, colour temperature | Art medium, painting/illustration words, named palette |
| 3 | Artistic | ONE named art medium or style, a 3-4 colour named palette, texture and mood | Every camera/photo word: film, still, lens, mm, depth of field, bokeh, shot, cinematic, photo |
| 4 | Unexpected angle | ONE unusual viewpoint or framing; a different time of day or weather only if you named none | Camera specs, art medium, named palette |

Each take is also told the other takes' lanes and "do not reuse their vocabulary or ideas here", so the takes differ
in kind, not just in wording. The list lives in one constant, `prompt_takes.DIRECTIONS` (`text` and `lane` per
direction); change the wording there, nothing else needs editing.

## How it works
- The request carries `prompt_takes: N` (only when N > 1 and enhance is on; a single take sends exactly what it
  always did). The server clamps it to 1..4; anything that is not a whole number counts as 1.
- With N > 1 and an enhanced entry, the server makes N copies of the same job (prompt, refs, fields, settings, enhance
  flag). If no seed was given it picks one and gives it to every take. Each copy carries
  `take = {take_id, index, of, direction, label}` and the N jobs are queued in one locked step, so they sit next to
  each other in the queue and render back to back on the same port.
- Each take is enhanced on its own: one enhancer call per take, the same JSON reply contract and model rules as a
  single take, plus a fenced `TAKE_DIRECTION` block appended after the model rules. That block is labelled as data:
  it may change how the take is worded, never the subject, named people, trigger words, rules or reply format. The
  direction text is looked up by key from the constant; it never comes from the request or the stored job.
- A take whose enhancement fails (enhancer down, bad JSON, refusal) renders your prompt as written and its card says
  "<Direction> take not enhanced…". The other takes carry on.
- With **creative take** on as well, each take gets its own LoRA / no-LoRA pair (2 × N renders). The creative half
  renders its take's final prompt.
- **Warm model across a set (Wan only).** When the next take of the set is queued on the same entry, a Wan take
  renders with `keep_warm` (no after-job `/free` on  a local port), and the next take runs right after it, ahead of the rest
  mechanism (`wan_tools.wan22_generate(keep_warm=, warm=)`), so pairs and takes chain through one warm port. The chain
  stops at the last take, or at the first take that does not end "done" (guard refusal, output withheld, render
  failure, cancel, VRAM wait), and the port is then released (`runners.release`, an idle-only free). The warm VRAM
  check still keeps the 4 GiB headroom (`video_edit_tools.HEADROOM_GIB`) and falls back to the normal check when the
  resident experts are not enough.
- Other engines run each take cold, as separate jobs do: ckpt/img (`E._free_if_idle` after every render) and H3
  would be counted as used and reclaimed (or refused) by the next take's check; Adding
  them means a warm-aware preflight per tool first (`runners.WARM_ENGINES` is the switch).

## Guards and gates
Every take is an ordinary job. Nothing is checked once on behalf of the whole set:
- The text guard (`character_policy`) runs on the request at submit, then on EACH take's final enhanced prompt in the
  JobStore before it renders. If one direction's rewrite trips the guard, only that take fails; the others render.
- The speedups never-wire guard runs on each take's graph as it is queued.
- Each take takes the GPU lock and the cross-session GPU turn on its own, and goes through the runner's VRAM preflight
  and big-model lock.

## Time and VRAM
- Time ≈ N × one render, plus roughly 2-4 s of enhancement per take (Muse Glimmer at reasoning "low"; one call per
  take, run just before that take renders).
- Wan sets stay warm between takes (above): one model load per set instead of one per take (the Wan baseline is
  36 s warm vs 165 s cold per clip, wan_tools docstring). Other engines reload per take as separate jobs would.
- VRAM is the same as one render: the takes run one after another, never at the same time.
- With creative take on, double it (2 × N renders).

## Known pitfalls / failure modes
- Prompt takes only apply to entries that are enhanced. Edits, upscales, character sheets and prompt-less Redux
  variations render one job, and the composer shows the note "prompt takes need ✨ enhance on…".
- If the enhancer is down, every take falls back to your raw prompt, so you get N identical renders (same prompt,
  same seed). Each card says it was not enhanced. Check the enhancer before a big set.
- A queue_when_free take that waits for VRAM goes to the back of the queue like any job, so in a busy queue the order
  of a set can change. Each take still renders in full.
- One take refused by the guard is not an error in the others. Read the failed card's reason.
- The faithful take can look almost the same as your single-take enhanced prompt. That is on purpose: it is the
  baseline for comparing the others.

- Tests that run the enhancer must join their JobStore before their patches are undone. The first route tests did
  not: worker threads outlived the test and ran the REAL enhancer, and its readiness check got the conductor to start
  muse-glimmer on the shared GPU. `tests/_live_guards.py` (autouse in tests/studio and tests/chatbox) now blocks and fails any test that touches :8088,
   a local port or  a local port, starts a model or runs `systemctl --user start/restart`; the route fixture joins its store at teardown.

## Evidence
- Tests: `tests/studio/test_prompt_takes.py` (clamp, directions, the fenced block, a single take's system prompt
  unchanged byte for byte, per-take fallback), `tests/chatbox/test_prompt_takes_routes.py` (N jobs with one seed and
  distinct directions, back-to-back queueing, each take guarded on its own final prompt, one failed take, takes = 1
  identical to today, creative pairs per take, retry), `tests/chatbox/js/takes.test.mjs` (payload, feed grouping).
- Live measurement 1, 2026-10-11, muse-glimmer-30b-gguf on :8088 (it was up, but it had been started at about 02:44 by a leak in this branch's own route tests, since fixed: see Known pitfalls), krea2 image idea "a woman in a
  yellow raincoat walks her dog through a rainy city street at night": one call per take took 2.6 s / 4.0 s / 3.9 s
  (faithful / cinematic / artistic; 10.5 s for 3 takes). One call returning all 3 prompts took 4.9 s (545 completion
  tokens) but needs a different JSON shape, a higher token cap than the 900-token single-take cap (an H3 video take
  alone uses about 507), and per-prompt validation and H3 build. One call per take was kept: it reuses the single-take
  contract unchanged, and the ~5 s it costs per set is small next to N renders.
- Live measurement 2 (direction steering before / after the lanes), same day, same model. Overlap of the words each
  take ADDED to the idea (Jaccard, lower = more different): raincoat idea before faithful~cinematic 0.10,
  faithful~artistic 0.14, cinematic~artistic 0.26; after 0.00 / 0.00 / 0.14. Fisherman idea before 0.13 / 0.11 /
  0.34; after faithful~cinematic 0.00 (the artistic take of that run did not come back: the enhancer service was
  stopped by its manager mid-run). Before, the artistic takes said "cinematic film still" and "shallow depth of
  field"; after, the artistic take was a gouache illustration with a named palette and no camera words, and the
  cinematic take only camera and light. After, the faithful take came back as the user's words verbatim; its text
  was then loosened to allow literal implied detail (not re-measured: the enhancer was down).
