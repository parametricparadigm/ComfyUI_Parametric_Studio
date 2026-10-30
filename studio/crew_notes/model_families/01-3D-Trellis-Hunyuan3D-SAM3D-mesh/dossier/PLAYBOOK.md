# PLAYBOOK.md: 01-3D-Trellis-Hunyuan3D-SAM3D-mesh

## Prompt structure

*   **Not in notes:** The provided documents do not contain specific text-to-image prompt engineering guidelines, keyword lists, or natural language phrasing instructions for generating 3D meshes from text prompts. The notes focus on code architecture, installation, weight management, and node wiring rather than semantic prompt crafting.
*   **Input Modality:** The primary input for the mesh generation models (TRELLIS.2, Hunyuan3D 2.1, Pixal3D) is **image-based**, not text-based. The system accepts "Image → textured PBR mesh" or "Image / multi-view → mesh" [3D_GAP_SCOUT_2026-10-11.md].
*   **Conditioning Nodes:** For Pixal3D, specific conditioning nodes are available: Pixal3DConditioning and Pixal3DMultiViewConditioning [3D_GAP_SCOUT_2026-10-11.md].
*   **SAM 3D Body Input:** For body mesh generation, the input is a photo or video track. The SAM3DBody_Predict node accepts SAM3_TRACK_DATA (from SAM 3.1 video track), detector bounding boxes, or full-frame images [SAM3D_BODY_HELPERS_SCOUT_2026-10-11.md].
*   **SAM 3D Objects Input:** For object extraction from cluttered photos, the input is "One real/cluttered photo + one object mask" [3D_INSTALLS_2026-10-11.md].

## Words and phrasing that work

*   **Not in notes:** There are no specific "magic words," trigger phrases, or semantic keywords documented in the provided files that improve mesh quality or fidelity.
*   **Technical Parameters as "Phrasing":** Instead of natural language prompts, the "phrasing" that works is defined by specific node parameters and model configurations:
    *   **TRELLIS.2:** Uses trellis_2_int8_convrot core with shape/texture VAEs and DINOv3 [3D_GAP_SCOUT_2026-10-11.md].
    *   **Hunyuan3D 2.1:** Supports --engine hunyuan and retexture flags in the pipeline [3D_GAP_SCOUT_2026-10-11.md].
    *   **SAM 3D Body:** Uses run_hand_refinement for hand details and gaussian/7/15 smoothing values for temporal stability [SAM3D_BODY_HELPERS_2026-10-11.md].
    *   **SAM 3D Objects:** Requires a specific "object mask" alongside the photo to isolate the target [3D_INSTALLS_2026-10-11.md].

## Settings that worked

*   **Hunyuan3D 2.1 Performance:**
    *   **Size:** 14 GB model [3D_GAP_SCOUT_2026-10-11.md].
    *   **Status:** Proven to work, but the first paint run can segfault [3D_GAP_SCOUT_2026-10-11.md].

*   **Pixal3D Performance:**
    *   **Size:** 23 GB model [3D_GAP_SCOUT_2026-10-11.md].
    *   **VRAM Peak:** 16.4 / 16.2 GB [3D_GAP_SCOUT_2026-10-11.md].
    *   **Time:** Mesh finalization takes ~6.5 minutes, mostly due to UV parameterization [3D_GAP_SCOUT_2026-10-11.md].
    *   **Output:** Generates GLBs of 39–40 MB [3D_GAP_SCOUT_2026-10-11.md].

*   **SAM 3D Body Settings:**
    *   **Smoothing:** SAM3DBody_Smooth uses gaussian/savgol with window ≤ 51. Official template values are gaussian/7/15 [SAM3D_BODY_HELPERS_SCOUT_2026-10-11.md].
    *   **Weights:** sam3/SAM 3D BODY/model.safetensors (2.13 GB) is byte-identical to the Pozzetti repack but may be rejected by the core loader due to missing keys (1053 missing keys reported in HANDOFF) [SAM3D_BODY_HELPERS_SCOUT_2026-10-11.md].
    *   **BodyMod Pack:** Uses SAM3DBodyMod_DetectShape to build a shape profile from 1–4 reference images to remove shape flicker [SAM3D_BODY_HELPERS_SCOUT_2026-10-11.md].

*   **General Environment:**
    *   **Python/Torch:** Tools generally use isolated venvs. TRELLIS uses venv-cu134 with torch 2.15.0.dev+cu134 [TRELLIS2_AND_HUNYUAN3D_PART.md]. SAM 3D Objects uses torch 2.14.1+cu132 [3D_INSTALLS_2026-10-11.md].
    *   **Pickle Scanning:** All .pt/.pth/.ckpt files must be scanned with ~/tools/3d-common/pickle_gate.sh before first load [3D_INSTALLS_2026-10-11.md].

## Processes built on it

*   **Studio Integration:**
    *   TRELLIS is wired to studio 3d:trellis and pp 06 / pp 59 default [3D_GAP_SCOUT_2026-10-11.md].
    *   Hunyuan3D is wired to studio 3d:hunyuan [3D_GAP_SCOUT_2026-10-11.md].
    *   UniRig is wired to studio rig chip [3D_GAP_SCOUT_2026-10-11.md].

*   **Pipeline Extensions (pp 06):**
    *   extras.py multiview for TRELLIS.2-4B [3D_GAP_SCOUT_2026-10-11.md].
    *   --engine hunyuan and retexture for Hunyuan3D [3D_GAP_SCOUT_2026-10-11.md].
    *   extras.py rig for UniRig [3D_GAP_SCOUT_2026-10-11.md].
    *   render.py for Blender EEVEE turntable (192 frames, 1080²) [3D_GAP_SCOUT_2026-10-11.md].
    *   extras.py remesh/decimate for mesh cleanup [3D_GAP_SCOUT_2026-10-11.md].

*   **Mesh Post-Processing:**
    *   Core nodes RemeshMesh, DecimateMesh, UnwrapMesh, RenderUVAtlas, BakeNormalMapFromMesh, BakeAmbientOcclusion, PaintMesh, BakeTextureFromVoxel, FillHoles, WeldVertices are used inside TRELLIS graphs [3D_GAP_SCOUT_2026-10-11.md].
    *   Typical TRELLIS graph settings: remesh 768, decimate 700k [3D_GAP_SCOUT_2026-10-11.md].

*   **SAM 3D Body Workflow:**
    *   **Shape Locking:** Use SAM3DBodyMod_DetectShape on reference images to create a consistent shape profile, then apply it to the animated pose data to remove flicker [SAM3D_BODY_HELPERS_SCOUT_2026-10-11.md].
    *   **Camera Drive:** SAM3DBodyMod_CameraDrive allows keyframed camera orbit before rendering [SAM3D_BODY_HELPERS_SCOUT_2026-10-11.md].
    *   **Export:** BuildPoseFile exports skinned GLB (with 72 face morph targets), OpenPose GLB, or BVH [SAM3D_BODY_HELPERS_SCOUT_2026-10-11.md].
    *   **Retargeting:** SOMA-X adapter (mhr2soma.py) converts MHR (SAM 3D Body) to SOMA77 skeleton for use with Kimodo/GEM-X [SAM3D_BODY_HELPERS_SCOUT_2026-10-11.md].

*   **Blender Integration:**
    *   Blender 5.2.2 LTS is used for DCC
