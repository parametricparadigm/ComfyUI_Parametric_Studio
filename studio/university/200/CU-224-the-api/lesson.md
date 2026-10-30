# CU-224 - The API: queue, watch, fetch

**Objective.** Queue a prompt from a script, follow it to completion, and download the result. Taught by Captain Graph.

## The idea

The web page is one client among others. Anything it does goes over HTTP and a websocket.

## The mechanism

From `server.py` and `execution.py` at v0.43.0:

| Call | What it does |
|---|---|
| `POST /prompt` | Validates and queues. 200 gives `prompt_id`, `number`, `node_errors`. 400 gives `error` and `node_errors` |
| `GET /ws?clientId=...` | Events for that client |
| `GET /history/{prompt_id}` | Outputs and status when finished |
| `GET /view?filename=&subfolder=&type=` | Fetches a file |
| `GET /queue`, `POST /queue` | Reads or edits the queue |
| `POST /interrupt` | Stops the running job |
| `POST /free` | Unloads models or frees memory |
| `GET /object_info` | Every node's inputs and outputs |
| `POST /upload/image` | Puts an input file on the server |
| `GET /system_stats` | Versions and memory |

The body of `POST /prompt` is `{"prompt": <API format graph>, "client_id": "..."}` (CU-109). `prompt_id` is optional and must be a canonical UUID if you send it. Note that validation runs inside this call, so a bad graph fails right there, without being queued.

The event order for a job:

```
execution_start → execution_cached (the list of cached nodes)
→ for each node: executing, progress..., executed (output nodes)
→ execution_success → executing with node = null
```

On failure you get `execution_error` or `execution_interrupted`. The official example `script_examples/websockets_api_example.py` treats `executing` with a null node and its own `prompt_id` as the end of the job.

## Lab

This runs against an in-memory stub that follows the code above. It has no network and it never touches a real server, so it shows the protocol, not the real server's timing.

```text
POST /prompt, unknown node -> 400 missing_node_type
POST /prompt, no output    -> 400 prompt_no_outputs
POST /prompt, good         -> 200 {'number': 0, 'node_errors': {}}
```

```text
  execution_start {}
  execution_cached {'nodes': []}
  executing {'node': '3'}
  executing {'node': None}
```

Those four lines are from the full list the lab prints, with the sampler's progress and the save node's `executed` event in between.

```text
GET /view?filename=app_00001_.png&subfolder=&type=output -> b'\x89PNG'
same prompt again: ['execution_start', 'execution_cached', 'executed', 'execution_success', 'executing']  cached: ['3', '9']
```

The second line shows a trap avoided. Queue the same prompt again and no node function runs, yet `emit_cached_output` still sends `executed` for the output node, and history still lists the file. So do not wait for a progress event, because a cached job has none.

## Common mistakes

- Do not bind ComfyUI to a public address without protection. The default is 127.0.0.1, and `--listen` changes it.
- Read `node_errors` even on a 200: a partly valid prompt still runs.
- Use a fresh `client_id` per client, since events are routed by it.

## Sources

- [ComfyUI docs: ComfyUI Server Routes (HTTP and WebSocket API)](https://docs.comfy.org/development/comfyui-server/comms_routes)
- [ComfyUI v0.43.0, server.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/server.py)
- [ComfyUI v0.43.0, execution.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/execution.py)
- [ComfyUI v0.43.0, comfy_execution/asset_enrichment.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_execution/asset_enrichment.py)
- [ComfyUI v0.43.0, script_examples/websockets_api_example.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/script_examples/websockets_api_example.py)
