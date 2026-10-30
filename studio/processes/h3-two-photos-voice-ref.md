# H3 with a second photo and a voice

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


author request 2026-10-20: "a voice adding option to my h3 video options", "two reference photos used together", "slot 2 available to all h3 models", and a raspy-smoker voice that never came out.
Spec: `the author's notes` (sections 4, 5, 8, 9). Plan: `the author's notes`.

## What changed

| Where | What |
|---|---|
| Prompt | A job with a second photo takes the Ref2VA reference prompt (`media_tools.anchor_prompt`) on any base; `<Picture 2>` is described by the role. Without a role the old meaning stays: a headshot of the bound character, or "the person shown in <Picture 1>" when no character is bound. |
| Voice text | A voice description typed with no line to say is never sent (pp writes the voice only into a spoken line). The composer now says so, and the job card carries `voice_note`. |
| Voice tab picker | No more silent default to the first saved voice; "Pick a voice..." is the empty choice, the picked voice's name is shown, and a failed save stays on screen. |

## Proof levels (nothing here is "verified")

- `h3:voice_ref`: wired and fake-tested only; pp's builder is marked untested on this box. Needs one real clip with a reference the author supplies (their own voice, or one they have permission to use).
- Voice text note and picker change: tested (Python and `node --test`).

## What was learned first (do not redo)

- The Voice tab's clones all sounded the same because the author's own clip was never saved and the picker auto-selected the first saved donor voice (`(earlier commit)`). Why their save failed is still unknown: it needs the message the form shows.

## author proofs still owed

2. One `h3:voice_ref` clip with a reference clip the author supplies (about 2 GPU minutes on standard H3).
3. The studio restart (ask first, check `GET /api/admin/restart` is empty) before any of it is visible.
