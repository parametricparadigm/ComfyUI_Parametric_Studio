# Model cookbook

What each model in this studio is best at alone, and what it does well with the others. The recipes in the app (Recipes page, `studio/recipes.json`) are these combinations as one-click chains.

**Where the claims come from.** "Measured here" means a real render through this studio on one 96 GB card, each with a cold model load (`/api/recipes` carries the same figures). "Owner's tests" means an A/B or note from the owner's earlier studio on the same box, on a different stack: treat those as strong hints, not as measurements of this code. Licence notes are a summary; see [MODELS.md](../MODELS.md) and read each licence yourself.

## Rules every chain follows

- One model on the card at a time: the runner unloads ComfyUI after each GPU step and checks free VRAM before the next (the step's peak + 4 GiB).
- Every clip is a separate render from a still or from words. Do not chain clips from each other's last frames unless you want that drift: in the owner's tests, face identity fell about 0.06 to 0.1 per chained segment.
- The studio's sound is real sound. H3 and LTX generate it with the picture; Music 3 and ACE-Step generate whole tracks. A chain picks which one the viewer hears.

## The models

### MiniMax H3 (Video H3, Animate H3, Director, Director keyframes, Recast, Reshoot)
Video with its own synced sound in one pass, 24 fps, 17k+5 frames.

**Alone.** Text to video (`h3_video`, `director`), first-frame animation (`h3_animate`), first and last frame (`director_keyframes`), reference plus a source clip (`recast`, `reshoot`). Measured here at 0.8 MP, 5 s, fast mode: 67 to 174 s, 45 to 49 GiB peak on the whole card. Recast 523 s and Reshoot 460 s at about 37 GiB.

**With others.** It is the moving-picture stage of almost every recipe:
- Klein or FLUX.3 still to `h3_animate`: you choose the exact opening frame.
- The same still as first and last frame: a loop (owner's rule: no person, fixed camera, "one smooth, even cycle that ends exactly where it began").
- Two stills of one place: `director_keyframes` travels between them with no cut.
- Any clip to `reshoot`: the same moment from a second camera, which cuts with the first.
- Any clip plus a character picture to `recast`: the performance stays, the actor changes.

**How to write for it** (owner's rules and MiniMax's guide): one main action, one camera decision, one continuous shot. Camera = move + amplitude + speed + start and end framing. Say props, place and light in identical words across shots. Describe what is present; a negation primes the thing. Blank garments invent logos, so say "plain, no print". Sound goes in `overall_soundscape`, music in `non_diegetic_music`, `N/A` turns music off. Dialogue: the voice is described outside the `<d>` tag, the words inside, about 2.6 words a second, early in the clip.

**The wider map, not all wired here yet (owner's tests).** His earlier studio ran H3 far past plain video: a speed LoRA per base (turbo v4 at 4 steps), keyframe animation (alvdansen hero, tween, sequence), video to video through rank-concat LoRAs (VFX edit: "the edit first, then what must stay"; style transfer: "linework, palette, brushwork"; sharpen only on soft clips), frozen-time orbit (first = last, trained on human splats), restore, person remover, depth restyle with Fun Union, handheld (baked at 1.0; the author's 1.7 breaks the scene), Meridian re-filming with a warped first frame, and lip-sync lock, where the song is inpainted into the audio latent so the picture sings it. Only one bypass LoRA per model.

Licence: MiniMax H3 Community License. Its grant lists excluded territories and commercial products must show the name; see MODELS.md. The owner reports Comfy approved H3 for this contest.

### MiniMax Music 3 (Music)
Whole songs with sung lyrics. Measured here: 18 s to render 60 s of audio, 27 GiB.

**Alone.** Use the three-block caption (Global Metadata, Vocal Details, Arrangement) and `[verse]`, `[chorus]` tags alone on their lines, no numbers on the tags, identical choruses. It sings as long as the lyrics last, about 6 s a line. For an instrumental write "No vocals. Purely instrumental." and only non-vocal tags; a lone `[instrumental]` still hums.

**With others.** The score of any chain. Owner's tests: it ignores a requested BPM about one time in six, so the beat-cut step measures the tempo from the audio. It renders hot (true peak at or over 0 dBTP), so the chain normalizes loudness. Upstream licence: MiniMax-Music3 Community License, commercial use must show the name.

### FLUX.2 Klein 4B (Image)
The fast, permissive still. Measured here: 6 to 22 s, 23 GiB. Apache-2.0.

**Alone.** Fast mode 4 steps, quality mode 20 steps.

**With others.** The keyframe stage. With its image-edit graph (the ComfyUI template `image_flux2_klein_image_edit_4b_distilled`) a character frame becomes a reference for every later keyframe, which is what keeps one character through a film: measured here across all shots of the short film. Same seed plus the same words keeps a layout close between boards, which is how the storyboard recipe gets frames first and last frame control can bridge.

### FLUX.3 Klein (Image HQ)
Highest still quality here. 24 GiB. Gated; commercial only under US$5,000,000 gross annual revenue. Use it for the one frame the viewer stares at: the hero of a product ad, then animate it.

### Anima (Anime)
Illustration and anime stills: 6 to 40 s, 13 GiB. Non-commercial licence. Keep realism words out of prompts (owner's rule); H3 carries the drawn look when it animates a frame if the prompt says "2D-animated".

### Wan 2.2 TI2V-5B (Video, Animate)
The fully permissive video lane: 91 to 105 s at 720p, 35 GiB, Apache-2.0. Silent. Choose it when licence terms matter more than sound or peak quality, and pair it with a separately rendered score. Its Fun Camera build (`reshoot_wan`) makes a new camera path from a clip's first frame, regenerating the motion.

### LTX-2.5 with IC-LoRAs (Video + sound, Animate + sound, VFX)
Fast video with sound (21 to 58 s, 44 GiB) and real VFX passes: water simulation, clean plate, day to night, alpha matte (49 to 116 s, 45 GiB). Gated; paid licence above US$10,000,000 revenue.

**With others.** The IC-LoRAs take any clip, so generate a plate with any engine, then stack passes, each taking the last output. Water at 1.3 is the card's stronger setting; 1.0 proved subtle in the owner's test. Describe the scene the same way in each pass.

### Tools the chains use
- **ffmpeg (CPU):** beat cut, join, loop seam, side by side, mux. Documented requirement.
- **A local language model (Qwen, or whatever `studio/llm_tiers.py` finds):** writes the shot list. A sleeping server is skipped; with none, a fixed pattern is used and the recipe says so.

### Installed on this box, not in a tested chain yet
From the ComfyUI templates that run here: ACE-Step 1.5 XL turbo (song drafts; owner's tests: 10 to 42 s for 2 minutes, BPM within 5% on 5 of 6 styles), Hunyuan3D 2.1 and TRELLIS.2 (still to 3D mesh), TripoSplat, MoGe and Depth Anything 3 (geometry, depth), BiRefNet (background removal), RIFE and FILM (frame interpolation), SeedVR2 (video upscale; owner's tests: best detail, about 17 to 20 GB on clips up to 480x832, and a 1344x768 x124 clip exceeded the card), Wan Animate 2 (motion transfer), Wan 2.2 14B first and last frame, Wan Dancer.

## Which combinations are worth it

| You want | Chain | Why this order | Recipe |
|---|---|---|---|
| A film from a sentence | LLM, Klein character, Klein keyframes, H3, Music 3, beat cut | The character frame is the anchor; the music is cut last so it never constrains a shot | One sentence to a short film |
| A music video | Music 3 first, Klein keyframes, H3, beat cut | The song sets the length and the cuts | Music Video Maker |
| A product ad | FLUX.3 hero, H3 animate, Reshoot, Music 3, beat cut | Reshoot keeps it the same product | Product ad from nothing |
| A seamless loop | Still, H3 first = last, seam fade | The fade closes the gap the model leaves | Perfect loop |
| Time passing in one shot | Klein boards with one seed, H3 keyframes, join | One seed keeps the layout | Storyboard to one continuous shot |
| A big VFX shot | LTX plate, clean plate, day to night, water | Each pass feeds the next | VFX stack |
| An anime opening | Anima, H3 ("2D-animated"), Music 3, beat cut | H3 keeps the drawn look | Anime opening |
| Your actor in any scene | Klein character, H3 scene, Recast | Keeps camera and timing | Recast any performance |
| Coverage from one take | Director, Reshoot, cut between | Same timing, so they cut on one sound | One take, two cameras |
| No licence caveats | Klein, Wan 2.2 5B, ACE-Step | All permissive weights | Fully open short |

## Recipes: tested or not

The Recipes page shows each recipe's status, its measured time and VRAM, and its output. A recipe says tested only after it rendered on this box. See `studio/recipes.json` and its `tested` block.
