# RECIPES - 06-Depth-normals-pose

## Sapiens2-Pose

| Setting | Value | Outcome / Notes | Source |
| :--- | :--- | :--- | :--- |
| Inference resolution | `1024 × 768` (H × W) | Standard input size for the model. | [MODEL.md], [SOURCES.md], [PUBLIC README https://huggingface.co/facebook/sapiens2-pose-1b/raw/main/README.md] |
| Patch size | `16` | Defines the tokenization granularity for the Vision Transformer. | [MODEL.md], [SOURCES.md], [PUBLIC README https://huggingface.co/facebook/sapiens2-pose-1b/raw/main/README.md] |
| Detector | `RTMDet` | Required to generate bounding boxes for top-down pose estimation. | [MODEL.md], [SOURCES.md], [PUBLIC README https://huggingface.co/facebook/sapiens2-pose-1b/raw/main/README.md] |
| Keypoints | `308` | Predicts 308 keypoints including detailed face, hand, and foot keypoints. | [MODEL.md], [SOURCES.md], [PUBLIC README https://huggingface.co/facebook/sapiens2-pose-1b/raw/main/README.md] |
| Steps | Not in sources: steps | | |
| CFG/guidance | Not in sources: CFG/guidance | | |
| Sampler/scheduler | Not in sources: sampler/scheduler | | |
| Frames/fps | Not in sources: frames/fps | | |
| Shift/strength | Not in sources: shift/strength | | |

## DWPose

| Setting | Value | Outcome / Notes | Source |
| :--- | :--- | :--- | :--- |
| Input Size (DWPose-t/s/m/l) | `256x192` | Input resolution for smaller model variants. | [MODEL.md], [PUBLIC README https://raw.githubusercontent.com/IDEA-Research/DWPose/HEAD/README.md] |
| Input Size (DWPose-l) | `384x288` | Input resolution for the larger model variant. | [MODEL.md], [PUBLIC README https://raw.githubusercontent.com/IDEA-Research/DWPose/HEAD/README.md] |
| Detector | `YOLOX` | Detects human bounding boxes for pose estimation. | [MODEL.md], [SOURCES.md] |
| Steps | Not in sources: steps | | |
| CFG/guidance | Not in sources: CFG/guidance | | |
| Sampler/scheduler | Not in sources: sampler/scheduler | | |
| Frames/fps | Not in sources: frames/fps | | |
| Shift/strength | Not in sources: shift/strength | | |

## Depth Anything V2

| Setting | Value | Outcome / Notes | Source |
| :--- | :--- | :--- | :--- |
| Post-processing | Interpolate to original image size | Predictions are often interpolated to the original image size. | [MODEL.md] |
| Steps | Not in sources: steps | | |
| CFG/guidance | Not in sources: CFG/guidance | | |
| Sampler/scheduler | Not in sources: sampler/scheduler | | |
| Resolution | Not in sources: fixed resolution (interpolated to input) | | |
| Frames/fps | Not in sources: frames/fps | | |
| Shift/strength | Not in sources: shift/strength | | |

## Marigold

| Setting | Value | Outcome / Notes | Source |
| :--- | :--- | :--- | :--- |
| Precision | `FP16` | Used for UNet, text encoder, and VAE. | [MODEL.md], [LOCAL_MODELS.tsv] |
| Steps | Not in sources: steps | | |
| CFG/guidance | Not in sources: CFG/guidance | | |
| Sampler/scheduler | Not in sources: sampler/scheduler | | |
| Resolution | Not in sources: resolution | | |
| Frames/fps | Not in sources: frames/fps | | |
| Shift/strength | Not in sources: shift/strength | | |

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
