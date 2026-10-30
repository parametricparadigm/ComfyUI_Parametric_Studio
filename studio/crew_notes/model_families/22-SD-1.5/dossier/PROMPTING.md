# PROMPTING - 22-SD-1.5

## Prompt Language and Structure
*   **Language**: The model was trained mainly with English captions and will not work as well in other languages; the ability to generate content with non-English prompts is significantly worse than with English-language prompts [https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5].
*   **Structure**: Prompts are text inputs used to condition the model. The model is designed for generating photo-realistic images given any text input [MODEL.md].
*   **Example**: A standard prompt example provided in the documentation is "a photo of an astronaut riding a horse on mars" [https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5].

## Prompt Length and Token Limits
*   **Token Limit**: The original Stable Diffusion implementation allows up to 75 tokens for prompts [https://github.com/AUTOMATIC1111/stable-diffusion-webui].
*   **Validation**: The AUTOMATIC1111 web UI includes a feature for "Live prompt token length validation" [https://github.com/AUTOMATIC1111/stable-diffusion-webui].
*   **No Token Limit (UI Specific)**: The AUTOMATIC1111 web UI features "No token limit for prompts" as a specific feature of that interface, distinct from the original model constraint [https://github.com/AUTOMATIC1111/stable-diffusion-webui].

## Negative Prompts
*   **Support**: The model supports optional negative prompts [MODEL.md].
*   **Function**: A negative prompt is an extra text field that allows the user to list what they do not want to see in the generated image [https://github.com/AUTOMATIC1111/stable-diffusion-webui].
*   **Implementation**: In ComfyUI workflows, a `CLIPTextEncode` node is used to encode the negative prompt, and its `CONDITIONING` output is connected to the negative conditioning input of the `KSampler` [WORKFLOW_PLAN.md].

## Attention and Weighting Syntax
*   **Parentheses**: Users can specify parts of the text that the model should pay more attention to using parentheses. For example, `a man in a ((tuxedo))` will pay more attention to tuxedo [https://github.com/AUTOMATIC1111/stable-diffusion-webui].
*   **Colon Syntax**: An alternative syntax for weighting is available, such as `a man in a (tuxedo:1.21)` [https://github.com/AUTOMATIC1111/stable-diffusion-webui].
*   **Composable Diffusion**: The AUTOMATIC1111 web UI supports Composable-Diffusion, allowing multiple prompts to be used at once by separating them with uppercase `AND`. It also supports weights for prompts, e.g., `a cat :1.2 AND a dog AND a penguin :2.2` [https://github.com/AUTOMATIC1111/stable-diffusion-webui].

## Text Encoder Behavior
*   **Encoder Model**: The model uses a fixed, pretrained CLIP ViT-L/14 text encoder to condition the model on text prompts [MODEL.md].
*   **Conditioning**: Stable Diffusion is a latent diffusion model conditioned on the (non-pooled) text embeddings of a CLIP ViT-L/14 text encoder [https://raw.githubusercontent.com/CompVis/stable-diffusion/HEAD/README.md].
*   **Classifier-Free Guidance**: The v1-5 checkpoint was fine-tuned with 10% dropping of the text-conditioning to improve classifier-free guidance sampling [https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5].
*   **Safety Checker Interaction**: The Safety Checker compares the class probability of harmful concepts in the embedding space of the `CLIPTextModel` after generation of the images [https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5].

## Style and Camera Vocabulary
*   **Photorealism**: The model is designed for generating photo-realistic images [MODEL.md].
*   **Limitations**: The model does not achieve perfect photorealism [https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5].
*   **Specific Vocabulary**: Not in sources: Specific recommended style or camera vocabulary lists (e.g., "8k", "cinematic lighting", "wide angle") are not explicitly defined in the provided sources, though "photo" is used in the example prompt.

## Other Prompting Features
*   **Textual Inversion**: Users can have as many embeddings as they want and use any names they like for them, allowing specific concepts to be added to prompts [https://github.com/AUTOMATIC1111/stable-diffusion-webui].
*   **Prompt Editing**: The AUTOMATIC1111 web UI supports prompt editing, allowing the prompt to be changed mid-generation [https://github.com/AUTOMATIC1111/stable-diffusion-webui].
*   **Styles**: The AUTOMATIC1111 web UI offers "Styles," a way to save part of a prompt and easily apply them via a dropdown [https://github.com/AUTOMATIC1111/stable-diffusion-webui].
*   **CLIP Interrogator**: A button in the AUTOMATIC1111 web UI tries to guess the prompt from an image [https://github.com/AUTOMATIC1111/stable-diffusion-webui].

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
