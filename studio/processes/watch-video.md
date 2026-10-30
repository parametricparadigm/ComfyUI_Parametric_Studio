# Watch a video, write prompts

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


## Purpose / when to use it
Show the studio a video and get H3 prompts that remake it: one prompt per scene segment, plus one single-clip prompt (up to 10 s) that stands for the whole video. You can edit a prompt, copy it, stage a test render, or save it to **my prompts** in the prompt library. Use Recreate instead when you want the studio to remake the video with your character; this page only writes the prompts.

## What it does (one CPU-lane job, `engine = vid2prompt`)
2. **Scenes**: time range, people, shot size from the face boxes, the camera move, 1 to 3 keyframes. A segment is at most 10 s (H3's longest clip chip).
3. **Transcript**: the Clip Studio Whisper helper (GPU when `gpu_device` says there is room, CPU otherwise) gives the spoken lines with times.
4. **Look at it**: Qwen3-VL-8B in a short-lived worker, only when there is room for it and the 4 GB floor holds; it never evicts anything. If it cannot run, the prompts are written from the measured facts (shot size, people, brightness, colours), the camera reading and the transcript, and the notes say "no picture description".

Faces and names are never described; people are `<Subject n>` slots. Nothing is posted, sent or rendered.

## Buttons and what they do
| Button | Effect |
|---|---|
| Watch | Starts the job; progress chips: Get the video, Scenes, Transcript, Look at it, Write the prompts |
| Rewrite | Runs only the writer step again with a new engine, profile or note (the scene notes are kept) |
| Copy | Copies the prompt text |
| Stage a test render | Opens the Composer filled in. **Nothing starts**; you press Generate yourself |
| Save to my prompts | Writes the **user collection** (`<library dir>/user/mine.jsonl`). The source URL is kept only if you tick it |

## Saved prompts ("my prompts")
- Kept apart from the community library: the community import, rebuild or reset never touches `user/`.
- In library search, facets and `retrieve` a user prompt is marked `mine` and ranks above every community prompt.

## Limits and pitfalls
- You always get the segment prompts plus a one-clip prompt. For a video longer than 10 s the one-clip prompt is a stand-in of at most 10 s built from the three longest scenes, and it uses the first spoken line that fits the clip; it does not cover the whole video.
- The writer may be loading: the step waits 20 s and retries once, then falls back to a draft from the scene notes (the card says so).
- A spoken line that is not word for word in the prompt is flagged on the card; fix it before using the prompt.
- Cost line under the results: writer calls and token estimate, vision backend and time, Whisper time, wall time.

## Evidence
`tests/studio/test_vid2prompt.py`, `test_vid2prompt_scenes.py`, `test_vid2prompt_vision.py`, `test_vid2prompt_write.py`, `test_prompt_library_user.py` (fake models, synthetic clips; hermetic), `tests/chatbox/js/watch_helpers.test.mjs`. **Not done**: a real run on a real clip, the Qwen3-VL worker on the GPU, a judged recreation.
