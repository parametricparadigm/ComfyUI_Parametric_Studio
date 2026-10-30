# Result search

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


## What it searches
Studio jobs that finished with a file, the song library, and the media under `a local folder` (the folders the Results hub shows, minus its skip list; a hardlink twin counts once; rows of the folder's `*.jsonl` and a `<stem>.txt` caption add words).
Today that is about 21,000 results. Nothing is written outside `a local folder` (`COMFY_RESULTSEARCH_STATE`): `index.sqlite` (the cache), `marks.json`, `saved.json`, `embeddings.sqlite`, `thumbs/`.

## How to use it
1. Open **🔍 Search**. The first visit builds the index in the background (niced, one stat per job file; about 17 s from nothing, about 1 s when little changed) and updates it when it is older than 10 minutes. **Update index** forces it.
2. Type words. `her laughing in the café` finds `coffee shop` too (a short synonym list; the exact word ranks first). `"golden light"` is an exact phrase, `-beach` leaves a word out.
   A filter value matches as a case-insensitive part of the field.
4. If nothing has every word, the page shows the results with most of the words and says so.
5. Each card: a thumbnail (picture, a frame at 1 s for a clip, a waveform for a sound; made on demand, cached, after the output guard has cleared the file), the matched fields as badges (a dashed badge = matched through a similar word), a highlighted snippet, the score line, and the buttons
   **Open**, **More like this** (the result's own best words; with the image index also its look), **Keep / Drop** (kept:yes later), **Edit it / Animate it / Make a GIF** (opens the composer with this result as the source; only for results a studio job made, by job reference, never a client path), **Details**.

## Layer A, how it ranks
BM25F over weighted fields: character 3, tags 2, caption 2, file name 1.5, studio 1.5, model 1.5, prompt 1, final prompt 0.9, notes 0.8, folder 0.6, settings 0.5, session 0.3. Stems (laughing/laughed/laughs, cafe/café/cafes). Synonyms count 0.45 of an exact word.
Every word must match (a synonym can stand in) unless that finds nothing. Failed and interrupted jobs have no file and are not results. The studio has no global keep / drop on a job: search reads a row's `verdict` and adds its own marks.

## Layer B, picture search (optional, author presses a button)
* **Nothing starts by itself.** Searching, opening the page and checking status never run a model. **Build image index** is the only thing that does; **Cancel** stops between chunks and a new build continues from where it stopped (a vector is kept per file; a changed file is embedded again; a file that failed is remembered, not retried every time).
* Model (default SigLIP so400m, local, nothing downloaded; CLIP ViT-L/14 and LAION CLAP for sounds are also wired). A clip is three frames (10 / 50 / 90 %) averaged. The query text is embedded by one short worker run on the CPU and cached by text.
* The worker is `resultsearch_embed_cli.py`: JSON in (`items`, `texts`, `model`, `device`), one `EMBED_RESULT {...}` line out (float16 base64, L2-normalised).
* **Interpreter (author approved RS-1, 2026-10-17): the ComfyUI `the ComfyUI venv` python, READ ONLY** (torch, transformers, sentencepiece are already in it; nothing is ever installed into it or written to it: `python -I`, `PYTHONDONTWRITEBYTECODE=1`, `HF_HUB_OFFLINE=1`, niced, CPU unless you pick the GPU). It is resolved on **every call**, so no restart is needed to change it. Order: `COMFY_RESULTSEARCH_PYTHON`, `"python"` in `a local folder`, `a local folder` if it exists, else the ComfyUI venv.
* GPU: offered only when the card has the model's size + the 4 GiB floor + 1 GiB margin free **after every other vram-mcp claim** (`vram_broker.free_gib` minus the ledger's claims). A GPU build takes a vram-mcp reservation (`ports.reserve`, model size + 1 GiB, renewed by the studio heartbeat) before the worker starts and releases it on every exit path (done, cancelled, error); if the reservation cannot be recorded the build is refused. Nothing builds until the author presses the button. CPU never touches the card (`CUDA_VISIBLE_DEVICES=""`).
* **Hybrid ranking** = weights × (word score, picture score), shown on every card ("words 62% · picture look 38% (mix 50/50)") and adjustable with the slider; weight 0 for the picture means the model is not even asked. A picture score is a z-score of the cosine similarity over the whole index (below z 2 it counts for nothing, z 5 counts full), so it is a relative signal, not a probability.
* **Honest limit: picture search is approximate.** Word search finds what the prompt said, not what the picture shows.

## Safety
* Thumbnails go through the output guard's `serve_open`; a refused file has no thumbnail. The page never serves an original itself: **Open** uses the studio's guarded `/api/studio/file/<job>/<n>`; folder results show their path to copy.
* Tests are hermetic: fake job store, fake outputs tree, fake songs, `FakeEmbedder`, and a real subprocess only for the worker's built-in `fake` model with the test interpreter.

## Queue (nothing below was run)
| # | Item | Exact commands, for when the author approves |
|---|---|---|
| RS-2 | Optional: an isolated venv outside every ComfyUI venv (needs a download, about 2.5 GB) | only if RS-1 is ever withdrawn: `python3 -m venv a local folder && a local folder install --index-url https://download.pytorch.org/whl/cpu torch && a local folder install transformers pillow numpy sentencepiece safetensors protobuf`; it is then picked ahead of the ComfyUI venv. Needs the author's OK (it pips, though not into a ComfyUI venv). |
| RS-3 | First image index | open Search, press **Check setup** (starts the worker once with no pictures), then **Build image index** on CPU (3-6 h in the background, cancel and resume any time) or, when the card has about 6 GB + the 4 GiB floor + 1 GiB margin free, on the GPU (minutes; the build reserves and releases its VRAM itself). |
| RS-4 | Sound index (CLAP) | after RS-3, `POST /api/studio/resultsearch/embed/build {"model": "clap-larger"}` (not in the UI yet). |
| RS-5 | Better model later | fetch Qwen3-VL-Embedding-8B (today's folder `a local folder` is empty), add one entry to `MODELS` and a backend to the worker. |

## Known limits
Captions exist only as `.txt` / `.caption` files next to a result and in jsonl rows; clips' transcripts and the makers' keep / drop are not read. PNGs have no embedded prompt on this box, so a loose picture is found by its folder, file name, row and caption only.
A prompt is a wish: a result can be found by words it does not show. Picture search is untried on real pictures. A query embedding costs one worker start (seconds on CPU). The index reads files the job store recorded; a moved or deleted file shows "gone".
