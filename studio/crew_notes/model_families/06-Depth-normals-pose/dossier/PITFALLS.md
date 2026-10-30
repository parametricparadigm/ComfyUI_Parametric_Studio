# PITFALLS - 06-Depth-normals-pose

## Backend Configuration Mismatch
*   **Symptom:** API requests fail or are sent to the wrong server instance.
*   **Cause:** `COMFY_BASE_URL` points at the wrong ComfyUI server.
*   **Fix:** Set `COMFY_BASE_URL` to the address of your running ComfyUI.
*   **Source:** [MODEL.md]

## Sapiens2-Pose Missing Detector Dependency
*   **Symptom:** Pose estimation fails or produces no output because the model is top-down and requires bounding boxes.
*   **Cause:** Sapiens2-Pose requires bounding boxes from a person detector. The documentation references RTMDet, but local files show `YOLOv8m` is the available detector. If the specific detector model file is not present or correctly configured, the pipeline cannot generate the required input boxes.
*   **Fix:** Ensure a compatible person detector (such as `YOLOv8m` or RTMDet) is installed and its model files are available in the expected path to generate bounding boxes before running Sapiens2-Pose.
*   **Source:** [MODEL.md], [SOURCES.md], [PUBLIC README https://huggingface.co/facebook/sapiens2-pose-1b/raw/main/README.md]

## DWPose Missing Detector Dependency
*   **Symptom:** DWPose inference fails or does not detect humans.
*   **Cause:** DWPose is a two-stage approach that requires a person detector (YOLOX) to function. The `DWPreprocessor` node may require the detector model to be available in a specified path.
*   **Fix:** Ensure the YOLOX detector model (e.g., `yolox_l.torchscript.pt` or `yolox_l.onnx`) is downloaded and placed in the correct directory for the DWPose pipeline.
*   **Source:** [MODEL.md], [WORKFLOW_PLAN.md], [PUBLIC README https://raw.githubusercontent.com/IDEA-Research/DWPose/HEAD/README.md]

## Depth Anything V2 Resolution Mismatch
*   **Symptom:** The generated depth map does not match the dimensions of the original input image.
*   **Cause:** The model outputs a depth map at a specific resolution that may differ from the input image size.
*   **Fix:** Interpolate the predicted depth to the original image size using bicubic interpolation (`torch.nn.functional.interpolate` with `mode="bicubic"` and `align_corners=False`).
*   **Source:** [MODEL.md], [PUBLIC README https://huggingface.co/depth-anything/Depth-Anything-V2-Small-hf/raw/main/README.md], [PUBLIC README https://huggingface.co/depth-anything/Depth-Anything-V2-Large-hf/raw/main/README.md]

## Sapiens2 Environment Requirements
*   **Symptom:** Installation or execution of Sapiens2 fails due to missing dependencies or version conflicts.
*   **Cause:** The Sapiens2 repository requires Python ≥3.12 and PyTorch ≥2.7. The local environment uses torch 2.16.0.dev20261027+cu134, which satisfies the version requirement, but specific Python dependencies for node packs are not listed in the material.
*   **Fix:** Verify that the Python version is ≥3.12 and PyTorch is ≥2.7. Ensure the Sapiens2 repo is installed via `pip install -e .` and checkpoints are placed under `$SAPIENS_CHECKPOINT_ROOT`.
*   **Source:** [MODEL.md], [PUBLIC README https://raw.githubusercontent.com/facebookresearch/sapiens2/HEAD/README.md]

## Marigold Model Loading Ambiguity
*   **Symptom:** Uncertainty in how to load specific Marigold components (UNet, Text Encoder, VAE) for depth vs. normals.
*   **Cause:** The workflow plan notes that `MarigoldModelLoader` likely handles loading based on the selected model type, but specific normal nodes are not listed separately from `MarigoldDepthEstimation` in the provided material.
*   **Fix:** Use `MarigoldModelLoader` to load the specific model variant (depth or normals) and connect it to `MarigoldDepthEstimation`. Verify that the correct UNet, text encoder, and VAE files (e.g., `diffusion_pytorch_model.fp16.safetensors`) are present in the `depthanything/marigold-depth-v1-1` and `depthanything/marigold-normals-v1-1` folders.
*   **Source:** [WORKFLOW_PLAN.md], [LOCAL_MODELS.tsv]

## DWPose Input Size Variance
*   **Symptom:** Suboptimal pose estimation accuracy or errors if input size is not matched to the model variant.
*   **Cause:** DWPose models have different input sizes depending on the variant (e.g., 256x192 for smaller models, 384x288 for larger models). Using an incorrect input size for the specific checkpoint can degrade performance.
*   **Fix:** Match the input image resolution to the specific DWPose model variant being used (e.g., use 384x288 for `dw-ll_ucoco_384`).
*   **Source:** [MODEL.md], [PUBLIC README https://raw.githubusercontent.com/IDEA-Research/DWPose/HEAD/README.md]

## Sapiens2 Inference Resolution Constraint
*   **Symptom:** Model performance degradation or errors if input resolution is not standard.
*   **Cause:** Sapiens2 models are trained at a specific inference resolution of 1024 × 768 (H × W) with a patch size of 16.
*   **Fix:** Resize input images to 1024 × 768 (H × W) before passing them to the Sapiens2 model.
*   **Source:** [MODEL.md], [SOURCES.md], [PUBLIC README https://huggingface.co/facebook/sapiens2-pose-1b/raw/main/README.md], [PUBLIC README https://raw.githubusercontent.com/facebookresearch/sapiens2/HEAD/README.md]

## Not in sources: Specific VRAM limits for individual models beyond the total family size and largest file sizes.
## Not in sources: Specific quantization format incompatibilities (e.g., INT8, INT4) for any model in this family.
## Not in sources: Specific scheduler incompatibilities for Marigold or other diffusion-based models.
## Not in sources: Specific error messages or crash logs for failure modes.
## Not in sources: Performance benchmarks (inference speed) for local models.
## Not in sources: Specific version of the `transformers` library required for Depth Anything V2, other than compatibility with the library.

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
