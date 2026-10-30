# Boogu image

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


## Purpose / when to use it
- **Turbo (text to image):** a fast second text-to-image next to Krea 2: about 3x faster warm (1.5-3 s vs 5.6 s in the
  same lane), natural portraits on par with Krea 2, correct product-label text. Krea 2 stays the default: it got a
  poster title right where Boogu doubled a word. Pick Boogu for quick drafts, or when an Apache-2.0 model is wanted.
- **Edit-Turbo (say the change):** a fast (≈5 s) Apache-licensed alternative to the Qwen 2.1 edit (≈28 s in the same
  lane, research licence) for small local edits: add a scarf, recolour a jacket, keep the face and the background.
  For full re-stages (clear a whole room, swap the whole background) use the Qwen 2.1 edit: Boogu left part of the
  clutter and kept the slate under the product in the test.

## Step-by-step in the studio UI
Turbo: Image tab → Generator `Boogu-Image 0.1 Turbo · Text → image …` → aspect (auto = 1:1, 1024x1024) → takes 1-4 →
prompt (✨ enhance on: the enhancer reads this model's rules page) → Generate.
Edit-Turbo: Edit tab → `Fast edit by instruction (Boogu Edit-Turbo)` → drop the picture → one sentence for the change,
then what must stay → takes 1-4 → Generate. There is no ✨ enhance on edits: the instruction is sent as typed.

## Optimal settings
| Setting | Turbo | Edit-Turbo | Source |
|---|---|---|---|
| Model | `boogu_image_turbo_hotfix_int8_convrot` (weight_dtype default) | `boogu_image_edit_turbo_hotfix_1k_20260708_int8_convrot` | dlq 0030-980; card news (hotfixes) |
| Text encoder / VAE | `qwen3vl_8b_bf16`, CLIPLoader type `boogu` / `flux/ae.safetensors` | same | Comfy templates; NEW_LANDED_TESTS §4 |
| Steps / CFG | 4 / 1 | 4 / 1 | Turbo card; origin model zoo (Edit-Turbo) |
| Sampler / scheduler | lcm / sgm_uniform | dpmpp_2m / simple (lcm/sgm_uniform near-identical in the test) | Turbo template; Edit template |
| Shift | model default | ModelSamplingAuraFlow 3.16 (the model's own) | Edit template; core `supported_models.Boogu` |
| Size | ~1 MP on a 16 grid; 1:1 = 1024x1024 (tested); other ratios untested | input scaled to 1 MP, shape kept | card: "1K"; test rows |
| Negative | ConditioningZeroOut (none) | empty | templates |
| Seed | 4242 (+1 per take) | 4242 (+1 per take) | test rows |

The rules pages may change steps / CFG / sampler / scheduler (and the edit's shift); they are read on every job.

## Prompting rules
Plain sentences, no tag lists, no negative. Quote the exact words of any text; keep titles short and check them.
Edits: one imperative sentence, then "Keep … unchanged".

## Guards and gates

## Time and VRAM (2026-10-11,  a local port)
| | warm | cold (first, with the load) | port peak | studio preflight |
|---|---|---|---|---|
| Turbo 1024² | 1.5-3 s (mean of 4 rows 6.8 s incl. the cold one) | 20.7 s | 30.3 GiB | 32 + 4 GiB headroom |
| Edit-Turbo ~1 MP | 2.4-6 s (mean of 8 rows 5.7 s) | 21.8 s | 29.3 GiB | 31 + 4 GiB headroom |

## Known pitfalls
- Same prompt + seed + settings = the same file (content-hashed); use ✦ Variations for new seeds.
- The Turbo card calls Boogu-Image 0.1 "a research project only, not an official model release" (the licence is still
  Apache-2.0).

## Evidence
`a local folder`; manifest `manifest_newlanded_img_20261011.json`; results
`a local folder`; sheets
`outputs/newlanded_tests_2026-10-11/t2i_*.jpg`, `edit_*.jpg`.
Sources: https://huggingface.co/Boogu/Boogu-Image-0.1-Turbo · https://huggingface.co/Boogu/Boogu-Image-0.1-Edit-Turbo ·
https://huggingface.co/Comfy-Org/Boogu-Image
