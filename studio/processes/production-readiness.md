# Production readiness

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


Status: built and tested with fakes and against the live catalogue (2026-10-17). **Nothing was rendered for it.** The proof plan below is
prepared, not run.
author request 2026-10-17: "make guaranteed deliverables for all of those as well, do your research and make sure they're all proper
production ready". The repo rule applies: "guaranteed" is a PROOF LEVEL, never a promise. Every seed makes a different picture; what is
repeatable is the setup.

Code: `earlier_studio/studio/readiness.py` (pure CPU: load, validate, report), data `earlier_studio/studio/data/readiness.json`, route
`GET /api/studio/readiness` (read-only, `scripts/chatbox/server.py`), plain list page `static/studio/Readiness.js` + `readiness_helpers.js`
(**not wired into the sidebar**: add `ws === "readiness"` in `app.js` and a rail entry in `modes.js` to show it), proof plan
`scripts/readiness_proof.py`. Research: `the author's research notes`. Plan files:
`the author's research notes` and `.md`.
Tests: `tests/studio/test_readiness.py` (validator on a fake world), `test_readiness_data.py` (the real data against the real catalogue,
templates and evidence files), `test_readiness_proof.py` (plan, refusals, resume, submit, verdicts), `tests/chatbox/test_readiness_routes.py`,
`tests/chatbox/js/readiness_helpers.test.mjs`.

## How to read a proof level

| Level | Meaning |
|---|---|
| verified | rendered AND judged on this box with the model and settings the deliverable uses |
| load-tested | the route loads and renders here without errors; nobody judged this deliverable's output |
| recipe | settings come from a model card / KB / process doc; not run here |
| unproven | no settled route or nothing to cite; the family says what blocks it |

Two more fields keep the level honest:
- **scope**: `family` = the deliverable itself (its templates, prompts, wiring through the studio) was rendered; `route` = only the model route
  it uses was (a bench in the KB); `none` = nothing was.
- **gap**: what is still missing. `none` = verified at family scope. `family` = the route is proven, the deliverable's own prompts and
  wiring never rendered. `route` = the route itself is not proven. A family can never rank above its weakest route (the validator checks).

Example: the Pictures "Mirror selfies" family is `recipe / none / gap family`: Krea 2 Turbo and Qwen 2.1 are verified routes (KB best-options
run), but no picture has been rendered through the Pictures page. That is the truth the registry shows, and exactly what the proof plan fixes.

## What is in the data

- **Routes** (37): a model path with its catalogue entries, settings (with source), CFG and the negative-prompt rule, prompt style, whether the
  Realism chip exists on it (cross-checked with `realism.CHIP_ENTRIES`), the Smart negative kind (cross-checked with `smart_negative.py`), the
  H3 2000-token rule (cross-checked with `h3_techniques.MAX_BUILT_CHARS`), proof level with evidence, GPU seconds per unit (marked
  measured or estimated), peak GiB, cold load, limits, and the fetched research facts (`research`, with URL and date, VERIFIED or UNVERIFIED)
  and where the studio differs (`differs`).
- **Families** (53): every deliverable the studio offers, each with a recommended route list, settings, prompt path (enhancer, negatives,
  Realism), the guards that apply, finishing, proof level, scope, verdict, evidence, the next step (or the blocker) and, for families
  without a template list, `proof_cases` (what the proof plan renders or what you press). Video templates are covered by category, picture
  templates by group, LoRA deliverables by proof level, so a new template that no family claims fails the validator.
- Families: 8 video template families (214 templates), 4 LoRA levels (93 LoRAs), 12 Pictures families (568 templates), 10 designers
  (furniture, mug, T-shirt, hair, nails, cosplay, vehicle, setting, animal, plant), Fashion, Signature 10, character sheet, character voice,
  long video, music video, anime, recreate, fusion, virtual set, four finishing families (smooth + 2x, true 4K, image upscale, Realism),
  two Content Studio families (package, send), video edits and two music families.
- Out of scope (listed in the data): 3D/motion pages, Edit-tab image tools, website/game/world builders.

## Today's numbers (53 families)

| proof / scope | families |
|---|---|
| verified / family | 1: character sheet |
| verified / route | 4: LoRA verified (3 LoRAs), LoRA warned (none today; withheld), Fusion paste, video edits |
| load-tested / family | 3: long video, recreate (GPU smoke 2026-10-12), Music 3 |
| load-tested / route | 3: LoRA load-tested (54), image upscale, Realism option |
| recipe / none | 39: all video template families, 11 of the 12 Pictures families, 10 designers, Fashion, Signature 10, character voice, music video, anime, finishing 2x, Content Studio, song recreate, LoRA recipe-only (36) |

Gap: 2 none, 47 family, 4 route. Routes: 18 verified, 15 load-tested, 2 recipe, 2 unproven.

