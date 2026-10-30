# PROMPTING - 14-Krea-2

## Prompt Structure and Language
*   **Language**: The model is tagged with `en` (English) in its metadata [https://huggingface.co/unsloth/Krea-2-Turbo].
*   **Structure**: Prompts are passed as a single positional argument `prompt` in the official inference script [https://raw.githubusercontent.com/krea-ai/krea-2/HEAD/README.md].
*   **Style Vocabulary**: The model is designed for "creative and stylistic exploration" [https://raw.githubusercontent.com/krea-ai/krea-2/HEAD/README.md]. Sample prompts in the sources demonstrate the use of detailed descriptive language covering subject, environment, lighting, perspective, and specific artistic styles (e.g., "monochromatic blue," "halftone dot pattern," "impressionist painting," "ligne claire drawing aesthetic") [https://huggingface.co/unsloth/Krea-2-Turbo].
*   **LoRA Trigger Words**: When using specific style LoRAs, specific trigger phrases are required in the prompt. The recommended strength for these LoRAs is `1.0` [https://huggingface.co/Comfy-Org/Krea-2]:
    *   `krea2_darkbrush`: `monochrome ink wash style`
    *   `krea2_dotmatrix`: `monochrome stippling style`
    *   `krea2_kidsdrawing`: `naive expressive sketch style`
    *   `krea2_neondrip`: `textured abstract style`
    *   `krea2_rainywindow`: `rainy window style`
    *   `krea2_retroanime`: `purple retro anime style`
    *   `krea2_softwatercolor`: `art deco watercolor style`
    *   `krea2_sunsetblur`: `ethereal motion blur style`
    *   `krea2_vintagetarot`: `vintage tarot style`

## Prompt Length
*   Not in sources: Specific character or token limits for prompt length.

## Negative Prompts
*   **RAW Model**: Uses classifier-free guidance (CFG), which typically implies the use of negative prompts, though the specific content of the negative prompt is not detailed in the sources. The workflow plan suggests creating a negative prompt using `CLIPTextEncode` [WORKFLOW_PLAN.md].
*   **Turbo Model**: CFG is disabled (`--cfg 0.0`). The workflow plan notes that "the negative prompt may not influence the result significantly, but standard nodes often require a conditioning input" [WORKFLOW_PLAN.md].
*   **Editing Workflows (CFG > 1)**: When using the RAW model for editing removals with CFG 3, the sources state to "ground the negative too: a second `Krea2EditGroundedEncode` with an empty prompt and the same image (this is the trained unconditional)" [https://raw.githubusercontent.com/lbouaraba/comfyui-krea2edit/HEAD/README.md].

## Text Encoder Behavior
*   **Model**: The family utilizes the `Qwen3-VL 4B` text encoder for semantic understanding [MODEL.md].
*   **Standard Generation**: The text encoder encodes text prompts for image generation [LOCAL_MODELS.tsv].
*   **Editing/Grounding**: In editing workflows, the source image is injected into the `Qwen3-VL` text encoder for "semantic grounding." This allows the model to "see" the image while reading the instruction [MODEL.md]. The `Krea2EditGroundedEncode` node performs this "image-grounded instruction encoding," where the text encoder sees the image while reading the prompt [https://raw.githubusercontent.com/lbouaraba/comfyui-krea2edit/HEAD/README.md].
*   **Importance of Grounding**: Using a stock `CLIPTextEncode` without the grounded encode means the model "never sees the image semantically and quality drops sharply, especially for scene-referential instructions" [https://raw.githubusercontent.com/lbouaraba/comfyui-krea2edit/HEAD/README.md].

## Resolution and Prompt Interaction
*   **RAW**: Trained to generate up to 1k resolution [https://raw.githubusercontent.com/krea-ai/krea-2/HEAD/README.md].
*   **Turbo**: Can generate images from 1k to 2k resolution [https://raw.githubusercontent.com/krea-ai/krea-2/HEAD/README.md].
*   **Padding**: Output resolution is padded up to a multiple of 16 if needed [https://raw.githubusercontent.com/krea-ai/krea-2/HEAD/README.md].

## Not in Sources
*   Specific guidance on prompt length optimization (e.g., optimal token count).
*   Specific negative prompt examples for standard text-to-image generation (only the "empty prompt" for grounded editing negatives is specified).
*   Detailed camera vocabulary lists beyond examples found in sample prompts (e.g., "ground level," "medium shot," "high-angle wide perspective").

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 59070 chars.
