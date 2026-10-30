# Depth, normals and albedo maps

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


## Purpose / when to use it
Image in, map out, no prompt:
- **depth**: relative (affine-invariant log) depth for compositing, fog, depth-of-field or as a control image. Sharper
  than DepthAnything V2 (the stack's depth estimator) on the 6 test inputs, and without its black "infinitely far"
  window hole.
- **normals**: camera-space surface normals for relighting. Very clean in the test.
- **albedo**: the colours with the lighting removed. It removed a red neon cast and window glare in the test.
Not a replacement inside the H3 depth-restyle pipeline (that runs DepthAnything V2 per frame; a per-frame Marigold pass
is untested and needs a 20 GB base load).

## Step-by-step in the studio UI
Edit tab → `Depth / normals / albedo map (Marigold v2)` (or a card preset: Depth, Surface normals, Albedo) → drop the
picture → task chip → Generate. There is no prompt box to fill and no enhance.

## Optimal settings (pinned in the graph)
| Setting | Value | Source |
|---|---|---|
| Base | `qwen_image_edit_2509_int8_convrot` | dlq 0070-981 (the repo ships only this base) |
| Task LoRA | `marigold_v2/marigold_v2_{depth_log_stage2,normals,albedo}` at 1.0 | templates `image_marigold_v2_*_estimation` |
| Sampling | ModelSamplingAuraFlow 1.73 `img_to_img_velocity`, DisableNoise, euler, ManualSigmas "0.5, 0" (one step) | same |
| Conditioning | ConditioningLoader `marigold_v2_<task>_conditioning` (precomputed: no text encoder) | card + templates |
| VAE | per-task `marigold_v2_<task>_vae` (encode and decode) | same |
| Size | input scaled to ~1 MP (lanczos, 16 steps) | card: ~17 GB at 1024²; box addition |
| Post | MarigoldV2PostProcess with the task | templates (the normals/albedo inner default says "depth"; the task is passed) |

Deterministic: the same picture and task return the cached map.

## Guards and gates
nothing to show or hide here.

## Time and VRAM (2026-10-11,  a local port)
Warm 0.5-3 s per map, first map 15.5 s with the base load; mean over 6 rows: depth 4.2 s, normals 1.3 s, albedo 2.0 s.
Port peak 34.3 GiB; studio preflight 36 + 4 GiB headroom.

## Known pitfalls
- Depth is relative: near/far order and shape are right, absolute distances are not.
- The base (20 GB) is unloaded after each job while  a local port is idle, so a single map costs the ~15 s load each time.

## Evidence
`a local folder` (`marigold`); manifest `manifest_newlanded_img_20261011.json`;
sheets `outputs/newlanded_tests_2026-10-11/depth_*.jpg`.
Sources: https://huggingface.co/huawei-bayerlab/marigold-v2-0 · https://huggingface.co/Comfy-Org/marigold-v2-0 ·
https://huggingface.co/Qwen/Qwen-Image-Edit-2509

## Follow-ups prepared 2026-10-17 (nothing rendered yet)
- **Depth control A/B**: `scripts/marigold_ab.py` renders Marigold v2 depth against DepthAnything V2 as the depth control of the studio's one still-picture depth route (Qwen 2.1 edit + Fun ControlNet Union, via a ready `control_map`), same prompt and seed, judged by CPU structure metrics and a contact sheet; the author decides. See [3d-proof-batch.md](3d-proof-batch.md) (G4).
- **Fix lighting**: albedo then a relight, entry `edit:fixlight` ([edit-fixlight.md](edit-fixlight.md)).
- **Depth DoF / haze**: `realism.post_image_depth(path, depth_path)` applies a depth-weighted lens blur and light atmospheric haze from a Marigold depth map (near = bright); off unless called and meant for the Realism chip being on AND a depth map existing; synthetic-depth tests only ([realism-4k.md](realism-4k.md)).
