# HiDream anime frames

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


## Purpose / when to use it
Anime key-frame and illustration look (speed lines, splash, clean line art) at 2048-class resolution. Best result on
the S08 anime prompt in the capability run. It is slow (~25 s); for a fast anime draft Klein 9B distilled is "nearly as
good at 2.8 s" but is not a studio text-to-image entry (`images.md` §2 "Anime"). For watercolour/painterly, Krea 2.

## Step-by-step in the studio UI
1. Image tab → Generator `HiDream-O1 · Anime / illustration (2048-class) · ~25 s`.
2. Aspect chip: only `auto` (= 3:4), 3:4, 1:1, 4:3. Other ratios are not offered.
3. takes 1-4.
4. Prompt (prose). ✨ enhance on or ✨ Preview.
5. Generate. ⤢ Upscale is rarely needed (output is already ~4 MP).

## Optimal settings
| Setting | Value | Source |
|---|---|---|
| Model / precision | HiDream-O1 full bf16 (`hidream_o1_image_bf16`) | the author's build notes "Anime / illustration" (CONFIRMED); `model_rules.ENTRY_FILES["img:anime"]` |
| Steps / sampler / scheduler | 40 / dpmpp_2m_sde_gpu / normal | `image_best_tools.py` docstring (cap_graphs.hidream full) |
| CFG | 5 | same |
| Seam smoothing | 0.8-1.0 | same |
| Sizes | 3:4 1728x2304, 1:1 2048x2048, 4:3 2304x1728 (the three the capability run rendered) | `HIDREAM_SIZES` |
| Negative | "" (empty) | `graph_for` passes `negative=""` |
| Default seed | 4242 | `Kind` default |
| LoRAs | none in the studio | no `lora_library` family for `img:*` |

## Prompting rules
- Prose prompts. Rules page (read at call time; no settings block, prompt_style prose):
  `a local folder`.
- Name the anime elements you want (key-frame, speed lines, cel shading, line weight); the S08 courier prompt is the
  tested example (`outputs/capability_run_2026-10-10/sheets/S08_sheet.jpg`).

## Guards and gates
- Download/publish: scrubbed export + TRIBE pre-post (`publish-download-tribe.md`).

## Time and VRAM
- ~25 s per image (capability run median 25.4 s), 19.5 GB port peak (`images.md` speed table).
- Code peak 22 GiB → needs 26 GiB free.  a local port.

## Known pitfalls / failure modes
- Only three sizes; a 9:16 or 16:9 request is not offered (refused by `best_generate` if sent).
- HiDream dev fp8 is a different file and garbled text on S01 (`images.md` §1): the studio uses the full bf16.
- Fixed default seed: Generate twice with the same prompt returns the cached file; use ✦ Variations.
- Anima (booru-tag anime model) is not in the studio; its strength is tags + LoRAs (`images.md` §2).

## Evidence
  the full bf16 was not on disk; the studio graph loads it and the capability run's `hidream_o1_full_bf16` arm ran 10/10).
- Commit (earlier commit).
