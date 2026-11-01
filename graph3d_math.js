/* Pure logic of the 3D Pro page: what each ComfyUI node does, where it sits, when light reaches it, what a run looks like. No DOM and no three.js here; tested in tests/studio_lanes/test_graph3d.mjs. */
const I = (kind, short, say) => ({ kind, short, say });
const LOADV = "Loads the VAE, which translates between pixels and the small latent space where the model works.";
const SAVE = "Writes the finished file to the output folder. This is the file you see in the studio.";
const DEC = "Uses the VAE to turn the finished latent into real frames.";
const DECA = "Uses the audio VAE to turn the finished latent into a sound wave.";
const EMPTY = "Creates an empty latent at the output size. Its shape sets the width, height and length of the result.";
export const CLASS_INFO = {
  MiniMaxH3FunUnion2LoaderEXPT8: I("load", "Loads H3's control model", "Loads MiniMax H3's Fun Union control model, the part that makes a video follow a depth or pose guide."),
  MiniMaxH3FunUnion2ApplyEXPT8: I("plan", "Follows a depth or pose video", "Makes MiniMax H3 follow a guide video frame by frame, so the layout and the camera move hold while the picture is made new."),
  Wan22FunControlToVideo: I("plan", "Follows a guide video (Wan)", "Sets up Wan 2.2 to follow a depth or pose video, with a reference picture for the look."),
  TextEncodeQwenImage21: I("text", "Reads the words and the picture", "Turns your words and a reference picture into what Qwen-Image 2.1 edits from."),
  QwenImage21Cache: I("load", "Keeps Qwen-Image ready", "Holds Qwen-Image 2.1 in a form that runs faster over its steps."),
  EasyCache: I("value", "Skips repeated work", "Reuses earlier results when a step changes little, which saves time at a small cost in detail."),
  SolidMask: I("media", "A plain mask", "Makes a mask of one value across the whole frame. White here means make every pixel new."),
  ResizeImageMaskNode: I("media", "Resizes", "Resizes a picture or a video to the size the model works at."),
  UNETLoader: I("load", "Loads the diffusion model", "Loads the diffusion model: the network that learned to turn noise into a picture, step by step."),
  CheckpointLoaderSimple: I("load", "Loads a checkpoint", "Loads one file that holds the diffusion model, the text encoder and the VAE together."),
  CLIPLoader: I("load", "Loads the text encoder", "Loads the text encoder, the model that turns your words into numbers the diffusion model understands."),
  DualCLIPLoader: I("load", "Loads two text encoders", "Loads two text encoders that read your prompt together."),
  TripleCLIPLoader: I("load", "Loads three text encoders", "Loads three text encoders that read your prompt together."),
  VAELoader: I("load", "Loads the VAE", LOADV),
  LoraLoaderModelOnly: I("load", "Adds a LoRA to the model", "Patches the model with a LoRA, a small add-on trained for one style, one subject or a faster run."),
  LoraLoaderBypassModelOnly: I("load", "Adds a LoRA to the model", "Patches the model with a LoRA, a small add-on trained for one style, one subject or a faster run. This version applies it while the model runs, which saves memory."),
  LoraLoader: I("load", "Adds a LoRA", "Patches the model and text encoder with a LoRA, a small add-on trained for one style or subject."),
  LTXICLoRALoaderModelOnly: I("load", "Adds the effect LoRA", "Patches LTX with an image-conditioning LoRA trained for one edit, such as adding water or clearing a plate."),
  ModelSamplingSD3: I("plan", "Shifts the noise schedule", "Shifts the noise schedule, which gives more of the steps to the noisy start where structure forms."),
  MiniMaxH3SigmaShift: I("plan", "Shifts H3's schedule", "Shifts H3's noise schedule, separately for the video and the audio."),
  CLIPTextEncode: I("text", "Turns words into conditioning", "Runs a prompt through the text encoder. The result, called conditioning, tells the sampler what to make or avoid."),
  MiniMaxMusic3TextEncode: I("text", "Encodes style and lyrics", "Encodes the song description and the lyrics so the music model knows what to play and sing."),
  ConditioningZeroOut: I("text", "Blanks the conditioning", "Zeroes the conditioning so it can act as a neutral negative prompt."),
  LTXVConditioning: I("text", "Adds the frame rate", "Attaches the frame rate to both prompts so LTX times its motion correctly."),
  CFGGuider: I("text", "Balances the prompts", "Combines the model with the positive and negative prompts. CFG sets how hard the prompt steers each step."),
  BasicGuider: I("text", "Points the model at the prompt", "Pairs the model with one conditioning and no negative prompt, so each step simply follows the prompt."),
  MiniMaxH3ImageToVideo: I("text", "Sets up the H3 shot", "Encodes the prompt and any frames, and builds the empty H3 video and audio latent to fill."),
  MiniMaxH3ReferenceToVideo: I("text", "Feeds references to H3", "Encodes the prompt together with your reference pictures and clips, and builds the latent H3 will fill."),
  LTXAddVideoICLoRAGuide: I("text", "Feeds your clip as a guide", "Encodes the source clip and attaches it to the conditioning, so the edit follows its motion and framing."),
  WanCameraImageToVideo: I("text", "Combines frame and camera", "Combines the start frame, the prompts and the camera data into what the Wan sampler needs."),
  WanCameraEmbedding: I("plan", "Describes the camera move", "Turns a camera preset into per-frame data that tells Wan how the view should move."),
  KSamplerSelect: I("plan", "Picks the sampler", "Chooses the sampling method, the math that decides how each denoising step moves."),
  BasicScheduler: I("plan", "Plans the noise steps", "Builds the list of noise levels, the sigmas, that the sampler walks down from pure noise to a clean result."),
  Flux2Scheduler: I("plan", "Plans the noise steps", "Builds the list of noise levels for FLUX.2, adjusted for the image size."),
  ManualSigmas: I("plan", "Exact noise steps", "Sets the noise levels by hand, as tuned for this distilled model."),
  RandomNoise: I("plan", "Makes the starting noise", "Generates the starting noise from a seed. The same seed and settings give the same result."),
  LoadBackgroundRemovalModel: I("load", "Loads the cut-out model", "Loads a background removal model such as BiRefNet."), RemoveBackground: I("media", "Finds the foreground", "Makes a mask of the main subject in a picture."), InvertMask: I("media", "Flips a mask", "Swaps the masked and unmasked areas."), JoinImageWithAlpha: I("media", "Adds transparency", "Puts a mask on a picture as its alpha channel, giving a cut-out."),
  LoadMoGeModel: I("load", "Loads the depth model", "Loads MoGe, which estimates the shape of a scene from one picture."), MoGeInference: I("media", "Estimates geometry", "Runs MoGe on the picture."), MoGeGeometryToFOV: I("value", "Reads the lens", "Works out the camera's field of view from the estimated geometry."), SAM3_VideoTrack: I("media", "Finds the person", "SAM 3 finds and masks the subject named by the text."), SAM3DBody_Loader: I("load", "Loads SAM 3D Body", "Loads the model that turns a person in a picture into a 3D body."), SAM3DBody_Predict: I("media", "Builds the 3D body", "Estimates the body's shape and pose."), SAM3DBody_FaceExpression: I("media", "Adds the expression", "Estimates the face's expression for the 3D body."), SAM3DBody_Render: I("media", "Renders the body", "Draws the 3D body to a picture for checking."), BuildPoseFile: I("save", "Builds the rigged file", "Packs the body and pose into a file with a skeleton."), SaveGLB: I("save", "Saves a 3D file", "Writes a .glb file to the output folder."),
  EmptyLatentImage: I("latent", "Blank latent canvas", EMPTY), EmptySD3LatentImage: I("latent", "Blank latent canvas", EMPTY), EmptyFlux2LatentImage: I("latent", "Blank latent canvas", EMPTY), EmptyLTXVLatentVideo: I("latent", "Blank video latent", EMPTY),
  LTXVEmptyLatentAudio: I("latent", "Blank audio latent", "Creates an empty audio latent the same length as the video, so LTX generates sound with it."),
  EmptyMiniMaxMusic3LatentAudio: I("latent", "Blank song latent", "Creates an empty audio latent as long as the song."),
  Wan22ImageToVideoLatent: I("latent", "Starts from your image", "Encodes the start image and makes the empty video latent that grows from it."),
  LTXVConcatAVLatent: I("latent", "Joins video and audio", "Packs the video and audio latents together so both are denoised as one."),
  LTXVSeparateAVLatent: I("latent", "Splits video and audio", "Separates the finished latent back into its video and audio parts."),
  LTXVImgToVideoInplace: I("latent", "Places your image", "Writes the encoded start image into the first frame of the video latent."),
  LTXVCropGuides: I("latent", "Removes the guide frames", "Cuts the guide frames back out of the latent before decoding."),
  LTXVLatentUpsampler: I("latent", "Doubles the picture's size", "Upscales the latent two times before the short second pass of LTX."),
  LatentUpscaleModelLoader: I("loader", "Loads the upscaler", "Reads the model that doubles a latent's size."),
  SamplerCustomAdvanced: I("sample", "The sampler: makes the result", "Where the result actually forms. It starts from noise and removes a little at every step, guided by your prompt."),
  KSampler: I("sample", "The sampler: makes the result", "Where the result actually forms. It starts from noise and removes a little at every step, guided by your prompt."),
  KSamplerAdvanced: I("sample", "One stage of sampling", "Runs a chosen range of denoising steps, so one model can hand off to another partway through."),
  VAEDecode: I("decode", "Turns latents into pixels", DEC),
  VAEDecodeTiled: I("decode", "Turns latents into pixels", "Same as VAE decode, but in overlapping tiles and chunks so long video fits in memory."),
  VAEDecodeAudio: I("decode", "Turns latents into sound", DECA), VAEDecodeAudioTiled: I("decode", "Turns latents into sound", DECA), LTXVAudioVAEDecode: I("decode", "Turns latents into sound", DECA),
  VAEEncode: I("decode", "Turns pixels into a latent", "Uses the VAE to compress an image into the latent space the model works in."),
  LoadImage: I("media", "Loads your picture", "Loads a picture you uploaded from ComfyUI's input folder."),
  LoadVideo: I("media", "Loads your clip", "Loads a clip you uploaded from ComfyUI's input folder."),
  "Video Slice": I("media", "Cuts the clip to length", "Cuts the source clip down to the part this shot will use."),
  GetVideoComponents: I("media", "Splits frames and sound", "Splits a clip into its frames, its sound and its frame rate."),
  PSN_FPSResampler: I("media", "Converts to 24 fps", "This studio's own node: resamples the frames to the rate the model expects."),
  ImageFromBatch: I("media", "Picks a run of frames", "Takes the frames the shot needs from a longer batch."),
  ImageScale: I("media", "Resizes the frames", "Resizes and crops the frames to the size the model will work at."),
  LTXVPreprocess: I("media", "Prepares the start image", "Applies light compression to the start image so the model treats it like a video frame."),
  CreateVideo: I("media", "Joins frames and sound", "Combines the decoded frames, and sound if any, into one video at the set frame rate."),
  SaveImage: I("save", "Saves the result", SAVE), SaveVideo: I("save", "Saves the result", SAVE), SaveAudio: I("save", "Saves the result", SAVE), SaveAudioAdvanced: I("save", "Saves the result", SAVE), PreviewImage: I("save", "Shows a preview", "Shows the image in ComfyUI without keeping it in the output folder."),
  VRAM_Debug: I("value", "Frees GPU memory", "Unloads the text encoder and clears the GPU cache before sampling, so the big model fits."),
  ComfySwitchNode: I("value", "Chooses one of two inputs", "Passes on one input or the other. A setting in the studio flips it."),
  PrimitiveInt: I("value", "A whole number", "Holds one whole number that other nodes read."),
  PrimitiveFloat: I("value", "A number", "Holds one number that other nodes read."),
  PrimitiveBoolean: I("value", "On or off", "Holds one on or off value that other nodes read."),
  ComfyMathExpression: I("value", "Calculates a value", "Works out a value from its inputs with a small formula."),
  ResolutionSelector: I("value", "Picks width and height", "Works out the width and height from an aspect ratio and a megapixel budget."),
  LTXFloatToInt: I("value", "Converts a number", "Rounds a decimal number to a whole one for the next node."),
  SeedNode: I("value", "Holds the seed", "Holds the seed that the other nodes share, so the run can be repeated."),
};
export const KIND_LABEL = { load: "Loader", text: "Prompt", latent: "Latent", plan: "Setting", sample: "Sampler", decode: "Decode", media: "Media", value: "Value", save: "Output", other: "Node" };
export const KIND_COLOR = { load: "#f5c518", text: "#ffe07a", latent: "#27e07f", plan: "#d8c25a", sample: "#ffc81f", decode: "#46e88f", media: "#7dffb8", value: "#a7ad8a", save: "#27e07f", other: "#c9cfb4" };
export function explain(cls) {
  const k = CLASS_INFO[cls]; if (k) return { ...k, known: true };
  const c = String(cls || ""), kind = /load/i.test(c) ? "load" : /sampler/i.test(c) ? "sample" : /save|preview/i.test(c) ? "save" : /decode/i.test(c) ? "decode" : /encode|condition|guider/i.test(c) ? "text" : /latent/i.test(c) ? "latent" : /primitive|switch|math/i.test(c) ? "value" : /image|video|audio/i.test(c) ? "media" : "other";
  return { kind, short: "", say: c, known: false };
}
/* ---------- wire types, gold for what steers the run, green for what it makes ---------- */
export const TYPE_COLOR = { MODEL: "#f5c518", CLIP: "#ffd866", VAE: "#e0a020", CONDITIONING: "#ffeca0", GUIDER: "#e9d850", NOISE: "#c7e24a", SAMPLER: "#cfc56a", SIGMAS: "#cfc56a", LATENT: "#27e07f", IMAGE: "#7dffb8", VIDEO: "#7dffb8", AUDIO: "#46e6c4", NUMBER: "#98a07c", BOOL: "#98a07c", ANY: "#98a07c" };
const OUT_TYPES = { UNETLoader: ["MODEL"], CheckpointLoaderSimple: ["MODEL", "CLIP", "VAE"], CLIPLoader: ["CLIP"], DualCLIPLoader: ["CLIP"], VAELoader: ["VAE"], LoraLoaderModelOnly: ["MODEL"], LTXICLoRALoaderModelOnly: ["MODEL", "NUMBER"], ModelSamplingSD3: ["MODEL"], MiniMaxH3SigmaShift: ["MODEL"], CLIPTextEncode: ["CONDITIONING"], ConditioningZeroOut: ["CONDITIONING"], LTXVConditioning: ["CONDITIONING", "CONDITIONING"], CFGGuider: ["GUIDER"], BasicGuider: ["GUIDER"], KSamplerSelect: ["SAMPLER"], BasicScheduler: ["SIGMAS"], Flux2Scheduler: ["SIGMAS"], ManualSigmas: ["SIGMAS"], RandomNoise: ["NOISE"], SamplerCustomAdvanced: ["LATENT", "LATENT"], KSampler: ["LATENT"], KSamplerAdvanced: ["LATENT"], VAEDecode: ["IMAGE"], VAEDecodeTiled: ["IMAGE"], VAEDecodeAudio: ["AUDIO"], VAEDecodeAudioTiled: ["AUDIO"], LTXVAudioVAEDecode: ["AUDIO"], LoadImage: ["IMAGE", "MASK"], LoadVideo: ["VIDEO"], "Video Slice": ["VIDEO"], GetVideoComponents: ["IMAGE", "AUDIO", "NUMBER"], ImageFromBatch: ["IMAGE"], ImageScale: ["IMAGE"], PSN_FPSResampler: ["IMAGE"], CreateVideo: ["VIDEO"], PrimitiveInt: ["NUMBER"], PrimitiveFloat: ["NUMBER"], PrimitiveBoolean: ["BOOL"], ComfyMathExpression: ["NUMBER", "NUMBER"], ResolutionSelector: ["NUMBER", "NUMBER"], LTXFloatToInt: ["NUMBER"], SeedNode: ["NUMBER"], MiniMaxH3ImageToVideo: ["CONDITIONING", "LATENT"], MiniMaxH3ReferenceToVideo: ["CONDITIONING", "LATENT"], LTXVConcatAVLatent: ["LATENT"], LTXVSeparateAVLatent: ["LATENT", "LATENT"], LTXVEmptyLatentAudio: ["LATENT"], EmptyLatentImage: ["LATENT"], EmptyFlux2LatentImage: ["LATENT"], EmptyLTXVLatentVideo: ["LATENT"], EmptyMiniMaxMusic3LatentAudio: ["LATENT"], Wan22ImageToVideoLatent: ["LATENT"], LTXVImgToVideoInplace: ["LATENT"], LTXAddVideoICLoRAGuide: ["CONDITIONING", "CONDITIONING", "LATENT"], LTXVCropGuides: ["CONDITIONING", "CONDITIONING", "LATENT"], LTXVPreprocess: ["IMAGE"], WanCameraEmbedding: ["CAMERA", "NUMBER", "NUMBER", "NUMBER"], WanCameraImageToVideo: ["CONDITIONING", "CONDITIONING", "LATENT"], MiniMaxMusic3TextEncode: ["CONDITIONING", "NUMBER"] };
const PASS_THROUGH = { ComfySwitchNode: ["on_true", "on_false"], VRAM_Debug: ["any_input"] };
export function keyType(key) {
  const k = String(key).toLowerCase();
  if (k === "model") return "MODEL"; if (k === "clip") return "CLIP"; if (/vae/.test(k)) return "VAE"; if (/^(positive|negative|conditioning)$/.test(k)) return "CONDITIONING"; if (k === "guider") return "GUIDER"; if (k === "noise") return "NOISE"; if (k === "sampler") return "SAMPLER"; if (k === "sigmas") return "SIGMAS";
  if (/latent|^samples$/.test(k)) return "LATENT"; if (/image|frame|pixels/.test(k)) return "IMAGE"; if (/video/.test(k)) return "VIDEO"; if (/audio/.test(k)) return "AUDIO"; if (/^switch$/.test(k)) return "BOOL"; if (/^(width|height|length|steps|fps|frame_rate|seed|value|seconds|source_fps|values\.)/.test(k)) return "NUMBER";
  return null;
}
const isLink = (v, graph) => Array.isArray(v) && v.length === 2 && typeof v[1] === "number" && graph[String(v[0])] != null;
const WIDGET_RANK = [/^(text|prompt|caption|lyrics)$/, /(unet|clip|vae|lora|ckpt)_name/, /^(file|image)$/, /seed/, /^steps$/, /^cfg$/, /sampler_name/, /^scheduler$/, /^(width|height|length|frames_number)$/, /^value$/, /aspect|megapixels|expression|camera_pose/, /strength|shift|sigmas|fps|frame_rate|denoise/];
const rank = (k) => { const i = WIDGET_RANK.findIndex((r) => r.test(k)); return i < 0 ? 99 : i; };
export const isLongText = (w) => /^(text|prompt|caption|lyrics|expression)$/.test(w.key);
export const fileBase = (s) => String(s).split(/[\\/]/).pop();
export function formatValue(v) { if (v === null || v === undefined) return ""; if (typeof v === "number") return Number.isInteger(v) ? String(v) : String(+v.toFixed(4)); if (typeof v === "boolean") return v ? "on" : "off"; if (typeof v === "object") return JSON.stringify(v); const s = String(v); return /\.(safetensors|ckpt|pt|pth|gguf|bin|onnx)$/.test(s) ? fileBase(s) : s; }
/** The graph as nodes and links: every link knows its source slot, target input and data type. Links to missing nodes are widgets, as ComfyUI would reject them anyway. */
export function buildModel(graph) {
  const g = graph || {}, ids = Object.keys(g), nodes = {}, links = [];
  ids.forEach((id) => { const n = g[id] || {}; nodes[id] = { id, cls: n.class_type || "Node", info: explain(n.class_type), inputs: [], widgets: [], outs: {}, depth: 0, col: 0, y: 0 }; });
  ids.forEach((id) => Object.entries((g[id] || {}).inputs || {}).forEach(([key, v]) => { if (isLink(v, g)) { const l = { id: links.length, from: String(v[0]), slot: v[1], to: id, key, type: "ANY" }; links.push(l); nodes[id].inputs.push(l); } else nodes[id].widgets.push({ key, value: v }); }));
  const seen = {}; const outType = (id, slot) => { const c = id + ":" + slot; if (seen[c]) return seen[c] === 1 ? "ANY" : seen[c]; seen[c] = 1; const n = nodes[id]; let t = (OUT_TYPES[n.cls] || [])[slot]; if (!t && PASS_THROUGH[n.cls]) { const k = n.inputs.find((l) => PASS_THROUGH[n.cls].includes(l.key)); if (k) t = outType(k.from, k.slot); } if (!t) { const l = links.find((x) => x.from === id && x.slot === slot && keyType(x.key)); t = l ? keyType(l.key) : "ANY"; } seen[c] = t; return t; };
  links.forEach((l) => { l.type = TYPE_COLOR[outType(l.from, l.slot)] ? outType(l.from, l.slot) : keyType(l.key) || "ANY"; const o = nodes[l.from].outs; (o[l.slot] ||= { type: l.type, to: [] }).to.push(l); });
  ids.forEach((id) => nodes[id].widgets.sort((a, b) => rank(a.key) - rank(b.key)));
  // longest path from any source; a cycle cannot loop forever (ComfyUI would reject it)
  const memo = {}; const dep = (id, st = new Set()) => { if (memo[id] != null) return memo[id]; if (st.has(id)) return 0; st.add(id); let d = 0; nodes[id].inputs.forEach((l) => { d = Math.max(d, dep(l.from, st) + 1); }); st.delete(id); return (memo[id] = d); };
  ids.forEach((id) => { nodes[id].depth = dep(id); });
  return { ids, nodes, links };
}
/* ---------- panel metrics, shared by the layout and the canvas that paints each panel ---------- */
export const PANEL = { rowH: 0.2, wrowH: 0.19, lineH: 0.165, foot: 0.12 };
export function panelSize(n) {
  const k = n.info.kind, w = k === "sample" ? 4.5 : k === "save" ? 3.9 : k === "value" ? 2.9 : 3.6, head = k === "value" ? 0.66 : k === "sample" ? 1.16 : 1.02;
  const rows = Math.min(8, Math.max(n.inputs.length, Object.keys(n.outs).length, 1)), shown = n.widgets.filter((x) => formatValue(x.value) !== "" && !/^(batch_size|weight_dtype|device|strict_duration|format|codec|start_time|bypass|multiple)$/.test(x.key)).slice(0, k === "value" ? 2 : 3);
  let wh = 0; shown.forEach((x) => { wh += isLongText(x) ? PANEL.lineH * 3 + 0.05 : PANEL.wrowH; });
  return { w, h: head + rows * PANEL.rowH + (wh ? 0.07 + wh : 0) + PANEL.foot, head, rows, shown, wh, rad: 0.11 };
}
/* ---------- columns: left to right by dependency, sources pulled up next to whatever first needs them, no column far taller than the rest ---------- */
function assignColumns(m) {
  const { ids, nodes, links } = m, consumers = {}; ids.forEach((i) => { consumers[i] = []; }); links.forEach((l) => consumers[l.from].push(l.to));
  const order = [...ids].sort((a, b) => nodes[b].depth - nodes[a].depth);
  order.forEach((id) => { const c = consumers[id]; nodes[id].col = c.length ? Math.min(...c.map((x) => nodes[x].col)) - 1 : nodes[id].depth; });
  const span = () => { const v = ids.map((i) => nodes[i].col); return [Math.min(...v, 0), Math.max(...v, 0)]; };
  const H = (id) => panelSize(nodes[id]).h + 0.5, total = ids.reduce((a, i) => a + H(i), 0), [lo0, hi0] = span(), cap = Math.max(7.5, (1.5 * total) / Math.max(1, hi0 - lo0 + 1));
  for (let c = hi0; c >= lo0; c--) { for (let guard = 0; guard < 30; guard++) { const here = ids.filter((i) => nodes[i].col === c), h = here.reduce((a, i) => a + H(i), 0); if (h <= cap || c <= lo0 && lo0 <= hi0 - 8) break; const mv = here.filter((i) => nodes[i].inputs.every((l) => nodes[l.from].col < c - 1)).sort((a, b) => H(a) - H(b) || a.localeCompare(b))[0]; if (!mv) break; nodes[mv].col = c - 1; } }
  const low = span()[0]; ids.forEach((i) => { nodes[i].col -= low; });
}
/* least-squares positions that keep the order and the gaps (pool adjacent violators) */
export function placeOrdered(want, heights, gap) {
  const n = want.length, off = [0]; for (let i = 1; i < n; i++) off[i] = off[i - 1] + (heights[i - 1] + heights[i]) / 2 + gap;
  const blocks = []; for (let i = 0; i < n; i++) { blocks.push({ s: want[i] - off[i], w: 1, n: 1 }); while (blocks.length > 1 && blocks[blocks.length - 2].s > blocks[blocks.length - 1].s) { const b = blocks.pop(), a = blocks.pop(); blocks.push({ s: (a.s * a.w + b.s * b.w) / (a.w + b.w), w: a.w + b.w, n: a.n + b.n }); } }
  const out = []; let i = 0; blocks.forEach((b) => { for (let k = 0; k < b.n; k++, i++) out.push(b.s + off[i]); }); return out;
}
function assignRows(m, gap) {
  const { ids, nodes, links } = m, maxCol = Math.max(0, ...ids.map((i) => nodes[i].col)), cols = Array.from({ length: maxCol + 1 }, () => []);
  ids.forEach((i) => cols[nodes[i].col].push(i)); const adj = {}; ids.forEach((i) => { adj[i] = []; }); links.forEach((l) => { const w = 1 / Math.max(1, nodes[l.to].col - nodes[l.from].col); adj[l.from].push([l.to, w]); adj[l.to].push([l.from, w]); });
  const sized = {}; ids.forEach((i) => { sized[i] = panelSize(nodes[i]); });
  cols.forEach((c) => { let y = 0; c.forEach((i) => { nodes[i].y = y; y += sized[i].h + gap; }); const mid = y / 2; c.forEach((i) => { nodes[i].y -= mid; }); });
  for (let it = 0; it < 14; it++) {
    const seq = it % 2 ? cols : [...cols].reverse();
    seq.forEach((c) => {
      if (!c.length) return; c.forEach((i) => { const a = adj[i], sw = a.reduce((s, x) => s + x[1], 0); nodes[i].want = sw ? a.reduce((s, [o, w]) => s + nodes[o].y * w, 0) / sw : nodes[i].y; });
      if (it < 10) c.sort((p, q) => nodes[p].want - nodes[q].want);
      const ys = placeOrdered(c.map((i) => nodes[i].want), c.map((i) => sized[i].h), gap); c.forEach((i, k) => { nodes[i].y = ys[k]; });
    });
  }
  const all = ids.map((i) => nodes[i]), top = Math.min(...all.map((n) => n.y - sized[n.id].h / 2)), bot = Math.max(...all.map((n) => n.y + sized[n.id].h / 2)), mid = (top + bot) / 2; all.forEach((n) => { n.y -= mid; n.size = sized[n.id]; });
  m.cols = cols; m.height = bot - top;
}
const add = (a, b, k = 1) => [a[0] + b[0] * k, a[1] + b[1] * k, a[2] + b[2] * k]; const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
export function bezierAt(c, t) { const u = 1 - t, a = u * u * u, b = 3 * u * u * t, d = 3 * u * t * t, e = t * t * t; return [0, 1, 2].map((i) => a * c[0][i] + b * c[1][i] + d * c[2][i] + e * c[3][i]); }
export function bezierLength(c, n = 24) { let L = 0, p = c[0]; for (let i = 1; i <= n; i++) { const q = bezierAt(c, i / n); L += dist(p, q); p = q; } return L; }
/** World layout of the whole graph on a gentle arc that faces the viewer, ending in the result plate. In: API-format graph. Out: nodes with pos/yaw/size, links with Bezier control points, length, arrival clock. */
export function layoutGraph(graph, opts = {}) {
  const m = buildModel(graph); if (!m.ids.length) return { ...m, cols: [], bounds: [], arrive: {}, maxArrive: 0, period: 20, floor: -6 };
  assignColumns(m); assignRows(m, opts.gap ?? (Math.max(...m.ids.map((i) => m.nodes[i].col), 0) > 7 ? 1.05 : 0.8));
  const { ids, nodes, links } = m, plate = opts.plate === false ? null : { w: opts.plateW ?? 7.6, h: opts.plateH ?? 6.2 }, colW = m.cols.map((c) => Math.max(...c.map((i) => nodes[i].size.w), 1)), pitchGap = opts.colGap ?? 1.25, colX = []; let x = 0;
  const deep = m.cols.length > 7, weave = deep ? 0.6 : 1; colW.forEach((w, c) => { colX[c] = x + w / 2; x += deep ? w * weave + 0.45 : w + pitchGap; }); const last = colW.length - 1, S = (deep ? x - 0.45 + colW[last] * (1 - weave) : x - pitchGap) + (plate ? plate.w + pitchGap * 1.25 : 0), R = Math.max(14, S / 1.75), shift = plate ? 0.06 : 0;
  const place = (s, y, st = 0) => { const th = (s - S / 2) / R + shift; return { pos: [R * Math.sin(th), y, R * (1 - Math.cos(th)) + st], yaw: -th * 0.9, th }; };
  m.cols.forEach((c, ci) => c.forEach((id, row) => { const n = nodes[id]; if (deep) n.y += ci % 2 ? 2 : -2; const p = place(colX[ci], n.y, (c.length > 1 ? (row % 2 ? -0.55 : 0.55) : 0) + (deep ? (ci % 2 ? -1.9 : 1.9) : 0)); n.pos = p.pos; n.yaw = p.yaw; n.th = p.th; n.axisX = [Math.cos(p.yaw), 0, -Math.sin(p.yaw)]; n.out = [Math.sin(p.th), 0, -Math.cos(p.th)]; }));
  const rowY = (n, i) => n.size.h / 2 - n.size.head - PANEL.rowH * (i + 0.5);
  ids.forEach((id) => { const n = nodes[id]; n.inputs.sort((a, b) => nodes[b.from].y - nodes[a.from].y); n.inputs.forEach((l, i) => { l.y1 = rowY(n, Math.min(i, n.size.rows - 1)); }); Object.keys(n.outs).map(Number).sort((a, b) => a - b).forEach((s, i) => { n.outs[s].y = rowY(n, Math.min(i, n.size.rows - 1)); n.outs[s].row = i; }); });
  links.forEach((l, i) => {
    const A = nodes[l.from], B = nodes[l.to], yA = A.outs[l.slot].y, p0 = add(add(A.pos, A.axisX, A.size.w / 2 + 0.03), [0, yA, 0]), p3 = add(add(B.pos, B.axisX, -B.size.w / 2 - 0.03), [0, l.y1, 0]), span = B.col - A.col, L = Math.max(0.8, dist(p0, p3) * 0.42), bulge = span > 1 ? Math.min(5, 0.95 * span) : 0, wob = ((i % 3) - 1) * 0.14;
    const p1 = add(add(p0, A.axisX, L), A.out, bulge + wob), p2 = add(add(p3, B.axisX, -L), B.out, bulge - wob); l.curve = [p0, p1, p2, p3]; l.len = bezierLength(l.curve); l.span = span;
  });
  /* the clock: a pulse arrives at a node when its longest input chain would, every input reaching it together, so light travels the graph as one wave */
  const arrive = {}, dep = (id, st = new Set()) => { if (arrive[id] != null) return arrive[id]; if (st.has(id)) return 0; st.add(id); let a = 0; nodes[id].inputs.forEach((l) => { a = Math.max(a, dep(l.from, st) + l.len); }); st.delete(id); return (arrive[id] = a); };
  ids.forEach((id) => dep(id)); links.forEach((l) => { l.start = arrive[l.to] - l.len; }); const maxArrive = Math.max(1, ...ids.map((i) => arrive[i]));
  m.arrive = arrive; m.maxArrive = maxArrive; m.period = Math.max(16, Math.min(34, maxArrive * 0.6));
  const bottom = Math.min(...ids.map((i) => nodes[i].y - nodes[i].size.h / 2)), top = Math.max(...ids.map((i) => nodes[i].y + nodes[i].size.h / 2)); m.floor = bottom - 1.5;
  if (plate) { const sinks = ids.filter((i) => !links.some((l) => l.from === i)), save = sinks.find((i) => nodes[i].info.kind === "save") || sinks[0] || ids[ids.length - 1], sn = nodes[save], py = Math.max(m.floor + plate.h / 2 + 0.35, sn.y); const p = place(S - plate.w / 2, py); m.plate = { ...plate, pos: p.pos, yaw: p.yaw * 1.05, th: p.th, save, axisX: [Math.cos(p.yaw * 1.05), 0, -Math.sin(p.yaw * 1.05)] }; }
  m.bounds = []; ids.forEach((id) => { const n = nodes[id], w = n.size.w / 2, h = n.size.h / 2; [-1, 1].forEach((sx) => [-1, 1].forEach((sy) => m.bounds.push(add(add(n.pos, n.axisX, sx * w), [0, sy * h, 0])))); });
  if (m.plate) { const q = m.plate; [-1, 1].forEach((sx) => [-1, 1].forEach((sy) => m.bounds.push(add(add(q.pos, q.axisX, (sx * q.w) / 2), [0, (sy * q.h) / 2, 0])))); }
  m.top = top; return m;
}
/** Camera for a view direction that fits every point, centred. Yaw and pitch in radians, fov vertical in degrees. */
export function fitView(points, yaw, pitch, fov, aspect, margin = 1.08) {
  const d = [Math.sin(yaw) * Math.cos(pitch), Math.sin(pitch), Math.cos(yaw) * Math.cos(pitch)], r = [Math.cos(yaw), 0, -Math.sin(yaw)], u = [d[1] * r[2] - d[2] * r[1], d[2] * r[0] - d[0] * r[2], d[0] * r[1] - d[1] * r[0]];
  const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2], tanV = Math.tan((fov * Math.PI) / 360), tanH = tanV * aspect;
  let c = [0, 0, 0]; points.forEach((p) => { c = add(c, p, 1 / Math.max(1, points.length)); });
  for (let it = 0; it < 4; it++) {
    let lox = 1e9, hix = -1e9, loy = 1e9, hiy = -1e9, dist0 = 0;
    points.forEach((p) => { const q = add(p, c, -1), x = dot(q, r), y = dot(q, u), z = dot(q, d); dist0 = Math.max(dist0, z + Math.abs(x) / tanH, z + Math.abs(y) / tanV); });
    points.forEach((p) => { const q = add(p, c, -1), z = dot(q, d), s = dist0 / (dist0 - z), x = dot(q, r) * s, y = dot(q, u) * s; lox = Math.min(lox, x); hix = Math.max(hix, x); loy = Math.min(loy, y); hiy = Math.max(hiy, y); });
    c = add(add(c, r, (lox + hix) / 2), u, (loy + hiy) / 2); if (it === 3) { const dd = dist0 * margin; return { target: c, position: add(c, d, dd), distance: dd }; }
  }
}
/* ---------- the wave ---------- */
/** Where comets are on a link at this clock, as fractions along it, source to target. */
export function cometsOn(l, clock, period) { const out = [], lo = Math.ceil((clock - (l.start + l.len)) / period), hi = Math.floor((clock - l.start) / period); for (let k = lo; k <= hi; k++) { const u = (clock - k * period - l.start) / l.len; if (u >= 0 && u <= 1) out.push(u); } return out; }
export const pulseAge = (at, clock, period) => { const d = (clock - at) % period; return d < 0 ? d + period : d; };
/* ---------- what lights up ---------- */
/** Direct neighbourhood (hover) or the whole chain feeding and leaving a node (click). */
export function focusSets(m, id, chain = false) {
  const nodes = new Set(id != null ? [id] : []), links = new Set(); if (id == null || !m.nodes[id]) return { nodes, links };
  if (!chain) { m.links.forEach((l) => { if (l.from === id || l.to === id) { links.add(l.id); nodes.add(l.from); nodes.add(l.to); } }); return { nodes, links }; }
  const walk = (start, fwd) => { const st = [start], seen = new Set([start]); while (st.length) { const c = st.pop(); m.links.forEach((l) => { const a = fwd ? l.from : l.to, b = fwd ? l.to : l.from; if (a === c) { links.add(l.id); nodes.add(b); if (!seen.has(b)) { seen.add(b); st.push(b); } } }); } }; walk(id, true); walk(id, false); return { nodes, links };
}
/** The state of each node in a run, from what ComfyUI reported. run = {running:{id:[value,max]}, done:[...], cached:[...], error}. */
export function nodeStates(m, run) { const out = {}; if (!run) return out; m.ids.forEach((id) => { out[id] = "pending"; }); (run.cached || []).forEach((i) => { if (out[i]) out[i] = "cached"; }); (run.done || []).forEach((i) => { if (out[i]) out[i] = "done"; }); Object.keys(run.running || {}).forEach((i) => { if (out[i]) out[i] = "running"; }); if (run.error && out[run.error]) out[run.error] = "error"; return out; }
export function linkState(l, st) { const a = st[l.from], b = st[l.to]; if (b === "running" && (a === "done" || a === "cached" || a === "running")) return "flow"; if (a === "running") return "next"; if ((a === "done" || a === "cached") && b === "pending") return "ready"; if ((b === "done" || b === "cached") && (a === "done" || a === "cached")) return "spent"; if (b === "error") return "ready"; return "idle"; }
/* ---------- replay of a run: a simulation that follows the real order of the graph, its share of the measured total comes from a small table of typical weights, and the page says so ---------- */
const WEIGHT = { sample: 60, decode: 7, load: 3, text: 3, media: 1.2, save: 1.5, latent: 0.5, plan: 0.25, value: 0.12, other: 1 };
export function executionOrder(m) { const left = new Set(m.ids), out = [], done = new Set(); while (left.size) { const ready = [...left].filter((i) => m.nodes[i].inputs.every((l) => done.has(l.from) || !left.has(l.from))).sort((a, b) => m.nodes[a].col - m.nodes[b].col || m.nodes[a].y - m.nodes[b].y || a.localeCompare(b)); const nx = ready[0] ?? [...left][0]; out.push(nx); done.add(nx); left.delete(nx); } return out; }
export function replayPlan(m, totalSeconds = 20) { const order = executionOrder(m), w = order.map((i) => WEIGHT[m.nodes[i].info.kind] ?? 1), sum = w.reduce((a, b) => a + b, 0) || 1; let t = 0; return order.map((id, i) => { const s = (w[i] / sum) * totalSeconds, e = { id, start: t, seconds: s, kind: m.nodes[id].info.kind, steps: m.nodes[id].info.kind === "sample" ? 20 : 0 }; t += s; return e; }); }
/** Run state at a moment of a plan: the same shape the live feed uses. */
export function replayAt(plan, at) { const run = { running: {}, done: [], cached: [], times: {} }; for (const e of plan) { if (at >= e.start + e.seconds) { run.done.push(e.id); run.times[e.id] = e.seconds; } else if (at >= e.start) { run.running[e.id] = e.steps ? [Math.min(e.steps, Math.floor(((at - e.start) / e.seconds) * e.steps) + 1), e.steps] : [0, 0]; break; } else break; } return run; }
/** What the Pro page should ask /api/graph for: always a graph. An empty prompt gets a sample; a missing upload gets a named placeholder the page points out. */
export const PREVIEW_SEED = 11;
export const PLACEHOLDER = { video: "your_clip.mp4", image: "your_picture.png", last_image: "your_last_frame.png" };
export function graphRequest(draft, goal, ideas = {}) {
  if (!draft || !draft.goal) return null; const g = goal || {}, { job, ...body } = draft, typed = String(draft.prompt || "").trim(), sampled = !typed && !g.prompt_optional, fills = [];
  if (sampled) body.prompt = (ideas[draft.goal] || ideas.image || ["a lighthouse on a cliff at dawn"])[0];
  [["needs_video", "video"], ["needs_image", "image"], ["needs_last_image", "last_image"]].forEach(([need, k]) => { if (g[need] && !body[k]) { body[k] = PLACEHOLDER[k]; fills.push(k); } });
  const fixed = body.seed !== "" && body.seed != null; if (!fixed) body.seed = PREVIEW_SEED; return { body, sampled, fills, previewSeed: !fixed };
}
/** First stop for the walk-through: nodes in the order data reaches them, skipping small value nodes. */
export function walkOrder(m) { return Object.values(m.nodes).filter((n) => n.info.kind !== "value").sort((a, b) => (m.arrive[a.id] ?? 0) - (m.arrive[b.id] ?? 0) || b.y - a.y).map((n) => n.id); }
