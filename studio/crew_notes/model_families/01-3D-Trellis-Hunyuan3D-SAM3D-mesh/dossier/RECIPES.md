# RECIPES - 01-3D-Trellis-Hunyuan3D-SAM3D-mesh

| Model / Pipeline | Setting / Parameter | Value | Outcome / Note | Source |
| :--- | :--- | :--- | :--- | :--- |
| TRELLIS.2-4B | Resolution | 512³ | Inference time ~3 seconds on NVIDIA H100 GPU | [SOURCES.md] |
| TRELLIS.2-4B | Resolution | 1024³ | Inference time ~17 seconds on NVIDIA H100 GPU | [SOURCES.md] |
| TRELLIS.2-4B | Resolution | 1536³ | Inference time ~60 seconds on NVIDIA H100 GPU | [SOURCES.md] |
| TRELLIS.2-4B | Spatial downsampling | 16× | Encodes a 1024³ asset into ~9.6K latent tokens | [SOURCES.md] |
| TRELLIS.2-4B | `decimation_target` | 1000000 | Parameter used in `o_voxel.postprocess.to_glb` for GLB export | [SOURCES.md] |
| TRELLIS.2-4B | `texture_size` | 4096 | Parameter used in `o_voxel.postprocess.to_glb` for GLB export | [SOURCES.md] |
| TRELLIS.2-4B | `remesh_band` | 1 | Parameter used in `o_voxel.postprocess.to_glb` for GLB export | [SOURCES.md] |
| TRELLIS.2-4B | `remesh_project` | 0 | Parameter used in `o_voxel.postprocess.to_glb` for GLB export | [SOURCES.md] |
| TRELLIS.2-4B | `fps` | 15 | Frame rate for the sample video saved via `imageio.mimsave` | [SOURCES.md] |
| TRELLIS.2-4B | `simplify` | 16777216 | Limit applied to mesh via `mesh.simplify` before rendering | [SOURCES.md] |
| Hunyuan3D 2.0 | Pipeline | Two-stage | Stage 1: Shape generation (Hunyuan3D-DiT); Stage 2: Texture synthesis (Hunyuan3D-Paint) | [SOURCES.md] |
| Hunyuan3D 2.0 | Gradio version | 3.39.0 | Version of `gradio` installed for the local app | [SOURCES.md] |
| TripoSR | Training Hardware | 22 GPU nodes | Each node has 8 A100 40GB GPUs; trained for 5 days | [SOURCES.md] |
| SAM-3D-Objects | Input | Image + Mask | Required inputs for `CampBSAM3DObjects` node | [WORKFLOW_PLAN.md] |
| UniRig | Input | `FILE_3D` | Required input for `CampBUniRig` node | [WORKFLOW_PLAN.md] |

Not in sources: CFG/guidance scale values for any model in this family.
Not in sources: Specific sampler or scheduler names (e.g., Euler, DPM++).
Not in sources: Number of inference steps for Hunyuan3D, SAM-3D-Objects, or TripoSR.
Not in sources: Shift or strength values for any model in this family.
Not in sources: Specific resolution settings for Hunyuan3D, SAM-3D-Objects, or TripoSR.

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