Read this as: the **model routes are mostly sound**; almost nothing is proven **as a deliverable**. The 3 verified LoRAs were judged outside
the Deliverables page, 54 LoRAs rest on a generic-setup batch the author stopped on 2026-10-16 (so "load-tested" there means loaded, not

## What validation found (real catalogue and templates)

The validator fails the build when the data and the studio disagree. Real findings, now fixed in the data or written down:
- The Pictures page could not offer Ideogram 4 (its title / subtitle fields), so text-heavy art groups (typography, graphic design, maps) had only
  Krea 2, which is exact on short text only. Fixed 2026-10-17: the fields are optional (`image_deliverables.OPTIONAL_FIELD_ENTRIES`), a caption
  writer turns the template's quoted words into Ideogram 4's JSON caption, and the families now recommend Ideogram 4 first at proof level
  "recipe" until a picture is rendered (`image-ideogram-poster.md`). Likewise the SDXL fallback CFG went 6 -> 4 with per-checkpoint author values
  and sources (`image-finetunes-ckpt.md`), and Z-Image base got a `Model negative` chip, OFF by default (`image-zimage.md`).
- HiDream-O1 offers only 3:4 / 1:1 / 4:3; **49 illustration templates need other aspects**, so Krea 2 is the recommended route for that
  group and HiDream the alternate (a rule now enforced for every Pictures family).
- Short (SFW) and Long-form templates contain product shots (`h3:product`); their families now name that route (the check covers every shot
  kind against `deliverables.ENTRY`).
- FLUX.3 Klein and Redux Advanced are listed but unavailable on this box by design; the registry marks FLUX.3 `available_expected: false`.
- The Realism chip list is a moving target (another session is wiring it); drift is reported as a warning, not an error.
- The studio's H3 long mode asks ~2000 tokens while the official Ref2VA guide says `detailed_description` is normally 350-500 words and
  gives no token cap (research doc, difference 1). The registry records it on every H3 route; the A/B is not run.
- Other research differences (Qwen 2.1 official 2K sizes, Turbo checkpoint vs the Turbo LoRA stack, Z-Image base negative, Ideogram JSON
  captions and non-commercial licence, SDXL default CFG 6 vs authors' 3-5, Wan 2.2 T2V LoRA version, Boogu aspects) are in the research doc's
  "Differences worth acting on" list and on the routes' `differs`.

## Running the proof plan (after the author approves GPU time)

`scripts/readiness_proof.py` (repo `.venv` python). It reads the data, and for every family whose gap is not `none` picks 1-2 cases: a real
template of the family (default drop-downs, slot examples filled, the template's first talk/act shot at Draft quality), the LoRA library's
sheet, never a photo-made character), the recommended route's entry and settings.

```
.venv/bin/python scripts/readiness_proof.py plan                      # CPU only: writes the plan files and prints the cost
.venv/bin/python scripts/readiness_proof.py run --approved [--families a,b] [--max-gpu-minutes N] [--wait SECONDS]
.venv/bin/python scripts/readiness_proof.py verdict CASE --result works --ok identity,anatomy,text,artefacts,prompt_adherence --note "..."
.venv/bin/python scripts/readiness_proof.py status
```

- **Gate** (the same as `negative_ab.py` / `realism_ab.py` / `lora_bench.py`): `run` refuses unless nvidia-smi shows at least 24 GB free and
  the queues of  a local port /  a local port /  a local port are empty, and the case's own peak must leave at least 4 GB free. A refusal is recorded in
- It submits through the studio's own `POST /api/studio/generate` (session `readiness-proof`), so the text guard, the enhancer, the character
  binding, the GPU turn and the output guard run exactly as for a composer request, then polls the job. A guard withhold is recorded as a
  result (`withheld`), not retried. Resumable: a case with a `done` or `withheld` row is skipped. Results: `a local folder`.
- **Judging**: open each result, answer the checklist (identity, anatomy, text, artefacts, prompt adherence, guard result; video adds
  lip-sync, motion and audio; designers add exact words and no logos) and record `verdict`. `status` says when every case of a family was
  judged good with every mark ok. Then raise the family in `readiness.json` by hand: add an evidence item of kind `render` or `verdict`
  with `judged: true` pointing at `out:readiness_proof_2026-10-17/results.jsonl`, set `proof` and `scope`, and run `test_readiness_data.py`.
  The proxies in the research doc (VQAScore, OCR exact match) are optional extras for a separate venv, never the final judge.

### What the plan would cost (estimated, not measured end to end)

loads), peak 70 GiB (Virtual Set); 46 cases the script can submit (about 41 minutes), 20 are manual or need an input you supply (a source
video, a finished clip, a garment picture, a saved voice, a World Kit place). By area: LoRA proofs 30 min, recreate 33, finishing 20, edits 16,
10 private cases) adds about 5.5 minutes. About 15% of the cases use an estimated rather than measured seconds-per-unit (`gpu_s_basis`).
It never fits beside a running 50 GB llama.cpp job plus a 70 GiB Virtual Set run: ask before evicting anything.

## Hard rules this respects

No server restart, no pip, no download, no GPU render and no submission to any ComfyUI port by the work that built this; the plan command
reads `nvidia-smi` and the three `/queue` GETs only (as the other A/B scripts do). The tests are hermetic: no live HTTP, no nvidia-smi, no
character store (the script reads the characters database read-only and returns ids only), no mail, no Drive.
