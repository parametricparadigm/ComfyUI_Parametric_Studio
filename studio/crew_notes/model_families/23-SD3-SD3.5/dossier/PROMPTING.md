# PROMPTING - 23-SD3-SD3.5

## Prompt Structure and Input Formats
*   **Single String or File List**: The reference implementation accepts text prompts as a single string or as a list of prompts from a text file [SOURCES.md].
*   **Node Input**: In ComfyUI workflows, the prompt is set via the `STRING` input of the `CLIPTextEncodeSD3` node [WORKFLOW_PLAN.md].
*   **Output Naming**: Generated images are output to a directory structure based on the model and prompt, following the pattern `outputs/<MODEL>/<PROMPT>_<DATETIME>_<POSTFIX>` [SOURCES.md].

## Prompt Length
*   Not in sources: Specific maximum or recommended character/word limits for prompts.

## Language
*   Not in sources: Specific language requirements or supported languages for the text encoders.

## Negative Prompts
*   **Usage in Workflows**: ComfyUI workflow plans explicitly include a step to encode a negative prompt using a second `CLIPTextEncodeSD3` node, connecting its `CONDITIONING` output to the `KSampler` [WORKFLOW_PLAN.md].
*   **Reference Implementation**: The provided `sd3_infer.py` command-line examples in the sources do not show a flag or argument for negative prompts [SOURCES.md].

## Style and Camera Vocabulary
*   **Example Prompts**: The sources provide specific example prompts that utilize style and camera vocabulary:
    *   "cute wallpaper art of a cat" [SOURCES.md].
    *   "generated ai art, a tiny, lost rubber ducky in an action shot close-up, surfing the humongous waves, inside the tube, in the style of Kelly Slater" [SOURCES.md].
    *   "A Night time photo taken by Leica M11, portrait of a Japanese woman in a kimono, looking at the camera, Cherry blossoms" [SOURCES.md].
    *   "photo of woman, presumably in her mid-thirties, striking a balanced yoga pose on a rocky outcrop during dusk or dawn. She wears a light gray t-shirt and dark leggings. Her pose is dynamic, with one leg extended backward and the other bent at the knee, holding the moon close to her hand." [SOURCES.md].
*   **Not in sources**: A comprehensive list of supported style tags, camera angles, or lighting keywords.

## Text Encoder Behavior
*   **Triple Encoder Architecture**: The inference process relies on three distinct text encoders to generate conditioning embeddings: OpenAI CLIP-L/14, OpenCLIP bigG, and Google T5-XXL [MODEL.md].
*   **Embedding Generation**: These encoders provide text embeddings for conditioning the diffusion models [LOCAL_MODELS.tsv].
*   **Local Availability**: While the architecture requires all three, the local file inventory explicitly lists only `clip_g.safetensors` (OpenCLIP bigG) in the `text_encoders/` folder. The presence of CLIP-L and T5-XXL files is not explicitly confirmed in the local file list, though they are required by the architecture [MODEL.md].
*   **ComfyUI Loading**: In ComfyUI, the `TripleCLIPLoader` node is used to load the text encoders, with the `CLIP` output connected to `CLIPTextEncodeSD3` nodes [WORKFLOW_PLAN.md].

## Additional Prompting-Related Settings
*   **Skip Layer Guidance**: For the SD3.5 Medium model, the reference implementation suggests using "Skip Layer Guidance" (`--skip_layer_cfg True`) to potentially improve structure and anatomy coherency [MODEL.md].
*   **ControlNet Conditioning**: When using ControlNets (Blur, Canny, Depth) with SD3.5 Large, specific preprocessing is required for the conditioning images, and the text prompt is used alongside these control signals [MODEL.md].

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 51855 chars.
