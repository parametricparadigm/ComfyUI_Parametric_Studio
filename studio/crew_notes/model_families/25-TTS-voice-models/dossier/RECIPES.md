# RECIPES - 25-TTS-voice-models

| Model / Variant | Setting / Parameter | Value / Configuration | Outcome / Purpose | Source |
| :--- | :--- | :--- | :--- | :--- |
| Chatterbox | `exaggeration` | `0.5` (default) | General use; works well for most prompts. | [MODEL.md] |
| Chatterbox | `cfg` | `0.5` (default) | General use; works well for most prompts. | [MODEL.md] |
| Chatterbox | `cfg` | `~0.3` | For fast speakers or expressive speech; improves pacing for fast reference speakers. | [MODEL.md] |
| Chatterbox | `exaggeration` | `~0.7+` | For dramatic speech; tends to speed up speech. | [MODEL.md] |
| Chatterbox | `cfg` | `0` | Mitigates accent inheritance from reference clip when language tag does not match reference language. | [PUBLIC README https://huggingface.co/ResembleAI/chatterbox/raw/main/README.md] |
| FireRedTTS-1S | `config_path` | `configs/config_24k.json` | Acoustic LLM decoder configuration. | [MODEL.md] |
| FireRedTTS-1S | `config_path` | `configs/config_24k_flow.json` | Flow-matching decoder configuration. | [MODEL.md] |
| FireRedTTS-1S | `use_tn` | `True` | Text normalization; enabled for test-hard evaluation. | [MODEL.md] |
| FireRedTTS-1S | `prompt_wav` duration | 3–10 seconds | Recommended duration for reference audio to enhance stability and naturalness. | [MODEL.md] |
| FireRedTTS-1S | Output sample rate | 24 kHz | Audio waveform output frequency. | [MODEL.md] |
| Qwen3-TTS | Synthesis latency | 97ms | End-to-end synthesis latency for streaming generation. | [MODEL.md] |
| Qwen3-TTS | Voice cloning input | 3-second audio | Rapid voice clone input duration for Base models. | [MODEL.md] |
| GPT-SoVITS | Zero-shot input | 5-second vocal sample | Input duration for zero-shot TTS. | [MODEL.md] |
| GPT-SoVITS | Few-shot input | 1 minute training data | Input duration for few-shot TTS. | [MODEL.md] |
| Maya1-TTS | Specific settings | Not in sources: Specific settings or configurations for Maya1-TTS. | N/A | [MODEL.md] |
| Kyutai TTS | Specific settings | Not in sources: Specific settings or configurations for Kyutai TTS. | N/A | [MODEL.md] |
| All Models | Sampler/Scheduler | Not in sources: Sampler or scheduler names. | N/A | [MODEL.md] |
| All Models | Steps | Not in sources: Number of inference steps. | N/A | [MODEL.md] |
| All Models | Resolution/Frames/FPS | Not in sources: Resolution, frame count, or FPS settings. | N/A | [MODEL.md] |
| All Models | Shift/Strength values | Not in sources: Shift or strength values. | N/A | [MODEL.md] |

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
