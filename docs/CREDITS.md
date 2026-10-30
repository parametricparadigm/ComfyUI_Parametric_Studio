# Credits

Parametric Studio's flagship apps stand on other people's open work. This page says what each app took and from whom. Model licences are separate from code licences: read each model's card before commercial use.

## Recast (character swap)

- **[Openjutsu](https://github.com/Comfy-Org/comfy-openjutsu)** by Comfy Org (MIT). The app idea and its inputs (a video, a character image, an optional direction, the source audio kept) follow Openjutsu. Its `workflows/swap.api.json` and `build/model-files.md` were read as the reference. No Openjutsu code or graph is copied or run.
- **[H3 Character Swap](https://github.com/akatz-labs/h3-character-swap-tool)** by Akatz Labs (workflow MIT, `h3_character_swap` node pack GPL-3.0). Openjutsu is built on this workflow. Recast does **not** use or ship the node pack: its graph is built around ComfyUI's core `MiniMaxH3ReferenceToVideo` node with `<Video 1>` and `<Picture 1>` (other nodes are listed under Tools), so it has no SAM mask, first-frame anchor or windowed continuation.
- **[MiniMax-H3-Character-Swap-LoRA](https://huggingface.co/akatz-ai/MiniMax-H3-Character-Swap-LoRA)** by akatz-ai, MiniMax H3 Community License. Recast's prompt is the example on this LoRA's card with the blanks filled in.

## Models

| Model | Used by | Licence |
|---|---|---|
| [MiniMax H3](https://huggingface.co/MiniMaxAI/MiniMax-H3) (ComfyUI repack: [Comfy-Org/MiniMax-H3](https://huggingface.co/Comfy-Org/MiniMax-H3)) | Recast, Reshoot, Frozen orbit, Director | MiniMax H3 Community License. Its standard grant excludes some regions, including the US, EU, UK and South Korea: read it before you deploy. |
| [MiniMax Music 3](https://huggingface.co/MiniMaxAI/MiniMax-Music3) (ComfyUI repack: [Comfy-Org/MiniMax-Music-3](https://huggingface.co/Comfy-Org/MiniMax-Music-3)) | Music | MiniMax-Music3 Community License: commercial products must display the name, and written authorization is needed above US$20,000,000 in yearly revenue |
| LTX-2.5 and its IC-LoRAs (Water Simulation, Clean Plate, Day To Night, Alpha Gen) by [Lightricks](https://huggingface.co/Lightricks) | VFX | LTX-2.x community licence, gated download |
| [MiniMax-H3 360 Orbit LoRA](https://huggingface.co/pablodawson/MiniMax-H3-360-Orbit-LoRA) by Pablo Dawson | Frozen orbit | MiniMax H3 Community License. Its prompt and settings are the card's. |
| [Wan 2.2 Fun Camera](https://huggingface.co/alibaba-pai/Wan2.2-Fun-A14B-Control-Camera) by alibaba-pai (ComfyUI repack: [Comfy-Org/Wan_2.2_ComfyUI_Repackaged](https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged)) | Reshoot (Wan camera) | Apache-2.0 |

## Tools

- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) core nodes run every graph.
- `VRAM_Debug` from [ComfyUI-KJNodes](https://github.com/kijai/ComfyUI-KJNodes) by kijai (GPL-3.0) unloads the text encoder before sampling in Recast. The graph calls this node; its code is not part of this repo.
- `LTXICLoRALoaderModelOnly` and `LTXAddVideoICLoRAGuide` from [ComfyUI-LTXVideo](https://github.com/Lightricks/ComfyUI-LTXVideo) by Lightricks drive the IC-LoRAs in VFX. The graph calls these nodes; their code is not part of this repo.

## Code and libraries included in this repository

| Component | Where | Licence |
|---|---|---|
| [Preact](https://github.com/preactjs/preact) 10.24.3 | `studio/web/vendor/preact.mjs`, `hooks.mjs` | MIT |
| [htm](https://github.com/developit/htm) 3.1.1 | `studio/web/vendor/htm.mjs` | Apache-2.0 |
| [three.js](https://github.com/mrdoob/three.js) r160 (core, OrbitControls, GLTFLoader, BufferGeometryUtils) | `studio/web/vendor/` | MIT |
| [Archivo](https://github.com/Omnibus-Type/Archivo) (font) | `studio/web/vendor/fonts/` | SIL OFL 1.1 |
| [Inter](https://github.com/rsms/inter) (font) | `studio/web/vendor/fonts/` | SIL OFL 1.1 |
| [awesome-claude-agents](https://github.com/vijaythecoder/awesome-claude-agents) role playbook excerpts | `psn/subagents/playbooks/` | MIT |

Each keeps its licence file beside it. ComfyUI (GPL-3.0) is a runtime dependency and is not included.

## Design ideas, no code taken

From [PROVENANCE.md](../PROVENANCE.md):

- [yanhuifair/ComfyUI-FairLab](https://github.com/yanhuifair/ComfyUI-FairLab) (MIT): the idea of evaluating a whitelisted expression tree instead of calling `eval` (`psn/expr.py`).
- [Duanyll/comfyui_functional](https://github.com/Duanyll/comfyui_functional): the lesson that running code should be off unless switched on (`psn/sandbox*.py`).
- ComfyUI's lazy-evaluation convention (`check_lazy_status`) and public node API shape (`PSN_Branch` and related nodes).

The sources listed in [SKILL_SOURCES.md](SKILL_SOURCES.md) informed interface polish and agent playbooks.

## Tools used to build the entry

Claude Code with Claude models (Anthropic) wrote and reviewed much of the studio. A local Qwen3.8-27B model, through a node factory built for this project, wrote the `psn_nodes/gen/` modules, which had to pass automated gates before merging (see [PROVENANCE.md](../PROVENANCE.md)). No model from either tool runs inside the studio unless you choose a local Qwen model for the crew.
