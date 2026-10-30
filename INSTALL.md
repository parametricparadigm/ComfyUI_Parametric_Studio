# Installing Parametric Studio

Parametric Studio needs a ComfyUI server and a small Python web app. `install.py` sets up both. You can also connect the app to a ComfyUI you already have.

## What was checked

| Command | Checked on |
|---|---|
| `python3 install.py --help` | Linux, run |
| `python3 install.py --list` | Linux, run |
| `python3 install.py --dry-run` | Linux with real hardware detection, and with simulated NVIDIA 12 GB, NVIDIA 96 GB, Windows AMD 16 GB, Apple 16 GB and CPU-only profiles |
| Installer logic: plan, commands, launchers, resume, hash check | Automated tests with no network (`tests/test_install.py`, `tests/test_boxcheck.py`) |
| Starting `python -m studio.server` from a fresh clone with no ComfyUI running | Linux, run |

**Not checked:** a real install from start to finish on any operating system. `install.py` has not been run on a real Windows or macOS machine, or on an AMD GPU, and the Windows launcher has not been executed. If a step fails there, please open an issue with its output.

## Requirements

- Python 3.12 is the tested version. `install.py` itself needs 3.10 or newer and only the standard library.
- git, and ffmpeg with ffprobe on your PATH (the timeline and clip tools use them).
- Disk: 15 GB for the smallest image goal, more for others. Run `python3 install.py --list` to see sizes.
- A GPU for real work. Peak VRAM measured on the author's card is in [MODELS.md](MODELS.md). Lower-memory cards can use ComfyUI's offloading, which is slower and has not been measured.

## Linux

```bash
git clone <this repository's URL> ComfyUI_Parametric_Studio
cd ComfyUI_Parametric_Studio
python3 install.py --dry-run
python3 install.py
```

Install ffmpeg with your package manager, for example `sudo apt install ffmpeg git python3-venv`.

## macOS

```bash
brew install python@3.12 git ffmpeg
git clone <this repository's URL> ComfyUI_Parametric_Studio
cd ComfyUI_Parametric_Studio
python3.12 install.py --dry-run
python3.12 install.py
```

Apple machines use MPS. The planner offers only the goals with no NVIDIA-specific requirement, and these have not been tried on a Mac: expect slow runs or failures.

## Windows

