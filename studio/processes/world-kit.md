# World kit

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Untested.


Status (2026-10-14): **code and tests done, never run end to end on the box.** Plan tasks 0-11, 21 and the pack export are
built and tested without a GPU (fakes for the studio and for Blender where it would render); the real Blender CPU steps
are covered by integration tests that run headless Blender 5.2.2, and the GPU probe (Task 0) measured EEVEE. No asset has
yet been made through the live studio, so every card says "untested". The chatbox needs a **restart** to serve the new
routes and the mode; nothing was restarted from the branch.

Spec: `the author's notes`. Plan: `the author's notes`.
Code: `earlier_studio/worldkit/` (library, glb facts, rig map, Blender runner, studio engine `blender`, resumable steps,
makers, previews, runner, `api.py`, `export.py`); the studio bridge is the `_wk_*` block in `scripts/chatbox/server.py`.

## What it is
One shared library of `.glb` assets, each with real scale, a rig and motion clips (characters), colliders (props, places)
and a turntable + thumbnail. Four types:

| Type | Made from | Build steps (each a studio job through the composer path, so every guard runs) |
|---|---|---|
| Character | a saved, built character sheet (`ready` or `unverified`; its full-body front shot) | mesh (SAM 3D Body by default) -> remesh (AutoRemesher, optional) -> rig (SkinTokens) -> one motion + retarget pair per clip -> `wk:assemble` (Blender, CPU) |
| Prop / vehicle | a picture, a text prompt, **or a studio mesh by job reference** | (text: Krea 2 picture) -> **cut-out (`img:bgremove`, core BiRefNet, MIT, RGBA)** -> SAM 3D Objects mesh -> `wk:cleanup` (Blender, CPU: real size, pivot at the bottom centre, box collider). A mesh source skips the picture, the cut-out and the mesh steps |
| Place | a brief ("rainy downtown block at night") | a kit recipe (street / interior / beach) -> tileable Krea 2 textures -> `wk:place` (Blender, procedural, colliders) |
| Look | a preset (day, golden hour, night city, ...) with time / weather overrides | preview only |

Then `wk:preview` (turntable mp4 + thumbnail) and an ingest into the library. A build is a list of steps saved with the
asset (`meta.json` -> `build`): a server restart leaves it "building" and **Retry** resumes (it waits on recorded jobs or
resubmits an interrupted one). Only one build runs per asset.

## Using it (UI)
Workspace bar -> 🧊 **World Kit**.
1. **New asset**: pick the type, fill the form, **Make it**. The grid shows thumbnails and a status chip.
2. Open an asset: the 3D viewer (three.js, vendored, orbit controls, clips as buttons), the turntable, the step list and
   any failed step's error. **Retry**, **Approve for sets** (only a finished build that passes validation: sane scale,
   a rig for characters, a collider for props and places), **Unapprove**, **Archive** (moved to `_archive/`, never
   deleted), and for a character whose rig failed **Use as a static prop**. Characters take more clips with **Add clip**.
3. **From the studio**: every finished `.glb` card (3D tab: game-ready LODs, SAM 3D / TripoSplat meshes, rigs) has a
   **🧊 World Kit** button. It sends the mesh **by job reference only** to a new prop asset; the studio then runs
   `wk:cleanup` on it. That is how a studio 3D result enters the library.
4. **Export for a game** (left panel): every approved asset becomes a pack (below).

## Export for a game engine
`POST /api/worldkit/export` `{name?, assets?: [ids], placements?: [{asset, pos: [x, y, z], yaw_deg?, scale?}]}` writes
`<library root>/_exports/<name>-<stamp>/` and a `.zip` of it:

- `assets/<type>/<name>-<id4>.glb`: the approved glbs. Each is checked through the output guard first (same check as
  serving it in the UI); a withheld or still-checking file stops the export with the reason.
- `manifest.json` (`worldkit-pack/1`): per asset the real size (`scale_m`), rig bones, clip names, collider count, look,
  licence note (informational, never a gate), source job ids and the placements used.
