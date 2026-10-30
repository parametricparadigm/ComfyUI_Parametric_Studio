# Restore a photo with references

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


## When to use it
A blurry, pixelated, noisy or compressed photo of a person + 1-5 other photos of the same person → the photo restored
with that person's real features. **One reference is enough**: it scored best (21.4 dB PSNR vs the ground truth; five
references 20.3, base model 40 steps 17.0, Turbo without the LoRA 16.4).

## In the studio
Edit tab → "RefRes v5 · Restore a degraded photo". `image` = the damaged photo, `ref_1` = another photo of the same
person (`ref_2`..`ref_5` optional). `who`: woman (the tested wording) / man / person.

## The recipe (pinned; graph = `sc_refres_turbo1` minus its in-graph degrade)
Qwen-Image 2.1 Turbo bf16 + RefRes v5 LoRA 1.0 + QwenImage21Cache, qwen3vl_8b bf16, Texture-Fix VAE,
TextEncodeQwenImage21 (resolution 1024, image 1 = the photo, images 2.. = the references, no negative), BasicGuider
CFG 1, euler, the 8 Turbo ManualSigmas, seed 4242, the card prompt verbatim. "turbo1" in the test = **one reference**
at 8 steps (the card: Turbo 8 steps / base 40), not one step. The test degraded its ground truth in-graph (area x0.1875,
back up bilinear); the studio takes your degraded photo as it is. 3.8 s exec, port peak 50,328 MiB (1 ref).

Studio-graph smoke 2026-10-11 ~20:00 on idle  a local port with the test's degraded input as image 1: success in 20 s incl.
load; mean pixel difference 0.86/255 from the tested result (`outputs/studio_motion_smoke_2026-10-11/refres_vs_test.jpg`).

## Limits
- Every arm **over-sharpens** (crunchy wall, HDR look); the LoRA arms the least and closest to the face. Too crunchy
  for hero use; next to try: lower LoRA strength / denoise (KB verdict).
- 2-4 references and the "man" / "person" wording were not tested (a note says so).
- Licence: RefRes for Qwen-Image 2.1 = Qwen Research License, **NON-COMMERCIAL** (hc0/RefRes card).
