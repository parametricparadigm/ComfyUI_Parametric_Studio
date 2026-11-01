/* ComfyUniversity: browser labs for the performance and packs tracks. No GPU, no model, no network. Pure functions are exported so a test can compare them with the ComfyUI functions they port. */
import { useEffect, useMemo, useState } from "preact/hooks";
import { html } from "./common.js";

const Slider = ({ label, value, min, max, step = 1, onInput, show }) => html`<label class="cu-ctl"><span>${label} <b>${show != null ? show : value}</b></span><input type="range" min=${min} max=${max} step=${step} value=${value} onInput=${(e) => onInput(+e.target.value)}/></label>`;
const Seg = ({ label, value, opts, onPick }) => html`<div class="cu-ctl"><span>${label}</span><div class="cu-seg" role="group" aria-label=${label}>${opts.map(([k, l]) => html`<button type="button" aria-pressed=${value === k} onClick=${() => onPick(k)}>${l}</button>`)}</div></div>`;
const Read = ({ items }) => html`<dl class="cu-read">${items.map(([k, v, cls]) => html`<div class=${cls || ""}><dt>${k}</dt><dd>${v}</dd></div>`)}</dl>`;

/* ---------- ports. Each names the function it follows, read at ComfyUI v0.43.0 ---------- */
/* comfy/cli_args.py enables_dynamic_vram */
export const enablesDynamicVram = ({ enable = false, disable = false, highvram = false, gpuOnly = false, novram = false, cpu = false }) => enable ? true : !disable && !highvram && !gpuOnly && !novram && !cpu;
/* comfy/ldm/modules/attention.py, the order of the optimized_attention choice, on a card where comfy/model_management.py turns on pytorch attention by default and with no xformers */
export function attentionLine(flag) {
  if (flag === "ck") return "Using Comfy Kitchen attention";
  if (flag === "sage") return "Using sage attention";
  if (flag === "flash") return "Using Flash Attention";
  if (flag === "split") return "Using split optimization for attention";
  if (flag === "quad") return "Using sub quadratic optimization for attention";
  return "Using pytorch attention";
}
/* comfy/model_management.py free_memory, simplified: whole models only, reference counts left out. The sort is most offloaded first, then smallest first. */
export function evictOrder(models, keep, required, total) {
  const live = models.filter((m) => !keep.includes(m.name)); const kept = models.filter((m) => keep.includes(m.name)); const order = [...live].sort((a, b) => (b.off - a.off) || (a.gb - b.gb));
  let on = models.slice(); const gone = [];
  for (const m of order) { const free = total - on.reduce((s, x) => s + x.gb, 0); if (required - free <= 0) break; on = on.filter((x) => x !== m); gone.push(m.name); }
  return { gone, on, kept };
}
/* comfy/model_sampling.py time_snr_shift and flux_time_shift */
export const timeSnrShift = (alpha, t) => alpha === 1 ? t : alpha * t / (1 + (alpha - 1) * t);
export const fluxTimeShift = (mu, sigma, t) => Math.exp(mu) / (Math.exp(mu) + Math.pow(1 / t - 1, sigma));
/* round to m mantissa bits, half to even, ignoring the exponent range */
export function roundMant(x, m) { if (x === 0) return 0; const e = Math.floor(Math.log2(Math.abs(x))); const s = Math.pow(2, e - m); const q = x / s; let r = Math.round(q); if (Math.abs(q - Math.trunc(q)) === .5) r = 2 * Math.round(q / 2); return r * s; }
export function runningSum(n, add, m) { let s = 0; let stall = -1; for (let i = 0; i < n; i++) { const t = roundMant(s + add, m); if (t === s && stall < 0) stall = i; s = t; } return { s, stall }; }

