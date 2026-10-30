# Text or video to 3D motion

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


## What you get
Both write a **SOMA77** skeleton animation (the rig Kimodo, GEM-X and the SAM 3D Body bridge share): a **BVH** (cm, Y up,
Root + 77 joints) and an **NPZ** (numeric arrays only), plus a faceless **mannequin preview** (video + a 3x3 sheet).
GEM-X also hands out its own 2D keypoint overlay, in-camera and global (world-space) videos. Everything lands in
`a local folder,gemx}/<run>/`. From the card: 🕺 Mixamo / UE5 / VRM retarget (see
[3d-retarget-smpl.md](3d-retarget-smpl.md)).

## Kimodo (3D tab → "Kimodo · Text → 3D motion")
- Prompt: one person, the actions in order ("A person walks forward, stops and waves with the right hand.").
- `seconds`: 5 (tested), 3 / 8 / 10 (Kimodo allows 2-10 s; a note says untested).
- Recipe: `a local folder PROMPT --duration 5 --bvh --seed 7` (Kimodo-SOMA-RP-v1.1, 100 diffusion steps,
  LLM2Vec text encoder on Llama-3-8B-Instruct on the GPU).
- Smoke 2026-10-11: walk_wave 29 s, dance 36 s, sit_down 1336 s wall (generation ~6 s; the text encoder loaded under
  contention), nvidia-smi peak 16,520 MiB. Budget 17 GiB + 4.
- Licence: code Apache-2.0; model NVIDIA Open Model License; Llama 3 Community Licence ("Built with Meta Llama 3").

## GEM-X (3D tab → "GEM-X · Video → world-grounded 3D motion")
- `source_video`: one clearly visible person (first 20 s are used); `camera`: moving (default) / static.
- Recipe: `a local folder --video CLIP --output_root DIR [--static_cam]` → `hpe_results.pt`, converted on
  the CPU by `scripts/motion/gemx_to_soma_bvh.py` (GEM-X venv, `torch.load(weights_only=True)`): GEM-X's own
  export_soma_bvh maths (GEM-X's exporter needs soma-retargeter, empty on this box), identity locked to the clip median,
  self-checked (BVH FK vs SOMA FK).
- Smoke 2026-10-11 17:28: box-made walkers 42 s / 53 s, peak 9,684 / 9,916 MiB. Converter on that output: max 6e-5 cm,
  identity lock moved joints <= 8e-5 cm, root travel 2.73 m on the walker.
- Licence: code Apache-2.0; weights NVIDIA Open Model License (no real people's video without consent, no deepfakes,
  no surveillance).

## Studio-tool smokes (2026-10-11, this branch)
- Kimodo "A person jogs forward, slows down, then jumps and lands with both feet." → 36 s end to end (generation +
  mannequin preview), `outputs/studio/kimodo/kimodo_e7d342969dc6/` (the sheet shows the jog, crouch, jump, landing).
- GEM-X on `outputs/civ_raw/wan_walk_none_00001_.mp4` → 59 s end to end, 81 frames, BVH vs SOMA FK 5e-5 cm,
  `outputs/studio/gemx/gemx_3a68470914b2/`.
- Retarget of Kimodo dance.bvh through the tool: mixamo / unreal5 FBX, VRMA, SkinTokens tira FBX + VRM + VRMA; contact
  sheet `outputs/studio_motion_smoke_2026-10-11/kimodo_dance_on_tira_preview.png` (the character dances, knees bend the
  right way).
- Every file of those runs passes `output_guard.probe_media` (bvh / npz / fbx / glb / video / png).

## The output guard
A BVH passes the guard's strict BVH grammar; an NPZ passes only as a numeric-only motion NPZ (no pickle, no text, no
bytes, no uint8 planes). Neither can carry a picture, so both are judged by a picture set on the job: the mannequin sheet
(Kimodo) or a 3x3 sheet of the clip's frames (GEM-X). Videos are checked frame by frame like any video.

## Skeleton from motion (2026-10-17)
A frame of a Kimodo / GEM-X (SOMA77) or SAM 3D Body (MHR127) BVH, or a SOMA / SMPL NPZ, can be drawn as the OpenPose picture the pose-control route uses, as a Wan Fun Control control video, or as a Virtual Set person: [skeleton-from-motion.md](skeleton-from-motion.md). The 3D proof batch ([3d-proof-batch.md](3d-proof-batch.md), G5) runs Kimodo and GEM-X through the studio and renders the skeletons from the results.
