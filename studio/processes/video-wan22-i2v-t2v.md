# Wan 2.2 text or image to video

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


## Purpose / when to use it
- The studio's only Wan path that renders on ComfyUI with LoRAs: short silent clips (5 s, 81 frames @ 16 fps).
- `wan:i2v`: animate a still (motion + camera). `wan:t2v`: a clip from text alone.
- Pick Wan over H3 when you want a Wan motion/camera/effect LoRA (dance, walking, camera rotation, rack focus, splash...),
  or a fast silent preview. Pick H3 when you need audio, speech or identity from references.
- Not for identity-critical character work (Wan holds identity weakly; see `video-wan-animate-svi-dfserve.md`).
- Since 2026-10-17 Deliverables can render whole templates on Wan too (`video_engine: wan22`, Wan LoRA templates): see [wan22-deliverables.md](wan22-deliverables.md).

## Step-by-step in the studio UI
1. Video tab → Generator drop-down → `Wan 2.2 · Image → video (4-step, LoRA presets) ·  a local port` or `… Text → video …`.
   (The old `wan22_*` dfserve entries are hidden; dfserve was retired 2026-10-12.)
2. Aspect chip: `Auto` = 9:16 (480x832). 9:16 and 16:9 are the measured sizes; other ratios render near the same pixel count.
3. Seconds chip: 5 only.
   `"presets": []`). Use the LoRA picker instead.