/* ---------- a card of questions, the same small machine for every judgement lab ---------- */
function Cards({ cards, onPass, note }) {
  const [got, setGot] = useState({}); const done = cards.filter((c, i) => got[i] != null && c.opts[got[i]][1]).length;
  useEffect(() => { if (done === cards.length) onPass(); }, [done]);
  return html`${cards.map((c, i) => html`<div class="cu-ctl" key=${i}><p class="cu-q-line">${c.q}</p>${c.code && html`<pre class="cu-play-note"><code>${c.code}</code></pre>`}<div class="cu-seg cu-seg-long" role="group" aria-label=${c.q}>${c.opts.map((o, k) => html`<button type="button" aria-pressed=${got[i] === k} onClick=${() => setGot({ ...got, [i]: k })}>${o[0]}</button>`)}</div>${got[i] != null && html`<p class=${c.opts[got[i]][1] ? "cu-why" : "cu-why no"}>${c.opts[got[i]][2]}</p>`}</div>`)}<${Read} items=${[["Right so far", `${done} of ${cards.length}`, done === cards.length ? "good" : ""]]}/>${note && html`<p class="cu-play-note">${note}</p>`}`;
}

/* ---------- console ---------- */
const CONSOLE = [
  { q: "This line was printed just before the model ran. How much of the model went to the card?", code: "loaded partially; 5120.00 MB usable, 4890.31 MB loaded, 2377.42 MB offloaded, 128.00 MB buffer reserved, lowvram patches: 0", opts: [["All of it", false, "No. Partially means some weights stayed off the card."], ["About two thirds", true, "4890 MB on the card and 2377 MB offloaded. Expect slower steps, not an error."], ["None", false, "4890 MB is on the card."]] },
  { q: "These three lines came from a first run. You queue the same model again. Which line tells you the second run did not load it again?", code: "A: got prompt\nB: Requested to load SDXL\nC: Prompt executed in 3.91 seconds", opts: [["A", false, "Every queue prints this. It only means the server took the job."], ["B", false, "This is printed when a model is not already in the list of loaded models."], ["None of them: on the second run B is simply missing", true, "Right. The console shows a reload by printing it, and shows no reload by saying nothing."]] },
  { q: "Your run sat at 0 of 20 for a long time, then printed this. What does it tell you?", code: "  5%|▌         | 1/20 [00:41<13:02, 41.20s/it]", opts: [["It is 41 seconds per step, so 13 minutes remain", true, "That is what tqdm's estimate says. If the first step included loading, the real rate will be better: wait for step 3."], ["It has crashed", false, "A crash prints a traceback."], ["It runs 41 steps per second", false, "s/it is seconds per step. Fast runs show it/s instead."]] },
  { q: "What should you read first here?", code: "!!! Exception during processing !!! CUDA out of memory.\nTraceback (most recent call last):\n  ...\nGot an OOM, unloading all loaded models.\nPrompt executed in 12.40 seconds", opts: [["The last line: it finished", false, "That line is printed for failed jobs as well. It tells you nothing about success."], ["The first line, then the memory summary above the OOM line", true, "The first line names the error. On an out-of-memory error ComfyUI also logs a memory summary."], ["Only the traceback's last frame", false, "The first line already says what failed."]] },
];
function ConsoleRead({ onPass }) { return html`<${Cards} cards=${CONSOLE} onPass=${onPass} note="The wording comes from ComfyUI v0.43.0's log calls. The numbers are examples, except where the lesson says otherwise."/>`; }

