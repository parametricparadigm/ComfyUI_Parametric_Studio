# Photo to 3D with Pixal3D

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Untested.


## Purpose / when to use it
- One photo of an object → a PBR-textured GLB whose geometry follows the photo pixel for pixel (TencentARC, SIGGRAPH
  2026, MIT). Best when the model must match a product photo closely. Slower than TRELLIS.2 (~4-9 min vs 1-3).

## Step-by-step in the studio UI
1. 3D tab → Generator `Pixal3D · Image → PBR mesh`. No prompt is needed.
2. Drop the object photo into `image` (an RGBA cut-out keeps your own matte; an RGB photo is cut out with RMBG-2.0).
3. Generate. The card shows the GLB (⤓ Download clean) plus a hero still and a 4-side sheet (Blender EEVEE).
4. On the card: 🦴 Rig / 🎮 Game-ready / 📷 Photo (see `3d-rig-gameready.md`, `3d-mesh2photo.md`).

## Optimal settings (fixed, no chips)
| Setting | Value | Source |
|---|---|---|
| Runner | `a local folder --image X --output Y.glb --low_vram --fov 0.2 --seed 42` (own venv, offline) | [tested] smoke_test.sh 2026-10-11 |
| Resolution | 1024 cascade (the `--low_vram` default; 1536 without it, ~18 GB) | [documented] README |
| FOV | 0.2 rad (MoGe-2 auto-FOV is not on the box) | [documented] README / [tested] |

## Guards and gates
- The output guard judges the GLB by the input photo plus every embedded texture; previews are checked as images.

## Time and VRAM
- VRAM peak 16,438 / 16,182 MiB (smoke, 2 objects); the studio budgets 17 + 4 GiB and refuses (Queue when free) below it.
- `--low_vram` parks the DiTs in system RAM: about 30 GB (README estimate); the studio refuses below 34 GiB available.
- ~4-9 min per object; mesh finalize (UV parameterisation) is most of it (6.5 min on the chair). Timeout 40 min.

## Evidence
- `a local folder` (GLBs, logs, `*.vram_peak_mib`), `a local folder`.
- Not wired: the core ComfyUI Pixal3D nodes (`Pixal3DConditioning`, multi-view) need Comfy-Org/Pixal3D weights that are
  not on disk (not downloaded, by rule).