Install [Python 3.12](https://www.python.org/downloads/), [Git](https://git-scm.com/download/win) and [ffmpeg](https://ffmpeg.org/download.html), then in PowerShell:

```powershell
git clone <this repository's URL> ComfyUI_Parametric_Studio
cd ComfyUI_Parametric_Studio
py -3.12 install.py --dry-run
py -3.12 install.py
```

The installer writes `run_studio.bat`. Windows may refuse the symlink it uses for the custom nodes without Developer Mode; it then copies the folder instead, so re-run the copy after updating the repository.

## Stable or nightly

Pick your ComfyUI with `--channel`. **Stable** pins the ComfyUI release this studio was tested on and is the default. **Nightly** follows ComfyUI's master branch, so it gets new models first and can break.

| | Stable | Nightly |
|---|---|---|
| Linux, macOS | `python3 install.py` | `python3 install.py --channel nightly` |
| Windows | `py install.py` | `py install.py --channel nightly` |

Add `--dry-run` to any of these to see the plan first. Windows and macOS have not been run end to end yet; the table at the top of this page says what was checked.

## Extended edition

The open edition, which is the contest entry, uses local open-weights models only. The Extended edition adds ComfyUI's partner workflows as forms and Connect your Printify. Those need your own accounts and can spend your credits. Build it with `python scripts/assemble_extended.py`, then start the studio with `PSN_EDITION=extended`.

## How `install.py` works

1. **Looks at the machine** (`studio/boxcheck.py`): operating system, GPU and VRAM, RAM, free disk, and which backend applies (`cuda`, `rocm`, `mps` or `cpu`).
2. **Plans.** For each goal you ask for, it compares the measured peak VRAM with your usable VRAM (2 GiB is held back), then chooses `gpu`, `offload` (adds `--lowvram` or `--novram`) or `unavailable`, and says why. Models that cannot work on the machine are not downloaded. The H3 goals need a card that can use NVFP4; on others they show as unavailable.
3. **Prints the plan and asks.** `--dry-run` stops after printing every step. `--yes` skips the question. It refuses to run as root without `--yes`.
4. **Installs** into `--dir` (default: a `parametric-studio-runtime` folder beside the repository): a venv, PyTorch for the backend, ComfyUI at the ref in `channels.json`, ComfyUI's requirements, the studio's packages, and a link to this repository in `ComfyUI/custom_nodes`. LTX goals also clone the Lightricks ComfyUI-LTXVideo pack, because the LTX graphs use its `LTXFloatToInt` node.
5. **Downloads models** from Hugging Face into `ComfyUI/models`, with resume and a SHA-256 check against `studio/models_manifest.json`. A file that fails the check is deleted.
6. **Writes a launcher**, `run_studio.sh` or `run_studio.bat`, which starts ComfyUI on port 8200 and the studio on port 8310 with the right paths and flags.

Exit codes: 0 done, 2 cancelled, 3 nothing installable for these goals, 4 a step failed.

### Options

| Option | Meaning |
|---|---|
| `--goals image,video` | Goals to fetch. Default `image`. `all` for every goal that fits. |
| `--list` | Goals with download sizes |
| `--channel stable` | ComfyUI `v0.43.0`, the release the studio was built against. `nightly` follows ComfyUI's `master` branch. |
| `--include-gated` | Also fetch gated models (FLUX.3 Klein, LTX-2.5) |
| `--no-models` | Software only |
| `--dir PATH` | Where everything goes |
| `--dry-run` | Print and change nothing |
| `--profile-json FILE` | Plan for a simulated machine |

Gated models: accept the licence on the model's Hugging Face page, create a read token, and set it as `HF_TOKEN` before running. The token is sent only to huggingface.co and is never printed or saved.

Bigger downloads are your choice, and `--goals all --include-gated` can reach 150 GB or more. Read [MODELS.md](MODELS.md) first: some of these licences have conditions that depend on where you are and what you do with the output.

## Using a ComfyUI you already have

```bash
python -m venv .venv && . .venv/bin/activate
pip install fastapi uvicorn python-multipart pydantic numpy pillow
ln -s "$PWD" /path/to/ComfyUI/custom_nodes/comfyui_parametric_studio   # for the PSN nodes; restart ComfyUI
COMFYUI_URL=http://127.0.0.1:8188 \
STUDIO_MODELS_ROOT=/path/to/ComfyUI/models \
STUDIO_OUTPUT_DIR=/path/to/ComfyUI/output \
STUDIO_COMFY_INPUT=/path/to/ComfyUI/input \
python -m studio.server
```

The `pip install` line is what the studio's imports require, but it was not run in an empty environment for this release. File names in the graphs are matched to what your ComfyUI has installed, so your folder layout can differ; close matches only.

The custom nodes run inside ComfyUI's own Python and use what is already there (torch, numpy, Pillow). The `PSN_` metadata encryption node also needs `cryptography`.

## Settings

| Variable | Default | Meaning |
|---|---|---|
| `COMFYUI_URL` | `http://127.0.0.1:8200` | The ComfyUI server |
| `STUDIO_HOST`, `STUDIO_PORT` | `127.0.0.1`, `8310` | Where the studio listens. See [SECURITY.md](SECURITY.md) before changing the host. |
| `STUDIO_MODELS_ROOT`, `PSN_MODELS_ROOT` | what the running ComfyUI reports, then `~/ComfyUI/models` | Your ComfyUI `models` folder |
| `STUDIO_OUTPUT_DIR` | what the running ComfyUI reports, then `~/ComfyUI/output` | Your ComfyUI `output` folder |
| `STUDIO_COMFY_INPUT` | what the running ComfyUI reports, then `~/ComfyUI/input` | Your ComfyUI `input` folder |
| `STUDIO_UNIVERSITY` | `studio/university/` in the repo | Optional: another folder holding lessons |
| `STUDIO_KB` | `studio/crew_notes/` in the repo | Optional: a larger folder of crew notes with the same layout |
| `PSN_SETTINGS` | `~/.config/parametric-studio/settings.env` | Optional file of `KEY=value` lines for any setting here, so you need not export them |
| `PSN_EDITION` | `open` | `open` hides partner nodes and closed APIs. See [EDITIONS.md](EDITIONS.md) |
| `STUDIO_LLM_URL`, `STUDIO_LLM_MODEL` | looks on local ports 8002, 8301, 11434 | An OpenAI-style local language model for the crew |
| `STUDIO_ALLOW_DOWNLOAD` | `1` | `0` turns off downloads from the model browser |
| `HF_TOKEN` | unset | Gated Hugging Face downloads |
| `CIVITAI_TOKEN` | unset | Civitai downloads |
| `GITHUB_TOKEN` | unset | Only for the optional GitHub publish tool |

The launcher sets the path variables for you.

## Optional: a language model for the crew

With no language model, the crew answers by quoting the closest passage from its notes. Written answers, and Prime, need a local OpenAI-style server. `GET /api/llm` prints the Qwen tier that fits your memory and the exact `llama-server` or vLLM command. Details are in [docs/LLM_TUNING.md](docs/LLM_TUNING.md). Memory detection there reads `/proc/meminfo`, so it works on Linux only for now.

## Troubleshooting

- **"ComfyUI is not reachable":** ComfyUI has not started or `COMFYUI_URL` is wrong. Check `GET /api/health`.
- **"ComfyUI rejected the graph":** usually a missing model or node. The Models tab and the message name it.
- **403 on a download:** accept the model's licence on Hugging Face and set `HF_TOKEN`.
- **Empty model list or an error about a path you do not have:** set the path variables above.
