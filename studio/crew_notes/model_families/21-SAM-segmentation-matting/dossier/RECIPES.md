# RECIPES - 21-SAM-segmentation-matting

## Concrete Settings and Outcomes

| Model / Task | Steps / Method | Settings / Parameters | Outcome | Source |
| :--- | :--- | :--- | :--- | :--- |
| **SAM 2.1 Image Prediction** | 1. Load `SAM2ImagePredictor` from `facebook/sam2-hiera-large`.<br>2. Set image.<br>3. Predict with input prompts. | `torch.autocast("cuda", dtype=torch.bfloat16)` | Masks, scores, and logits for prompted objects. | [https://huggingface.co/facebook/sam2-hiera-large] |
| **SAM 2.1 Video Prediction** | 1. Load `SAM2VideoPredictor` from `facebook/sam2-hiera-large`.<br>2. Initialize state with video.<br>3. Add new points or box.<br>4. Propagate in video. | `torch.autocast("cuda", dtype=torch.bfloat16)` | Frame indices, object IDs, and masks throughout the video. | [https://huggingface.co/facebook/sam2-hiera-large] |
| **SAM 2.1 Automatic Mask Generation** | 1. Use `mask-generation` pipeline.<br>2. Feed image URL. | `points_per_batch=64` | 39 masks generated for the test image. | [https://huggingface.co/facebook/sam2-hiera-large] |
| **SAM 2.1 Single Point Click** | 1. Load `Sam2Model` and `Sam2Processor`.<br>2. Process image with single point input.<br>3. Post-process masks. | `input_points = [[[[500, 375]]]]`<br>`input_labels = [[[1]]]` | 3 masks with shape `torch.Size(1, 3, 1500, 2250)`. | [https://huggingface.co/facebook/sam2-hiera-large] |
| **SAM 2.1 Multiple Points Refinement** | 1. Process image with multiple positive points.<br>2. Post-process masks. | `input_points = [[[[500, 375], [1125, 625]]]]`<br>`input_labels = [[[1, 1]]]` | Refined segmentation masks. | [https://huggingface.co/facebook/sam2-hiera-large] |
| **SAM 2.1 Bounding Box Input** | 1. Process image with bounding box input.<br>2. Post-process masks. | `input_boxes = [[[75, 275, 1725, 850]]]` | Segmentation masks for the boxed region. | [https://huggingface.co/facebook/sam2-hiera-large] |
| **SAM 2.1 Multiple Objects** | 1. Process image with points for two objects.<br>2. Post-process masks. | `input_points = [[[[500, 375]], [[650, 750]]]]`<br>`input_labels = [[[1], [1]]]`<br>`multimask_output=False` | Masks for 2 objects. | [https://huggingface.co/facebook/sam2-hiera-large] |
| **SAM 2.1 Batched Images** | 1. Process multiple images simultaneously.<br>2. Post-process masks for each. | `input_points = [[[[500, 375]]], [[[770, 200]]]]`<br>`input_labels = [[[1]], [[1]]]`<br>`multimask_output=False` | Processed 2 images, each with 1 object. | [https://huggingface.co/facebook/sam2-hiera-large] |
| **SAM ViT-B Prompted Mask Generation** | 1. Load `SamModel` and `SamProcessor`.<br>2. Process image with point input.<br>3. Post-process masks. | `input_points = [[[450, 600]]]` | Masks and IoU scores. | [https://huggingface.co/facebook/sam-vit-base] |
| **SAM ViT-B Automatic Mask Generation** | 1. Use `mask-generation` pipeline.<br>2. Feed image URL. | `points_per_batch = 256` | Segmentation masks for all objects (zero-shot). | [https://huggingface.co/facebook/sam-vit-base] |
| **BiRefNet Inference** | 1. Load `BiRefNet` model.<br>2. Resize image to `(1024, 1024)`.<br>3. Normalize with mean `[0.485, 0.456, 0.406]` and std `[0.229, 0.224, 0.225]`.<br>4. Predict and apply sigmoid.<br>5. Resize mask to original image size. | `image_size = (1024, 1024)`<br>`torch.set_float32_matmul_precision(['high', 'highest'][0])`<br>`birefnet.half()` | Image with alpha channel (transparent background) and mask. | [https://huggingface.co/ZhengPeng7/BiRefNet] |
| **SAM 2 Video Optimization** | 1. Build SAM 2 video predictor.<br>2. Enable full model compilation. | `vos_optimized=True` | Major speedup for VOS inference. | [https://github.com/facebookresearch/sam2] |
| **ComfyUI Plan 1: SAM 2.1 Segmentation** | 1. Load model via `DownloadAndLoadSAM2Model`.<br>2. Auto-segment via `Sam2AutoSegmentation`.<br>3. Optional refinement via `Sam2Segmentation`. | Model: `sam2/sam2.1_hiera_large-fp16.safetensors` | Bounding boxes, refined mask, processed image. | [WORKFLOW_PLAN.md] |
| **ComfyUI Plan 2: BiRefNet Background Removal** | 1. Remove background via `BiRefNetRMBG`.<br>2. Optional mask enhancement via `AILab_MaskEnhancer`. | Model: `rmbg/BiRefNet/BiRefNet-general.safetensors` | Image with removed background, alpha mask. | [WORKFLOW_PLAN.md] |
| **ComfyUI Plan 3: SAM 3 Text-Guided Segmentation** | 1. Load model via `LoadSAM3Model`.<br>2. Segment via `SAM3Grounding` with text prompt. | Model: `sam3/sam3.pt` | Segmented image, mask, string output. | [WORKFLOW_PLAN.md] |

## Not in Sources
- CFG/guidance scale values.
- Specific sampler/scheduler names (e.g., Euler, DPM++).
- Shift/strength values for diffusion-based steps (as these models are primarily segmentation/matting, not diffusion generation).
- FPS or latency benchmarks for the specific local hardware.
- Exact API graph configurations for each model.

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
