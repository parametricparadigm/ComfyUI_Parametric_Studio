# Retarget motion to other rigs

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


Both are buttons on a finished motion card: SAM 3D Body (photo / clip), Kimodo, GEM-X. They take the motion **by job
reference only**; the new job is judged by the motion's own picture (the photo, the frame sheet or the mannequin
sheet), which the server copies forward. An uploaded BVH / GLB is refused (it has no judged picture).

## Retarget (🕺 Mixamo / 🕺 UE5 / 🕺 VRM)
`a local folder` (Blender 5.2, Retarget + VRM add-ons, CPU, seconds):
| preset | what | files |
|---|---|---|
| mixamo | rename the source rig to `mixamorig:` names (mesh, skin, face morphs and animation kept) | FBX (mixamo flavour) |
| unreal5 | rename to UE5 mannequin names | FBX (unreal flavour) |
| vrm | VRM humanoid assignment | VRM (a GLB with a mesh) + VRMA |
| skintokens | transfer onto a SkinTokens-rigged character (`target`, a 🦴 Rig result or your GLB / FBX / VRM) | FBX + VRM + VRMA |
SOMA77 BVHs (Kimodo, GEM-X) use `scripts/blender/soma77_slots.json`: SOMA's `LeftLeg` is the thigh (Mixamo's is the
shin), so the automatic detection would mis-map the legs. Tested: KB §3 (SAM 3D Body GLB / BVH → Mixamo, UE5, VRM,
SkinTokens tira; BVH → Mixamo character 0.000 % joint error); Kimodo walk_wave.bvh → Mixamo FBX + VRMA (1.6 s) and →
tira FBX + VRM + VRMA (6.5 s, 0.07° mean / 1.25° max body), 2026-10-11 19:14. The skintokens transfer has no card picker
for the target yet: post `refs.target` (a job reference or a workspace file) with the API.

## SMPL-X / SMPL export (SMPL-X (NC) button) — NON-COMMERCIAL
SMPL and SMPL-X are MPI-IS research licences: everything lands in
`a local folder` with `NONCOMMERCIAL.txt`; keep it out of commercial
work until the author's legal team clears it. SAM 3D Body results only: the body result's photo, or the first 5 s of
its clip (up to 80 frames), runs through core SAM 3D Body as a library (`a local folder`, the ComfyUI venv python,
fp32, batch 8, 10 GB cap), then `a local folder` (MHR venv, CPU; one identity for a clip). Files:
`smplx_params.npz` (or `smpl_params.npz`) + the first SMPL mesh (PLY). Tested KB §4: 64-frame clip dump 69 s / 6.9 GB,
SMPL-X single identity 46 s, 8.2 mm mean converter error. Kimodo / GEM-X motions are refused (no SOMA → SMPL converter
on the box). Studio-tool smoke 2026-10-11 ~20:10 on a box-made photo: 25 s, 7.5 mm converter error,
`outputs/studio/smpl/smpl_bead1c99a5e2_NONCOMMERCIAL/`.