/* ---------- flags ---------- */
function Flags({ onPass }) {
  const [vram, setVram] = useState("none"); const [dyn, setDyn] = useState("none"); const [attn, setAttn] = useState("none"); const [cache, setCache] = useState("ram"); const [res, setRes] = useState(0);
  const dynamic = enablesDynamicVram({ enable: dyn === "on", disable: dyn === "off", highvram: vram === "highvram", gpuOnly: vram === "gpu-only", novram: vram === "novram", cpu: vram === "cpu" });
  const cmd = ["python main.py", vram !== "none" && "--" + vram, dyn === "on" && "--enable-dynamic-vram", dyn === "off" && "--disable-dynamic-vram", attn === "split" && "--use-split-cross-attention", attn === "quad" && "--use-quad-cross-attention", attn === "pytorch" && "--use-pytorch-cross-attention", attn === "sage" && "--use-sage-attention", attn === "flash" && "--use-flash-attention", attn === "ck" && "--use-ck-attention", cache === "classic" && "--cache-classic", cache === "lru" && "--cache-lru 8", cache === "none" && "--cache-none", res > 0 && "--reserve-vram " + res].filter(Boolean).join(" ");
  const ok = dynamic && res === 4 && cache === "none"; useEffect(() => { if (ok) onPass(); }, [ok]);
  return html`<div class="cu-ctlrow"><${Seg} label="VRAM mode" value=${vram} opts=${[["none", "no flag"], ["lowvram", "lowvram"], ["novram", "novram"], ["highvram", "highvram"], ["gpu-only", "gpu-only"], ["cpu", "cpu"]]} onPick=${setVram}/><${Seg} label="Dynamic VRAM flag" value=${dyn} opts=${[["none", "no flag"], ["on", "enable"], ["off", "disable"]]} onPick=${setDyn}/><${Seg} label="Attention" value=${attn} opts=${[["none", "no flag"], ["pytorch", "pytorch"], ["split", "split"], ["quad", "quad"], ["sage", "sage"], ["flash", "flash"], ["ck", "ck"]]} onPick=${setAttn}/><${Seg} label="Node cache" value=${cache} opts=${[["ram", "RAM pressure"], ["classic", "classic"], ["lru", "LRU 8"], ["none", "none"]]} onPick=${setCache}/><${Slider} label="--reserve-vram" value=${res} min=${0} max=${8} show=${res ? res + " GB" : "not set"} onInput=${setRes}/></div>
    <pre class="cu-play-note"><code>${cmd}</code></pre>
    <${Read} items=${[["enables_dynamic_vram()", dynamic ? "True" : "False", dynamic ? "good" : ""], ["Attention line you would see", attentionLine(attn)], ["Node cache", cache === "ram" ? "Using RAM pressure cache." : cache === "lru" ? "Using LRU cache" : cache === "none" ? "Disabling intermediate node cache." : "classic, no line printed"], ["Reserved for other programs", res ? res + " GB" : "the default: 400 MB on Linux, 600 MB or more on Windows"]]}/>
    <p class="cu-play-note">Dynamic VRAM also needs a supported card and PyTorch: main.py checks that after this function. The attention line assumes an NVIDIA card with no xformers, and that the library behind a flag is installed.</p>`;
}

/* ---------- evict ---------- */
function Evict({ onPass }) {
  const [card, setCard] = useState(24); const [next, setNext] = useState(12); const [te, setTe] = useState(5); const [vae, setVae] = useState(.5); const [work, setWork] = useState(6);
  const req = next * 1.1 + Math.max(.8 + .39, work + .39); const r = evictOrder([{ name: "text encoder", gb: te, off: 0 }, { name: "VAE", gb: vae, off: 0 }], [], req, card); const left = card - r.on.reduce((s, m) => s + m.gb, 0); const fits = left >= next;
  const ok = fits && r.gone.length === 1; useEffect(() => { if (ok) onPass(); }, [ok]);
  return html`<div class="cu-ctlrow"><${Slider} label="Your card" value=${card} min=${6} max=${48} show=${card + " GB"} onInput=${setCard}/><${Slider} label="Model to load next" value=${next} min=${1} max=${40} show=${next + " GB"} onInput=${setNext}/><${Slider} label="Working memory the sampler asks for" value=${work} min=${0} max=${16} step=${.5} show=${work + " GB"} onInput=${setWork}/><${Slider} label="Text encoder on the card" value=${te} min=${0} max=${16} show=${te + " GB"} onInput=${setTe}/><${Slider} label="VAE on the card" value=${vae} min=${0} max=${4} step=${.25} show=${vae + " GB"} onInput=${setVae}/></div>
    <${Read} items=${[["Room asked for", `${next} × 1.1 + ${Math.max(1.19, work + .39).toFixed(2)} = ${req.toFixed(2)} GB`], ["Unloaded, in order", r.gone.length ? r.gone.join(", ") : "nothing"], ["Free after that", `${left.toFixed(2)} GB`], [fits ? "The model" : "The model loads partly", fits ? "fits whole" : `${Math.max(0, left).toFixed(2)} of ${next} GB on the card`, fits ? "good" : "bad"]]}/>
    <p class="cu-play-note">A simplified copy of free_memory, without dynamic VRAM. It unloads whole models, smallest first, and stops as soon as there is room. Real runs also weigh reference counts and partly offloaded models.</p>`;
}

