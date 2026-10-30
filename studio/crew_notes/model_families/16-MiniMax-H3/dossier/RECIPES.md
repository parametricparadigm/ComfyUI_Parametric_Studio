# RECIPES - 16-MiniMax-H3

| Setting | Value | Outcome / Note | Source |
| :--- | :--- | :--- | :--- |
| Guidance Scale | `1.0` | Required because the model is distilled and cfg-free; aborts above `1.0` while the default is `7.0` | [MODEL.md], [unsloth/MiniMax-H3-GGUF] |
| Frame Rate | `24 FPS` | Fixed output frame rate | [MODEL.md], [MiniMaxAI/MiniMax-H3] |
| Resolution (Default) | `768p` | Shorter side set to `768` pixels | [MODEL.md], [MiniMaxAI/MiniMax-H3] |
| Resolution (2K) | `2K` | Achieved via `H3-Regenerate-2K` module which feeds the `768p` result and original context back into H3 | [MODEL.md], [MiniMaxAI/MiniMax-H3] |
| Duration | `4–15 seconds` | Output duration range | [MODEL.md], [MiniMaxAI/MiniMax-H3] |
| Audio | `32 kHz` stereo | Native stereo audio generated jointly with video | [MODEL.md], [MiniMaxAI/MiniMax-H3] |
| Steps (GGUF Example) | `8 steps` | Used in `UD-Q2_K_XL` example at `960x544`, `124 frames` | [unsloth/MiniMax-H3-GGUF] |
| Steps (CLI Example) | `4 steps` | Used in `sd-cli` example with `--video-frames 25` | [unsloth/MiniMax-H3-GGUF] |
| Sampler/Scheduler | Not in sources: Specific sampler or scheduler names (e.g., Euler, DPM++) are not listed in the evidence | | |
| Shift/Strength | Not in sources: Specific shift or strength values are not listed in the evidence | | |
| Seed (GGUF Example) | `11` | Used in `UD-Q2_K_XL` example | [unsloth/MiniMax-H3-GGUF] |
| Backend (CLI) | `te=cpu` | Keeps the `12 GB` text encoder off the card | [unsloth/MiniMax-H3-GGUF] |
| Diffusion Model Quant | `int8_convrot` | Recommended for diffusion models if PyTorch with `cu130` is available | [MODEL.md], [Comfy-Org/MiniMax-H3] |
| Text Encoder Quant | `nvfp4_awq` | Does not require a Blackwell GPU to use | [MODEL.md], [Comfy-Org/MiniMax-H3] |
| LoRA (Turbo 4-step) | `minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors` | Listed in Comfy-Org file structure | [Comfy-Org/MiniMax-H3] |
| LoRA (Turbo 8-step) | `minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors` | Listed in Comfy-Org file structure | [Comfy-Org/MiniMax-H3] |
| LoRA (Ref2V Turbo) | `minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16.safetensors` | Listed in Comfy-Org file structure | [Comfy-Org/MiniMax-H3] |
> UNVERIFIED: name not in evidence:  | Used in ; name not in evidence:  module which feeds the ; name not in evidence: 4 steps; name not in evidence:  | Achieved via 

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
