# Coverage: notable open models from SD 1.5 to today

Checked on 30 Oct 2026. 87 notable open models, by kind and year, each marked as a core goal here, a family instance here, or missing. The same data drives the Coverage view in the Atlas page (`studio/atlas_models.json`, key `coverage`).

- **Core goal here**: a button in Create runs it (or, for the Qwen language models, it is a crew LLM tier in `studio/llm_tiers.py`).
- **Family instance here**: the family has a folder under the model library and its own ComfyUI instance (`python -m psn.instances start <family>`). 82 families are installed.
- **Missing**: no family folder and no goal. That is not a claim the model cannot be added.

Totals: 9 core goal, 53 family instance, 25 missing.

## What it was compared against

- Comfy's own list of local models, https://comfy.org/hub/models/local/ (read with curl on 30 Oct 2026; 334 model slugs).
- The ComfyUI workflow template packages in the studio's Python environment, `comfyui_workflow_templates_*` (661 template files).
- `psn.instances.families()`: the 82 installed families.

Dates and licences were read from arXiv (first submission), Hugging Face repository metadata, or an official page; anything not read says unverified. Utilities (depth, segmentation, background removal) and community fine-tunes and LoRAs were not audited model by model.

## Missing from this studio (a notable model, by name)

| Model | Kind | Date | Licence | In Comfy's hub or templates | Source |
|---|---|---|---|---|---|
| DeepFloyd IF | Image | 2023 | deepfloyd-if-license (see the model card) | no | [link](https://huggingface.co/DeepFloyd/IF-I-XL-v1.0) |
| MusicGen | Audio | 2023 | CC BY-NC 4.0 | no | [link](https://arxiv.org/abs/2306.05284) |
| Kandinsky 2.2 | Image | 2023 | Apache-2.0 | no | [link](https://huggingface.co/kandinsky-community/kandinsky-2-2-decoder) |
| AnimateDiff | Video | 2023 | Not verified here (unverified) | no | [link](https://arxiv.org/abs/2307.04725) |
| Stable Zero123 | 3D | 2023 | sai-nc-community (see the model card) | no | [link](https://huggingface.co/stabilityai/stable-zero123) |
| Playground v2.5 | Image | 2024 | playground-v2dot5-community (see the model card) | no | [link](https://huggingface.co/playgroundai/playground-v2.5-1024px-aesthetic) |
| AuraFlow | Image | 2024 | Apache-2.0 | no | [link](https://huggingface.co/fal/AuraFlow-v0.3) |
| Pyramid Flow | Video | 2024 | Stability AI Community License | no | [link](https://huggingface.co/rain1011/pyramid-flow-sd3) |
| Open-Sora 2 | Video | 2025 | Apache-2.0 | no | [link](https://huggingface.co/hpcai-tech/Open-Sora-v2) |
| MAGI-1 | Video | 2025 | Apache-2.0 | yes | [link](https://huggingface.co/sand-ai/MAGI-1) |
| SkyReels V2 | Video | 2025 | skywork-license (see the model card) | no | [link](https://huggingface.co/Skywork/SkyReels-V2-T2V-14B-540P) |
| gpt-oss | LLM | 2025 | Apache-2.0 | yes | [link](https://openai.com/index/introducing-gpt-oss/) |
| NetaYume Lumina | Image | 2025 | Apache-2.0 | yes | [link](https://huggingface.co/duongve/NetaYume-Lumina-Image-2.0) |
| Chroma | Image | 2025 | Apache-2.0 | yes | [link](https://huggingface.co/lodestones/Chroma1-HD) |
| HuMo | Video | 2025 | Apache-2.0 | yes | [link](https://huggingface.co/bytedance-research/HuMo) |
| Qwen3 and Qwen3-VL | LLM | 2025 | Apache-2.0 | yes | [link](https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct) |
| ChronoEdit 14B | Image | 2025 | Apache-2.0 | yes | [link](https://huggingface.co/nvidia/ChronoEdit-14B-Diffusers) |
| NewBie-image | Image | 2025 | newbie-nc-1.0 (see the model card) | yes | [link](https://huggingface.co/NewBie-AI/NewBie-image-Exp0.1) |
| FireRed-Image-Edit | Image | 2026 | Apache-2.0 | yes | [link](https://huggingface.co/FireRedTeam/FireRed-Image-Edit-1.1) |
| JoyAI-Image-Edit | Image | 2026 | Apache-2.0 | yes | [link](https://huggingface.co/jdopensource/JoyAI-Image-Edit) |
| Stable Audio 3 and Stable Audio Open | Audio | 2026 | stable-audio-community (see the model card) | yes | [link](https://huggingface.co/stabilityai/stable-audio-3-medium) |
| Gemma 4 | LLM | 2026 | Apache-2.0 | yes | [link](https://huggingface.co/google/gemma-4-12b) |
| TripoSplat | 3D | 2026 | MIT | yes | [link](https://huggingface.co/VAST-AI/TripoSplat) |
| Mage-Flow | Image | 2026 | MIT | yes | [link](https://huggingface.co/Comfy-Org/Mage-Flow) |
| Stable Diffusion 2.x | Image | n/a (unverified) | Not verified here (unverified) | no | none |

Notes on the missing models:

- **MusicGen**: arXiv 2306.05284; weights are CC BY-NC 4.0. Not on Comfy's lists.
- **AnimateDiff**: arXiv 2307.04725, listed by date only.
- **Stable Zero123**: Not on Comfy's lists.
- **AuraFlow**: Date is the v0.3 repository.
- **gpt-oss**: Comfy's hub lists gpt-oss-20b. This atlas has the history card; no studio tier uses it.
- **NetaYume Lumina**: An anime fine-tune of Lumina-Image 2.0 that Comfy's templates include.
- **Chroma**: Comfy's templates include Chroma and Chroma Radiance.
- **Qwen3 and Qwen3-VL**: Comfy has text-generation templates for these; the studio has no tier for them.
- **JoyAI-Image-Edit**: The video edit sibling, JoyAI-Video-Edit, is installed.
- **Stable Audio 3 and Stable Audio Open**: Stable Audio 3 is a 2026 release; Stable Audio Open 1.0 is from 2024.
- **Gemma 4**: Date is the 12b repository; the family began in March 2026. Used inside LTX-2.5 as a text encoder.
- **Mage-Flow**: Date is the Comfy-Org repackage.
- **Stable Diffusion 2.x**: The Hugging Face repository answers 401 without a login, so its date and licence are not verified here.

## Core goals here

| Model | Kind | Year | Goals |
|---|---|---|---|
| Wan 2.2 | Video | 2025 | video, animate, reshoot_wan |
| FLUX.2 [klein] | Image | 2026 | image |
| Anima | Image | 2026 | anime |
| LTX-2.5 (with LTX-2 and 2.3 support files) | Video | 2026 | video_ltx, animate_ltx, vfx_ltx |
| MiniMax H3 | Video, Audio | 2026 | h3_video, h3_animate, recast, reshoot, director, director_keyframes |
| MiniMax Music 3 | Audio | 2026 (unverified) | music |
| Qwen3.8 (crew tier) | LLM | 2026 | crew LLM tier |
| FLUX 3 Image Klein | Image | 2026 | flux3 |
| Qwen3.5 (crew tiers) | LLM | n/a (unverified) | crew LLM tier |

## Family instances here

| Model | Kind | Year | Family folder | Licence |
|---|---|---|---|---|
| Stable Diffusion 1.5 | Image | 2022 | SD15 | CreativeML Open RAIL-M |
| Shap-E | 3D | 2023 | Shap-E | MIT |
| SDXL, SDXL Turbo | Image | 2023 | SDXL | CreativeML Open RAIL++-M |
| Stable Video Diffusion | Video | 2023 | SVD | Stable Video Diffusion Community licence |
| Stable Cascade | Image | 2024 | Stable-Cascade | Non-commercial research licence |
| TripoSR | 3D | 2024 | TripoSR | MIT |
| PixArt-Sigma | Image | 2024 | PixArt-Sigma | CreativeML Open RAIL++-M |
| InstantMesh | 3D | 2024 | InstantMesh | Apache-2.0 |
| HunyuanDiT | Image | 2024 | HunyuanDiT-1.2 | Tencent Hunyuan Community License |
| Kolors | Image | 2024 | Kolors | Apache-2.0 |
| Stable Diffusion 3 and 3.5 | Image | 2024 | SD3-SD3.5 | Stability AI Community License |
| Stable Fast 3D | 3D | 2024 | Stable-Fast-3D | Stability AI Community License |
| FLUX.1 (dev, schnell, Kontext, Fill) | Image | 2024 | Flux.1 | [schnell] Apache-2.0; [dev] FLUX.1 [dev] Non-Commercial License |
| CogVideoX | Video | 2024 | CogVideoX | Apache-2.0 |
| Allegro | Video | 2024 | Allegro | Apache-2.0 |
| Mochi 1 | Video | 2024 | Mochi | Apache-2.0 |
| HunyuanVideo and 1.5 | Video | 2024 | HunyuanVideo | Tencent Hunyuan Community License |
| Lumina-Image 2.0 | Image | 2025 (unverified) | Lumina-2 | Apache-2.0 |
| Wan 2.1 | Video | 2025 | Wan2.1 | Apache-2.0 |
| MIDI-3D | 3D | 2025 | MIDI-3D | Apache-2.0 |
| HiDream-I1 and O1 | Image | 2025 (unverified) | HiDream | MIT |
| UniRig | 3D | 2025 | UniRig | Not verified here (unverified) |
| Cosmos-Predict2 | Image, Video | 2025 | Cosmos | NVIDIA Open Model License |
| PartCrafter | 3D | 2025 | PartCrafter | MIT |
| Hunyuan3D 2.x | 3D | 2025 | Hunyuan3D-2.1 | Tencent Hunyuan Community License |
| OmniGen2 | Image | 2025 | Omnigen-2 | Apache-2.0 |
| HunyuanWorld | 3D | 2025 | HunyuanWorld | Tencent HunyuanWorld-1.0 Community License |
| Matrix-Game 2.0 | Video | 2025 | Matrix-Game-2 | MIT |
| Wan 2.2 Animate | Video | 2025 | Wan2.2-Animate | Apache-2.0 |
| SANA-Video | Video | 2025 | SANA-Video | Apache-2.0 |
| Kandinsky 5.0 (T2I Lite) | Image | 2025 | Kandinsky-5.0-T2I-Lite | MIT |
| SAM 3D Objects | 3D | 2025 | SAM-3D-Objects | Custom licence (see the model card) |
| FLUX.2 [dev] | Image | 2025 | Flux.2 | FLUX Non-Commercial License |
| Z-Image | Image | 2025 (unverified) | Z-Image | Apache-2.0 |
| Ovis-Image | Image | 2025 | Ovis-Image | Apache-2.0 |
| TRELLIS and TRELLIS.2 | 3D | 2025 | TRELLIS-2-4B | MIT |
| LongCat-Image | Image | 2025 | LongCat-Image | Apache-2.0 |
| HY-Motion | 3D | 2025 | HY-Motion | Tencent Hunyuan Community License |
| ACE-Step | Audio | 2026 | ACE-Step-1.5 | MIT |
| MOVA | Video, Audio | 2026 | MOVA | Apache-2.0 |
| PixelDiT | Image | 2026 | PixelDiT | NVIDIA licence nsclv1 (see the model card) |
| ERNIE-Image | Image | 2026 | Ernie-Image | Apache-2.0 |
| Pixal3D | 3D | 2026 | Pixal3D | MIT |
| LongCat-Video-Avatar | Video | 2026 | LongCat-Avatar-15 | MIT |
| Ideogram 4 | Image | 2026 | Ideogram4 | Ideogram 4 Non-Commercial licence |
| SCAIL-2 | Video | 2026 | Wan-SCAIL-2 | MIT |
| Boogu-Image | Image | 2026 | Boogu | Apache-2.0 |
| Krea 2 | Image | 2026 | Krea2 | Krea 2 Community License |
| JoyAI-Video-Edit | Video | 2026 | JoyAI-Video-Edit | Apache-2.0 |
| YuE2 | Audio | 2026 | yue2 | CC BY-NC 4.0 |
| Qwen-Image 2.x | Image | 2026 | Qwen-Image-2.1 | Qwen Research License |
| Ming-Image | Image | 2026 | Ming-Image | MIT |
| MOSS-Image | Image | 2026 | Moss-Image | Apache-2.0 |

## How to refresh

Rebuild `studio/atlas_models.json` with the builder script (it rereads Hugging Face, arXiv, Comfy's hub page and the template packages; it is kept with the author's working files, outside this repository for now), then regenerate this file from the new data.
