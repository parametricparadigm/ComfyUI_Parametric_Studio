# PROMPTING - 06-Depth-normals-pose

## Prompt Structure and Language
The models in this family primarily accept RGB images as input, not text prompts, for their core estimation tasks.
- **Depth Anything V2**: Uses a `transformers` pipeline where the input is an image object. The code example shows `pipe(image)["depth"]`, indicating no text prompt is passed to the depth estimation function [MODEL.md].
- **Sapiens2-Pose**: Requires bounding boxes from a person detector (e.g., RTMDet or YOLOv8) as input, in addition to the image. It does not accept text prompts for pose estimation [MODEL.md].
- **DWPose**: Uses a detector (YOLOX) with a pose estimator to generate keypoint maps. The input is an image, and the detector handles the localization [MODEL.md].
- **Marigold**: This is the only model in the family explicitly stated to be conditioned on text and image inputs. It uses a text encoder to process text prompts [MODEL.md].

## Negative Prompts
Not in sources: Specific guidance on negative prompts for any model in this family.

## Style and Camera Vocabulary
Not in sources: Specific style or camera vocabulary requirements for prompting.

## Text Encoder Behavior
- **Marigold**: The text encoder encodes text prompts into embeddings for the Marigold normal estimation diffusion model and for Marigold depth estimation. The text encoder is a separate component (0.63 GB) used in the pipeline [MODEL.md].
- **Other Models**: Depth Anything V2, Sapiens2, and DWPose do not have text encoders listed as part of their core inference pipeline in the provided evidence. They rely on image inputs and, in the case of pose models, detector bounding boxes [MODEL.md].

## Prompt Length
Not in sources: Specific prompt length requirements or limits.

## Model-Specific Prompting Notes
- **Marigold**: As a diffusion-based approach, it denoises latent representations to generate depth or normal maps, conditioned on text and image inputs. The workflow involves loading the model, connecting the image, and using the text encoder for conditioning [MODEL.md].
- **Depth Anything V2**: Trained on synthetic and real unlabeled images to predict relative or absolute depth. It is noted to be more efficient and robust than SD-based models, implying it does not require the complex text conditioning of SD-based models like Marigold [MODEL.md].
- **Sapiens2-Pose**: A top-down pose estimation model. The "prompt" is effectively the bounding box provided by the detector. It predicts 308 keypoints [MODEL.md].
- **DWPose**: Uses a two-stage distillation approach. The "prompt" is the detected person bounding box from the YOLOX detector [MODEL.md].

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
