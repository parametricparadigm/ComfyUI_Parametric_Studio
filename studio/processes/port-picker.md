# Port picker

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


## Purpose / when to use it
- Run two image jobs at the same time: pin one to another ComfyUI port. The studio used to render one job at a time,
  always on  a local port.
- Free VRAM when you are done, without waiting for the 15-minute idle unload.

## Step-by-step in the studio UI
1. In the composer, next to the other job chips, open **Port**. Each option shows the port's state (idle / busy), the
   VRAM its ComfyUI holds, and the idle-unload countdown in the tooltip.
2. Leave it on **Auto** for today's behaviour: auto jobs run one after another on one port. That is  a local port first, or
   another idle port that has the model's nodes when  a local port is busy with work from outside the studio.
3. Pick a port to pin the job there. A port that lacks a node the model needs is greyed out with the missing node
   names. Generators that keep their own port offer only Auto: Wan, LTX, H3, upscale, music, voice, TTS, 3D (FLUX.1 Fill and the crop outpaint became portable when dfserve was
   retired, 2026-10-12)
   and crops.
4. Press **⚡** for the VRAM panel:
   - each port's state, the GB it holds, and an **Unload** button. The button is disabled with the reason when the
     port is busy, rendering a studio job, claimed by another session, or down;
   - **Unload all idle**, which skips busy and claimed ports and lists them;
   - the loaded **LLMs**: llama-swap and Ollama models each have an Unload button, disabled while a studio LLM call
     (the enhancer or the chat judge) is running. The  a local port MoE and any vLLM or llama.cpp service are listed
     read-only, because they need a service stop.
5. Inside ComfyUI, the **Studio** sidebar tab has **Unload this port**. It frees that ComfyUI's models only while its
   queue is empty, and reports the GB freed.

## Optimal settings
| Setting | Value | Source |
|---|---|---|
| Port (default) | Auto ( a local port first, one at a time) | `ports.AUTO_ORDER`, `PortPlanner.lane` |
| Portable engines | qwen21, img (Krea 2, Ideogram, HiDream, Klein, Z-Image, Boogu), imgedit, redux, ckpt, character, looks | `ports.PORTABLE_ENGINES` |
| Free VRAM a lane job needs | peak + 4 GiB, after other studio reservations | `video_edit_tools._lane_admit`, `ports.fit` |
| Reservation TTL | 15 min, renewed every 60 s while the job runs; dropped when the job ends, on shutdown, and by the dead-pid sweep | `ports.RESERVATION_TTL_S`, `ports.HEARTBEAT_S` |
| Content LLMs give way to renders | ON: a render short of VRAM unloads idle llama-swap / Ollama models first (no content-LLM call in flight, no busy slot, not claimed); never the  a local port MoE, vLLM or a llama.cpp unit | `studio/llm_room.py`, `COMFY_STUDIO_RECLAIM_LLM=off` |
| Idle auto-unload | 15 min (comfy-idle-unload.service, unchanged) | `COMFY_IDLE_MIN=15` |
| Turn the lanes off | `COMFY_STUDIO_PORT_LANES=0`: one worker, gen4.lock exclusive (pre-port-picker behaviour) | `server._studio` |

## Guards and gates (the lock contract)
- **gen4.lock** (`/tmp/comfyui-eval-$UID/gen4.lock`) means "I'm using the GPU". Every external user takes it
  **exclusive** (audited 2026-10-12):
  - `LOCK_EX`: capability_run.py (the late sweeps), int8_bypass_check.py, pipeline/lp/gate.py,
    ComfyUI/tools/skill_smoke.py.
- A studio job on a port lane takes **gen4.lock shared** plus **studio-port-<P>.lock exclusive**, neither waited on.
  Studio jobs on different ports therefore run together. An external exclusive holder blocks all of them, and while
  any of them runs, an external `flock -x` waits.
