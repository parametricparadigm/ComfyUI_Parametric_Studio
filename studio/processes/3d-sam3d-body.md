# Photo to rigged 3D body

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


## What you get
**The GLB is the main deliverable.** The BVH is a standard skeleton, retarget-ready.

| From | Files |
|---|---|
| a photo | **rigged GLB** (the posed body: real armature, 127 bones, skinning, 72 face morphs), a mesh render over the photo, an OpenPose 2D render (black background, usable as pose control) |
| a clip (first 5 s) | **animated rigged GLB**; a **BVH: standard skeleton, retarget-ready**, one per tracked person (re-exported from that GLB, see below); a mesh-over-source preview video; an OpenPose 2D video |

## The BVH (clip): re-exported from the GLB, never the core BVH
ComfyUI core's own BVH (`BuildPoseFile` format `bvh`, `comfy_extras/sam3d_body/export/bvh.py`) writes MHR's parent-local
offsets as OFFSET and folds the bind rotations into the channels. Its frames are right but its zero-rotation rest
skeleton is garbled, so a retarget from it leans and floats (12x root travel, up to 89 deg; KB
`SAM3D_BODY_RETARGET_SMPL_2026-10-11.md`). the author chose a studio-side fix (2026-10-11 ~17:10), not a core patch, so the
graph has no core BVH node at all. Instead `body3d_tools.glb_to_bvh` runs Blender headless
(`scripts/blender/glb_to_bvh.py`, the studio's `scripts/blender/` pattern) on the animated GLB:

- one BVH per tracked person: SAM3 tracking (up to 4 people) gives the GLB one armature per track (`track00`,
  `track01`, …), and each becomes `<run>_bvh_<track>.bvh`, checked on its own;
- joint names: the real MHR names (`scripts/blender/mhr127_joint_names.json`, by the GLB's `bone_NNN` index; copied
  from `a local folder`), root = MHR `root` (the world anchor `body_world` is folded in);
- centimetres, Y up; OFFSET = the GLB's bind pose (world-aligned), so the zero-rotation rest pose IS the GLB's bind
  pose; root channels = absolute position + rotation, joints Z X Y rotation (continuous between frames);
- the GLB moves joints along their bones frame to frame (per-frame body shape, twist helpers: up to 6.3 cm from the
  bind offsets on the test clip), so a joint whose offset moves gets position channels too, in Blender's own BVH
  convention (the value is the whole local offset). A rotation-only reader gets the bind skeleton.

**The check, every run:** the BVH is re-imported with Blender's BVH importer (independent of the writer) and every
joint's world position is compared with the GLB on every frame (tolerance 0.01 cm); the rest pose with the GLB bind
pose; the root's travel with the GLB's (no 12x travel); the rest skeleton must stand upright (head over root within 30
deg, head > root > feet, 50-250 cm). A BVH that fails is **withheld** (the GLB still ships) and the card says why. The
report (`*_bvh_check.json`) and Blender log stay beside the files as debug files; the card's BVH carries the numbers
(`bvh_check`).

Measured on the 2026-10-11 16:47 library-mode GLB (`outputs/sam3d_retarget_smpl_2026-10-11/dump/sam3d_body.glb`, the
box-made fictional walker clip, 64 frames, 16 fps), CPU only:

| Check | Result |
|---|---|
| joint positions, 126 joints x 64 frames (8,064 samples) | max 0.00016 cm, mean 0.00005 cm |
| rest pose vs GLB bind pose | max 0.00003 cm; upright |
| root travel | 13.92 cm BVH = 13.92 cm GLB |
| output guard (strict BVH grammar) | accepted as a 3D model (`bvh`) |
| retarget onto a Mixamo character (`a local folder --src-map detect`) | 0.99 deg mean / 2.09 deg body (GLB route 0.99 / 2.08; the earlier rotation-only standard BVH 0.64 / 1.35); hips travel 0.108 m (GLB route 0.105; core BVH 1.27) |
| Blender wall time | ~2 s |

**Studio smoke (2026-10-11 17:4x, the tool code itself,  a local port restarted 17:34 with core fix (earlier commit), hand refinement on,
no dtype error)**, outputs `outputs/body3d_smoke_2026-10-11/` (photo) and `outputs/body3d_smoke_2026-10-11_run2/` (clip):

| Run | Result |
|---|---|
| photo: a still of the box-made fictional walker (`walker_frame.png`) | 50 s; GLB 17.8 MB (guard: model/glb), mesh preview fits the person, pose PNG |
| clip: `outputs/civ_raw/wan_walk_none_00001_.mp4` (box-made fictional walker, 81 f @ 16 fps; first 5 s = 80 f) | 89 s; GLB 18.4 MB; SAM3 tracked 2 people (the walker + a background pedestrian) → 2 BVHs, each 126 joints x 80 frames: max error 0.00019 / 0.00015 cm, rest 0.00003 cm, upright, guard: model/bvh; preview + pose videos |
| that clip's walker BVH → Mixamo character (`retarget.py --src-map detect`) | 1.27 deg mean / 2.33 deg body; walks and waves upright |

**Root motion: `camera_translation: centered` (clip only).** author 2026-10-11 ("yes to all of them"). The core tooltip
says: "Bake pred_cam_t into the root's translation … 'centered' = delta from frame 0" (`off` = bind position, `absolute`
= raw, Z = camera depth). In `comfy_extras/sam3d_body/export/glb_skeletal.py` it animates the track node's translation,
which `glb_to_bvh.py` folds into the BVH root channels. The photo entry stays `off`.

| Re-check 18:10,  a local port, every ComfyUI port idle (the tool's own check, not bypassed), vramclaim 20 GB + watchdog (min free 50.4 GB, 0 interrupts) | Result |
|---|---|
| the walker clip with `centered`, through `body3d_tools` | 52 s; GLB 18.4 MB; 2 BVHs (guard: model/bvh) |
| walker BVH (`track00`), 126 joints x 80 frames | max error 0.00016 cm (mean 0.00005); rest 0.00003 cm; upright; **root travel 15.25 cm GLB = 15.25 cm BVH** (root range x 7.2 / y 8.2 / z 25.9 cm) |
| background pedestrian BVH (`track01`) | max error 0.0013 cm; root travel 3,130 cm GLB = BVH (see the caveat) |
| walker BVH → Mixamo character | 1.27 deg mean / 2.33 deg body; hips travel 0.127 m; walks and waves upright |

Outputs: `outputs/body3d_smoke_2026-10-11_centered/`. Caveat: the root follows SAM 3D Body's camera-depth estimate, so a
small, distant person (the 31 m pedestrian above) can jump metres in depth. The BVH reproduces the GLB either way; drop or
smooth that track's root if you use it. Before the switch (17:5x run, `off`) the root travel was 0 in both.

The first clip attempt (before per-track export) withheld the BVH as designed ("expected one armature, found 2") and still
shipped the GLB.

## When it turns on
The entries are listed but **unavailable** until `detection/sam_3d_body_dinov3_bf16.safetensors` (Comfy-Org/sam-3d-body
(no restart). Tested 2026-10-11 (one photo smoke, two clip smokes; see below).

## In the studio
1. 3D tab → "SAM 3D Body · Photo → …" (drop a photo in `image`) or "… Video → …" (drop a clip in `source_video`).
2. No prompt. Generate.
   the source picture (for a clip: a 3x3 sheet of frames from the analysed 5 s, built by the tool) and checks every
   frame of the preview and pose renders.

## The graph (from the Comfy-Org template `utility_sam3d_body.json`)
| Step | Value | Source |
|---|---|---|
| Person tracking | SAM 3.1 multiplex fp16 + CLIPTextEncode "person" → SAM3_VideoTrack 0.5, max 4 objects, every frame | [documented] template |
| FOV | LoadMoGeModel `moge_2_vitl_normal_fp16.safetensors` → MoGeInference level 9 → MoGeGeometryToFOV vertical degrees | [documented] template (safetensors: the pickled MoGe .pt is not used) |
| Body | SAM3DBody_Loader → Predict (hand refinement, batch 64, track data, FOV) → FaceExpression 1 / 1 / 2 / 2 / 0.02 / 7 → (clip) Smooth gaussian 7, 15 deg | [documented] template |
| Files | BuildPoseFile `glb` / `body_mesh` (bones off, default shader); camera_translation `off` (photo) / `centered` (clip); SaveGLB. Clip: the BVH comes from the GLB (above), not from a graph node | [documented] node tooltips; [inference] body_mesh instead of the template's scail capsules, because a rigged GLB is the point |
| Renders | SAM3DBody_Render `mesh` over the source (opacity 1) and `openpose_2d` (node defaults) | [documented] template / node defaults |
| Clip length | Video Slice 0-5 s | [documented] template |

Box differences: the template's RT-DETR boxes are dropped (its `rt_detr_v4-x-hgnet_fp32.safetensors` UNETLoader file is not
on the box; the fp16 file sits in `detection/`, which UNETLoader does not list); the template says boxes are optional and
SAM3 tracking supplies them. The animation fps follows the clip (the template's widget says 24).

## Output guard
A BVH file is plain text, which the guard used to refuse outright. It now recognises a BVH (every line a BVH keyword or a
row of numbers, whole file read, ≤ 64 MB) and judges it like a 3D model: by the job's source picture (for a clip, the
frame sheet). The re-exported BVH goes through the same strict grammar and the same judgement as before.

## Hand refinement and the dtype fix
Hand refinement stays on (the template's; better hands). On the `--highvram` ports (no on-the-fly weight casts) it needs
the ComfyUI core fix `(earlier commit)` (ComfyUI-v0.39.3 sam3d_body hand-refinement dtype cast, 2026-10-11 16:43), which a port
loads at its next restart. A run that stops inside a `SAM3DBody_*` node on a Float/Half dtype error is refused with
"ComfyUI  a local port needs a restart for the hand-refinement fix …" and the raw error; if the port started after the fix, the
message says it is another core dtype bug to report. (Chosen over probing the port's start time: the error itself is the
signal, and nothing renders twice.)

## Time and VRAM
One smoke each: photo ~50 s, 5 s clip ~90 s (cold load included). Peak not isolated (the card was shared; free VRAM fell
by ~9 GB during the clip). Budget kept at 16 GiB + 4 GiB headroom [inference: SAM 3D Body bf16 2.8 GB + SAM 3.1 + MoGe
ViT-L + activations].

## Licence
SAM License, KB audits/3D_GAP_SCOUT_2026-10-11.md).

## Evidence
- KB UNTESTED_MODELS_TESTS_2026-10-11.md §9 (the Meta-format file cannot load; the Comfy-Org repack can).
- Core code `a local folder`; template in
  `the ComfyUI venv/.../comfyui_workflow_templates_json/templates/utility_sam3d_body.json`.

## Body shape lock (clips, chip `lock_shape`, default on)
an earlier branch Per-frame SAM 3D Body predictions change the body's build a little every frame (rest-mesh
flicker ~0.9 mm per frame). With `lock_shape` on, the clip graph adds the BodyMod nodes (Burgstall-labs
fit_iterations 0 (= the per-coefficient median shape and scale: the test's self profile) → `SAM3DBodyMod_ApplyShape`
(strength 1 / 1, pelvis anchor) on the prediction, before FaceExpression and Smooth. KB SAM3D_BODY_HELPERS_2026-10-11.md
pick 1: rest-mesh flicker 0.89 mm → 2e-6 mm per frame, bone-length CV 0.91 % → 0.63 %, 2D keypoints move 2.1 px (core
Smooth alone removes only 29 %). Tested on a one-person clip; with several people only person 0 is locked (a note says
so). `off` renders the template as before. Studio-graph smoke 2026-10-11 ~19:55 on idle  a local port (box-made walker): 33 s,
GLB + renders; both tracks' BVHs pass the joint-for-joint check (max 0.00017 / 0.0013 cm, upright).

## Card actions on a body result
🕺 Mixamo / UE5 / VRM retarget and SMPL-X (NC) export: [3d-retarget-smpl.md](3d-retarget-smpl.md).
