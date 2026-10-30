# Prompt enhancer and model rules

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


## Purpose / when to use it
Turn a rough idea into the prompt a specific model responds to: its prompt style (prose, tags, JSON, H3 sections), its
trigger words and length. Use it for text-to-image and generation prompts. Turn it off when you already have a proven
prompt, when VRAM is tight, or for instruction-type inputs (they are sent raw anyway).

## Step-by-step in the studio UI
1. Pick the generator, type the idea.
2. Optional: press **✨ Preview**. The panel shows "Yours" and the rewrite (model used, why, any H3 lint note). Edit the
   rewrite in place, then **Use this** (it fills the prompt box and unticks ✨ enhance so it is not rewritten again).
3. Or leave **✨ enhance** ticked (default) and press Generate: the job rewrites at render time (card status
   "✨ Writing the prompt"). The card's "prompt" details show the final text; "prompt (not enhanced)" means it fell back.
4. Untick ✨ enhance to send your words exactly.

## Optimal settings
| Setting | Value | Source |
|---|---|---|
| KB guides | per family: H3 (MINIMAX_H3_PROMPTING, PROMPT_LIBRARY, MEDIA_CAPABILITIES), Wan (WAN22_PROMPTING), Qwen (`qwen21_prompting/`), image/flux/sdxl/3d (MEDIA_CAPABILITIES), music (MINIMAX_MUSIC3); 12,000 chars shared | `prompt_sources.GUIDES` |
| Realism direction (chip ON by default for `qwen21:t2i`, `img:krea2`, `h3:cinematic`, `h3:ugc`; OFF elsewhere; 2026-10-17) | with the `Realism` chip on (image: `qwen21:t2i`, `img:krea2`; video: `h3:cinematic`, `h3:ugc`) the enhancer gets one more fenced block after the persona stance: `REALISM DIRECTION` = `realism.direction_text(medium)`, capped 1500 chars, "the subject, action, named people, model rules, take direction, format style, persona stance, JSON format and content rules win over it". Absent = the system prompt is byte-identical. Not applied when the prompt is not enhanced, or when the prompt names a stylised look (anime, painting, 3D render ...: `realism.stylised_prompt`); the card says so | `enhance.REALISM`, `enhance_job`, `docs/processes/realism-4k.md` |
| Model rules | the model page's `model-rules` block (or `<name>.rules.json`), read fresh every call, max 1,800 chars to the enhancer | `model_rules.read_rules`, `enhancer_context` |
| prompt skill | the former dfserve prompt skill of that model, snapshotted in `config/df_prompt_skills.json` (flux_local, flux_svdquant, flux_fill, minimax_music = music3) when dfserve was retired 2026-10-12 | `enhance._skill_for` |

Rules pages the studio reads (link, do not copy; built by `a local folder`, hand edits go to `.md.new`
or a `.rules.json` sidecar):

| Entry | Rules page |
|---|---|
| `img:krea2` | `a local folder` |
| `img:poster` | `a local folder` |
| `img:anime` | `a local folder` |
| `img:tryon`, `img:product` | `a local folder` |
| `img:style`, `character:klein9b` | `a local folder` |
| `qwen21:*`, `character:qwen21` | `a local folder` |
| `redux:*` | `a local folder` |
| `wan:i2v` / `wan:t2v` | `a local folder,T2V}-A14B-HIGH_fp8_e4m3fn_scaled_KJ.md` |
| `h3:*`, `h3p:handheld`, `edit:char_swap`, `edit:remove_person` | `a local folder` |
| `h3p:*`, `edit:depth_restyle` | `a local folder` |
| `ckpt:<id>` | the fine-tune's own page beside its file (`diffusion_models/sdxl/*.md`, `diffusion_models/flux/*.md`, `checkpoints/DreamShaper_8_pruned.md`) |
| upscale, 3D | none |

## Prompting rules
- Never enhanced (sent raw): video edits, upscales, character sheets, Redux variation, try-on/product/style instructions,
  Qwen outfit/fusion task edits, and the raw-prompt H3 pipelines (multishot, long video). A rewrite of an `h3p:*` prompt that
  comes back as a finished H3 prompt is dropped for your words.
- H3 modes: the rewrite is built into a pp.h3prompts prompt and linted; lint warnings show in the panel.
- The enhancer keeps your subject and named people; it only restructures (camera, light, motion, sound).
- Rules blocks are data: only whitelisted keys (steps, cfg, guidance, clip_skip, shift, prefix, triggers, negative, style)

## Guards and gates
- Text guard on your input and again on the rewrite ("refused (the rewritten prompt)"). See `guards-text-and-output.md`.

## Time and VRAM
- Warm: a chat completion with a 180 s timeout; H3 build bounded to 60 s. Not measured per job.
- **VRAM cost:** at render time `enhance_job` calls `ensure_ready` on the chain, which can cold-start muse-glimmer (~20.9 GB)
  still start  a local port. With VRAM tight, untick ✨ enhance or use ✨ Preview while the LLM is already up.

## Known pitfalls / failure modes
- If no enhancer answers, the job renders your prompt unchanged and the card says "not enhanced" with the reason.
- Retry/Variations reuse the shown enhanced prompt (no new rewrite).
- Mellum (llama-swap  a local port) is paused until the tests end; it is not in this chain, but a reload of it once killed a GPU
- A page edit takes effect on the next job without a restart; a broken page simply means no rules (tested values apply).

## Evidence
  fallback … can still start  a local port on demand") and 01:50 (MoE on-demand).
- `a local folder` (page builder and layout).
- Tests: `tests/studio/test_enhance.py`, `tests/studio/test_model_rules.py`.
