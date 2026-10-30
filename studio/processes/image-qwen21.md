# Qwen-Image 2.1

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


## Purpose / when to use it
- `qwen21:t2i`: photoreal people/portraits (KB pick for "photoreal portrait", medium-low confidence), correct wide noodles,
  counting and binding. Slower than Krea 2.
- `qwen21:edit`: "say the change" edits of one image ("make it night", "remove the sign"). The identity path of
  character mode (a reference edit keeps the face).
- `qwen21:outfit`: dress the person in image 1 in the outfit of image 2 (a photo of someone wearing it works).
- `qwen21:fusion`: blend a roughly pasted object into the photo (the only working blend on the box; Klein Fusion fails).

## Step-by-step in the studio UI
1. Image tab → pick the Qwen-Image 2.1 row.
2. t2i: Aspect chip (auto = 1:1) + Resolution chip (1 MP default | 2 MP | 4 MP official) + takes 1-4. Edit / outfit / fusion: no aspect chip ("follows input"), takes 1-4.
3. Reference slots: edit = `image`; outfit = `image` (person) + `garment`; fusion = `image` (the photo with the object
   already pasted on it).
4. 🎛 LoRAs (t2i and edit only): up to 3 Qwen 2.1 LoRAs from the library, strength slider defaulted to the library's
   recommendation, "add trigger words" checkbox (`lora-picker.md`).
5. Prompt: t2i/edit are enhanced (✨ on, or ✨ Preview); outfit/fusion prompts go raw and may be empty (the proven
   instruction is used).
6. Generate. A Character chip on t2i reroutes to the edit (identity path).

## Optimal settings
| Setting | Value | Source |
|---|---|---|
| Model / precision (all four) | `qwen-image/qwen_image_2.1_bf16.safetensors`, `weight_dtype default` (bf16) | graphs; dtype A/B: fp8 lost the required cat on S02, **keep bf16** (`images.md` §7) |
| author pick for VRAM | int8 ConvRot (`qwen-image/qwen_image_2.1_int8_convrot.safetensors`, 7.26 GB, on disk) matches bf16 on 4/4 prompts at 25-27 GB | `images.md` §7. **Not wired in the studio** (see pitfalls) |
| t2i / edit steps, CFG, sampler | 40 / 1 / euler simple | `qwen21_t2i.api.json`, `qwen21_edit.api.json`; rules page settings block |
| Portrait speed-up (KB pick) | EasyCache 0.1/0.30 (~0.6x time, invisible) | `images.md` §2 "Photoreal portrait" (T3q). Not in the studio graphs |
| Outfit / fusion stack | task LoRA baked 1.0 (outfit-swap / Fusion_2000), then Comfy-Org's Turbo LoRA (extracted from the base) 1.0 LAST, 8 steps euler on the official sigmas (ManualSigmas), CFG 1 | the author's build notes "Editing (task)" (CONFIRMED, T8 B); graphs |
| Fusion input | pre-scaled to 1.8 MP | `TASKS` comment |
| Edit size | keeps the input size up to 1344 long side; larger inputs re-encoded to ~1024x1024 px area | `EDIT_MAX_SIDE`, `EDIT_RESOLUTION` |
| t2i size | studio ratio, ~1 MP (1:1 1024x1024, 9:16 768x1344 ...): the default | `aspects.IMAGE_SIZES` |
| Resolution chip (t2i only, 2026-10-17) | `Resolution: 1 MP (default) / 2 MP / 4 MP (official)`: 1 MP is the table above, byte-identical (graph, cache key, 36 GiB peak). 4 MP uses the model card's own sizes (1:1 2048x2048, 4:3 2400x1792, 3:4 1792x2400, 3:2 2528x1696, 2:3 1696x2528, 16:9 2752x1536, 9:16 1536x2752; all multiples of 32); 4:5 (1824x2304) and 21:9 (2752x1184, under 4 MP because no side goes past 2752) are snapped to the same 32 grid; 2 MP is computed (1:1 1440x1440, 16:9 1920x1088, 9:16 1088x1920). **Time and VRAM above 1 MP are ESTIMATES, not measured**: about x2.4 / x5.5 the ~10 s of 1 MP and +4 / +10 GiB over its 36 GiB peak (so ~40 / ~46 GiB), shown on the chip labels. The room check is the usual one: the tool refuses (names the holders, "GiB free") rather than queues when peak + the 4 GiB floor does not fit. Default stays 1 MP until the author has judged the A/B sheet | `studio/qwen21_resolution.py`, `tools/image_qwen21_tools.py` `qwen21_generate(resolution=)`, model card https://huggingface.co/Qwen/Qwen-Image-2.1 (fetched 2026-10-17) |
| Realism chip (t2i only; opt-in, OFF by default) | `Realism: off / on`: the enhancer writes with the camera-real rules (one fenced block, the subject and model rules win). Wording only here; the 4K file comes from the Upscale card at x4 with its own Realism chip on. Proof level kb-ab (one-seed A/B + 5-prompt proxy A/B), not a guarantee | `studio/realism.py` preset `image.qwen21`, `docs/processes/realism-4k.md` |
| LoRAs (picker) | baked on the bf16 base after the UNet loader; cap 3 | `_with_loras`; `lora_library.MAX_STACK` |
| Helpful LoRAs (tested) | outpaint-v2 1.0, next_scene 0.8, grainscape/analogcore/lenovo 0.7 (author recipe res_2m/beta/cfg 3.5 only) | `images.md` §3 |
| Default seeds | t2i 2101, edit / tasks 2102 | `T2I_SEED`, `EDIT_SEED` |

