# Fix light

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Untested.


## Purpose / when to use it
A photo with a colour cast (neon, a coloured wall, the wrong white balance) or window / flash glare. Marigold v2 albedo is the picture with the
lighting taken out (see [edit-marigold.md](edit-marigold.md)); this entry blends it with the original and then gives the picture a new light.
No prompt. It is **not** for changing a person: IC-Light SD 1.5 changed faces and hair on every person in its test
([3d-mesh2photo.md](3d-mesh2photo.md) has the product relight), so the entry checks for a face first.

## What it does (two routes, picked by a CPU face check)
| Picture | Route | Result |
|---|---|---|
| no face | one ComfyUI graph: Marigold v2 albedo -> ImageBlend with the original -> IC-Light fc relight (light map gradient + the tested light prompt) | 768x512 or 512x768 (the relight's tested sizes) |
| a face, or the face check could not run | Marigold v2 albedo -> ImageBlend, then a CPU grade (colour temperature, a soft gradient from the light side, small exposure move) | about 1 MP, the face untouched by any generator |

Chips: **Cast removal** gentle (40% albedo) / medium (70%, default) / strong (pure albedo, flat on its own); **Light** day (new, untested) / golden hour /
soft window / studio (the last three are the tested relight prompts `sunset_left`, `window_left`, `studio_top`). The result's `route` field says which route ran.

## Why these graphs, not the three on the box
| Existing graph | Used? | Why |
|---|---|---|
| `iclight_fc_lightmap` (repo) | yes, as the relight tail | tested (`UNTESTED_MODELS_TESTS_2026-10-11` section 3), light presets, products only |
| `iclight_relight_api.json` (`a local folder`, easy-use `icLightApply`) | no | needs the easy-use node pack, which the studio does not ship; the same IC-Light model |
| `lbm_relight_api.json` (LBM relighting) | no | one step, no target-light input: it cannot take a "golden hour" |
| `gap_marigold_iid_api.json` (IID appearance / lighting) | no | a different Marigold model than the tested v2 albedo LoRA |

## Time and VRAM (estimates, not measured)
Marigold's port peak was 35.1 GiB; the IC-Light tail adds about 3 GiB resident after the Qwen base is swapped out. Budget 38 GiB + 4 headroom. The tool refuses
(never queues) when a port is busy or the card is short, and frees  a local port's cache afterwards while it is idle.

## How it is proven
Offline: both graphs validate against a slice of the live  a local port `GET /object_info` (`tests/studio/data/fixlight_object_info.json`; nothing was
submitted), the tool runs against fakes, the CPU grade has numeric tests. On the GPU: step `G3` of the 3D batch ([3d-proof-batch.md](3d-proof-batch.md)) (`scripts/marigold_ab.py run --only fixlight`),
judged by eye on a before / after sheet. Readiness family `edit.fixlight` stays at `recipe` until the author judges it.
