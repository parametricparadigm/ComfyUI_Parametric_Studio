# Faster Wan decode

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


author 2026-10-11: "im sure you can wire one up for light vae", then "yes to all of them" for the studio chip.
Code: `earlier_studio/tools/lightvae_decode.py`. Box side: ComfyUI pack `ComfyUI-ComfyUI-LightVAE`

## What it changes
Only the VAE **decode** at the end of the graph. The chip swaps the graph's core `VAELoader wan/wan_2.1_vae` for
anchor are encoded exactly as before) and whose decode is a ModelTC LightVAE decoder. Sampling, seeds, LoRAs and the
latent are identical; the saved clip differs only by the decoder.

| Option | Decoder | When |
|---|---|---|
| **standard** (default) | stock Wan 2.1 VAE | the tested graphs as they were |
| **fast** | LightVAE **Pro** (`lightvae/lightvae-pro-wan21-decoder.safetensors`, 179 MB) | finals: same quality, faster decode |
| **preview** | LightVAE **Lite** (`lightvae/lightvae-lite-wan21-decoder.safetensors`, 71 MB) | drafts and iteration |

Entries with the chip: `wan:i2v`, `wan:t2v`, `vid:preview`, `vid:svi` (all three clip decodes), `vid:lightwan_i2v`,
`vid:lightwan_t2v`. Not on `vid:turbowan` (its TurboDiffusion sampler decodes inside its own node with its own VAE
wrapper; there is no VAELoader to swap) nor on H3 (the H3 Lite decoder blocks on fast motion; the int8 H3 VAE the
studio uses is already 1.6-1.8x faster than fp16 and lossless).

## The A/B (2026-10-11, this box) [tested]
Same latents (the stock encoder's encoding of three finished Wan clips), core `VAE.decode` in bf16, median of 3,
RTX PRO 6000. PSNR/SSIM vs the stock decode, and vs the source clip.

| Clip | Decoder | Decode s | Speed-up | Decode VRAM | vs stock decode | vs source |
|---|---|---|---|---|---|---|
| 720x1280 x81 | standard | 5.93 | 1.00x | 7.2 GiB | — | 41.95 dB |
| | fast (Pro) | 3.97 | 1.49x | 5.4 GiB | 45.0 dB / 0.991 | 42.02 dB |
| | preview (Lite) | 1.99 | 2.98x | 5.0 GiB | 39.7 dB / 0.963 | 38.93 dB |
| 480x832 x81 | standard | 2.30 | 1.00x | 3.1 GiB | — | 40.52 dB |
| | fast (Pro) | 1.59 | 1.44x | 2.4 GiB | 43.3 dB / 0.994 | 40.23 dB |
| | preview (Lite) | 0.81 | 2.83x | 2.2 GiB | 37.4 dB / 0.981 | 36.97 dB |
| 720x1280 x81 (spin) | standard | 5.94 | 1.00x | 7.2 GiB | — | 43.82 dB |
| | fast (Pro) | 4.06 | 1.46x | 5.4 GiB | 46.7 dB / 0.996 | 43.69 dB |
| | preview (Lite) | 1.98 | 3.00x | 5.0 GiB | 42.0 dB / 0.987 | 41.31 dB |

Read it as: **fast** is as close to the source as standard (within ±0.3 dB) at 1.45-1.5x the decode speed;
**preview** is 3x and a little softer (1-3.6 dB lower; slightly firmer shadows at 1:1). Visual sheets:
`a local folder`. In-server proof: 9/9 Wan decode rows on the  a local port
sidecar (LoadLatent → loader → VAEDecode → mp4). Parity of the box's port vs upstream ModelTC code: 56-58 dB.

## Studio smoke (2026-10-11 18:44-18:49,  a local port after its restart) [tested]
`lightwan_generate("t2v", ..., seed=777)` with decode standard and fast, this branch: both ok, 81 f 1280x720;
difference; PSNR between the two saved mp4s 37.1 dB (each went through its own h264 encode, so this is lower than the
45 dB of the raw decodes above). Live rows (par_lightvae_live): 18/18 ok on  a local port.

## What it buys in the studio [inference from the numbers]
A Wan render is 20-70 s of sampling plus the model loads; the decode is a few seconds of that. The chip saves about 2 s
(fast) or 4 s (preview) per 81-frame 720p clip, three times that on an SVI chain, and ~2 GiB of decode VRAM. Pick it for
throughput on many takes, not to rescue one slow job.

## When the port has not loaded the pack
The pack loads at a ComfyUI restart. Until the port ( a local port for Wan / SVI / preview,  a local port for LightWan) has restarted,
the card's notes ("fast decode needs the LightVAE pack, which  a local port has not loaded yet ... rendered with the standard
decode"). Standard is the higher-quality option, so the fallback never gives a worse clip and a job never fails over a
speed setting.

## Licence
LightVAE weights: Apache-2.0 per the HF card (lightx2v/LightVAE); the GitHub repo ModelTC/LightVAE ships no LICENSE file
(2026-10-11). The box pack is a local port (torch only).

## Sources
- [documented] https://huggingface.co/lightx2v/LightVAE (card: Pro = original decoder depth with temporal low-rank
  convs, Lite = additional pruning; Wan uses its original encoder + a LightVAE decoder)