## Prompting rules
- Edits are instructions ("change the jacket to red leather"), not scene descriptions.
- Outfit default: "Dress the person in image 1 in the outfit shown in image 2. Keep their face, hair, hands, pose and the
  background exactly the same. Replace everything they wear." Fusion default: "blend the pasted object into the image
  seamlessly" (`TASKS`).
- Rules page (read at call time, and by the enhancer): `a local folder`;

## Guards and gates
- Output guard on every image (`guards-text-and-output.md`).

## Time and VRAM
- t2i/edit: ~10 s per image (MEDIA_CAPABILITIES §5, §9); capability run base 5.8 s at 26 GB (that run loaded fp8).
  bf16 peak ~32-36 GB (QUANT_BEST_OPTIONS "Qwen-Image 2.1"; 34.5 GB seen in the clean-frame step).
- Code peak 36 GiB → needs 40 GiB free (Resolution 2 MP / 4 MP: estimated 40 / 46 GiB peak → 44 / 50 GiB free; not measured). Outfit/fusion: 3.3-5 s, 48-52 GB, code peak 52 GiB → needs 56 GiB free.  a local port.
- After a render  a local port's cache is dropped while idle (bf16 otherwise stays ~33 GB resident).

## Known pitfalls / failure modes
- **author decision not wired:** the author's Qwen 2.1 precision is int8; every studio graph loads the bf16 file. Wiring
  int8 needs a graph change and a test; LoRA-on-int8 is untested (QUANT_BEST_OPTIONS). Until then budget ~36 GiB.
- The rules page's notes line still says "fp8_e4m3fn load (author 2026-10-10)", which the later dtype A/B reversed (fp8
  loses content); the studio graph is bf16. Only the enhancer reads that note.
- A plain edit is 40 steps (T8 turbo was never run without a task LoRA): it is slower than outfit/fusion.
- Fixed seeds: same inputs return the cached file; ✦ Variations for new seeds.
- dfserve's `qwen_image` / `qwen_image_edit` are hidden (weights never downloaded; dfserve itself was retired 2026-10-12).

## Evidence
- dtype A/B rows `a local folder`.
- Commits (earlier commit), (earlier commit), (earlier commit).

## Resolution A/B (prepared 2026-10-17, NOT run)
`scripts/qwen21_res_ab.py`: 5 prompts (face, hands, exact lettering, small faces at a distance, fine landscape detail) x 2 seeds (2101, 4242) x 5 arms
(1 MP, 2 MP, 4 MP, 4 MP + Enhance, 4 MP + Enhance + Realism) = 50 renders, all through the studio's own `/api/studio/generate` for `qwen21:t2i`. Resumable
(`results.jsonl`), refuses unless nvidia-smi shows >= 24 GB free, the queues of  a local port/ a local port/ a local port are empty and the arm's peak leaves >= 4 GB (the 4 MP arms
therefore need ~50 GiB free). Cost: ~33 GPU minutes of rendering (estimated: 1 MP ~10 s measured, 2 MP ~24 s, 4 MP ~55 s each), ~7 minutes of prompt
writing on the enhanced arms, ~40 minutes wall; VRAM 36 / 40 / 46 GiB (the last two estimated). Commands: `plan`, `run --approved`, `verdict`, `sheet`
(`sheet.html` + contact sheets), `tally`, `times` (measured seconds against the estimates, to replace them). The chip default flips only after the author
has seen the sheet. Source of the sizes and the 2K claim: the Qwen-Image-2.1 model card and README (fetched 2026-10-17).