- **Writer preference:** a studio job does not start while an external process is blocked waiting for gen4.lock
  exclusive (read from `/proc/locks`), so overlapping studio jobs cannot starve a night run. A non-blocking poller
  (capability_run's `LOCK_NB` loop) is not visible there. It gets in at the next gap, as it did before.
- **Exclusive studio jobs:** every non-portable engine (FireRed TTS, upscale:image, H3, Wan and the rest). The worker
  waits until every lane is idle, then takes gen4.lock **exclusive**, as before.
- **The GPU turn** (`a local folder`) is shared by the lanes. The first job takes it, the last releases it,
  and chat-started GPU tools still refuse while any studio job runs.
- **VRAM admission** (per lane job, before submitting):
  - available = nvidia-smi free + what the job's own port holds (its own cache, unless another claim names the
    port) − Σ(other studio reservations − what their port already uses), and at most card total − other sessions'
    reservations. "Uses" is the larger of the port's torch figure and its process's nvidia-smi figure
    (`ports.used_gib`), so a neighbour that is mid-load is not counted twice;
  - it must cover peak + 4 GiB. If not, the job **waits** (it never fails for room another lane holds, and nothing
    is evicted);
  - the reclaims: the chosen port's own idle cache (only when it was not already counted as room, and only if no
    other vram-mcp claim names that port), then the opt-in idle ports (never one holding < 1 GiB), then idle content
    Any other engine refused short of VRAM (H3, voice, dfserve, music, looks) gets the same LLM unload and one
    immediate retry (JobStore make_room). After the enhancer answers, its model is unloaded at once when the job's
    render will not fit beside it; and a content LLM that does not fit first frees idle, unclaimed ComfyUI ports (the
    reclaim's rules; never a busy port, never a lane's) before it falls back to the 12B or the raw prompt
    (`studio/llm_room.py`);
  - a passing job writes a vram-mcp reservation `studio <entry> <job> on :<port>` to `a local folder`.
    It uses the MCP's record format and its `.lock`, and comfy-idle-unload then leaves the port alone too.
  - **Stale reservations** (fixed 2026-10-12): a heartbeat renews live ones; `use()`, atexit and the SIGTERM/SIGINT
    handler release them; at startup and at every lane preflight `ports.sweep` deletes studio-owned records whose pid
    is dead or reused (never another author's), and `read_claims` hides them meanwhile. comfy-idle-unload ignores any
    claim whose pid is dead.
  - A job that fails only because the GPU had no room (or a VRAM wait that timed out) is marked `retry_hint: "gpu"`
    and its card says Retry / Queue when free.
- **Busy ports:** a port with work from outside the studio still blocks a lane job (as before). Another studio lane does
  not.
- **Nodes:** a graph sent to a port other than  a local port is checked against that port's `/object_info` and refused before
  queueing if a node is missing. Files staged into ComfyUI/input are hardlinked into the  a local port sidecar's own input
  folder.
- **Unloads** are POSTs behind the chatbox's cross-site and token guard. Each one is logged with time, who, what and
  GB freed to `<studio jobs root>/unload_log.jsonl`, and as a `[studio]` note in the session when one is open. The
  studio never stops or restarts a service.

## Opt-in idle-port reclaim (author 2026-10-12: "yeah switch it"; on for  a local port)
- **When it acts:** only inside a studio job, and only when the job is still short of VRAM after its own port's
  reclaim.
- **Candidates:** the ports in **⚡ → Auto-free idle ports for studio jobs**. The default is ` a local port` after 25 min
  idle; the studio ports default to 10 min. The env default is `COMFY_STUDIO_RECLAIM_PORTS=a local port`, and the panel saves
  to `a local folder`. The job's own port and any port a studio lane is rendering on are
  never candidates.
- **Order:** largest resident first. It stops as soon as the job fits.
- **When it frees a port:** it sends `POST /free {"unload_models": true, "free_memory": true}` only if all of these
  hold:
  - the `/queue` is empty, both at selection and again right before the `/free`;
  - the port has been idle for at least N minutes, measured from the newest `/history?max_items=1` entry;
  - no unexpired vram-mcp claim covers the port. A claim covers it when its pid is that port's ComfyUI process (its
    `--port`), or when its purpose, model or author names `:<port>`;
  - no other process holds gen4.lock exclusive (a non-blocking probe).
- **What it never does:** stop or restart a unit, or touch llama.cpp, vLLM or Ollama.
- **Record:** each eviction is logged to `unload_log.jsonl` and added to the job's notes, for example
  `freed idle  a local port (63 GiB, idle 27 min, no claim)`. If the job still does not fit, it waits.
- Code: `earlier_studio/studio/reclaim.py`. Tests: `tests/studio/test_reclaim.py`.

## Visibility in ComfyUI
All four ports write to one output folder (`a local folder`, the launcher's `--output-directory`). The
studio's cleared results are hardlinked into `outputs/studio/<tool>/<run>/` (`tools/comfy_visible.py`), and the Studio
sidebar pack is loaded on every port:  a local port- a local port share `ComfyUI/custom_nodes`, and the  a local port sidecar has its own copy.
A pinned job's result therefore shows in every port's Studio tab, and its prompt history is in the port that rendered it.

## Known pitfalls
-  a local port (the sidecar) has about 2,600 node classes against about 7,500 on the others. Most image graphs need a node
  it lacks, so it is usually greyed out.
- Code-built graphs (fine-tunes, Explore looks, Boogu) have no template to check up front. Auto never sends them to
   a local port, and a pin there is checked when the job queues.
- Two lanes that both load a large model may not fit. The second waits, with "only N GiB free after reservations",
  until the first ends.
- The ComfyUI **Unload this port** button checks only the queue (it cannot read the vram-mcp ledger). The studio's
  panel also checks claims.
- The button is JavaScript only. A browser reload of the ComfyUI page picks it up; the sidecar has its own copy of the
  pack, updated on the same branch.

## Evidence
- Tests: `tests/studio/test_port_picker.py` (locks, admission math, nodes, auto choice), `tests/studio/test_unload.py`,
  `tests/chatbox/test_port_routes.py`, `tests/chatbox/js/ports.test.mjs`, `tests/chatbox/js/studio_gallery.test.mjs`.
- Node sets read 2026-10-12:  a local port =  a local port =  a local port = 7,463 classes;  a local port = 2,613.
