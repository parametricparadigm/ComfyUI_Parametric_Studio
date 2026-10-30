# Sound for silent clips (ControlFoley)

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


## Purpose / when to use it
- Sound effects and ambience for a silent clip (Wan clips are silent), muxed in as the clip's only audio track.
- `v2a`: from the pictures alone. `tv2a`: the pictures plus a description of the sounds you want.
- Not for speech or music beds (use H3 for dialogue, Music for songs).

## Step-by-step in the studio UI
1. Video tab → "ControlFoley · Add sound to a video".
2. Drop the clip in `source_video` (up to 30 s; tested on 5 s).
3. Mode chip: `v2a` (prompt optional, ignored) or `tv2a` (prompt required: name the sounds, e.g. "footsteps on a wet
   stone quay, a raincoat rustling, water lapping, distant gulls"). Your words go as typed (never the enhancer's rewrite).
4. Generate. The  a local port sidecar must be up (see below).

## The sidecar
- The node pack lives only in `a local folder` (with the two
  ComfyUI patches of 2026-10-11). It is not in the live ports, and the studio never copies it there.
- Default: the studio uses  a local port only when it is already up (the author started it, or the late-sweep lane is running)
  and refuses otherwise with the command:
  and afterwards `systemctl --user stop comfyui-sidecar-8192-np`. A sidecar the studio did not start is used, /freed
  after the job, and left running.
- `COMFY_STUDIO_SIDECAR_AUTOSTART=1` on the studio server lets each foley job start that unit (exactly the lane's
  command), wait for `/system_stats` (up to 10 min), run, and stop it again, also on errors. It never starts while
  `night-phases` is active or over a unit someone else started. **author decision pending**: this is a server start/stop.

## Optimal settings (pinned in the graph)
| Setting | Value | Source |
|---|---|---|
| Model | ControlFoley `large_44k`, bf16, low_vram **off** (every video mode needs CLAP + MusicGen) | [tested] cf_* rows; [documented] KB plan |
| Sampling | 25 steps, guidance 4.5, seed 42 | [tested]; [documented] node defaults |
| Length | the clip's own length, 0.7-30 s | [documented] node `MAX_GENERATION_DURATION` |
| Output | 44.1 kHz wav + mux (replace) into the mp4 | [tested] |

## Guards and gates
- The result is a video: the output guard checks its frames like any studio video. The text guard reads the prompt.

## Time and VRAM
- 50 s for the first clip (includes the model load), 4-6 s per clip warm;  a local port port peak 13.7 GiB (budget 14 GiB +
  floor; 20 GiB for clips longer than the tested 5 s, an estimate). Starting the sidecar adds 1-2 min.

## Licence
- ControlFoley weights **CC-BY-NC-4.0** (non-commercial); MusicGen-style and MERT weights CC-BY-NC-4.0; node code

## Evidence
- `a local folder`; `a local folder`
  (4/4 success 2026-10-11 after the two patches; earlier rows failed on BigVGAN `resume_download`).
- KB `PRISM_CONTROLFOLEY_PLAN_2026-10-10.md` (modes, defaults, licences, the sidecar route); `a local folder` (the start/stop this code mirrors).
- Upstream: https://huggingface.co/YJX-Xiaomi/ControlFoley, https://github.com/YJX-Research/comfyui-controlfoley-official.
