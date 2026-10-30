# Motion transfer with SCAIL-2

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


## When to use it
Your character (one still) performs the motion of a driver clip: dances, actions, blocking. The default driver is a
**SAM 3D Body mesh render** of the clip: it carries the motion and the camera move but never the driver's face or look
head-turn drift; `raw` uses the clip itself and copies the driver's facial expression.

## In the studio
1. Video tab → "SCAIL-2 · Your character does a clip's moves".
2. `character`: the character still (full body). `source_video`: the driver clip (the first 81 frames are used).
3. Prompt: the character, what they do and the room, in prose (the tested prompt described outfit, room and moves).
4. `driver`: mesh (default) / capsules / raw.

## The recipe (pinned; graph = pick-5 `s_raw` node for node)
Official template `video_wan21_scail2_character_replacement` (base subgraph, distill ON) in **Animation Mode**:
UNETLoader `scail2/wan2.1_14B_SCAIL_2_nvfp4_mxpf8_mix` + DPO LoRA 1.0 + lightx2v I2V 480p r64 0.8, ModelSamplingSD3
shift 5, euler / simple 6 steps, CFG 1 (SamplerCustom), umt5 fp8, CLIP vision H on the still, SAM 3.1 "human" tracks of
driver and still → SCAIL2ColoredMask, 512x896 centre crop, 81 frames at the driver's fps, seed 4242.
Mesh / capsule driver: core `SAM3DBody_Predict` (hand refinement off, fov 0) → `SAM3DBody_Smooth` (gaussian 7, 15°) →
`SAM3DBody_Render` (mesh: default shader, opacity 1, falloff 0.6, full body; capsules: radius 0.022 m, dwpose hands, no
face) on black: the tested s_core / s_caps driver values. The test rendered the driver first (library mode); here the
same nodes run inside the SCAIL graph: one-graph smoke 2026-10-11 ~19:58 on idle  a local port (mesh driver), success in 155 s
incl. loads, identity / outfit / room kept, dance + dolly-in followed
(`outputs/studio_motion_smoke_2026-10-11/scail_mesh_sheet.jpg`).

| Arm (pick 5) | time | result |
|---|---|---|
| s_core (mesh) | 100 s | identity, outfit, room kept; dance + dolly-in followed; neutral face |
| s_caps | 94 s | as the mesh, slightly more head-turn drift |
| s_raw | 199 s (first load) | also copies the driver's smile |

VRAM: only whole-card peaks were recorded (69-75 GiB with other tenants); budget 46 GiB (raw) / 50 GiB (mesh, capsules)
only, in the still and in the driver.
