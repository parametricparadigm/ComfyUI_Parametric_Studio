# Models

Models are not part of this repository. They download from their publishers and keep their own licences, which are separate from this project's AGPL. This page is a summary to help you find the terms, not legal advice. Read the licence itself before you rely on any of this.

**How this was checked (2026-10-30):** gated status and licence fields come from the Hugging Face API for each repository. Where a licence's terms are described below, the licence text was read from the same source, except where marked. Sizes come from `studio/models_manifest.json` and are in GiB (Hugging Face shows GB, so its numbers look about 7% larger). Peak VRAM is the highest figure measured for that goal in the studio's own showcase renders, on one 96 GB NVIDIA card at small sizes and short lengths. On other cards or settings it will differ.

## Generation models

| Family | Goals | Total GiB | Files (GiB) | Peak VRAM GiB | Licence | Gated | Source |
|---|---|---|---|---|---|---|---|
| FLUX.2 Klein 4B | Image | 15.0 | `flux-2-klein-4b.safetensors` (7.22)<br>`qwen_3_4b.safetensors` (7.49)<br>`flux2-vae.safetensors` (0.31) | 22.6 | Apache-2.0 | No | [Comfy-Org/Flux-2-Klein-4B](https://huggingface.co/Comfy-Org/Flux-2-Klein-4B), upstream [black-forest-labs/FLUX.2-klein-4B](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B) |
| Wan 2.2 TI2V-5B | Video, Animate | 16.9 | `wan2.2_ti2v_5B_fp16.safetensors` (9.31)<br>`umt5_xxl_fp8_e4m3fn_scaled.safetensors` (6.27)<br>`wan2.2_vae.safetensors` (1.31) | 34.7 | Apache-2.0 | No | [Comfy-Org/Wan_2.2_ComfyUI_Repackaged](https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged), upstream [Wan-AI/Wan2.2-TI2V-5B](https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B) |
| Anima | Anime | 9.2 | `anima-aesthetic-v1.1.safetensors` (3.90)<br>`anima-turbo-v1.1.safetensors` (3.90)<br>`qwen_3_06b_base.safetensors` (1.11)<br>`qwen_image_vae.safetensors` (0.24) | 13.2 | CircleStone Labs Non-Commercial License v1.2 | No | [circlestone-labs/Anima](https://huggingface.co/circlestone-labs/Anima) |
| FLUX.3 Klein | Image HQ | 18.9 | `flux3-image-klein-bf16.safetensors` (10.34)<br>`qwen3vl_4b_bf16.safetensors` (8.27)<br>`flux2-vae.safetensors` (0.31) | 24.1 | FLUX Kommunity License | Yes (accept on Hugging Face) | [black-forest-labs/flux-3-image-klein-comfy](https://huggingface.co/black-forest-labs/flux-3-image-klein-comfy), upstream [black-forest-labs/flux-3-image-klein](https://huggingface.co/black-forest-labs/flux-3-image-klein) |
| LTX-2.5 | Video + sound, Animate + sound | 36.0 | `ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.safetensors` (20.03)<br>`gemma4-12b-with-proj-ltx-2.5-comfy-int8-convrot.safetensors` (14.32)<br>`ltx-2.5-video-vae-conv-bf16.safetensors` (1.35)<br>`ltx-2.5-audio-vae-bf16.safetensors` (0.34) | 44.3 | LTX-2.x Community License | Yes (accept on Hugging Face) | [Lightricks/LTX-2.5](https://huggingface.co/Lightricks/LTX-2.5) |
| MiniMax H3 | Video H3, Animate H3 | 41.4 | `minimax_h3_fl2va_pruned_int8_convrot.safetensors` (19.53)<br>`qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` (14.61)<br>`minimax_h3_video_vae_fp16.safetensors` (4.85)<br>`minimax_h3_audio_vae_fp32.safetensors` (0.56)<br>`minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors` (1.82) | 45.4 | MiniMax H3 Community License | No | [Comfy-Org/MiniMax-H3](https://huggingface.co/Comfy-Org/MiniMax-H3), upstream [MiniMaxAI/MiniMax-H3](https://huggingface.co/MiniMaxAI/MiniMax-H3) |
| MiniMax Music 3 | Music | 20.3 | `minimax_music3_dit_fp16.safetensors` (4.58)<br>`minimax_music3_text_encoder_pruned_bf16.safetensors` (15.56)<br>`minimax_music3_dav.safetensors` (0.20) | 26.8 | MiniMax-Music3 Community License (see the note below) | No | [Comfy-Org/MiniMax-Music-3](https://huggingface.co/Comfy-Org/MiniMax-Music-3), upstream [MiniMaxAI/MiniMax-Music3](https://huggingface.co/MiniMaxAI/MiniMax-Music3) |

Animate shares its files with Video, Animate + sound with Video + sound, and Animate H3 with Video H3, so each set downloads once.

### What the licences say

Verified from the licence text unless noted.

- **FLUX.2 Klein 4B, Wan 2.2 TI2V-5B:** Apache-2.0 on both the ComfyUI repackage and the upstream repository.
- **Anima:** non-commercial. You may not receive payment from its use. Hugging Face lists it as built on NVIDIA Cosmos-Predict2-2B, which has its own [NVIDIA Open Model License](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-open-model-license).
- **FLUX.3 Klein:** non-commercial by default. Outputs may be used commercially only by a "Qualifying User", meaning you and your affiliates have gross annualized revenue under US$5,000,000. Anything else needs a licence from Black Forest Labs. Also read its limits on prohibited uses.
- **LTX-2.5:** LTX-2.x Community License. Entities with annual revenue of at least US$10,000,000 need a paid commercial licence. The text read for this summary was the copy shipped with Lightricks' ComfyUI-LTXVideo pack (dated January 5, 2026). The current text is at [LICENSE-2_x](https://github.com/Lightricks/LTX-2/blob/main/LICENSE-2_x).
- **MiniMax H3:** **the licence excludes some countries.** Its grant applies "worldwide, excluding the Excluded Territories", defined as the European Union, the United Kingdom, the Republic of Korea and the United States of America, and it says you may not use or display the works or their outputs outside the permitted territory. MiniMax invites people in those places to contact them about a licence. If you are in one of those places, read it before you install these goals. Commercial products need the name "MiniMax H3" shown in their interface, and written authorization above US$20,000,000 in yearly revenue. Anyone offering a hosted service has further safeguard duties.
- **MiniMax Music 3:** the sources disagree. The [Comfy-Org repackage](https://huggingface.co/Comfy-Org/MiniMax-Music-3) that the installer downloads from is tagged Apache-2.0, but the [upstream LICENSE](https://huggingface.co/MiniMaxAI/MiniMax-Music3/blob/main/LICENSE) is the "MiniMax-Music3 Community License": commercial products must display the name, and authorization is needed above US$20,000,000 in yearly revenue. This page treats the upstream text as the one that applies. The studio's label says the same.

The H3, FLUX.3 and LTX text encoders (Qwen3-VL, Gemma 4) are packaged inside those model repositories, and their base models have their own terms: Qwen/Qwen3-VL-32B-Instruct and google/gemma-4-12b are tagged Apache-2.0 on Hugging Face (Gemma's page links its own [licence page](https://ai.google.dev/gemma/docs/gemma_4_license)). Unverified: whether anything beyond the package's licence applies to the repackaged encoder files.

### Not in the manifest yet

Unverified means not checked against the licence text.

| File | Used by | Status |
|---|---|---|
| `flux-2-klein-base-4b.safetensors` (Comfy-Org/Flux-2-Klein-4B, Apache-2.0) | Image, quality mode | The installer does not fetch it; the fast mode works without it |
| `minimax_h3_ref2va_pruned_int8_convrot.safetensors` (Comfy-Org/MiniMax-H3) | Recast, Reshoot (in progress) | Not in the manifest |
| [akatz-ai/MiniMax-H3-Character-Swap-LoRA](https://huggingface.co/akatz-ai/MiniMax-H3-Character-Swap-LoRA) | Recast (in progress) | Card says MiniMax H3 Community License; not in the manifest. Unverified: whether the exact file name the graph uses comes from this repository |
| Lightricks LTX-2.5 IC-LoRAs: [Water Simulation](https://huggingface.co/Lightricks/LTX-2.5-22b-IC-LoRA-Water-Simulation), [Clean Plate](https://huggingface.co/Lightricks/LTX-2.5-22b-IC-LoRA-Clean-Plate), [Day To Night](https://huggingface.co/Lightricks/LTX-2.5-22b-IC-LoRA-Day-To-Night), [Alpha Gen](https://huggingface.co/Lightricks/LTX-2.5-22b-IC-LoRA-Alpha-Gen) | VFX (in progress) | Gated. The Clean Plate card says LTX-2.x community licence; the other three unverified. Not in the manifest |

## Language models for the crew

From `studio/llm_tiers.py`. All are tagged Apache-2.0 and ungated on Hugging Face, for both the Qwen source and the unsloth GGUF. The sizes are the weights, from that file.

| Tier | Model | Quant | GB | Needs | Runs on | Licence | Gated | Source |
|---|---|---|---|---|---|---|---|---|
| tiny | Qwen/Qwen3.5-2B | Q8_0 | 2.0 | 6 GB RAM | cpu | Apache-2.0 | No | [unsloth/Qwen3.5-2B-GGUF](https://huggingface.co/unsloth/Qwen3.5-2B-GGUF) `Qwen3.5-2B-Q8_0.gguf` |
| small | Qwen/Qwen3.5-4B | UD-Q6_K_XL | 4.1 | 8 GB RAM | cpu | Apache-2.0 | No | [unsloth/Qwen3.5-4B-GGUF](https://huggingface.co/unsloth/Qwen3.5-4B-GGUF) `Qwen3.5-4B-UD-Q6_K_XL.gguf` |
| medium | Qwen/Qwen3.5-9B | UD-Q5_K_XL | 6.7 | 16 GB RAM | cpu | Apache-2.0 | No | [unsloth/Qwen3.5-9B-GGUF](https://huggingface.co/unsloth/Qwen3.5-9B-GGUF) `Qwen3.5-9B-UD-Q5_K_XL.gguf` |
| moe | Qwen/Qwen3.5-35B-A3B | UD-Q4_K_XL | 22.2 | 32 GB RAM | cpu | Apache-2.0 | No | [unsloth/Qwen3.5-35B-A3B-GGUF](https://huggingface.co/unsloth/Qwen3.5-35B-A3B-GGUF) `Qwen3.5-35B-A3B-UD-Q4_K_XL.gguf` |
| large | Qwen/Qwen3.5-27B | UD-Q4_K_XL | 17.6 | 32 GB RAM, 24 GB VRAM | gpu | Apache-2.0 | No | [unsloth/Qwen3.5-27B-GGUF](https://huggingface.co/unsloth/Qwen3.5-27B-GGUF) `Qwen3.5-27B-UD-Q4_K_XL.gguf` |
| studio | Qwen/Qwen3.8-27B-FP8 | FP8 | 29.0 | 64 GB RAM, 64 GB VRAM | gpu | Apache-2.0 | No | [Qwen/Qwen3.8-27B-FP8](https://huggingface.co/Qwen/Qwen3.8-27B-FP8) (vLLM) |

The speed figures in that file are estimates from memory bandwidth, not benchmarks.

## Partner-node audit

Open Weights Only forbids partner nodes and closed-source APIs. A node counts as a partner node if ComfyUI marks it `api_node` in `/object_info`. This audit checked every graph against ComfyUI v0.43.0's node list on 2026-10-30, and searched the code for hosted API hosts.

| Where | Result |
|---|---|
| `workflows/*.json` (all, including the in-progress flagship graphs) | **No partner nodes.** All nodes are ComfyUI core, except `LTXFloatToInt` (Lightricks ComfyUI-LTXVideo, used by LTX), `VRAM_Debug` (KJNodes), the LTX IC-LoRA nodes (ComfyUI-LTXVideo) and `PSN_FPSResampler` (this repo) |
| `studio/edits.py`, tool `bgremove` | **Partner node.** The `utility-bria_remove_video_background` template uses `BriaRemoveVideoBackground`. The other 15 tools use local nodes. Hidden in the open edition |
| Apps tab, official apps from ComfyUI's template package | **8 of 11 official apps use partner nodes** (`GeminiImage2Node`, `GeminiNode`, `KlingFirstLastFrameNode`, `GrokImageEditNodeV2`, `GrokImageNode`, `RecraftRemoveBackgroundNode`). The open edition hides them: the studio reads the `api_node` flag and leaves out any app that uses one. A later edition could turn them back on (see EDITIONS.md) |
| `psn_nodes/gen/psn_gemini_prompt_crafter.py` | Prepares requests for a closed API. Not registered as a node in the open edition |
| Language model for the crew | Local by default. Subagents talk only to loopback servers in the Open edition. `STUDIO_LLM_URL` can point the crew at a server you choose |
| `psn/`, `psn_nodes/` | A test (`tests/test_open_edition_no_paid_apis.py`) fails the build if a paid host or SDK appears. The node `psn_gemini_prompt_crafter` only builds and parses payloads and makes no call; it is still worth removing from an Open Weights entry |
| Model browser | Catalogue lookups to Civitai and Hugging Face. No generation goes through them |
| `psn/connectors/registry.py` | Remote generation connectors are marked planned, and off in the Open edition |