/* ---------- attention memory ---------- */
function AttnMem({ onPass }) {
  const [px, setPx] = useState(1024); const [patch, setPatch] = useState(1); const [bytes, setBytes] = useState(2); const [steps, setSteps] = useState(1); const [batch, setBatch] = useState(2); const [heads, setHeads] = useState(8);
  const side = px / 8 / patch; const n = side * side; const full = n * n * batch * heads * bytes; const slice = full / steps; const gb = (x) => (x / 2 ** 30).toFixed(2) + " GB"; const ok = px >= 1024 && patch === 1 && slice < 2 ** 30 * 2 && steps > 1; useEffect(() => { if (ok) onPass(); }, [ok]);
  return html`<div class="cu-ctlrow"><${Slider} label="Image side" value=${px} min=${256} max=${2048} step=${64} show=${px + " px"} onInput=${setPx}/><${Seg} label="Tokens per side of latent" value=${patch} opts=${[[1, "every cell"], [2, "2 × 2 patches"], [4, "1/4 scale"]]} onPick=${setPatch}/><${Seg} label="Number size" value=${bytes} opts=${[[2, "fp16"], [4, "fp32"]]} onPick=${setBytes}/><${Slider} label="Batch rows (CFG makes 2)" value=${batch} min=${1} max=${8} onInput=${setBatch}/><${Slider} label="Heads" value=${heads} min=${1} max=${16} onInput=${setHeads}/><${Seg} label="Slices of queries" value=${steps} opts=${[[1, "1"], [2, "2"], [4, "4"], [8, "8"], [16, "16"], [64, "64"]]} onPick=${setSteps}/></div>
    <${Read} items=${[["Tokens", n.toLocaleString("en")], ["Whole score matrix", gb(full), full > 2 ** 34 ? "bad" : ""], ["Largest piece with slicing", gb(slice), slice < 2 ** 31 ? "good" : ""]]}/>
    <p class="cu-play-note">Only the score matrix is counted. Tokens grow with the square of the image side, and the matrix with the square of tokens. Slicing the queries divides the memory and leaves the arithmetic the same, as attention_split does.</p>`;
}

/* ---------- accumulation ---------- */
function Accum({ onPass }) {
  const [m, setM] = useState(10); const [add, setAdd] = useState(-3); const [n, setN] = useState(2); const a = Math.pow(10, add); const N = Math.pow(10, n); const r = useMemo(() => runningSum(N, a, m), [N, a, m]); const truth = N * a; const err = Math.abs(r.s - truth) / truth;
  const ok = m === 10 && r.stall > 0 && err > .5; useEffect(() => { if (ok) onPass(); }, [ok]);
  return html`<div class="cu-ctlrow"><${Seg} label="Mantissa bits" value=${m} opts=${[[3, "fp8 e4m3 (3)"], [7, "bf16 (7)"], [10, "fp16 (10)"], [23, "fp32 (23)"]]} onPick=${setM}/><${Slider} label="Each number added" value=${add} min=${-6} max=${-1} show=${a.toExponential(0)} onInput=${setAdd}/><${Slider} label="How many" value=${n} min=${2} max=${5} show=${N.toLocaleString("en")} onInput=${setN}/></div>
    <${Read} items=${[["True sum", truth.toPrecision(4)], ["Running sum in this format", r.s.toPrecision(4)], ["Error", (err * 100).toFixed(2) + "%", err > .01 ? "bad" : "good"], ["The sum stopped moving", r.stall < 0 ? "never" : `at number ${r.stall.toLocaleString("en")}, at ${r.s.toPrecision(3)}`]]}/>
    <p class="cu-play-note">A plain loop: add, round, repeat. Once half the spacing between representable numbers is larger than what you add, the sum never moves again. Exponent range is ignored here.</p>`;
}

