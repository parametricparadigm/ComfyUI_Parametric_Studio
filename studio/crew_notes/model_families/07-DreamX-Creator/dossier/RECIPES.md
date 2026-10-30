# RECIPES - 07-DreamX-Creator

| Setting | Value | Outcome / Notes | Source |
| :--- | :--- | :--- | :--- |
| `--duration` | `5` | 5 seconds duration | [EvoAwaken-Workshop/DreamX-Creator-gguf] |
| `--fps` | `24` | 24 FPS | [EvoAwaken-Workshop/DreamX-Creator-gguf] |
| `--steps` | `50` | 50 sampling steps | [EvoAwaken-Workshop/DreamX-Creator-gguf] |
| `--seed` | `0` | Fixed seed for reproducibility | [EvoAwaken-Workshop/DreamX-Creator-gguf] |
| `--target-spatial-tokens` | `880` | Target spatial tokens | [EvoAwaken-Workshop/DreamX-Creator-gguf] |
| `--refine` | enabled | Enables 2x video refinement | [EvoAwaken-Workshop/DreamX-Creator-gguf] |
| `--refiner-kv-len` | `9` | Refiner KV history length | [EvoAwaken-Workshop/DreamX-Creator-gguf] |
| `--latent-upsample` | `flash` | Latent upsampling method | [EvoAwaken-Workshop/DreamX-Creator-gguf] |
| `--refiner-decoder` | `lightvae` | Refiner decoder type | [EvoAwaken-Workshop/DreamX-Creator-gguf] |
| `--threads` | `8` | CPU thread count | [EvoAwaken-Workshop/DreamX-Creator-gguf] |
| `--negative-prompt` | `"low quality"` | Negative prompt text | [EvoAwaken-Workshop/DreamX-Creator-gguf] |
| Scheduler | `normal` | ComfyUI normal scheduler | [T8mars/Comfyui-DreamX-Creator-T8] |
| Sampler | `Euler` | Euler sampler | [T8mars/Comfyui-DreamX-Creator-T8] |
| Steps | `20` | 20 sampling steps | [T8mars/Comfyui-DreamX-Creator-T8] |
| Spatial tokens | `256` | 256 spatial tokens | [T8mars/Comfyui-DreamX-Creator-T8] |
| Resolution | `512x512` | 512x512 for a square input | [T8mars/Comfyui-DreamX-Creator-T8] |
| Duration | `2 seconds` | 2 seconds duration | [T8mars/Comfyui-DreamX-Creator-T8] |
| FPS | `24` | 24 FPS | [T8mars/Comfyui-DreamX-Creator-T8] |
| Frame count | `45` | 45 frames (1.875 s) | [T8mars/Comfyui-DreamX-Creator-T8] |
| `window_chunk` | `1` | Refiner loader default | [T8mars/Comfyui-DreamX-Creator-T8] |
| Latent KV-history frames | `3` | Refiner loader default on 24 GB Windows systems | [T8mars/Comfyui-DreamX-Creator-T8] |
| Latent KV-history frames | `9` | Selectable on higher-memory systems | [T8mars/Comfyui-DreamX-Creator-T8] |
| `--latent-upsample` options | `bilinear`, `flash`, `causal2d` | Available latent upsampling options | [Liyulingyue/rust-model-inference] |
| `--refiner-decoder` options | `wan`, `lightvae` | Available refiner decoder options | [Liyulingyue/rust-model-inference] |
| Audio VAE precision | `float32` | Bundled Audio VAE stays in float32 | [T8mars/Comfyui-DreamX-Creator-T8] |
| Frame snap rule | `4N+1` | Duration is truncated down to a Wan-compatible 4N+1 frame count | [T8mars/Comfyui-DreamX-Creator-T8] |
| Refiner steps | `1` | Autoregressive 1-Step refinement | [AMAP-ML/DreamX-Creator] |
| Refiner output | `2K` | Upgrades generated video to high-quality 2K output | [AMAP-ML/DreamX-Creator] |

Not in sources: CFG/guidance value
Not in sources: Specific output resolution for the Rust runtime example (only spatial tokens provided)

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
