# Krea 2 image

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


## Purpose / when to use it
The studio's default image model: the Composer opens on it. Use it for any general text-to-image job: scenes, product
packshots, signage and short text, worm's-eye or unusual camera angles, watercolour/painterly looks. It was the best
all-rounder of the 2026-10-10 capability run (9/10 SFW prompts clean, exact text, the only true worm's-eye view).
Use something else for: designed posters with layout (Ideogram 4, `image-ideogram-poster.md`), anime key-frame look
(HiDream-O1, `image-hidream-anime.md`), edits of an existing photo (Qwen-Image 2.1, `image-qwen21.md`), photoreal
portraits where Qwen 2.1 base is the KB pick (medium-low confidence).

## Step-by-step in the studio UI
1. Image tab. Generator drop-down: `Krea 2 Turbo · Text → image (default) · 8 steps, ~2.4 s` (first entry).
2. Aspect chip: `auto` = 1:1 (1024x1024), or any of 1:1, 4:5, 2:3, 3:4, 4:3, 9:16, 16:9, 3:2, 21:9.
3. takes chip: 1-4 (consecutive seeds, one preflight).
4. Leave the Character chip on "No character": `img:*` entries have no identity input and refuse a character
   (`characters.apply_character`). For a stored character use Qwen-Image 2.1 or H3 (`character-sheet.md`).
5. Type the prompt. Leave ✨ enhance on, or press ✨ Preview to see and edit the rewrite first, then "Use this".
6. Generate. On the card: ✦ Variations (same prompt, new seed), ⤢ Upscale, 🎬 Animate (opens Video with the image),
   ⤓ Download clean.

## Optimal settings
| Setting | Value | Source |
|---|---|---|
| Model / precision | `krea2/krea2_turbo_bf16.safetensors` loaded `weight_dtype fp8_e4m3fn` (W8A8 on this box) | graph `krea2_t2i.api.json`; fp8 allowlisted after same-quality A/B, BEST_OPTIONS `images.md` §7 |
| Text encoder / VAE | qwen3vl_4b (type krea2) / qwen_image_vae | `image_best_tools.py` docstring; the author's build notes "Default image" |
| Steps / CFG | 8 / 1 | same |
| Sampler / scheduler | euler / simple | same |
| Negative | none | same |
| Realism chip (opt-in, OFF by default) | `Realism: off / on`: camera-real wording from the enhancer; wording only (4K via the Upscale card at x4 with Realism on). Proof level "loads": the Krea chain was only measured by proxies and no realism LoRA is proven for it; not a guarantee | `studio/realism.py` preset `image.krea2`, `docs/processes/realism-4k.md` |
| Resolution | ~1 MP on a 32 grid: 1:1 1024x1024, 3:4 896x1184, 9:16 768x1344, 16:9 1344x768, 4:5 928x1152, 21:9 1568x672 | `studio/aspects.py` `IMAGE` / `IMAGE_SIZES` |
| Alt arm mu 1.15 | neutral, keep default | `images.md` §1 "Alt arms" |
| LoRAs | no studio LoRA picker on this entry (QuadView_krea2 / DynamicCharacterSheet_krea2 help in tests but are not wired) | `lora_library.ENTRY_FAMILIES` (no img:* key); `images.md` §3 |
| Default seed | 710001 | `KINDS["krea2"]` |

## Prompting rules
- Prose, not tag lists. Rules page read at call time (and by the enhancer):
  `a local folder` (prompt_style prose; 8 steps, CFG 1).
- Text in the image: quote the exact words; Krea rendered S01 signs and "PLATFORM 7" exactly (`images.md` §1).
- No negative prompt: CFG 1 ignores it.
- Counting and colour binding work ("five mugs in order", S02).

## Guards and gates
- Layer 1 text guard on the prompt (and every field) before the job is created and again on the final enhanced prompt
  (`guards-text-and-output.md`).
  (`earlier_studio/studio/imagecheck.py` docstring).
- Downloads and publish go through the scrubbed export and the TRIBE pre-post gate (`publish-download-tribe.md`).

## Time and VRAM
- 2.3-2.4 s per image warm, 22.0-22.7 GB port peak at fp8 (bf16 would be 33.9-34.6 GB): `images.md` §1 and §7;
  capability run median 2.3 s (`outputs/capability_run_2026-10-10/results.jsonl`, main arm).
- Code peak 24 GiB (`KINDS["krea2"].peak_gib`) → needs 28 GiB free (peak + `video_edit_tools.HEADROOM_GIB` 4).  a local port.
- If any ComfyUI port is busy the job waits ("Waiting for GPU") or fails; tick "Queue when free" on Retry.

## Known pitfalls / failure modes
- Same prompt + same settings = same file: the first Generate always uses seed 710001 and outputs are content-hashed,
  so pressing Generate again returns the cached image. Use ✦ Variations for new seeds.
- The fp8 vs `weight_dtype default` dtype A/B said "same quality on 4/4 prompts"; S03 recomposed (still valid). Not a
  problem, but don't expect bf16-identical images.
- Hands crop/camera-out-of-frame prompts are fine on Krea; crowd counts were ~6 for "six people" (S04), good not exact.

## Evidence
- Sheets: `a local folder`.
- dtype A/B rows: `a local folder`.
- Commits (earlier commit), (earlier commit).
