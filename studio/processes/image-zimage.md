# Z-Image

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Untested.


## Purpose / when to use it
- **Turbo**: a fast (~1.7 s) text-to-image model with an Apache-2.0 licence: the pick when a non-commercial licence
  (Qwen 2.1, Klein) rules a model out. Strong on counting/colour binding and food; low variety between seeds; miscounts
  crowds (BEST_OPTIONS images.md, S02/S04/S09).
- **Base**: the undistilled model: real CFG and a negative, more variety, 50 steps. No judged A/B against Turbo yet.

## Step-by-step in the studio UI
1. Image tab → Generator `Z-Image Turbo` or `Z-Image base`.
2. Aspect chip (Auto = 1:1) and takes 1-4. Describe the scene in plain sentences.

## Optimal settings
| Setting | Turbo | Base | Source |
|---|---|---|---|
| Load | bf16 file as `fp8_e4m3fn` | bf16, `default` | [tested] dtype A/B (fp8 = bf16 quality 4/4, on `FP8_W8A8_OK`); base: fp8 is W8A8 here, not allowed |
| Encoder / VAE | qwen_3_4b (lumina2) / z_image/ae | same | [tested] capability run |
| Sampling | 8 steps res_multistep/simple, CFG 1, AuraFlow shift 3 | 50 steps, CFG 4, same sampler/shift | [tested] dtab_zit_fp8_* / zib_base_bf16_* |
| Negative | ConditioningZeroOut (CFG 1 ignores it) | real empty CLIPTextEncode | [tested] / [documented] card + template |
| Steps / CFG range | 8 NFE, guidance 0 (= CFG 1 here) | 28-50 steps, CFG 3-5 | [documented] Tongyi-MAI cards |

The model page's rules block (`a local folder`, base:
`z_image_bf16.rules.json`) is read at every render: `steps` / `cfg` / `shift` there override the tested values; the chips
override neither (there is no steps chip).

## Model negative (Z-Image base only, 2026-10-17)
Chip `Model negative: off/on` on `img:zimage_base` (settings key `model_negative`, tooltip with the sources). When on, the model's own
static negative is the FIRST part of the negative the base graph carries; the Smart negative and your words stack behind it
chip is not even offered there). Code `studio/model_negative.py`, data `studio/data/model_negatives.json`.

What the authors really say (fetched 2026-10-17): CFG 3.0-5.0, 28-50 steps, `cfg_normalization` False for general stylism / True for
realism, and a negative is "Strongly recommended for better control" (GitHub README) or "Optional, but would be powerful" (current HF
card); the official demo, the card and the Comfy template all send an EMPTY negative, so **there is no official negative text**. The
wording in the data file is the studio's own, and the chip therefore starts OFF; flip `default` to `on` in the data file after
`scripts/negative_ab.py` has been looked at. Studio settings (50 steps, CFG 4) sit inside the authors' ranges.
Sources: https://github.com/Tongyi-MAI/Z-Image , https://huggingface.co/Tongyi-MAI/Z-Image , https://huggingface.co/spaces/Tongyi-MAI/Z-Image .

## Time and VRAM
- Turbo fp8: 15.1-16.6 GB on the port (cold first row 24.9); budget 26 + 4 GiB. ~1.7 s per image.
- Base bf16: 20.5-22.8 GB on the port, 20-36 s per image (zib_base_bf16_s01-s04); budget 26 + 4 GiB.

## Evidence
- `audits/BEST_OPTIONS_2026-10-10/images.md` (speed table, S02/S04/S09, §7 dtype verdicts).
- `audits/LORA_RETEST_2026-10-09_par_zimage_basejson.md` (base 4/4 rendered).
- https://huggingface.co/Tongyi-MAI/Z-Image-Turbo, https://huggingface.co/Tongyi-MAI/Z-Image (fetched 2026-10-11).
