# Virtual set

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Untested.


Status (2026-10-14): **code and tests done; never rendered on the GPU.** Every video model call is covered by fakes; the
Blender passes (`vset:scene`) have a headless CPU integration test. The three modes' defaults are not chosen: that is the
bake-off (plan Task 23), which needs the GPU and the author. The chatbox needs a **restart** to serve `/api/vset/*` and the
mode; nothing was restarted from the branch.

Spec: `the author's notes`. Plan: `the author's notes`
(Tasks 12-19, 22). Code: `earlier_studio/vset/` (camera maths, shot schema and storage, passes, three modes, QC, shot runner,
shot lists, `api.py`), `earlier_studio/tools/vset_control_tools.py` (Wan 2.2 Fun Control tool), the `_vs_*` block in
`scripts/chatbox/server.py`.

## What it does
Block a shot in an **approved** World Kit place with up to 2 approved characters (marks, an action clip), pick a camera
preset (`push_in`, `orbit`, `walk_along`, `pov`, `selfie_arm`, `handheld`, `static`) or your own path, preview the camera in
3D, then render. Blender writes exact per-frame passes (depth, pose skeletons drawn from the rig, edges, shaded) and first /
last stills; a video model then makes it photoreal:

| Mode | Steps | Format limits (from the models on the box) | Peak VRAM |
|---|---|---|---|
| A guide passes | `vset:funcontrol` (Wan 2.2 Fun Control A14B on the depth or pose pass; the character's full-body sheet shot is its reference) | 81 frames at 16 fps (5 s); 9:16 tested in the sweep, 16:9 untested | ~70 GB |
| B restyle | `edit:depth_restyle` (H3 Fun Union depth control) on the shaded render | up to 5 s | ~48 GB |
| C keyframes | `qwen21:edit` on the first and last Blender stills (identity edit), then `h3:fl` | 5, 8 or 10 s | ~50 GB |

The spec's "5-15 s" is refused above a mode's limit with the reason. QC then checks the face match, flicker and set
consistency; a shot gets one automatic reroll, then waits for review. A **shot list** (a script turned into ordered shots,
or the `vset:shotlist` pipelines role) keeps one place and look across a video.

## Status of each piece
- Done and tested without a GPU: camera presets to per-frame keys, shot validation and storage, the Blender pass scene
  script, all three modes with fakes, QC, the runner, shot lists, `/api/vset/*`, the UI.
- **Untested on real hardware**: Fun Control on Blender passes (the sweep fed it DepthAnything / DWPose maps of a real clip),
  16:9 for mode A, restyle identity (it has no identity input on the box; QC's face match is its only gate).
- **Not done**: pipelines roles (plan Task 20, blocked on the pipelines Wave 0 merge), the GPU bake-off (Task 23).

## Rules
studio job. QC's face match is a quality check, not a content gate. Shots and lists live under `a local folder`
(`VSET_ROOT` overrides).
