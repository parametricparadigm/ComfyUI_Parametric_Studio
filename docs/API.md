# The studio's API

Every graph the studio runs is plain ComfyUI API format, in `workflows/` and over HTTP. Start the studio and these work on `http://localhost:8310`.

| Call | What it does |
|---|---|
| `GET /api/graphs` | Every goal, its model and its workflow file |
| `GET /api/graphs/{goal}` | The API-format graph, and the `${names}` the studio fills in |
| `POST /api/graph` | The filled graph for your prompt and options, without running it |
| `POST /api/generate` | Runs it. Returns a job id |
| `GET /api/jobs/{id}` | Status and output files |
| `POST /api/upload` | Upload an image, video or audio input |
| `GET /api/goals` | Goals with their options and defaults |

```bash
curl -s localhost:8310/api/graphs/image
curl -s -X POST localhost:8310/api/generate -H 'Content-Type: application/json' \
  -d '{"goal":"image","prompt":"a lighthouse at dawn","options":{"aspect":"16:9","mode":"fast"}}'
```

Other agents and apps can use the same calls. `POST /api/graph` output also runs unchanged on your own ComfyUI, or through Comfy's official SDK:

```python
from comfy_sdk import Comfy          # pip install comfy-sdk
import requests
graph = requests.post("http://localhost:8310/api/graph", json={"goal": "image", "prompt": "a lighthouse at dawn"}).json()["graph"]
client = Comfy()                     # Comfy Cloud with COMFY_API_KEY, or your server with COMFY_BASE_URL
job = client.run(client.workflows.from_json(graph))
for out in job.outputs: out.to_file(out.name)
```

To run the whole studio through the SDK, start it with `STUDIO_BACKEND=sdk`.
