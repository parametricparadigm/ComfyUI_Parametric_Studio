# PROMPTING - 27-VLM-captioning-tagging

## Prompt Structure and Task Selection
For the Florence-2 lineage, the prompt structure is defined by specific task tokens that switch the model's behavior. The model uses a prompt-based approach where simple text prompts determine the task, such as captioning, object detection, or segmentation [MODEL.md]. The primary task tokens documented are:
- `<CAPTION>`: Generates a general description [MODEL.md].
- `<DETAILED_CAPTION>`: Generates a longer description [MODEL.md].
- `<MORE_DETAILED_CAPTION>`: Generates a more detailed caption [PUBLIC README https://huggingface.co/microsoft/Florence-2-large/raw/main/README.md].
- `<OD>`: Generates object detection bounding boxes and labels [MODEL.md].
- `<OCR>`: Extracts text from the image [MODEL.md].
- `<OCR_WITH_REGION>`: Extracts text with region-specific quadrilateral boxes [PUBLIC README https://huggingface.co/microsoft/Florence-2-large/raw/main/README.md].
- `<DENSE_REGION_CAPTION>`: Generates dense region captions with bounding boxes [PUBLIC README https://huggingface.co/microsoft/Florence-2-large/raw/main/README.md].
- `<REGION_PROPOSAL>`: Generates region proposals [PUBLIC README https://huggingface.co/microsoft/Florence-2-large/raw/main/README.md].
- `<CAPTION_TO_PHRASE_GROUNDING>`: Requires additional text input (a caption) to ground phrases to bounding boxes [PUBLIC README https://huggingface.co/microsoft/Florence-2-large/raw/main/README.md].

For general VLMs (such as `Qwen__Qwen2.5-VL-7B-Instruct` or `MiMo-VL-7B-RL-2508`), the prompt is a natural language instruction, for example, "Describe this image" [WORKFLOW_PLAN.md].

## Prompt Length and Context
The Florence-2-large model is described as a continued pretrained version with a 4k context length [PUBLIC README https://huggingface.co/microsoft/Florence-2-large/raw/main/README.md]. The generated output length is controlled by the `max_new_tokens` setting. In the provided inference examples, `max_new_tokens` is set to `1024` for the base and finetuned models, and `4096` for the large model [PUBLIC README https://huggingface.co/microsoft/Florence-2-large/raw/main/README.md].

## Language
Not in sources: Specific language requirements or multilingual capabilities for the prompt input are not detailed in the provided evidence, other than the English task tokens and natural language examples.

## Negative Prompts
Not in sources: The provided evidence does not mention the use of negative prompts for this model family.

## Style and Camera Vocabulary
Not in sources: The sources do not provide specific guidance on using style or camera vocabulary within the prompts for these VLMs. The prompts are primarily task identifiers (e.g., `<CAPTION>`) or natural language instructions for description.

## Text Encoder and Processing
The models operate on a sequence-to-sequence architecture, taking an image (pixel values) and a text prompt as input [MODEL.md]. The text prompt and image are processed together to generate a text sequence [MODEL.md]. The `processor` (specifically `AutoProcessor`) is used to handle the text and image inputs, returning tensors for `input_ids` and `pixel_values` [PUBLIC README https://huggingface.co/microsoft/Florence-2-large/raw/main/README.md]. For tasks requiring additional text input, such as `<CAPTION_TO_PHRASE_GROUNDING>`, the text input is concatenated to the task prompt before processing [PUBLIC README https://huggingface.co/microsoft/Florence-2-large/raw/main/README.md].

## Inference Settings
The following settings are documented for inference:
- `max_new_tokens`: Controls the length of the generated text (e.g., `1024` or `4096`) [MODEL.md].
- `num_beams`: Beam search width, typically set to `3` in examples [MODEL.md].
- `do_sample`: Boolean for sampling vs. greedy/beam search, typically set to `False` in examples [MODEL.md].
- `torch_dtype`: Data type for inference, typically `float16` (fp16) or `bfloat16` (bf16) [MODEL.md].

## Output Parsing
The raw generated text is post-processed using `processor.post_process_generation` [PUBLIC README https://huggingface.co/microsoft/Florence-2-large/raw/main/README.md].
- For captioning tasks, the output is a text string [MODEL.md].
- For object detection (`<OD>`), the output is parsed into a dictionary containing `bboxes` (list of [x1, y1, x2, y2] coordinates) and `labels` (list of strings) [MODEL.md].
- For OCR with region (`<OCR_WITH_REGION>`), the output includes `quad_boxes` and `labels` [MODEL.md].

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
