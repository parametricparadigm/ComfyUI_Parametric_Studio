# RECIPES - 17-Music-song-models

| Model / Variant | Steps | CFG / Guidance | Sampler / Scheduler | Resolution / Frames / FPS | Shift / Strength | Outcome / Notes | Source |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| ACE-Step 1.5 Turbo | 8 | Not used | Not in sources | 48kHz stereo WAV | Not in sources | Fast generation; "Very High" quality, "Medium" diversity | [MODEL.md], [PUBLIC README https://huggingface.co/ACE-Step/Ace-Step1.5/raw/main/README.md] |
| ACE-Step 1.5 Base | 32-50 | Supported | Not in sources | 48kHz stereo WAV | Not in sources | "Medium" quality, "High" diversity; supports Cover, Repaint, Extract, Lego, Complete | [MODEL.md], [PUBLIC README https://huggingface.co/ACE-Step/Ace-Step1.5/raw/main/README.md] |
| ACE-Step 1.5 SFT | 32-50 | Supported | Not in sources | 48kHz stereo WAV | Not in sources | "High" quality, "Medium" diversity; supports Cover, Repaint | [MODEL.md], [PUBLIC README https://huggingface.co/ACE-Step/Ace-Step1.5/raw/main/README.md] |
| ACE-Step 1.5 SftTurbo50 | Not in sources | Not in sources | Not in sources | 48kHz stereo WAV | Not in sources | Weight merge provides "a little more richness from the SFT while maintaining the low number of Turbo steps" | [PUBLIC README https://huggingface.co/Serveurperso/ACE-Step-1.5-GGUF/raw/main/README.md] |
| ACE-Step 1.5 Turbo-Shift1 | Not in sources | Not in sources | Not in sources | 48kHz stereo WAV | Not in sources | Variant available in standard 2B DiT | [PUBLIC README https://huggingface.co/Serveurperso/ACE-Step-1.5-GGUF/raw/main/README.md] |
| ACE-Step 1.5 Turbo-Shift3 | Not in sources | Not in sources | Not in sources | 48kHz stereo WAV | Not in sources | Variant available in standard 2B DiT | [PUBLIC README https://huggingface.co/Serveurperso/ACE-Step-1.5-GGUF/raw/main/README.md] |
| ACE-Step 1.5 Turbo-Continuous | Not in sources | Not in sources | Not in sources | 48kHz stereo WAV | Not in sources | Variant available in standard 2B DiT | [PUBLIC README https://huggingface.co/Serveurperso/ACE-Step-1.5-GGUF/raw/main/README.md] |
| ACE-Step 1.5 Turbo-RL | 8 | Not used | Not in sources | 48kHz stereo WAV | Not in sources | "Very High" quality, "Medium" diversity; RL trained | [PUBLIC README https://huggingface.co/ACE-Step/Ace-Step1.5/raw/main/README.md] |
| Mini-Max Music 3 | Not in sources | Not in sources | Not in sources | Not in sources | Not in sources | Text-to-Music generation | [WORKFLOW_PLAN.md], [PUBLIC README https://huggingface.co/Comfy-Org/MiniMax-Music-3/raw/main/README.md] |

Not in sources: Specific CFG scale values for ACE-Step 1.5 Base/SFT variants.
Not in sources: Specific sampler or scheduler names (e.g., Euler, DPM++).
Not in sources: Specific shift or strength values for ACE-Step 1.5 variants.
Not in sources: Specific resolution, frame count, or FPS settings for Mini-Max Music 3.
Not in sources: Steps, CFG, or sampler settings for Mini-Max Music 3.

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
