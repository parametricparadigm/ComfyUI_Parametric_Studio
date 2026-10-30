# RECIPES - 27-VLM-captioning-tagging

## Inference Settings Table

| Model / Variant | Task Prompt | `max_new_tokens` | `num_beams` | `do_sample` | `torch_dtype` | Output / Outcome | Source |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `microsoft/Florence-2-base` | `<OD>` | `1024` | `3` | `False` | `torch.float16` | Parsed object detection results (`bboxes`, `labels`) | [https://huggingface.co/microsoft/Florence-2-base] |
| `microsoft/Florence-2-base` | `<CAPTION>` | `1024` | `3` | Not in sources: `do_sample` value for this specific task block | `torch.float16` | Caption string | [https://huggingface.co/microsoft/Florence-2-base] |
| `microsoft/Florence-2-large` | `<OD>` | `4096` | `3` | `False` | `torch.float16` | Parsed object detection results (`bboxes`, `labels`) | [https://huggingface.co/microsoft/Florence-2-large] |
| `microsoft/Florence-2-large` | `<CAPTION>` | `1024` | `3` | Not in sources: `do_sample` value for this specific task block | `torch.float16` | Caption string | [https://huggingface.co/microsoft/Florence-2-large] |
| `microsoft/Florence-2-large-ft` | `<OD>` | `1024` | `3` | `False` | `torch.float16` | Parsed object detection results (`bboxes`, `labels`) | [https://huggingface.co/microsoft/Florence-2-large-ft] |
| `florence2/large-promptgen` | `<CAPTION>` | `4096` | `3` | Not in sources: `do_sample` value | `f32` | Detailed prompt/caption string | [WORKFLOW_PLAN.md] |
| `florence2/Florence-2-base` | `<CAPTION>` | `1024` | `3` | Not in sources: `do_sample` value | `fp16` | Caption string | [WORKFLOW_PLAN.md] |

## Notes on Settings

- **Sampler/Scheduler**: The sources specify `num_beams` and `do_sample` for the `model.generate` call. No specific sampler or scheduler names (e.g., Euler, DPM++ or specific beam search variants beyond `num_beams`) are mentioned in the evidence.
- **CFG/Guidance**: Not in sources: CFG or guidance scale values.
- **Resolution/Frames/FPS**: Not in sources: Specific input resolution, frame count, or FPS settings. The code uses `image.width` and `image.height` dynamically for post-processing.
- **Shift/Strength**: Not in sources: Shift or strength values.
- **Context Length**: The `microsoft/Florence-2-large` README states it is a "continued pretrained version... with 4k context length". [https://huggingface.co/microsoft/Florence-2-large]
- **Precision**: 
    - `microsoft/Florence-2-base`, `microsoft/Florence-2-large`, and `microsoft/Florence-2-large-ft` are trained with `float16` and loaded with `torch.float16` on CUDA. [https://huggingface.co/microsoft/Florence-2-base] [https://huggingface.co/microsoft/Florence-2-large] [https://huggingface.co/microsoft/Florence-2-large-ft]
    - `florence2/large-promptgen` is specified as `f32` in local model metadata. [LOCAL_MODELS.tsv]
    - `florence2/Florence-2-base` is specified as `fp16` in local model metadata. [LOCAL_MODELS.tsv]

## Workflow Steps (ComfyUI Nodes)

The following steps are derived from `WORKFLOW_PLAN.md` for local node execution:

### Plan 1: Florence-2 Base Captioning and Tagging
1. **`Florence2ModelLoader`**: Connects to `florence2/Florence-2-base`. Configured for `fp16`. [WORKFLOW_PLAN.md]
2. **`LoadImage`**: Connects to input image file. [WORKFLOW_PLAN.md]
3. **`Florence2Run`**: Connects `Florence2ModelLoader` and `LoadImage`. `STRING` input set to `<CAPTION>` or `<OD>`. [WORKFLOW_PLAN.md]
4. **`Florence2JsonShow`**: Connects to `JSON` output of `Florence2Run` for `<OD>` tasks. [WORKFLOW_PLAN.md]
5. **`SaveImage`**: Connects to `IMAGE` output if visualized boxes are returned. [WORKFLOW_PLAN.md]

### Plan 2: Florence-2 Large Prompt Generation
1. **`Florence2ModelLoader`**: Connects to `florence2/large-promptgen`. [WORKFLOW_PLAN.md]
2. **`LoadImage`**: Connects to input image file. [WORKFLOW_PLAN.md]
3. **`Florence2Run`**: Connects `Florence2ModelLoader` and `LoadImage`. `STRING` input set to `<CAPTION>`. [WORKFLOW_PLAN.md]
4. **`TextDisplay`**: Connects to `STRING` output of `Florence2Run`. [WORKFLOW_PLAN.md]

### Plan 3: Qwen2.5-VL Captioning
1. **`QwenVLModelLoader`**: Connects to `VLM/Qwen__Qwen2.5-VL-7B-Instruct`. [WORKFLOW_PLAN.md]
2. **`LoadImage`**: Connects to input image file. [WORKFLOW_PLAN.md]
3. **`QwenVLCaption`**: Connects `QwenVLModelLoader` and `LoadImage`. `STRING` input is the prompt. [WORKFLOW_PLAN.md]
4. **`TextDisplay`**: Connects to `STRING` output of `QwenVLCaption`. [WORKFLOW_PLAN.md]

## Missing Information

- Not in sources: Specific `max_new_tokens` or `num_beams` for `Qwen__Qwen2.5-VL-7B-Instruct` or `MiMo-VL-7B-RL-2508`.
- Not in sources: Specific `torch_dtype` for `Qwen__Qwen2.5-VL-7B-Instruct` or `MiMo-VL-7B-RL-2508` in the workflow plans (though `MiMo-VL-7B-RL-2508` is listed as BF16 in `LOCAL_MODELS.tsv`).
- Not in sources: Specific node names or settings for `MiMo-VL-7B-RL-2508` workflows.
> UNVERIFIED: name not in evidence:  | Not in sources: ; name not in evidence:  value for this specific task block | ; name not in evidence:  | Parsed object detection results (; name not in evidence:  value | 

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
