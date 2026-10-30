# PROMPTING - 16-MiniMax-H3

## Prompt Structure and Content
*   **Multimodal Context:** The system supports unified understanding of multimodal contexts composed of text, images, video, and audio [MODEL.md].
*   **Instruction Complexity:** The system is designed for task generalization, enabling it to follow complex multimodal instructions [MODEL.md].
*   **Context Processing:** The `H3-Context-IR` module performs instruction parsing, cross-modal association, temporal understanding, and logical reasoning to create a Context Intermediate Representation [MODEL.md].
*   **Semantic Supplementation:** `H3-Context-IR` may supplement missing or underspecified semantic details where appropriate without deviating from the user’s original intent [https://huggingface.co/MiniMaxAI/MiniMax-H3].
*   **Prompting Guidance:** Developers are advised to follow the "Prompting Guidance" to build their own context-processing systems if not using the hosted `H3-Context-IR` API [https://huggingface.co/MiniMaxAI/MiniMax-H3].
*   **Official Skills:** Official skills to improve prompt writing are available in the repository under `skills/h3-prompt-writing/references/`, including `base-en.txt` for text/keyframe modes and `ref-en.txt` for full-reference (Ref2VA) mode [https://raw.githubusercontent.com/MiniMax-AI/MiniMax-H3/HEAD/README.md].

## Language
*   **Supported Languages:** The model has stable support for 11 languages: Arabic, Chinese, English, French, German, Italian, Japanese, Korean, Portuguese, Russian, and Spanish [MODEL.md].
*   **Additional Languages:** Additional languages are supported to varying degrees [https://huggingface.co/MiniMaxAI/MiniMax-H3].

## Embeddings
*   **Syntax:** Specific embeddings can be invoked in text prompts using the syntax `embedding:<filename>` [MODEL.md].
*   **Usage:** To use embeddings in a text prompt, invoke them in the `CLIPTextEncode` node by combining `embedding:` with the filename of the embedding [https://huggingface.co/Comfy-Org/MiniMax-H3].
*   **Example:** For the file `minimaxh3_art_is_explosion.safetensors`, the prompt syntax is `embedding:minimaxh3_art_is_explosion` [https://huggingface.co/Comfy-Org/MiniMax-H3].
*   **Available Embeddings:** The Comfy-Org repository lists the following embedding files: `minimaxh3_art_is_explosion.safetensors`, `minimaxh3_blooming_flowers.safetensors`, `minimaxh3_bullet_time.safetensors`, `minimaxh3_dark_magic.safetensors`, `minimaxh3_fire_breath.safetensors`, `minimaxh3_four_seasons.safetensors`, `minimaxh3_kiss_camera.safetensors`, `minimaxh3_spiral_ascent.safetensors`, `minimaxh3_storm_magic.safetensors`, and `minimaxh3_truman_show.safetensors` [https://huggingface.co/Comfy-Org/MiniMax-H3].

## Negative Prompts
Not in sources: Negative prompts

## Style and Camera Vocabulary
Not in sources: Specific style or camera vocabulary lists

## Text Encoder Behavior
*   **Model Identity:** The text encoder is based on `Qwen3-VL-32B` [MODEL.md].
*   **Hidden States:** The encoder provides the hidden states from its 50th layer to the transformer [https://huggingface.co/MiniMaxAI/MiniMax-H3].
*   **Special Tokens:** Several special tokens, such as `<d>`, are added to the tokenizer configuration [https://huggingface.co/MiniMaxAI/MiniMax-H3].
*   **Encoding Process:** Text is encoded by the H3-Encoder (the text encoder component) [https://huggingface.co/MiniMaxAI/MiniMax-H3].
*   **Quantization Note:** The `nvfp4_awq` quantization of the text encoder does not require a Blackwell GPU to use [https://huggingface.co/Comfy-Org/MiniMax-H3].

## Guidance Scale and CFG
*   **CFG-Free:** The model is distilled and cfg-free [MODEL.md].
*   **Required Setting:** The guidance scale must be set to 1.0 for optimal performance [MODEL.md].
*   **Constraint:** The model aborts if the guidance scale is above 1.0, while the default in some tools is 7.0 [https://huggingface.co/unsloth/MiniMax-H3-GGUF].

## Example Prompt
*   **Example Text:** "a red panda stepping along a mossy log in a misty forest, cinematic" [https://huggingface.co/unsloth/MiniMax-H3-GGUF].
*   **Example Text 2:** "a red fox trotting through falling snow, cinematic" [https://huggingface.co/unsloth/MiniMax-H3-GGUF].

## Not in Sources
*   Prompt length limits
*   Specific camera movement keywords
*   Negative prompt syntax or usage

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
