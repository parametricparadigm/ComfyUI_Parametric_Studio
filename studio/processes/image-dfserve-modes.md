# Image modes moved to ComfyUI

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


## What happened to each entry

Every former entry keeps its id (`df:<mode>:<variant>`) so saved picks and habits still work. A routed entry IS the
adapter and port picker. Its label starts with the old name (`flux_svdquant · Text → image · ComfyUI: ...`).

| Old entry | Now | Same weights (on disk) | Notes |
|---|---|---|---|
| `df:flux_svdquant:t2i` | `ckpt:flux1_svdq_fp4_r32` (Nunchaku `NunchakuFluxDiTLoader`) | `diffusion_models/flux/svdq-fp4_r32-flux.1-dev.safetensors` (dfserve's path was a symlink to it) | SFW |
| `df:flux_fill:inpaint` | engine `fill` (`tools/image_fill_tools.py`) | `diffusion_models/flux/flux.1-fill-dev-OneReward-transformer_fp8.safetensors` | ~1 MP in the input's shape (dfserve squared it to 1024²); portable (port picker) |
| `df:minimax_music:music` | `music:music3` | `diffusion_models/mini_max_music/minimax_music3_dit_fp16.safetensors` | Stays first in the Music tab (the default); now gets the 3-block caption and AR guidance 3.0 the dfserve port never got |
| `df:sdxl:t2i` | **unavailable** | SDXL base 1.0 exists only as a diffusers folder in the HF cache | Needs `checkpoints/sd_xl_base_1.0.safetensors` (dlqueue). Use an SDXL fine-tune (`ckpt:`) |
| `df:sdxl_ip:t2i` | **unavailable** | as sdxl | Also needs an IP-Adapter graph with a reference slot (the entry never had one) |
| `df:flux_local_ip:t2i` | **unavailable** | `ipadapter/FLUX IP/ip_adapter.safetensors` (XLabs) | Needs the x-flux-comfyui nodes (`LoadFluxIPAdapter` / `ApplyFluxIPAdapter`), not installed; no reference slot |
| `df:flux_local_cn:t2i` | **unavailable** | `controlnet/flux/FLUX.1-dev-ControlNet-Union-Pro-2.0.safetensors` | ComfyUI has the nodes (ControlNetLoader, ControlNetApplyAdvanced) but no tested graph and no control-image slot |
| `df:flux_schnell:t2i` | **unavailable** | the FLUX.1-schnell transformer was never downloaded (HF cache: text encoders + VAE only) | Needs `diffusion_models/flux1-schnell.safetensors` (dlqueue) |
| `qwen_image`, `qwen_image_edit`, `ltx_video`, `flux_dev`, `flux2`, `flux_redux`, `wan22_*` (4) | hidden, as before | never on disk / removed | Listed under "skipped" with the reason, prefixed "dfserve retired (author 2026-10-12)" |

An unavailable entry's reason reads `dfserve retired (author 2026-10-12); no ComfyUI path yet: <what is missing>`.

## Step-by-step in the studio UI
1. Image tab: the old `df:` rows sit where they were (after the picks). Routed rows render on ComfyUI; unavailable rows
   are greyed out with the reason.
2. `flux_fill · Inpaint`: drop the picture and paint the mask (white = repaint); describe only the new content.
3. Old studio cards made by dfserve still show their images (served from `a local folder`); a
   **Retry** of one renders on the ComfyUI route of its entry id. A job still queued for dfserve fails with the reason.

## Settings
- Routed `ckpt` entries: the fine-tune's chips (aspect, takes, steps, guidance), the model page's rules block.
- Fill: FluxGuidance **30**, 28 steps, euler / normal, CFG 1, DifferentialDiffusion, InpaintModelConditioning
  (noise_mask off) + SetLatentNoiseMask (official template image_flux.1_fill_dev_OneReward; the box's
  `fu_flux_fill_onereward_outpaint` graph: success, 28.4 s wall, 22.0 GB port peak, 2026-10-10).
- Music: `config/studio_music.json` (read per job).

## Chat generation modes
The chatbox Mode dropdown lists the routed modes only (`flux_local`, `flux_svdquant`, `flux_fill`, `minimax_music`,
plus `explore`), read from `config/df_prompt_skills.json`. `df_generate` keeps its name and dfserve's parameter names
(prompt / caption / lyrics / seconds / width / height / seed / num_inference_steps / guidance_scale) and renders on
ComfyUI through the same tools as the studio; results land in `a local folder id>/` and are served
by `/api/artifact/<job id>` after the output guard (dfserve's old outputs are still served from its folder).

## Guards and VRAM
file, the shared preflight (peak + 4 GiB, only the chosen port's idle cache reclaimed, nothing evicted; short = the
card waits). dfserve's own VRAM logic and its 15-minute self-unload are gone with it.

## GPU smoke (2026-10-12,  a local port, `df_generate` end to end on this branch)

| Route | Settings | First call (cold) | Second call | Resident 2nd take (two takes, one load) | dfserve reference |
|---|---|---|---|---|---|
| flux_svdquant → Nunchaku SVDQuant | 25 st, 1024² | 15.3 s | 4.1 s | 4.1 s | none recorded (registry: "~2.5x faster than fp8") |
| flux_fill → ComfyUI Fill | 20 st, guidance 30, 1024² | 20.1 s | 4.1 s | 6.1 s | 7.2 s (NOTES.md, 1024², 20 st) |
| minimax_music → ComfyUI Music 3 | 10 s, instrumental | 21.5 s | 10.2 s | — | not recorded in its params.json |

Every call's tool frees the port after the job, so "second call" includes a reload from the page cache. Images checked
by eye: correct subjects, no black frames; Fill repainted only the masked area (one seed drew a flat disc on the flat
synthetic test picture). The music file is 10.0 s.

## Evidence
- `a local folder` holds only
  `config.json` + the index (2026-10-12); SDXL base 1.0 snapshot = diffusers fp16 files only.
- ` a local port /object_info` 2026-10-12: NunchakuFluxDiTLoader, InpaintModelConditioning, DifferentialDiffusion,
  LoadImageMask present; LoadFluxIPAdapter absent; ControlNetLoader lists FLUX.1-dev-ControlNet-Union-Pro-2.0.
- dfserve timings for comparison: `a local folder` (FLUX local float8+compile 28 steps 6.4 s
  warm; Fill 1024² 20 steps 7.2 s) and the studio job records (flux_local warm job 12.6 s end to end, 2026-10-12 06:41).