/* ---------- where the time goes ---------- */
function Amdahl({ onPass }) {
  const [part, setPart] = useState("sampler"); const [x, setX] = useState(1); const base = { load: 40, text: 2, sampler: 60, decode: 8 }; const t = { ...base, [part]: base[part] / x }; const before = Object.values(base).reduce((a, b) => a + b, 0); const after = Object.values(t).reduce((a, b) => a + b, 0); const firstRun = after; const again = after - t.load - t.text;
  const [sped, setSped] = useState(false); useEffect(() => { if (part === "sampler" && x >= 2 && x <= 4) setSped(true); }, [part, x]); const ok = sped && part === "text" && x >= 2; useEffect(() => { if (ok) onPass(); }, [ok]); const sec = (v) => v.toFixed(v < 1 ? 1 : 0);
  return html`<div class="cu-ctlrow"><${Seg} label="Speed up this part" value=${part} opts=${[["load", "loading"], ["text", "text encoding"], ["sampler", "sampling"], ["decode", "VAE decode"]]} onPick=${setPart}/><${Slider} label="By how much" value=${x} min=${1} max=${10} step=${.5} show=${x === 1 ? "no change" : x + " times"} onInput=${setX}/></div>
    <div class="cu-vram" role="img" aria-label=${`${after.toFixed(0)} seconds in total`}><i class="w" style=${{ flexGrow: t.load }}><b>${sec(t.load)}</b></i><i class="t" style=${{ flexGrow: t.text }}><b>${sec(t.text)}</b></i><i class="l" style=${{ flexGrow: t.sampler }}><b>${sec(t.sampler)}</b></i><i class="r" style=${{ flexGrow: t.decode }}><b>${sec(t.decode)}</b></i></div>
    <ul class="cu-amdahl-key"><li><i style="background:#f5c518"></i>loading</li><li><i style="background:#5a9bf0"></i>text encoding</li><li><i style="background:#e8703f"></i>sampling</li><li><i style="background:#888"></i>VAE decode</li></ul>
    <${Read} items=${[["First run", `${firstRun.toFixed(1)} s, was ${before} s`], ["Saved", `${(100 * (1 - after / before)).toFixed(0)}%`], ["Same prompt again (loader and text cached)", `${again.toFixed(1)} s, was ${before - base.load - base.text} s`]]}/>
    <p class="cu-play-note">The four numbers are made up for the exercise. Your own come from the console. Compare a tenfold speed-up of text encoding with a twofold speed-up of sampling.</p>`;
}

