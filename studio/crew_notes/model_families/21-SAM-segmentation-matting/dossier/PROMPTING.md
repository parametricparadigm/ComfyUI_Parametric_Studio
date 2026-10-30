# PROMPTING - 21-SAM-segmentation-matting

## Prompt Structure and Types

The "prompt" for this model family is not natural language text but rather spatial or geometric inputs. The specific structure depends on the model variant:

*   **SAM 3:**
    *   **Text Prompts:** SAM 3 supports text-based segmentation. The `SAM3Grounding` node accepts a `STRING` input for the text prompt [WORKFLOW_PLAN.md].
    *   **Boxes and Points:** The `SAM3Grounding` node also requires `SAM3_BOXES_PROMPT` and `SAM3_POINTS_PROMPT` inputs, which may be empty or default if text grounding is the primary mode [WORKFLOW_PLAN.md].

*   **BiRefNet, ViTMatte, CorridorKey, U2-Net:**
    *   These models do not use user-defined prompts. They operate on the input image directly to perform background removal, matting, or salient object detection [MODEL.md] [https://huggingface.co/ZhengPeng7/BiRefNet].

## Prompt Length and Quantity

*   **Single Object:** Typically one point or one bounding box is sufficient to segment a single object [https://huggingface.co/facebook/sam2-hiera-large].
*   **Refinement:** Multiple points can be provided to refine the segmentation. For example, adding both positive and negative points helps adjust the mask boundaries [https://huggingface.co/facebook/sam2-hiera-large].
*   **Multiple Objects:** To segment multiple objects simultaneously, the prompt structure expands to include multiple sets of points or boxes. For example, `input_points = [[[[500, 375]], [[650, 750]]]]` segments two objects in the same image [https://huggingface.co/facebook/sam2-hiera-large].
*   **Batching:** The models support batched images and multiple objects per image. In batched scenarios, the prompt structure accommodates different numbers of objects per image (e.g., one image with 2 objects and another with 1 object) [https://huggingface.co/facebook/sam2-hiera-large] [MODEL.md].
*   **Automatic Mode:** In automatic mask generation, the model uses a fixed grid of points (e.g., `1024` points for SAM, or `points_per_batch` arguments like `64` or `256` for SAM 2 pipelines) to generate masks for all objects [https://huggingface.co/facebook/sam-vit-base] [https://huggingface.co/facebook/sam2-hiera-large].

## Language

*   **SAM / SAM 2:** The original SAM and SAM 2 models do not support text prompts. The official repository states that "passing a text as input is not supported by the official model" [https://huggingface.co/facebook/sam-vit-base]. Prompts are strictly numerical coordinates or binary labels.
*   **SAM 3:** SAM 3 supports text prompts via the `STRING` input in the `SAM3Grounding` node [WORKFLOW_PLAN.md]. The specific language or vocabulary for these text prompts is not detailed in the sources.
*   **Other Models:** BiRefNet, ViTMatte, CorridorKey, and U2-Net do not use text prompts [MODEL.md].

## Negative Prompts

*   **SAM / SAM 2:** Negative prompts are supported via point labels. A label of `0` indicates a negative click, which tells the model that the point is outside the object of interest. This is used to refine masks by excluding specific regions [https://huggingface.co/facebook/sam2-hiera-large].
*   **SAM 3:** Not in sources: Specific mechanism for negative text prompts or negative spatial prompts in SAM 3.
*   **Other Models:** Not in sources: Support for negative prompts in BiRefNet, ViTMatte, CorridorKey, or U2-Net.

## Style and Camera Vocabulary

*   Not in sources: Guidance on style or camera vocabulary for any model in this family. The models are designed for segmentation and matting, not generative image creation, and the sources do not describe any vocabulary related to artistic style or camera angles.

## Text Encoder Behavior

*   **SAM / SAM 2:** These models do not use a text encoder for prompting. The `PromptEncoder` module generates embeddings for points and bounding boxes, not text [https://huggingface.co/facebook/sam-vit-base].
*   **SAM 3:** SAM 3 uses a text prompt via the `SAM3Grounding` node. The sources do not detail the specific text encoder architecture or how it processes the text internally, only that a `STRING` input is provided [WORKFLOW_PLAN.md].
*   **Other Models:** BiRefNet, ViTMatte, CorridorKey, and U2-Net do not use text encoders for prompting [MODEL.md].

## Additional Notes

*   **Precision:** Models are available in FP32, FP16, and mixed precision, which may affect inference speed and memory usage but not the prompt structure [MODEL.md].
*   **Resolution:** BiRefNet supports dynamic resolutions, which may affect the coordinate system for any spatial prompts if they were applicable (though BiRefNet does not use prompts) [MODEL.md].
*   **Optimization:** SAM 2 supports `torch.compile` for video speedup via `vos_optimized=True`, which does not change the prompt structure [MODEL.md] [https://raw.githubusercontent.com/facebookresearch/sam2/HEAD/README.md].
> UNVERIFIED: name not in evidence:  indicates a negative click (outside the object). The structure for labels is ; name not in evidence:  indicates a positive click (inside the object), and 

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
