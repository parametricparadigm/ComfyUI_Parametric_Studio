# Job queue and VRAM checks

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


## Purpose / when to use it
Read this when a card sits on "Waiting for GPU", fails with "N GiB free", or a render seems slow to start. The box has one

## Step-by-step in the studio UI
1. Generate as usual. The studio runs **one job at a time** (FIFO); a second Generate queues behind the first.
2. "Waiting for GPU" shows the reason (which lock or port is busy, how many GiB are free).
3. If a job failed on VRAM, press **Queue when free**: it re-queues every 30 s for up to 30 min.
4. To make room yourself: check the Inspector (LLM roster with Load/unload), stop idle LLMs, or wait for a test lane to end.

## Optimal settings
| Setting | Value | Source |
|---|---|---|
| Wait loop | 30 s interval, 30 min budget | `JobStore(wait_s=30.0, wait_max_s=1800.0)` |
| Peaks (code constants) | Krea 24, Ideogram 40, HiDream 22, Klein try-on 24 / product 22 / style 36, Qwen 2.1 36, Wan 64 (measured 63.5-66.2 GB), H3 modes 38-68, h3p 35-48, char swap 50, remover 65, depth 48, VOID 23, RIFE 2, upscale 3/5 GiB | `image_best_tools.KINDS`, `image_qwen21_tools.PEAK_GIB`, `wan_tools.PEAK_GIB`, `h3_pipelines`, LOCAL_MOE_REFERENCE §15 |
| Fine-tunes | per model `peak_gb` (SDXL ~10, SD1.5 ~5, FLUX.1 ~34 family default) | `finetunes.FAMILY_DEFAULTS`, capability_run models.json |

## Prompting rules
- None. Prompt length does not change VRAM; resolution, frames and the base model do.

## Guards and gates
Port picker (an earlier branch, [port-picker.md](port-picker.md)): image jobs (portable engines) run on per-port
lanes with gen4.lock SHARED + a per-port lock and a VRAM admission that counts the other lanes' vram-mcp reservations;
everything below still applies to every other job, which runs exclusive (gen4.lock EXCLUSIVE once every lane is idle).

In order, every studio render:
1. **gen4 flock** (`/tmp/comfyui-eval-$UID/gen4.lock`) and the **cross-session GPU turn** (`a local folder`), both
   taken non-blocking. Held = VramBusy naming the holder (wait or fail).
2. **Shared preflight:** any running or pending job on  a local port/ a local port/ a local port = busy (refuse). Then free VRAM vs peak + 4 GiB;
   if short, only the target port's own idle cache is `/free`d and VRAM re-read. Nothing else is evicted: LLMs and
   other sessions are the operator's call.
3. (dfserve jobs and their own "needs_vram" path are gone: dfserve was retired 2026-10-12; its former entries render on
   ComfyUI through the shared preflight above.)
While the studio holds the turn, chat-started GPU tools refuse.

## Time and VRAM
- Cold loads: the first job after a base change includes the load (Wan 130-190 s cold vs ~21-36 s warm; Krea 40 s cold vs 3 s).
- ComfyUI runs `--highvram`: models stay resident; the studio tools `/free` the port after a job when it is idle (Wan
  keeps  a local port warm only for the creative take that follows).
- LLMs: the MoE ( a local port, ~46 GB) is on-demand since 2026-10-11 (`moe up` refuses under 50 GB free unless `--force`; the
  chatbox sweeper stops it after 20 min idle). The ✨ enhancer can wake muse-glimmer (~21 GB) or the MoE (see
  `prompt-enhancer-and-model-rules.md`). Ollama Gemma 12B (~10 GB) is the content-build LLM and unloads when idle.
- `vram-floor-watch.service` warns on the desktop under 6 GB free and on the phone under 4 GB.

## Known pitfalls / failure modes
- A night test lane on any ComfyUI port blocks every studio job (by design: a busy port can look idle in VRAM while it
  encodes on the CPU).
- Known gaps (accepted): legacy chat tools `render_h3_shot/video/duo_*` and `df_generate` skip the busy check; a chat GPU
  tool's preflight→submit window can collide with a studio job (LOCAL_MOE_REFERENCE §15 "Known gaps").
- After the H3 person remover,  a local port once kept ~23.9 GiB that `/free` did not release; a unit restart clears it (ask first).
- A job left mid-render by a server restart shows "Interrupted": press Retry.
- Restart the studio itself with **⟳ Restart** in the top bar (next to "＋ New chat"). It asks first and says how many
  studio jobs are running or queued (a restart interrupts them; Retry them afterwards), shows "Restarting studio…" and
  reloads the page when the server answers again, usually in 5-20 s. Behind it: `POST /api/admin/restart` (refuses
  while jobs run unless `{"force": true}`) and `scripts/chatbox/restart.sh`, which waits for the old pid and the port,
  runs `launch.sh` without a browser window and logs the outcome to `scripts/chatbox/chatbox.log`.

## Evidence
  (Mellum reload killed a test row: why stray LLM loads matter).
- Tests: `tests/studio/test_jobs.py`, `tests/studio/test_gputurn.py`.