/* ---------- same name, different maths ---------- */
function SameName({ onPass }) {
  const [alpha, setAlpha] = useState(3); const [mu, setMu] = useState(3); const [sigma] = useState(1); const [core, setCore] = useState(5); const [pack, setPack] = useState(5);
  const ts = [.1, .25, .5, .75, .9]; const gap = Math.max(...ts.map((t) => Math.abs(timeSnrShift(alpha, t) - fluxTimeShift(mu, sigma, t)))); const shiftOk = gap < .01; const nagOk = Math.abs(core - (pack + 1)) < 1e-9 && core !== pack; const ok = shiftOk && nagOk && alpha > 1.5; useEffect(() => { if (ok) onPass(); }, [ok]);
  return html`<div class="cu-ctlrow"><${Slider} label="SD3-style shift (time_snr_shift)" value=${alpha} min=${1} max=${8} step=${.5} onInput=${setAlpha}/><${Slider} label="Flux-style μ (flux_time_shift)" value=${mu} min=${0} max=${4} step=${.01} show=${mu.toFixed(2)} onInput=${setMu}/></div>
    <${Read} items=${[["At t = 0.5", `${timeSnrShift(alpha, .5).toFixed(3)} and ${fluxTimeShift(mu, sigma, .5).toFixed(3)}`], ["Biggest gap across the schedule", gap.toFixed(3), shiftOk ? "good" : "bad"], ["ln of the shift", Math.log(alpha).toFixed(2)]]}/>
    <div class="cu-ctlrow"><${Slider} label="φ in z₊φ − z₋(φ−1) (core NAG)" value=${core} min=${1} max=${12} onInput=${setCore}/><${Slider} label="φ in z₊ + φ(z₊−z₋) (one pack's NAG)" value=${pack} min=${0} max=${12} onInput=${setPack}/></div>
    <${Read} items=${[["Weight on (z₊−z₋), core", core - 1], ["Weight on (z₊−z₋), pack", pack], ["Same strength?", nagOk ? "yes" : "no", nagOk ? "good" : "bad"]]}/>
    <p class="cu-play-note">Both shift curves are read from comfy/model_sampling.py, with σ = 1 in the Flux one. The first NAG line is core's nodes_nag.py and the second is sd-perturbed-attention's nag_nodes.py. Neither is wrong: they count from different places.</p>`;
}

/* ---------- scan ---------- */
const SCAN = [
  { q: "A scan flags this line for dynamic code. Real worry?", code: "preview = base64.b64decode(image_field)", opts: [["False alarm, probably", true, "Decoding a picture is ordinary. Check that the result goes to an image decoder, not to exec."], ["Real worry", false, "Nothing here runs. A decode alone is not execution."]] },
  { q: "A scan flags this for install commands. Real worry?", code: 'raise ImportError("Missing onnx: run pip install onnx")', opts: [["Real worry", false, "The word pip is inside a string that is only shown."], ["False alarm", true, "It is a message for a human. Nothing runs pip."]] },
  { q: "A scan flags this for paid services. Real worry?", code: 'x = F.pad(x, (1, 1), mode="replicate")', opts: [["False alarm", true, "replicate is a padding mode here, not a company."], ["Real worry", false, "No network, no key, no service."]] },
  { q: "A scan flags this for install commands, at the top of __init__.py. Real worry?", code: 'subprocess.run([sys.executable, "-m", "pip", "install", "-U", "numpy"])', opts: [["False alarm", false, "It is indented nowhere: it runs every time ComfyUI starts, and it can move versions other packs depend on."], ["Real worry", true, "Top level means it runs at import, on every start."]] },
  { q: "This file scanned clean. What can you conclude?", code: 'f = getattr(__builtins__, "ev" + "al")\nf(request.query["x"])', opts: [["It is safe", false, "A text match looks for eval( and this has no such text. A clean scan means no pattern matched."], ["Nothing: this is the kind of line scans miss", true, "It joins the name at run time, so the word never appears. A human or a stricter parser has to catch it."]] },
];
function ScanRead({ onPass }) { return html`<${Cards} cards=${SCAN} onPass=${onPass} note="We wrote these lines for this lab. They are not from any real pack."/>`; }

