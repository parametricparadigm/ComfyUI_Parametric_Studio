# Wan creative take

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


## Purpose / when to use it
- One Generate gives two cards side by side: the LoRA render and the same render with every concept/style/character LoRA
  removed (seed, accelerators, steps, size and prompt identical).
- Use it for ideation, for narrow template LoRAs whose action your prompt already describes, and for style LoRAs that may
  do nothing on a photo start still. author verdict: LoRAs help, the no-LoRA takes are looser and fun; keep both.
- Do not rely on the creative take alone for camera, gesture or SVI work.

## Step-by-step in the studio UI
1. Video tab → `Wan 2.2 · Image → video …` or `… Text → video …`.
2. Add at least one concept LoRA with the 🎛 LoRAs picker. (The `lora` preset chip only offers `none` today: the preset
   registry is empty, so a LoRA-library pick is the only way to get a pair.)
3. Set `creative_take` to `true`. Fill the slots/prompt as for `video-wan22-i2v-t2v.md`. Generate.
4. Two cards appear, folded together with a note naming what was removed and kept. The creative card renders right after
   the LoRA card on the same port.
5. ✦ Variations / Retry on the creative card = that creative take alone with a new seed; on the LoRA card = a new pair.

## Optimal settings
| Setting | Value | Source |
|---|---|---|
| Everything except LoRAs | identical to the LoRA half (base, accelerators, 4 steps, CFG 1, shift 5, size, 81 f, seed, prompt incl. trigger words) | CREATIVE_TAKE.md table |
| Removed | concept LoRAs = any LoRA under `loras/wan/` not listed as an accelerator in `a local folder` or under `loras/wan/accel/`; unknown LoRAs are removed too and listed | CREATIVE_TAKE.md "Classification" |
| Default | off; `COMFY_STUDIO_CREATIVE_TAKE=1` in the chatbox env makes it on by default | `catalog.creative_take_default` |
| When it is worse | gesture/effect LoRAs (middle finger, slap, hip shake, big splash), camera LoRAs (camera rotation, rack focus, orbit, long lens, handheld), SVI chaining, trained motion (walking, dancing) | same |

## Prompting rules
- Write for the LoRA half (trigger words as trained, the LoRA's intended scene). The creative half reuses that exact final
  prompt, trigger words included, with no second rewrite.
- Camera-LoRA rule still applies: no "static camera" in a prompt that drives a camera-move LoRA
  (`audits/LORA_PROMPT_AUDIT_2026-10-11.md`).
- Rules pages: same as `video-wan22-i2v-t2v.md`.

## Guards and gates
  `guards-text-and-output.md`.
- An unremovable LoRA node refuses the take (`pair.creative_take = "refused"`); accelerator-only renders are not paired
  (`"skipped"`). The LoRA job still runs alone in both cases.

## Time and VRAM
- Port  a local port. The LoRA half skips its `/free` so both experts stay warm; the creative half needs only ≥ 8 GiB on top of
  what  a local port holds, else falls back to the normal 64 GiB + 4 check. Expect roughly 2 × the single-clip time
  (~21-24 s warm each, BEST_OPTIONS wan.md); not separately measured as a pair.

## Known pitfalls / failure modes
- No pair appears with the `lora` chip alone: it only has `none`. Use the picker.
- Cancelling the creative half releases  a local port via a hook; cancelling the LoRA half while it waits for VRAM also holds back
  the creative half (it never overtakes).
- Unknown LoRAs (speed-named files missing from the accelerator map) are stripped as concepts; add real accelerators to
  the map if that is wrong.

## Evidence
- Tests: `tests/studio/test_creative_take.py`, `tests/studio/test_creative_pairs.py`, `tests/chatbox/test_creative_take_routes.py`;
  `scripts/chatbox/wan_creative_check.py` 8/8 valid vs  a local port (2026-10-10). No pair has been rendered live in these reports.
