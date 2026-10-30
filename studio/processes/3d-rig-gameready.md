# Rig and game-ready LODs

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


## How to start them
- On a finished 3D card (TRELLIS.2, Hunyuan3D, Pixal3D, SAM 3D object, TripoSplat mesh, an LOD): **🦴 Rig**
  (SkinTokens → GLB + FBX), **🦴 Rig (UniRig)** (the older rigger, GLB), **🎮 Game-ready** (from an unrigged GLB/OBJ).
  Each makes a new card. With several models on one card the buttons are numbered (or named by LOD).
- The mesh goes by job reference only. The server copies the source picture of the mesh's own job onto the new job,
  because the output guard judges a 3D model by the picture it was built from; an uploaded mesh (no picture) is refused.

## Rig this mesh (SkinTokens, default)
| Setting | Value | Source |
|---|---|---|
| Command | `a local folder --input M --output rigged.glb --use_transfer` (10 beams) | [tested] smoke_test.sh 2026-10-11 |
| Output | rigged GLB: skeleton + skin weights transferred onto the original mesh, texture + scale kept | [tested] smoke + deform_check.txt |
| FBX | Blender converts the GLB (armature + skin, no leaf bones); textures NOT embedded: the output guard withholds an FBX with an image inside, so use the GLB for textures | [tested] glb_to_fbx.py on both smoke rigs 2026-10-11 |
| Skeleton sheet | bones as orange sticks through a ghosted body, front + side (`rig_preview.py`, rest pose) | [tested] both smoke rigs 2026-10-11 |
| Seed | none: SkinTokens samples; the studio seed only names the run, a retry rigs again and can differ | [documented] demo.py has no seed flag |
- VRAM: measured 4.2-5.1 GB (README asks for 14 GB); the studio budgets 6 + 4 GiB. 62-87 s.
- One run at a time: its Blender helper holds the local server (patched from 0.0.0.0); a busy port is refused.

## Rig (UniRig) — fallback
| Setting | Value | Source |
|---|---|---|
| Command | `a local folder a local folder rig --input M --out OUT.(glb|fbx) --seed 12345 --faces 50000` | [tested] pp 06 `pp.three_d.rig` (PROVEN ~60 s) |
| Output | skeleton + skin weights merged onto the original mesh, textures kept; + skeleton sheet | [tested] pp 06 |
| Pose | A-pose characters rig best (arm weights bleed into hips otherwise) | [tested] pp 06 note 2026-10-07 |
- VRAM: 12 GiB budget (pp.three_d; not a measured peak) + 4 headroom. ~1 min. FBX via the API (`settings.format`).

## Game-ready LODs (AutoRemesher, one object)
| Step | Values | Source |
|---|---|---|
| Object count | Blender voxel remesh (256 voxels across), loose parts over 1 % of the faces and not nested in another = objects (`mesh_parts.py`) | [tested] bottle 1, SAM 3D objects 1, humanoid 1, Pixal3D chair scene 3, desk scene 2 (2026-10-11) |
| Prep | Blender voxel remesh 256 → one watertight shell (TRELLIS / Pixal3D meshes are stacks of shells) | [tested] runner default |
| LODs | `run_autoremesher.sh M OUT 20000 5000 1500` → quads OBJ + triangulated GLB per LOD | [tested] smoke: 8,684 / 2,181 / 467 quads, ~99 % quads, 10 s |
| Colour | none: geometry only, no UVs | [tested] runner note |
- CPU only (no VRAM). Single objects only: a scene lost its small parts at LOD0 and was nearly empty at LOD2 (smoke).

## Game-ready fallback (core mesh nodes, UNTESTED chain) — scenes of several objects
Taken when the model holds more than one object (or AutoRemesher / the object count is unavailable); the card says why.
For quad LODs of a scene, build each object on its own (Photo → 3D objects) and press Game-ready on each.
| Step | Values | Source |
|---|---|---|
| Load | Load3DAdvanced → Get3DComponents (GLB/glTF/OBJ; not FBX) | [documented] core node |
| Remesh | RemeshMesh 768, udf, smooth 20, drop 0.01 | [tested] pp06_trellis2_pbr |
| LODs | DecimateMesh midpoint to 20k / 5k / 1.5k triangles, MeshSmoothNormals 180 | targets [inference] (scout's suggested test) |
| UV | UnwrapMesh pec, 1024, padding 1, weld 0.0002 | [tested] pp06_trellis2_pbr |
| Bakes | BakeNormalMapFromMesh 1024 cage 0.05 backfaces on; BakeAmbientOcclusion 1024, 64 rays, 0.71, 1.0, 0.01 | [tested] pp06_trellis2_pbr |
| Colour | flat grey base colour (0x8C8C8C): core has no mesh-to-mesh colour bake | [inference] |
- VRAM unknown (mesh ops on the GPU); 16 GiB budgeted. The graph validates against  a local port `/object_info` (2026-10-11).

## Evidence
- Studio tool path 2026-10-11 (`outputs/studio_3dtools_smoke_2026-10-11/moe_mesh3d/`): `skinrig` on the UniRig humanoid
  example → GLB + FBX (1 mesh, 22 bones, no embedded images) + previews + skeleton sheet in 69 s; `gameready` on the
  SAM 3D compass → 1 object → 14,669 / 2,646 / 605 quads in 39 s; `count_objects` on the Pixal3D chair scene → 3.
- Blender's glTF importer adds an Icosphere object as the bones' display shape; the preview / FBX scripts drop it.
  `outputs/skintokens_smoke_2026-10-11/`, `outputs/autoremesher_smoke_2026-10-11/final_voxel/`.
- https://github.com/VAST-AI-Research/SkinTokens · https://github.com/VAST-AI-Research/UniRig ·
  https://github.com/huxingyi/autoremesher
