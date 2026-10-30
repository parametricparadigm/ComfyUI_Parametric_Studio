# Image to textured mesh

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


## Purpose / when to use it
- Turn one image of an object or character into a GLB mesh (cutout first, then the 3D model), optionally auto-rigged.
- `3d:trellis`: TRELLIS.2 4B, textured PBR GLB; the default. `3d:hunyuan`: Hunyuan3D 2.1 mesh + PBR paint (own venv).
- Rig = UniRig skeleton + skin (for animation).

## Step-by-step in the studio UI
1. 3D tab → Generator `TRELLIS.2 (PBR)` or `Hunyuan3D 2.1`.
2. Chips: `textured` true/false (false = shape only; matters most for Hunyuan, 29 vs 10 GiB), `rig` false/true.
3. Drop the source picture into `image`: one clear subject on a plain background works best (a cutout runs first).
4. The prompt box is not used by the 3D builder (inferred from `_run_3d`, which passes only image, engine, textured, rig);
   type a short label if the button stays disabled. Generate.
5. The card offers the GLB as a file (⤓ Download clean).

## Optimal settings
| Setting | Value | Source |
|---|---|---|
| Engine | TRELLIS.2 (core int8 on  a local port, 4B pack) for textured PBR; Hunyuan3D 2.1 when you want its paint from several refs (the studio passes one) | MEDIA_CAPABILITIES §6 |
| Textured | true (default chip) | `variants.SETTINGS["3d"]` |
| Rig | false unless you will animate; UniRig ~60 s | MEDIA_CAPABILITIES §6 |
| Seed / steps / resolution | pp.three_d defaults; not exposed, not verified here | — |

## Prompting rules
- No text prompt drives the mesh. Prepare the image: single subject, whole object in frame, plain background, even light.
  For characters, an A-pose full-body still rigs best (pp has an `apose` option the studio does not expose).
- No per-model rules page (3D models are not in `model_rules.ENTRY_FILES`).

## Guards and gates
- The output guard judges a 3D model by the image it was built from plus every texture embedded in the GLB; an external
  texture or an image embedded in OBJ/PLY/FBX is withheld (`output_guard.py` docstring). See `guards-text-and-output.md`.
- Downloads are scrubbed exports (`publish-download-tribe.md`); a GLB is "not applicable" for TRIBE.

## Time and VRAM
| Step | Need (GiB, before +4 headroom) | Measured |
|---|---|---|
| TRELLIS.2 | 16 | 47-184 s (MEDIA_CAPABILITIES §6) |
| Hunyuan shape only / textured | 10 / 29 | not timed in these reports |
| UniRig rig | 12 (need = max(step, 12) + 4) | ~60 s |
- Cutout + TRELLIS on  a local port; Hunyuan in its own venv (`a local folder`). The studio path was not live-checked
  (LOCAL_MOE_REFERENCE §15: "not covered by these reports").

## Known pitfalls / failure modes
- Hunyuan's first paint run can segfault: Retry.
- The tool refuses while the studio holds the GPU or any ComfyUI port is busy; use Queue when free.
- TripoSplat is offered as `3d:triposplat` (untested, `3d-triposplat.md`); SAM 3D Body: untested, not offered.
- A finished result can be rigged later or turned into game LODs from its card (`3d-rig-gameready.md`).

## Evidence