/* ---------- licences ---------- */
const LIC = [
  { q: "You changed an AGPL-3.0 pack and run it on a website strangers use. You give nobody a copy of the code files. What does section 13 ask?", opts: [["Nothing, no copy left your server", false, "That is GPL-3.0's rule, not AGPL's."], ["Offer those users your modified source", true, "Section 13: your modified version must prominently offer all users interacting with it remotely the Corresponding Source."]] },
  { q: "The same thing, but the pack is GPL-3.0.", opts: [["Offer those users your source", false, "GPL-3.0 section 0: mere interaction with a user through a network, with no transfer of a copy, is not conveying."], ["GPL's source duty is not triggered by that alone", true, "The duty attaches to conveying. Remote use alone is not conveying."]] },
  { q: "You send your modified GPL-3.0 pack to a friend.", opts: [["Pass on the source and keep the licence", true, "That is conveying. Section 5 asks for notices that you modified it and for the whole work to stay under this licence, and section 6 asks for the source."], ["Nothing applies between friends", false, "The licence has no such exception."]] },
  { q: "You copy an MIT pack's function into your own closed-source tool.", opts: [["You must publish your tool", false, "MIT has no such condition."], ["Keep the copyright and permission notice", true, "That is MIT's one condition, for all copies or substantial portions."]] },
  { q: "A model is under CreativeML OpenRAIL-M. Is every use allowed?", opts: [["No: Attachment A lists banned uses, and they pass down", true, "Paragraph 5 and Attachment A set use restrictions, and paragraph 4 makes you pass them on to anyone you give it to."], ["Yes, it says open", false, "Open here does not mean unrestricted use."]] },
];
function LicRead({ onPass }) { return html`<${Cards} cards=${LIC} onPass=${onPass} note="Each answer is what the licence text says, read by us. It is not legal advice."/>`; }

/* ---------- which files run code ---------- */
const LOADS = [
  { q: "ComfyUI's load_torch_file gets model.safetensors.", opts: [["Header and raw tensors, no pickle", true, "It goes down the safetensors branch. There is no unpickler in that path."], ["It unpickles the file", false, "Only the other branch uses torch.load."]] },
  { q: "ComfyUI's load_torch_file gets model.ckpt.", opts: [["torch.load with no limits", false, "Not in this version. Older versions and packs may differ."], ["torch.load with weights_only=True", true, "Read in comfy/utils.py at v0.43.0. A file that needs other classes is refused."]] },
  { q: "A pack calls pickle.load(open(path, 'rb')) on a file you downloaded.", opts: [["The file can run code", true, "The Python docs say so plainly. Nothing limits it."], ["It is fine, it ends in .pt", false, "The name of a file changes nothing."]] },
  { q: "A pack calls torch.load(path, weights_only=False).", opts: [["It is safe, it is torch", false, "With False, torch.load uses the full unpickler."], ["The file can run code", true, "That turns the limit off. Search packs for this exact string."]] },
  { q: "A loader passes trust_remote_code=True to a downloader.", opts: [["It runs Python from the model's repo", true, "That is what the option is for. Read that code, or say no."], ["It only checks a signature", false, "It does not check anything: it runs code."]] },
];
function LoadRead({ onPass }) { return html`<${Cards} cards=${LOADS} onPass=${onPass}/>`; }

/* ---------- core or pack ---------- */
const PICK = [
  { q: "You want perturbed-attention guidance on an image model.", opts: [["Install a guidance pack first", false, "A pack may add options, but you have no reason yet."], ["Core PerturbedAttentionGuidance", true, "Core has it. Start there."]] },
  { q: "You want a labelled grid across several settings, with video cells. Core has ImageGrid and ImageCompare.", opts: [["Read a sweep pack, then test it in a sandbox", true, "ImageGrid has no labels and no sweeps, so core stops short here. That is a real gap."], ["Core already does this", false, "ImageGrid takes images, columns and sizes. It has no axes."]] },
  { q: "You want a step cache on a model, and have not tried one yet.", opts: [["A pack's speed claim is enough to install it", false, "An author's number is a claim until you measure it on your graph."], ["Core EasyCache, and measure", true, "Core has EasyCache and LazyCache. Try them with a timer first."]] },
  { q: "Two packs do the same thing. One is a fork with no named fix.", opts: [["Use the original", true, "A copy needs a reason. Name the fix or use the source of it."], ["Use whichever has more stars", false, "Stars say little, and new packs for new models have few."]] },
  { q: "A pack does what you want, but pips at import and replaces a sampler for every job.", opts: [["Install it, it works", false, "Those side effects reach every other job on your server."], ["Take the idea, write your own or find another", true, "An idea is free to reuse in your own words. The side effects are not."]] },
];
function PickRead({ onPass }) { return html`<${Cards} cards=${PICK} onPass=${onPass}/>`; }

