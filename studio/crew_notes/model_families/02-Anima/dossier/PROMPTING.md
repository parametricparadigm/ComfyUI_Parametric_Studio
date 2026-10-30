# PROMPTING - 02-Anima

## Prompt Structure and Format
The model is trained on Danbooru-style tags, natural language captions, and combinations of tags and captions [https://huggingface.co/circlestone-labs/Anima].

### Tag Formatting
*   Use lowercase for tags.
*   Use spaces instead of underscores for tags.
*   Score tags are the only tags that use underscores [https://huggingface.co/circlestone-labs/Anima].
*   When using a tag that is different between Danbooru and Gelbooru, prefer the Gelbooru version [https://huggingface.co/circlestone-labs/Anima].

### Tag Order
The general tag order follows this sequence:
1.  Quality/meta/year/safety tags
2.  Character count tags (e.g., `1girl`, `1boy`, `1other`)
3.  Character
4.  Series
5.  Artist
6.  General tags

Within each tag section, the tags can be in arbitrary order [https://huggingface.co/circlestone-labs/Anima].

### Tag Dropout
The model was trained with random tag dropout. You don't need to include every single relevant tag for the image [https://huggingface.co/circlestone-labs/Anima].

## Natural Language Prompting
*   Follow standard English capitalization rules for character and series names.
*   If using pure natural language, more descriptive is better. Aim for at least 2 sentences. Extremely short prompts can give unexpected results.
*   You can mix tags and natural language in arbitrary order.
*   You can put quality / artist tags at the beginning of a natural language prompt.
    *   Example: "masterpiece, best quality, @big chungus. An anime girl with medium-length blonde hair is..."
*   Name a character, then describe their basic appearance.
    *   Example: "Digital artwork of Fern from Sousou no Frieren, with long purple hair and purple eyes, wearing a black coat over a white dress with puffy sleeves..."
    *   This is extra important when prompting for multiple characters. If you just list off character names with no description of appearance, the model can get confused [https://huggingface.co/circlestone-labs/Anima].

## Prompt Weighting
Prompt weighting works, but needs a weight higher than typically used for SDXL.
*   Example: `(chibi:2)` [https://huggingface.co/circlestone-labs/Anima].

## Recommended Prompts
### Positive Prefix
Recommended positive prefix: "masterpiece, best quality, score_7, safe, " [https://huggingface.co/circlestone-labs/Anima].

### Negative Prompts
Recommended negative prompts: "worst quality, low quality, score_1, score_2, score_3, artist name, blurry, jpeg artifacts, chromatic aberration" [https://huggingface.co/circlestone-labs/Anima].

### Aesthetic Version Specifics
Anima-Aesthetic is fine-tuned only on high quality images, with all of the quality tags stripped out from the captions.
*   You don't need to use quality tags in the positive at all, but "masterpiece, best quality, " is safe to leave in.
*   It is recommended **not** to use `score_*` tags in both the positive and negative prompt. It is already high quality enough and the score tags can push it too hard into slop territory [https://huggingface.co/circlestone-labs/Anima].

## Text Encoder and Conditioning
*   The model uses a text encoder to process prompts [MODEL.md].
*   The local text encoder is `qwen_3_06b_base.safetensors` (Qwen 0.6B, BF16) [MODEL.md].
*   In the ComfyUI workflow, the text encoder is loaded via `CLIPLoader` and connected to `CLIPTextEncode` nodes for both positive and negative prompts [WORKFLOW_PLAN.md].
*   The `CLIPTextEncode` nodes output CONDITIONING to a `BasicGuider` [WORKFLOW_PLAN.md].

## Style and Camera Vocabulary
*   The model is focused mainly on anime concepts, characters, and styles, but is also capable of generating a wide variety of other non-photorealistic content [MODEL.md].
*   The model is designed for making illustrations and artistic images, and will not work well at realism [MODEL.md].
*   For a more realistic or painterly look, the `beta57` scheduler (from the ComfyUI RES4LYF custom node pack) can be used. This emphasizes low-noise timesteps to make better textures [MODEL.md].
*   Not in sources: Specific camera angle vocabulary or lens terminology distinct from general tag/natural language descriptions.

## Limitations and Risks
*   The model doesn't do realism well. This is intended. It is an anime / illustration / art focused model [https://huggingface.co/circlestone-labs/Anima].
*   The model may generate undesired content, especially if the prompt is short or lacking details. Avoid this by using the appropriate safety tags in the positive and negative prompts, and by writing sufficiently detailed prompts [https://huggingface.co/circlestone-labs/Anima].
*   The model isn't great at text rendering. It can generally do single words and sometimes short phrases, but lengthy text rendering won't work well [https://huggingface.co/circlestone-labs/Anima].
*   The base version is a true base model. It hasn't been aesthetic tuned on a curated dataset. The default style is very plain and neutral [https://huggingface.co/circlestone-labs/Anima].

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 56837 chars.