- `scenes/main.tscn`: a Godot 4 text scene that instances the glbs. With no `placements` the first place sits at the
  origin and every character / prop stands in a row (a "showroom"). Placements are Blender Z-up metres; the scene
  converts to Y-up. Godot 4.7.2 is installed at `a local folder` since 2026-10-14, and the Game Builder's 3D stage imports these packs headless
  (see [game-builder.md](game-builder.md) "3D games"); `scenes/main.tscn` itself has still not been opened in the editor (it uses
  only plain `ExtResource` + `instance` lines); the glbs and the manifest are engine-neutral glTF 2.0.
- `IMPORT.txt`: copy the folder into a Godot project and open `scenes/main.tscn`. A node named `<x>-colonly` imports as
  a collision shape only, which is how a prop's or place's collider arrives.

Only **approved** assets are exported; a draft is refused by name.

## HTTP API (`earlier_studio/worldkit/api.py`; JSON, `no-store` on files)
- `GET /api/worldkit/assets?type=&tag=&q=&status=`, `GET /api/worldkit/assets/<id>`
- `GET /api/worldkit/assets/<id>/file/<asset.glb|preview.mp4|thumb.jpg>`: through `output_guard.serve_open`, judged by the
  asset's recorded source picture; 403 withheld, 503 + `Retry-After` while the guard is still checking
- `GET /api/worldkit/looks`, `GET /api/worldkit/characters` (who can become a 3D character, and why not)
- `POST /api/worldkit/assets` (create + start the build), `POST /api/worldkit/assets/<id>/<retry|approve|unapprove|archive|as-prop|clips>`
- `POST /api/worldkit/export`, `GET /api/worldkit/exports`, `GET /api/worldkit/exports/<name>.zip`

Studio entries (hidden group `wk_steps`, engine `blender`): `wk:place`, `wk:cleanup`, `wk:assemble`, `wk:preview`.
Cleanup and assemble run on the CPU lane (any GPU request from them raises); place and preview use EEVEE with a VRAM
reservation (peak recorded as 2.5 GiB) and fall back to CPU Cycles.

## Rules in force
  face-age estimate; the prop maker has no face check (removed on purpose, author 2026-10-13). The output guard judges a
  `.glb` by its source picture and every step's result like any studio render.
- Characters come only from saved sheets, never an upload.
- Ids are 12 lowercase letters (they travel in job fields, which the text guard reads).

## Not built yet (plan tasks 12-20, 22-24)
Virtual Set: camera presets and per-frame keys (12), shot schema (13), Blender passes (14), the three video-steering
modes A guide passes / B restyle / C keyframes (15-17), QC (18), the shot runner and `/api/vset` (19), the pipelines roles
(20, blocked on pipelines Wave 0), the shot-editor UI (22), the GPU bake-off with the author (23). A playable template and a "game" stage now exist for one genre (Game Builder, 3D games: third-person collect-the-items);
still not built: a city, NPCs, missions (spec items 3-5). See `the author's notes`.

## Troubleshooting
- **An asset says "interrupted - press Retry"**: the server restarted mid-build; Retry resumes it.
- **"the output guard has not cleared this output yet"**: the guard queue was busy; Retry when it is free.
- **Approve is refused**: the message lists why (e.g. a character with fewer rig bones than the humanoid minimum, a prop
  with no collider, a scale outside 1.5-2.0 m for a character).
- **Export refused with "approve these first"**: Approve for sets on each named asset.
- **A studio mesh will not add**: only `.glb` results (not quads, splats or previews) have the button, and the card's
  session must match (the mesh goes by job reference inside its own session).

## Prop build: why there is a cut-out step (2026-10-17)
The first live prop build (the 3D proof batch, W1) failed in the mesh step with "SAM 3D needs to know which object to build": SAM 3D Objects takes a mask (white = object) or an RGBA cut-out's own alpha, and refuses an RGB picture with neither (`mesh3d_tools.object_masks`). The prop maker therefore cuts the picture out first (`cutout` step, `img:bgremove`, BiRefNet: MIT; RMBG-2.0, which Pixal3D's own RGB path uses, is non-commercial and is not used) and hands the RGBA result to SAM 3D. The step is in the build list (`image`, `cutout`, `mesh`, `cleanup`, ...), so an existing prop build that stopped at `mesh` resumes with **Retry** and runs the cut-out first. Glass and liquids come out solid in BiRefNet's alpha ([edit-bg-remove-relight.md](edit-bg-remove-relight.md)). Tests: `tests/worldkit/test_prop_maker.py` (text, upload, job-reference picture and mesh sources).
