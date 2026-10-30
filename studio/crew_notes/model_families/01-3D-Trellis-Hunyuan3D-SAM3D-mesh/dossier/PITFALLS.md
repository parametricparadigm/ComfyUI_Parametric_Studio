# PITFALLS - 01-3D-Trellis-Hunyuan3D-SAM3D-mesh

## TRELLIS-2-4B: Geometric Artifacts in Raw Meshes
*   **Symptom**: Generated raw meshes contain small holes or minor topological discontinuities.
*   **Cause**: While the O-Voxel structure handles complex topology, the raw output from the model is not guaranteed to be strictly watertight.
*   **Fix**: Use accompanying mesh post-processing scripts, such as hole-filling algorithms, or the `Trellis2PostProcessMesh` node in ComfyUI workflows.
*   **Source**: [PUBLIC README https://huggingface.co/microsoft/TRELLIS.2-4B/raw/main/README.md], [WORKFLOW_PLAN.md]

## TRELLIS-2-4B: Operating System Incompatibility
*   **Symptom**: The model may fail to run or is not supported on non-Linux systems.
*   **Cause**: The model is currently tested only on Linux.
*   **Fix**: Ensure the execution environment is a Linux system.
*   **Source**: [PUBLIC README https://huggingface.co/microsoft/TRELLIS.2-4B/raw/main/README.md]

## TRELLIS-2-4B: Hardware Memory Limit
*   **Symptom**: Out-of-memory errors or failure to load the model.
*   **Cause**: The model requires an NVIDIA GPU with at least 24GB of memory.
*   **Fix**: Use a GPU with at least 24GB VRAM (e.g., NVIDIA A100 or H100). The local setup uses a 96 GB Blackwell card which is sufficient.
*   **Source**: [PUBLIC README https://huggingface.co/microsoft/TRELLIS.2-4B/raw/main/README.md], [MODEL.md]

## TRELLIS-2-4B: Software Dependency Requirements
*   **Symptom**: Compilation errors or missing dependencies during installation.
*   **Cause**: The code requires the CUDA Toolkit (recommended version 12.4) and Python version 3.8 or higher. Conda is recommended for managing dependencies.
*   **Fix**: Install the CUDA Toolkit and ensure Python version is 3.8+. Use Conda for dependency management.
*   **Source**: [PUBLIC README https://huggingface.co/microsoft/TRELLIS.2-4B/raw/main/README.md]

## TRELLIS-2-4B: Unaligned Aesthetic Output
*   **Symptom**: Outputs vary in style and may not meet specific aesthetic standards or human preferences.
*   **Cause**: TRELLIS.2-4B is a pre-trained foundation model that has not been aligned with human preferences (e.g., via RLHF) or fine-tuned for specific aesthetic standards.
*   **Fix**: Users may need to experiment with inputs to achieve the desired artistic result.
*   **Source**: [PUBLIC README https://huggingface.co/microsoft/TRELLIS.2-4B/raw/main/README.md]

## Hunyuan3D-2.1: Workflow Node Input Mismatch
*   **Symptom**: Inability to construct a pure image-to-3D workflow using only the listed ComfyUI nodes for Hunyuan3D-2.1.
*   **Cause**: The `CampBHunyuan3DPaint` node requires a `FILE_3D` input, implying it is for texturing an existing mesh. There is no standalone "Hunyuan3D Shape Generator" node listed that outputs a `FILE_3D` or `TRIMESH` directly from an image without a pre-existing mesh input for the paint node.
*   **Fix**: The shape generation step might be handled by a different node not listed, or the `FILE_3D` input might be optional/ignored in some configurations (not stated in sources). Alternatively, use SAM-3D-Objects for image-to-3D if a mask is available.
*   **Source**: [WORKFLOW_PLAN.md]

## SAM-3D-Objects: Mask Dependency
*   **Symptom**: The `CampBSAM3DObjects` node cannot process the input image correctly if the object is not isolated.
*   **Cause**: The node requires a `MASK` input to isolate the object. If no mask generation node is available in the current graph, this step is a bottleneck.
*   **Fix**: Use an image with a transparent background and load it using `Trellis2LoadImageWithTransparency` to generate the `MASK`, or provide the mask externally.
*   **Source**: [WORKFLOW_PLAN.md]

## UniRig: Data Type Mismatch
*   **Symptom**: The `CampBUniRig` node may not accept the output from standard mesh loading nodes directly.
*   **Cause**: `CampBUniRig` expects a `FILE_3D` input, while nodes like `GeomPackLoadMeshPath` output a `TRIMESH`. There is no explicitly listed node that converts `TRIMESH` to `FILE_3D`.
*   **Fix**: Ensure the mesh is already in a `FILE_3D` format (e.g., from a previous generation step like TRELLIS-2-4B export) before passing it to `CampBUniRig`.
*   **Source**: [WORKFLOW_PLAN.md]

## General: Precision and Format Variance
*   **Symptom**: Potential compatibility issues or performance variations depending on the specific model file used.
*   **Cause**: Models in the family are stored in various precisions, including FP16, BF16, and F32. For example, TRELLIS-2-4B DiTs are BF16, while its VAEs are F16. Hunyuan3D-2.1 DiT is FP16.
*   **Fix**: Ensure the loading nodes and pipeline configurations match the precision of the specific model files (e.g., `slat_flow_img2shape_dit_1_3B_1024_bf16.safetensors` for TRELLIS).
*   **Source**: [MODEL.md], [LOCAL_MODELS.tsv], [WORKFLOW_PLAN.md]

## General: Backend Integration Constraints
*   **Symptom**: Models may not be usable by the Parametric Studio backend.
*   **Cause**: The models must have their Python dependencies in the Parametric Studio venv, their nodes must be placeable in API-format graphs, they must not conflict with the PS torch/CUDA pins, and their model files must be under the designated models directory.
*   **Fix**: Verify Python dependencies are installed in the correct venv, check for torch/CUDA conflicts, and ensure files are in the correct directory.
*   **Source**: [MODEL.md]

## Not in sources: Specific quantization format incompatibilities (e.g., INT8/INT4)
## Not in sources: Specific scheduler incompatibilities for Hunyuan3D or TRELLIS
## Not in sources: Specific version conflicts between ComfyUI node packs (e.g., ComfyUI-Trellis2 vs. PozzettiAndrea__ComfyUI-TRELLIS2)

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