## Grainy edits and the seed 4242 rule (2026-10-17)
Measured on the author's own edits ("one comes out awesome and the next is an exact duplicate but grainy and weird"): on `qwen21:edit` (enhance off, the same source) many results with seed **4242** are an
over-sharpened, grainy, HDR-looking copy of the source that ignores the pose instruction. The reading is the high-frequency energy (std of the luminance minus its Gaussian blur, radius 2, on the native pixels, `studio/grain.py`):
the bad ones read 17.1-19.9 (the 8 pose prompts at seed 4242: 17.2-17.9), clean ones 4.9-8.9 (the same prompt at seeds 7 / 11 / 108971: 6.25 / 5.99 / 6.13), the source pictures 4-6. Of the 60 most recent Qwen edit
files (identical pairs) 22 were bad and 38 clean, with an empty gap between. It is not every 4242: one author job at 4242 ((earlier commit)) read 5.3.
- **Cause (INFERRED, not proven; nothing was run on the GPU for it; a 20-seed sweep of one prompt, run by the coordinator on 2026-10-17, read 5.5-6.2 for every seed 1 2 3 42 99 100 123 1000 1234 2024 2026 3407 4241 4243 4244 5000 7777 31337 12345 424242: none grainy, so only 4242 is blacklisted and the grain gate is the real fix):** the graph is a plain `KSampler` (40 steps, euler / simple, CFG 1) after `TextEncodeQwenImage21` and a `QwenImage21Cache` node, with no per-seed state, so the
  seed only sets the starting noise: the artefact is that noise realisation meeting this sampler (and, from the clean 4242 job, the prompt / source), not a cache or a LoRA. A distilled 8-step sigma schedule is NOT in this graph.
- **Seed policy** (`studio/seeds.py`, Qwen edit family only: `qwen21:edit / outfit / fusion / outpaint`; other engines keep their defaults): no seed given = a random seed that is never 4242; a character's locked seed is used
- **Grain gate on every Qwen edit** (`tools/image_qwen21_tools._render_gated` + `studio/grain.gate_take`; covers the studio runner and so Pictures, the outfit pass, pose sets, Deliverables stills, character sheets, the `edit / outfit / fusion` entries and anything else that calls `qwen21_edit` / `qwen21_task`): after each render the result's high-frequency energy is measured against its input (CPU, native pixels, ~0.2 s; ratio >= 2x AND >= 10 absolute, so an input that is itself noisy is judged relative to itself). A flagged result is re-rendered automatically up to 2 more times with fresh seeds (derived, never 4242, part of the cache key), the cleanest is kept, and the job card says 're-rendered because the first result was over-sharpened/grainy (seed X)' and 'kept the cleanest of N attempts'. If every attempt flags, the cleanest is kept and the card says 'grainy: check' (never silent, never withheld). A checker error never blocks or fails a job; a grainy file already in the cache is never served again (a re-run re-measures it); a busy GPU on a grainy cached result returns it with a visible note instead of waiting. `grain_gate=False` switches it off for A/B scripts. `grain.gate_take` is engine-neutral: Klein edit and the others can use it, but it is enabled for Qwen only until a sweep shows the same defect there. Outpaint is not measured (its canvas grows). In the pose set the same measurement is also a FAILED check (Qwen route), so its one automatic reroll uses a new seed. Clean results I could compare read 1.3-1.5x their input, the bad one 4.2x. Tests: `tests/studio/test_seeds_grain.py`, `tests/tools/test_qwen21_grain_gate.py` (synthetic clean / grainy pictures, the retry loop with fake renders, checker errors, the cache).

**The 20-seed sweep (2026-10-17, run by the coordinator on the live studio: one `qwen21:edit` prompt and source, hf = high-frequency std, radius-2 Gaussian blur residual):**

| seed | hf | seed | hf | seed | hf | seed | hf |
|---|---|---|---|---|---|---|---|
| 1 | 5.80 | 2 | 5.71 | 3 | 6.15 | 42 | 6.05 |
| 99 | 5.83 | 100 | 5.70 | 123 | 5.71 | 1000 | 5.50 |
| 1234 | 5.88 | 2024 | 6.13 | 2026 | 6.02 | 3407 | 5.78 |
| 4241 | 5.90 | 4243 | 5.86 | 4244 | 5.77 | 5000 | 6.04 |
| 7777 | 5.82 | 31337 | 5.49 | 12345 | 5.90 | 424242 | 5.86 |

None of the 20 is grainy (all 5.49-6.15); 4242 read 17.2-17.9 on 9 prompts. So **only 4242 is blacklisted**, for every `qwen21` entry (t2i shares the edit's 40-step KSampler; outfit / fusion / outpaint
share the model and the 8-step turbo sampler; no sweep exists for those routes, so there the blacklist is a hint and, for the edits, the grain gate is the safety net; a t2i has no input to compare with, so it only has the blacklist).
