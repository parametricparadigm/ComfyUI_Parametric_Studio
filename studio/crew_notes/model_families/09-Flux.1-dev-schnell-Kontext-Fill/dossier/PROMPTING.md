# PROMPTING - 09-Flux.1-dev-schnell-Kontext-Fill

## Prompt Structure and Encoding
The Flux.1 family utilizes a diffusion transformer architecture where the inference process involves conditioning the model using text encoders [MODEL.md]. Specifically, the system uses T5-XXL and CLIP-L text encoders to provide conditioning for the diffusion models [MODEL.md]. For the Kontext variant, specific text encoders (T5-XXL and CLIP-L) are located in `_complete_pipelines/Flux-Kontext/text_encoders` and provide conditioning for the Flux-Kontext diffusion model [MODEL.md, LOCAL_MODELS.tsv].

In the ComfyUI workflow context, the prompt is processed by the `CLIPTextEncode` node, which takes the `CLIP` output from the model loader and outputs `CONDITIONING` [WORKFLOW_PLAN.md]. This conditioning is then passed to the `FluxGuidance` node to set the guidance scale before being used in the sampling process [WORKFLOW_PLAN.md].

## Prompt Language and Content
The primary input for text-to-image and image editing tasks is a text prompt [MODEL.md]. For the `FLUX.1 Kontext [dev]` model, the prompt is used for in-context image generation and editing based on prompts and reference images [MODEL.md]. An example of a prompt structure for the Kontext variant is provided in the official repository documentation: "replace the logo with the text 'Black Forest Labs'" [PUBLIC README https://raw.githubusercontent.com/black-forest-labs/flux/HEAD/README.md].

Not in sources: Specific language requirements (e.g., English only) or token limits for the T5-XXL and CLIP-L encoders.

## Negative Prompts
Not in sources: Whether negative prompts are supported or required for the Flux.1 family.

## Style and Camera Vocabulary
Not in sources: Specific style or camera vocabulary recommendations or supported tags.

## Text Encoder Behavior
The text encoders (T5-XXL and CLIP-L) are responsible for converting the text prompt into conditioning signals for the diffusion transformer [MODEL.md]. The T5-XXL encoder is a 4.77B parameter model (BF16) and the CLIP-L encoder is a 0.12B parameter model (BF16) for the main Flux.1 pipeline [MODEL.md, LOCAL_MODELS.tsv]. For the Kontext variant, the text encoders are in F16 precision [MODEL.md, LOCAL_MODELS.tsv]. The encoders output conditioning that is subsequently modified by the `FluxGuidance` node to apply the guidance scale [WORKFLOW_PLAN.md].

## Guidance and Sampling
The `FluxGuidance` node is used to set the guidance scale, which is a critical parameter for controlling how strictly the model follows the prompt [WORKFLOW_PLAN.md]. The specific default values for sampling steps and guidance scales are not stated in the provided materials [MODEL.md]. Users must determine these settings manually or use defaults if available in the specific node implementation [WORKFLOW_PLAN.md].

## Variant-Specific Prompting Notes
- **FLUX.1 [schnell] / [dev]**: Used for Text to Image. The prompt is encoded by the standard Flux.1 text encoders [MODEL.md].
- **FLUX.1 Kontext [dev]**: Used for Image Editing. The prompt works in conjunction with reference images for in-context editing [MODEL.md].
- **FLUX.1 Fill [dev]**: Used for In/Out-painting. While the primary input is a mask, text prompts are part of the general input set for the family [MODEL.md].
- **Structural Conditioning (Canny/Depth)**: These variants use ControlNet adapters or LoRAs to guide generation based on structural maps (Canny edges or depth maps) in addition to text prompts [MODEL.md].

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
