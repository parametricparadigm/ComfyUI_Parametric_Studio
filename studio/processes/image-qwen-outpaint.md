# Extend an image

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Untested.


## Purpose / when to use it
- Extend a picture past its edges (wider shot, taller story frame, room for text) while the original pixels stay exactly
  as they were.
- The CONFIRMED outpaint pick of the final build (the author's build notes "Qwen outpaint (T8 B)").

## Step-by-step in the studio UI
1. Edit tab (or the launcher card "Outpaint / extend") → Generator `Qwen-Image 2.1 · Outpaint / extend the frame`.
2. Drop the picture into `image`.
3. Chips: `extend` = right (default, tested) / left / top / bottom / sides / all; `amount` = 50 % (default, tested) / 25 % /
   100 % of that side's dimension; `takes` 1-4.
4. Optional prompt: what continues past the edge ("the counter and a window with plants continue to the right"). It is
   sent as typed (never the enhancer's rewrite) and becomes `Scene: ...` after the LoRA's trigger sentence.
5. Generate. The result is the padded canvas with the new area filled and the original pasted back.

## Optimal settings
| Setting | Value | Source |
|---|---|---|
| Model / LoRAs | Qwen-Image 2.1 bf16 + `outpaint-v2` baked 1.0, then Comfy-Org's Turbo LoRA (extracted from the base) 1.0 LAST | [tested] dn_t8_outpaint_B (DO-NOW T8 arm B) |
| Sampling | 8 steps euler on the official sigmas (ManualSigmas → SamplerCustom), CFG 1, seed 2102 | [tested] dn_t8_outpaint_B |
| Encoder | TextEncodeQwenImage21, image_1 = the padded picture, resolution 0 | [tested] / [documented] card |
| Padding | flat #808080, each side a multiple of 32, canvas 1-2 MP | [documented] AusBoss card (LORA_USAGE_RECIPES §2.11) |
| Geometry | right +50 % (1024² → 1536x1024) | [tested]; other sides/amounts [documented] only |
| Paste-back | crop the original area from the padded input, composite it over the result | [tested] dn_t8_outpaint_B |
| Prompt | `Outpaint the image: replace the solid gray areas with a seamless continuation of the scene, keeping the existing picture unchanged. Scene: <your words>` | [documented] card |
| Resize | the picture is resized (LANCZOS) to reach 1 MP / stay under 2 MP and onto the 32 grid before padding | [inference] |

## Guards and gates
- Text guard on the prompt as for every job; the output guard checks the result image.
- Non-commercial: Qwen-Image 2.1 base licence; the LoRA's commercial flag is RentCivit only.

## Time and VRAM
- ~5 s per take after load; 48.3 GB on  a local port, 55.7 GB card total (dn_t8_outpaint_B). The studio budgets 52 + 4 GiB
  headroom (`image_qwen21_tools.TASK_PEAK_GIB`) and refuses (Queue when free) below that.

## Known pitfalls
- Very thin pictures get a small kept area (the 2 MP cap applies to the whole canvas).
- The older 25-step stack (no turbo) is the W6 test; T8 B matched or beat it at 3.3-5 s (BEST_OPTIONS images.md).

## Evidence