5. 🎛 LoRAs picker (below the slots): search, ＋ add (max 3; a Wan pair adds high + low together), set strength (slider default
   = the library's recommended value), ⓘ opens the LoRA's usage page. Keep "add trigger words" ticked; the hint line shows
   the exact prompt that will be sent.
6. `creative_take` chip: off by default; on = also render the same clip without the concept LoRAs (see
   `video-wan-creative-take.md`).
7. I2V: drop the start still into the `image` slot (or drag an image card in, or use 🎬 Animate on an image card).
8. Character chip (optional): fills the image slot from a stored character sheet (head shot first; `characters.apply_character` got its `wan22_i2v` branch on
   2026-10-17: before that the studio refused a character on this entry although this page said it worked) and binds the job's guards and face check.
9. Write the prompt; leave ✨ enhance on, or ✨ Preview to see/edit the rewrite first. Generate.
10. Card: Remix, ✦ Variations (new seed; on a LoRA card it makes a new pair), Retry / Queue when free on failure, ⤓ Download clean.

## Optimal settings
| Setting | Value | Source |
|---|---|---|
| Base | Wan 2.2 A14B HIGH + LOW `fp8_e4m3fn_scaled_KJ` (the only copy on the box), `weight_dtype default` | graphs `wan22_*_4s.api.json`; QUANT_BEST_OPTIONS via BEST_OPTIONS wan.md |
| Accelerators (I2V) | `Wan_2_2_I2V_A14B_HIGH_lightx2v_4step_lora_v1030_rank_64_bf16` 1.0 + `wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise` 1.0, baked | graph; = BEST_OPTIONS wan.md I2V winner (medium) |
| Accelerators (T2V) | `wan2.2_t2v_lightx2v_4steps_lora_250928_{high,low}_noise` at **1.0 / 1.0** in the studio | graph. BEST_OPTIONS wan.md T2V winner is **high 1.5** / low 1.0 (sharper, more motion, same time; medium-low) — not wired: the studio runs the runner-up |
| Steps / split | 4 steps, 2 high + 2 low (KSamplerAdvanced) | graph; LORA_USAGE_RECIPES §7.1 |
| CFG / sampler | CFG 1, euler / simple | graph |
| Shift | 5 (ModelSamplingSD3) | graph; WAN22_PROMPTING.md local findings (5 follows camera better, 8 holds detail; 8 not offered) |
| Size | 480x832 (9:16) / 832x480 (16:9); other ratios ~399k px on a 16 grid (21:9 = 848x368) | `aspects.WAN`; aspect check 2026-10-11 rendered 4:5, 2:3, 21:9 fine |
| Frames / fps | 81 @ 16 fps (5 s) | `wan_tools.FRAMES` |
| Text encoder / VAE | umt5_xxl fp8 scaled / `wan/wan_2.1_vae` | graph |
| Negative | empty (CFG 1: a negative has no effect). The Smart negative chip never applies here; `tests/studio/test_persona_negative.py` pins that the distilled graphs carry an empty negative | WAN22_PROMPTING.md §5 |
| LoRA strength | the library page's recommended value (picker default); per-LoRA verdicts in BEST_OPTIONS wan.md "Per-LoRA verdicts" | `a local folder` |
| Loader | bake (LoraLoaderModelOnly) after each expert's accelerator; rank ≤ 8 files go on bypass | `lora_library.py` docstring, LORA_USAGE_RECIPES §1.1-1.3 |
| Seed | 4242 default | `wan_tools.SEED` |

## Decode chip (standard / fast / preview)
`decode`: **standard** (default, the tested graph), **fast** = LightVAE Pro (1.45-1.5x decode, same quality as standard vs the source; finals), **preview** = LightVAE Lite (2.8-3x decode, 1-3.6 dB softer; drafts). Only the decode changes; the encode stays the stock Wan 2.1 VAE. Until  a local port has restarted with the LightVAE pack a fast/preview job renders standard with a card note. Numbers and details: [video-wan-decode.md](video-wan-decode.md).

## Prompting rules
- Per-model rules page (read at call time by the enhancer):
  `a local folder`,
  `a local folder`.
  - I2V = motion + camera only; do not re-describe the person or room. Add an anchor ("her face and the room stay identical").
  - T2V = style first, then shot/light, subject, one or two action beats, ONE camera move with a speed.
  - One main event per 5 s clip; multi-event prompts collapse into walking.
  - Never ask for signs, logos or "space for text" (fake neon text appears).
  - "FPV drone races" draws a drone: write "First-person FPV view, the camera races…".
- LoRAs (author rule, `audits/LORA_PROMPT_AUDIT_2026-10-11.md`): use the trigger words exactly as trained (the picker adds
  only the library's `trigger_inject` words) and describe the scene the LoRA was made for. **Never write "static camera"
  with a camera-move LoRA** (rack focus, orbit, camera rotation, drone, handheld, long lens). Slider/look LoRAs may keep it.
- Max 3 LoRAs; more than three concept LoRAs fight each other (`lora_library.MAX_STACK`).

## Guards and gates
- Output guard samples the clip at 4 fps + scene changes + first/last frame before the card shows it.
- Download clean / publish: scrubbed export; publishing a video runs a TRIBE pre-post check (`publish-download-tribe.md`).

## Time and VRAM
- Port  a local port. Code peak 64 GiB → needs ~68 GiB free (peak + 4). Measured port peaks 63.5-66.2 GB (`nolora` A/B).
- 21-24 s warm per 81-frame clip; first clip after a model change ~130-190 s cold (BEST_OPTIONS wan.md). `wan_tools`
  docstring: 36 s warm / 165 s cold.
- It refuses rather than queues when any ComfyUI port is busy; tick "Queue when free" on a failed card to wait.

## Known pitfalls / failure modes
- Changing LoRA strengths without a `/free` left patched weights resident: 75-79 GB peaks and watchdog kills at 87-88 GB in
  tests (wan.md I2V VRAM note). The tool frees  a local port after each job; don't chain manual ComfyUI work on  a local port in between.
- The three-sampler recipe (2 base steps cfg 3.5 + 2+2) is broken on I2V and refused by the speedups guard.
- Rank-4 LoRAs Bullet Time and Anime Style v2 showed no effect; Orbit v2 orbits but ghosts mid-clip (wan.md).
- I2V start stills that are portrait get letterboxed/cropped to the chosen ratio; pick the ratio of your still.
- Text in video is unreliable; add text in post.
- A T2V-trained LoRA filed under `2.2-i2v` (flagged in LORA_LIBRARY.md) may do nothing on `wan:i2v`.

## Evidence
- Tests: `tests/tools/test_wan_tools.py`, `tests/studio/test_wan_runner.py`.

## Update 2026-10-17: a recipe's own sampler settings, and a warm port in a run
* **Sampler settings per LoRA.** The pinned graphs above are still the default. A Wan LoRA whose recipe (`the author's research notes`) asks for other settings now
  gets them through `wan_tools.wan22_generate(sampler=...)` (`sampler_from_recipe` -> `check_sampler` -> `apply_sampler`): steps and the step where the low-noise expert takes over, shift, CFG,
  sampler / scheduler (euler, uni_pc, dpmpp_2m; simple, beta) and the two accelerators' strengths. The Deliverables LoRA templates and the bench builder (`wan_bench_run.specs`, control and LoRA
  arm alike) use the same code. CFG above 1 sends Wan's official negative; CFG 1 keeps the negative empty. A job carries it as `wan_sampler` (server field, validated). The result card note
  reads "recipe settings: 6 steps, split 3, shift 7". Size and frames are not taken from a recipe. 18 graphs (the 9 distinct shapes in the 109 class A recipes, i2v and t2v) were validated
  offline against the live `/object_info`; nothing was rendered.
* **Warm port.** `wan22_generate(keep_resident=...)`: a Deliverables run's shot tells the port that the next shot is another Wan clip; the experts then stay loaded when the card has room
  (`keep_resident_ok`, `COMFY_WAN_KEEP_RESIDENT=off` restores the old free-after-every-job rule). An out-of-memory render frees and renders once more.
* The Character chip on `wan:i2v` works since `characters.apply_character` got its `wan22_i2v` branch.
