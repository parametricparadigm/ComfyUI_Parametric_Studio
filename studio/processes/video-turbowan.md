# TurboWan 720p

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


## When to use it
A 720p (720x1280), 81-frame clip from a still at **~28 GB** of VRAM, where the box's Wan 2.2 stack needs 65-70 GB at
720p. Time is similar to that stack at 720p (85-90 s vs 68-125 s). The face stayed consistent through a laugh and a turn,
with a little less motion blur than the box stack at 720p; it moves a bit less (motion 6.4 vs 8.8-9.0).

## In the studio
1. Video tab → "TurboWan 2.2 · Image → video 720p".
2. Drop the start still in `image` (centre-cropped to the aspect).
3. Prompt: a **long English prompt** (the README: "only trained on long English prompts"): who and what they wear, the
   setting, the motion beat by beat, the camera, the light. The tested prompts were 60-80 words. ✨ enhance helps (it
   reads the Wan guides); a prompt under 25 words gets a note on the result.
4. Aspect: auto (the still's orientation), `9:16` (tested), `16:9` (the node's own 720p preset, never rendered here).

## The sidecar
- The node pack lives only in `a local folder`, branch
  `ComfyUI-local-patches`: (earlier commit) (load the converted .safetensors) and **(earlier commit)** (rcm_sampler feeds the net bf16, as
  upstream's tensor_kwargs; fp32 init noise hit "mat1 and mat2 must have the same dtype"). The live ports carry the
  unpatched pack; nothing copies the sidecar pack there.
- Same start / stop as ControlFoley (`foley_tools.Sidecar`): with `COMFY_STUDIO_SIDECAR_AUTOSTART=1` (on in the live
  launch scripts) a job starts the lane's unit `comfyui-sidecar-8192-np`, waits for `/system_stats`, runs and stops it
  again; a sidecar already up is used and left running. One sidecar job at a time (shared lock with ControlFoley).

## Settings (pinned in the graph)
| Setting | Value | Source |
|---|---|---|
| Models | TurboWan2.2-I2V-A14B-{high,low}-720P-quant (converted int8 safetensors), attention `sla`, top-k 0.10, offload comfy_native | [tested] ut_wan_tw010_*; [documented] README default top-k 0.1 ("0.15 for better quality": looked the same here and ran slower) |
| Sampler | TurboDiffusionI2VSampler 81 frames, 4 steps, `720p`, boundary 0.9, sigma_max 200, SDE, seed 4242 | [tested]; [documented] README I2V defaults |
| VAE | `TurboWanVAELoader wan/wan_2.1_vae.safetensors` (the core VAELoader's VAE lacks spatial_compression_factor) | [tested] |
| Output | CreateVideo 16 fps | [tested] |

## Time and VRAM
85-90 s warm per clip, ~200 s with the cold load;  a local port port peak 27.2 GiB (28 GiB budgeted + 4 GiB headroom). Starting
the sidecar adds 1-2 min when it was down.

## Guards
The text guard reads the prompt; the output guard checks the clip's frames like every studio video.

## No decode chip
TurboWan's sampler decodes inside its own node with TurboDiffusion's VAE wrapper (there is no core VAELoader to swap), so the LightVAE decode chip of the other Wan entries is not offered here ([video-wan-decode.md](video-wan-decode.md)).

## Licence
Apache-2.0 (thu-ml/TurboDiffusion; Wan 2.2 weights Apache-2.0).

## Evidence
- `a local folder` rows `ut_wan_tw010_*`; results
  `a local folder,4}.jsonl`; sheets `wan_*.jpg` in
  `a local folder`.
- https://github.com/thu-ml/TurboDiffusion