/* ---------- a safe install, in order ---------- */
const STEPS = ["Read the entry files as text, without running them", "pip install --dry-run with your constraints file", "Compare the report with the packages you protect", "Install into a separate test environment", "Start a sandbox with no outside network and read-only models", "Run a no-model graph, then a real one", "Copy to the live install, and write down the version"];
function Install({ onPass }) {
  const [done, setDone] = useState([]); const order = useMemo(() => [4, 1, 6, 2, 0, 5, 3], []); const ok = done.length === STEPS.length && done.every((k, i) => k === i); useEffect(() => { if (ok) onPass(); }, [ok]);
  const tap = (k) => setDone(done.includes(k) ? done.filter((x) => x !== k) : [...done, k]);
  return html`<div class="cu-seg cu-seg-stack" role="group" aria-label="Steps">${order.map((k) => html`<button type="button" aria-pressed=${done.includes(k)} onClick=${() => tap(k)}>${done.includes(k) ? done.indexOf(k) + 1 + ". " : ""}${STEPS[k]}</button>`)}</div><${Read} items=${[["In the right place", `${done.filter((k, i) => k === i).length} of ${STEPS.length}`, ok ? "good" : ""]]}/><p class="cu-play-note">Tap the steps in the order you would do them. Tap one again to take it back.</p>`;
}

export const MORE = {
  console: { title: "Read the console", task: "Answer every card from what the line really says.", C: ConsoleRead },
  flags: { title: "Build a launch line", task: "Leave 4 GB for another program, keep dynamic VRAM on, and turn the node cache off.", C: Flags, after: "--reserve-vram sets the room, and --cache-none costs you every cached result. No VRAM flag was needed." },
  evict: { title: "Who gets unloaded", task: "Set a case where exactly one model is unloaded and the next model still fits whole.", C: Evict, after: "Unloading stops as soon as there is room. That is why the other model is still there on the next run." },
  attnmem: { title: "The memory of an attention matrix", task: "At 1024 px or more, with a token for every latent cell, slice the queries until the largest piece is under 2 GB.", C: AttnMem, after: "Same sums, same answer, less held at once. It costs more passes." },
  accum: { title: "When a running sum stops", task: "In fp16, find a small number and a count where the sum stalls and the error passes 50%.", C: Accum, after: "Try fp32 with the same numbers. This is why training keeps its sums in a wider format." },
  amdahl: { title: "Speed up the part that matters", task: "Speed up sampling by two to four times, then switch to text encoding at the same setting and see what that effort would have saved.", C: Amdahl, after: "Measure first, then work on the biggest number." },
  samename: { title: "Same name, different maths", task: "Line the two shift curves up with a shift above 1.5, then give both NAG sliders the same real strength.", C: SameName, after: "μ is the logarithm of the shift. Core's NAG φ is one higher than that pack's for the same strength." },
  scan: { title: "Judge a scan hit", task: "Decide what each hit means.", C: ScanRead },
  licence: { title: "What does the licence ask", task: "Answer each case from the licence text.", C: LicRead },
  loadfile: { title: "Which files can run code", task: "Say what each loader does with the file.", C: LoadRead },
  pick: { title: "Core, pack, or just the idea", task: "Decide each case.", C: PickRead },
  install: { title: "Install without breaking anything", task: "Put the seven steps in a safe order.", C: Install },
};
