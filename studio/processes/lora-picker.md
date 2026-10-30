# LoRA picker

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


## Purpose / when to use it
Add up to 3 LoRAs from the box library (every LoRA has a usage page) to a render, at the recommended strength, with the
right loader and the trained trigger words. Use it for camera moves, gestures, styles and characters the base model cannot
do from a prompt alone.

## Step-by-step in the studio UI
1. Pick a generator that shows the **🎛 LoRAs** row (list above, plus `h3:cinematic` and `h3:ugc`: one H3 add-on, see
   `video-h3-modes.md`). The other H3 entries, Krea 2, Klein, Ideogram, HiDream, the unavailable former dfserve entries and
   SD 1.5 / SVDQuant fine-tunes have none.
2. Press **🎛 LoRAs**, search by name, trigger or purpose. Groups: camera, motion, style, detail, character, edit, speed,
3. Press **ⓘ** to read the LoRA's usage page before picking (trigger, strength, DO/DON'T, box test status).
4. **＋** adds it (cap 3). A Wan file brings its high/low partner as one pick.
5. Adjust the slider only if the page says so; **↺** returns to the recommended strength.
6. Keep **add trigger words** ticked; the hint "Prompt sent: …" shows the final prompt.
7. Wan only: the separate **lora** chip lists presets from the pipeline registry; it is empty today, so it shows `none`.

## Optimal settings
| Setting | Value | Source |
|---|---|---|
| Stack | ≤ 3 per model (a Wan pair counts once) | `lora_library.MAX_STACK` |
| Strength | the library's recommended value (slider default) | `strength_spec`; per-LoRA pages |
| Loader | bake (`LoraLoaderModelOnly`) on bf16/fp16 and the Wan fp8 experts; rank ≤ 8 on Wan goes bypass if the expert's bypass slot is free; bypass on nvfp4/int8/fp8/SVDQuant bases; one bypass LoRA per model | lora_library.py; LORA_USAGE_RECIPES §1.1-1.3 |
| Triggers | only the library's `trigger_inject` words are pasted (no alternatives, optional words or templates) | (earlier commit); LORA_PROMPT_AUDIT_2026-10-11 |
| Wan camera / gesture LoRAs | keep the LoRA (creative take is worse for these) | BEST_OPTIONS wan.md "Creative no-LoRA mode" |
| Per-LoRA best strengths | link, do not copy | BEST_OPTIONS images.md §3, wan.md per-LoRA table |

## Prompting rules
- Write the scene the LoRA was trained for. A camera-move LoRA must not be told "static camera" (LORA_PROMPT_AUDIT).
- Triggers at the start for most camera/style LoRAs; some are a phase label in the middle (H3 bullet-time) or a fixed
  sentence (Qwen outpaint, fusion, Klein try-on). The usage page says where (LORA_USAGE_RECIPES §1.4).
- If a LoRA's page offers alternatives (e.g. ORB360_CW vs ORB360_CARDSPIN), only one is injected; type the other yourself.
- Unknown triggers (Jacko, RKO, KennethFal H3 styles) are not invented; those LoRAs inject nothing.

## Guards and gates
- Each pick is re-resolved at submit and at render (known id, compatible family, file on disk, strength finite, gate).
- The text guard reads the prompt **with** the trigger words in front ((earlier commit)).

## Time and VRAM
- A baked LoRA adds patch time and workspace on the first render; not measured per LoRA in the studio.
- Wan: `/free` between strength changes; without it, patched weights stayed resident and rows hit 87-88 GB (wan.md I2V
  VRAM note). The studio frees  a local port after each Wan job except the LoRA half of a creative-take pair.

## H3 verdicts and usage notes (2026-10-14)
- `lora_library.h3_tested()` = the hardcoded `H3_TESTED` three merged with the test runner's
  `lora_library.VERDICTS_PATH`). mtime-cached, so a file the runner is still writing works as it grows; missing, malformed or
  junk entries mean just the three (or just the good entries), never an error.
- Per verdict: works / subtle / no visible effect = "tested" with `best_strength` as the default and `safe_range` as the
  hard-capped slider (resolve refuses outside it); `trigger` + `prompt_prefix` lead the prompt like trigger words and
  `prompt_suffix` closes it (`h3_payload`, `rendered_prompt`, so they apply with the enhancer OFF too); `breaks` is hidden from
  the drop-down (the row says "N hidden (test: breaks)"); `skipped` stays "not tested" with the reason.
- Usage notes: `python tools/h3_notes.py [--dry-run] [--diff]` writes a delimited `<!-- studio-usage:start -->` block (what it
  does, strength and range, words, good for / avoid, tips, the two tested prompts, peak VRAM and seconds, the single-seed
  caveat) into each tested LoRA's library page; first change backs the page up to `<name>.md.bak-2026-10-14`. Safe to rerun
  as verdicts arrive. Editing a page makes `build_library.py` write `<name>.md.new` instead of overwriting it.
- Prompt writer: `enhance.enhance_job` -> `lora_context(job)` -> `lora_library.enhancer_notes(picks)` (<= 1500 chars) adds a
  fenced LORA NOTES block to the enhancer's system prompt (what it does, strength, the words the render adds itself, good
  for / avoid, 3 tips, 1 example). The H3 three-section format is unchanged.

## Known pitfalls / failure modes
- H3 (cinematic, ugc only): ONE add-on per render. Turbo v4 and a bypass LoRA share the model's one bypass slot, so a pick
  renders on the verified add-on path instead: nvfp4 Ref2VA + the bypass LoRA at 20 steps, no turbo (~3 min, ~48 GiB planning
  figure). The picker says so under the row, marks each LoRA "tested" (handheld_h3_100, fpv_headbob_h3_50, DetailSlider-V1) or
  "untested here", caps handheld at 1.0, and hides the LoRAs that need their own graph (v2v, keyframe, orbit, remover, distills).
  Two picks are refused; stacking needs a rank-concat file (`lora_retest/rankcat.py`, not wired).
- A second bypass LoRA on the same model is refused (it would silently replace the first).
- "No studio engine yet" families (Klein, Krea 2, Anima, Z-Image, H3, LTX) are greyed even though injection exists.
  only work through the library picker.
- Broken/flagged LoRAs carry ⚠; check the page (e.g. 0 keys bind) before using one.

## Evidence
- Injection validated via `scripts/chatbox/lora_library_check.py` (GET /object_info): 42/42 valid on a local port/a local port/a local port.
