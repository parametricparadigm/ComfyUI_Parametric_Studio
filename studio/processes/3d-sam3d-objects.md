# Photo to 3D objects

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


## Purpose / when to use it
- One ordinary photo (cluttered, objects partly hidden is fine) → for **each object you mark**: a GLB mesh with vertex
  colours, a 3D Gaussian splat (PLY) and its pose (scale / rotation / translation in the camera frame).
- Use it for real photos with several things in them. For one clean product shot where the model must match the photo
  closely, Pixal3D or TRELLIS.2 give textured (PBR) models instead.
- **Known limit:** colours are per vertex (no texture bake: nvdiffrast is not built), so small logo text and labels come
  out garbled. Shapes and colours of the objects are right.

## Step-by-step in the studio UI
1. 3D tab → Generator `SAM 3D Objects · Photo → 3D objects`. No prompt.
2. Drop the **full photo** into `image` (keep the scene: SAM 3D uses the context around the object).
3. Optional `mask_image`: 🖌 Paint mask (or drop one): **white = object**. Separate white patches are separate objects
   (up to 4, largest first). No mask: an RGBA cut-out's own alpha is the mask; an RGB photo with no mask is refused.
4. Chip `objects`: `separate` (default: one model per patch) or `one` (the whole mask is one object).
5. Generate. The card gets, per object, the GLB and the splat PLY (⤓ Download clean); one object → a hero still and a
   4-side sheet, several → a hero still each plus a sheet of them. Each GLB artifact also carries its `pose`.
6. On the card: 🦴 Rig, 🎮 Game-ready (AutoRemesher works best on exactly these single-object GLBs), 📷 Photo.

## Optimal settings
| Setting | Value | Source |
|---|---|---|
| Runner | `run_sam3d.sh --image PHOTO --mask OBJ_MASK --out-dir D --name object_N --seed 42` once per object | [tested] smoke_test.sh 2026-10-11 |
| Output | vertex colours, no mesh post-process, no layout post-process | [tested] run_sam3d.py defaults |
| Input | the full photo + that object's mask (not a cut-out) | [documented] run_sam3d.py / upstream notebook |
| Objects | mask regions split by flood fill, regions under 0.1 % of the picture (or 400 px) ignored, max 4 | [inference] |

## Guards and gates
- The output guard judges each GLB / PLY by the input photo (the models carry no textures); previews are checked as
  images. Mesh actions on an object (rig, LODs) carry the same photo forward.
- VRAM: the studio budgets **24 GiB peak + 4 headroom** and refuses (Queue when free) below it; system RAM: refuses below
  24 GiB available ([inference]: ~13 GB of checkpoints load through RAM).
- Licence: **SAM License** (Meta, code + weights): use, modify and distribute royalty-free, commercial use not excluded;
  ship the licence with redistributions; no military / ITAR / trade-control-violating use; acknowledge in publications.

## Time and VRAM
- 55-70 s per object (model load 13-42 s of it); nvidia-smi peak 21.7-23.4 GB, torch peak 17.4-18.1 GiB (2 objects).
- Upstream asks for >= 32 GB VRAM (`doc/setup.md`); the measured peak on this box is ~24 GB.
- A job with N objects loads the model N times (one run per object). A failed object leaves the finished ones cached: a
  retry continues from there.

## Evidence
  (compass + bottle GLBs, splats, `*_run.json`, `preview.png`). https://github.com/facebookresearch/sam-3d-objects
- Studio tool path 2026-10-11 (`mesh3d_tools.sam3d_objects`, real preflight + vramclaim,
  `outputs/studio_3dtools_smoke_2026-10-11/moe_mesh3d/`): compass photo + mask → 1 object in 41 s (card peak ~23.8 GB);
  a two-object photo (compass + bottle side by side, both masks) → 2 GLBs + 2 splats + hero each + `objects.png` in 62 s;
  both shapes and colours right, the bottle's logo text garbled as expected.
