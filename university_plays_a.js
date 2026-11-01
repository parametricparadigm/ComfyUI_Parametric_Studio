/* ComfyUniversity: browser labs for the first-graph track. No GPU, no model, no network. Pure functions are exported so a test can compare them with what they port. */
import { useEffect, useMemo, useState } from "preact/hooks";
import { html } from "./common.js";

const Slider = ({ label, value, min, max, step = 1, onInput, show }) => html`<label class="cu-ctl"><span>${label} <b>${show != null ? show : value}</b></span><input type="range" min=${min} max=${max} step=${step} value=${value} onInput=${(e) => onInput(+e.target.value)}/></label>`;
const Seg = ({ label, value, opts, onPick }) => html`<div class="cu-ctl"><span>${label}</span><div class="cu-seg" role="group" aria-label=${label}>${opts.map(([k, l]) => html`<button type="button" aria-pressed=${value === k} onClick=${() => onPick(k)}>${l}</button>`)}</div></div>`;
const Read = ({ items }) => html`<dl class="cu-read">${items.map(([k, v, cls]) => html`<div class=${cls || ""}><dt>${k}</dt><dd>${v}</dd></div>`)}</dl>`;
const Check = ({ items }) => html`<ul class="cu-errs">${items.map(([t, done]) => html`<li class=${done ? "cu-pass" : "cu-wait"}>${done ? "✓ " : "○ "}${t}</li>`)}</ul>`;

/* ---------- a seeded generator, ours and not PyTorch's ---------- */
export function rng(seed) {
  let a = (seed >>> 0) + 0x6d2b79f5; const u = () => { a = (a + 0x6d2b79f5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  return { u, n: () => Math.sqrt(-2 * Math.log(Math.max(u(), 1e-12))) * Math.cos(2 * Math.PI * u()) };
}

/* ---------- CU-101: copy, underfit, fit ---------- */
const TRUTH = { w: [.3, .7], m: [-2, 1.5], s: [.3, .5] };
const drawTruth = (r) => { const k = r.u() < TRUTH.w[0] ? 0 : 1; return TRUTH.m[k] + TRUTH.s[k] * r.n(); };
const pdf = (x, m, s) => Math.exp(-.5 * ((x - m) / s) ** 2) / (s * Math.sqrt(2 * Math.PI));
export function emFit(xs, it = 40) {
  let w = [.5, .5], m = [-1, 1], s = [1, 1];
  for (let t = 0; t < it; t++) {
    const n = [0, 0], a = [0, 0], b = [0, 0]; const rs = xs.map((x) => { const p0 = w[0] * pdf(x, m[0], s[0]), p1 = w[1] * pdf(x, m[1], s[1]); return p0 / (p0 + p1 + 1e-300); });
    xs.forEach((x, i) => { const r = [rs[i], 1 - rs[i]]; for (const k of [0, 1]) { n[k] += r[k]; a[k] += r[k] * x; } });
    m = [a[0] / n[0], a[1] / n[1]]; xs.forEach((x, i) => { const r = [rs[i], 1 - rs[i]]; for (const k of [0, 1]) b[k] += r[k] * (x - m[k]) ** 2; });
    s = [Math.sqrt(b[0] / n[0]), Math.sqrt(b[1] / n[1])]; w = [n[0] / xs.length, n[1] / xs.length];
  }
  return { w, m, s };
}
export function fitModels(n = 1000, seed = 1) {
  const r = rng(seed); const train = Array.from({ length: n }, () => drawTruth(r)); const seen = new Set(train);
  const mean = train.reduce((a, b) => a + b, 0) / n; const std = Math.sqrt(train.reduce((a, b) => a + (b - mean) ** 2, 0) / (n - 1)); const f = emFit(train); const q = rng(seed + 1);
  const samples = { copier: Array.from({ length: n }, () => train[Math.floor(q.u() * n)]), gauss: Array.from({ length: n }, () => mean + std * q.n()), mix: Array.from({ length: n }, () => { const k = q.u() < f.w[0] ? 0 : 1; return f.m[k] + f.s[k] * q.n(); }) };
  const inGap = (a) => a.filter((x) => x > -1 && x < .5).length / a.length; const isNew = (a) => a.filter((x) => !seen.has(x)).length / a.length;
  return { train, samples, gapTrain: inGap(train), rows: { copier: { numbers: n, fresh: isNew(samples.copier), gap: inGap(samples.copier) }, gauss: { numbers: 2, fresh: isNew(samples.gauss), gap: inGap(samples.gauss) }, mix: { numbers: 5, fresh: isNew(samples.mix), gap: inGap(samples.mix) } } };
}
function hist(a, lo = -4, hi = 4, bins = 48) { const c = new Array(bins).fill(0); for (const x of a) { const i = Math.floor((x - lo) / (hi - lo) * bins); if (i >= 0 && i < bins) c[i]++; } return c; }
function FitGap({ onPass }) {
  const d = useMemo(() => fitModels(), []); const [k, setK] = useState("copier"); const [seen, setSeen] = useState({ copier: true }); const pick = (v) => { setK(v); setSeen({ ...seen, [v]: true }); };
  const ok = seen.copier && seen.gauss && k === "mix"; useEffect(() => { if (ok) onPass(); }, [ok]);
  const a = hist(d.train), b = hist(d.samples[k]); const top = Math.max(...a, ...b, 1); const W = 640, H = 200, bw = W / a.length; const r = d.rows[k];
  return html`<div class="cu-ctlrow"><${Seg} label="Model" value=${k} opts=${[["copier", "The copier"], ["gauss", "One Gaussian"], ["mix", "A two-part mixture"]]} onPick=${pick}/></div>
    <svg class="cu-chart" viewBox=${`0 0 ${W} ${H}`} role="img" aria-label=${"Histogram of the training data against samples from " + k}>${a.map((v, i) => html`<rect key=${"a" + i} x=${i * bw} y=${H - v / top * (H - 8)} width=${bw - 1} height=${v / top * (H - 8)} fill="#5a9bf0" opacity=".55"/>`)}${b.map((v, i) => html`<rect key=${"b" + i} x=${i * bw + bw * .25} y=${H - v / top * (H - 8)} width=${bw * .5} height=${v / top * (H - 8)} fill="#f5c518"/>`)}<rect x=${(-1 + 4) / 8 * W} y="0" width=${1.5 / 8 * W} height=${H} fill="#fff" opacity=".06"/></svg>
    <${Read} items=${[["Numbers it stores", r.numbers], ["Samples that are new", (r.fresh * 100).toFixed(0) + "%", r.fresh > .9 ? "good" : "bad"], ["Samples in the empty gap", (r.gap * 100).toFixed(1) + "%", r.gap < .05 ? "good" : "bad"], ["Training data in that gap", (d.gapTrain * 100).toFixed(1) + "%"]]}/>
    <p class="cu-play-note">Blue is the training data, gold is what the model draws, and the pale band is the gap between the humps. Our own generator and a new fit in your browser, so the numbers differ a little from the lab below.</p>`;
}

/* ---------- CU-105: what a seed fixes ---------- */
const S_MAX = 14.6146, S_MIN = .0292;
export function sigmasExp(steps) { const out = []; for (let i = 0; i < steps; i++) out.push(Math.exp(Math.log(S_MAX) + (Math.log(S_MIN) - Math.log(S_MAX)) * i / (steps - 1))); out.push(0); return out; }
export function denoise1d(x, s) { const v = .25, m = [-2, 2]; const w = m.map((u) => Math.exp(-.5 * (x - u) ** 2 / (v + s * s))); const t = w[0] + w[1] + 1e-300; return (w[0] * (m[0] * s * s + x * v) + w[1] * (m[1] * s * s + x * v)) / (t * (v + s * s)); }
/* get_ancestral_step in comfy/k_diffusion/sampling.py, with eta 1. */
export const ancestralStep = (a, b) => { const up = Math.min(b, Math.sqrt(b * b * (a * a - b * b) / (a * a))); return [Math.sqrt(b * b - up * up), up]; };
export function walk(kind, seed, steps) {
  const sig = sigmasExp(steps); const eps = rng(seed).n(); const extra = rng(seed + 1); let x = eps * Math.sqrt(1 + sig[0] * sig[0]); const path = [x];
  for (let i = 0; i < steps; i++) {
    const a = sig[i], b = sig[i + 1], d = (x - denoise1d(x, a)) / a;
    if (kind === "euler" || b === 0) x = x + d * (b - a);
    else { const [down, up] = ancestralStep(a, b); x = x + d * (down - a) + extra.n() * up; }
    path.push(x);
  }
  return path;
}
export function sameBlob(kind, steps, n = 300) { let same = 0; for (let s = 0; s < n; s++) { const a = walk(kind, s, steps), b = walk(kind, s, 80); if (a[a.length - 1] * b[b.length - 1] > 0) same++; } return same / n; }
function SeedWalk({ onPass }) {
  const [kind, setKind] = useState("euler"); const [steps, setSteps] = useState(20); const [seed, setSeed] = useState(7); const [seen, setSeen] = useState({});
  const a = useMemo(() => walk(kind, seed, 80), [kind, seed]); const b = useMemo(() => walk(kind, seed, steps), [kind, seed, steps]); const share = useMemo(() => sameBlob(kind, steps), [kind, steps]);
  useEffect(() => { if (steps <= 20) setSeen((v) => v[kind] ? v : { ...v, [kind]: true }); }, [kind, steps]); const ok = seen.euler && seen.ancestral && steps <= 20; useEffect(() => { if (ok) onPass(); }, [ok]);
  const W = 640, H = 220, y = (v) => H / 2 - Math.max(-7, Math.min(7, v)) / 7 * (H / 2 - 6); const line = (p) => p.map((v, i) => `${(i / (p.length - 1) * W).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  return html`<div class="cu-ctlrow"><${Seg} label="Sampler" value=${kind} opts=${[["euler", "euler"], ["ancestral", "euler ancestral"]]} onPick=${setKind}/><${Slider} label="Steps" value=${steps} min=${4} max=${40} onInput=${setSteps}/><${Slider} label="Seed" value=${seed} min=${0} max=${99} onInput=${setSeed}/></div>
    <svg class="cu-chart" viewBox=${`0 0 ${W} ${H}`} role="img" aria-label=${`Two runs from seed ${seed}: 80 steps and ${steps} steps`}><line x1="0" x2=${W} y1=${y(2)} y2=${y(2)} stroke="#2bb886" opacity=".5"/><line x1="0" x2=${W} y1=${y(-2)} y2=${y(-2)} stroke="#2bb886" opacity=".5"/><polyline points=${line(a)} fill="none" stroke="#5a9bf0" stroke-width="1.5"/><polyline points=${line(b)} fill="none" stroke="#f5c518" stroke-width="2"/></svg>
    <${Read} items=${[["Runs ending in the same blob as 80 steps", (share * 100).toFixed(0) + "% of 300 seeds", share > .95 ? "good" : "bad"], ["This seed, this run ends near", b[b.length - 1] > 0 ? "+2" : "-2"], ["The 80-step run ends near", a[a.length - 1] > 0 ? "+2" : "-2"]]}/>
    <p class="cu-play-note">One number walking from noise to one of two blobs at +2 and -2, with an exact denoiser and no network. Blue is 80 steps, gold is your step count, both from the same seed. It uses our own generator, so it will not match PyTorch's numbers. The step rules follow sample_euler and sample_euler_ancestral, with the noise source seeded at seed + 1 as ComfyUI does on the CPU.</p>`;
}

/* ---------- CU-107: a safetensors header ---------- */
const DT = { F32: 4, F16: 2, BF16: 2, I64: 8, U8: 1 };
export function headerErrors(h, buffer) {
  const errs = []; const rows = Object.entries(h).filter(([k]) => k !== "__metadata__").sort((a, b) => a[1].data_offsets[0] - b[1].data_offsets[0]); let at = 0;
  for (const [name, t] of rows) {
    if (!(t.dtype in DT)) { errs.push(`${name}: unknown dtype ${t.dtype}`); continue; }
    const [b, e] = t.data_offsets; const want = t.shape.reduce((x, y) => x * y, 1) * DT[t.dtype];
    if (b !== at) errs.push(`${name}: starts at ${b}, but the previous tensor ended at ${at}. No holes, no overlaps.`);
    if (e - b !== want) errs.push(`${name}: ${t.shape.join(" x ")} of ${t.dtype} is ${want} bytes, but the offsets give ${e - b}.`);
    at = e;
  }
  if (at !== buffer) errs.push(`The tensors end at ${at}, but the buffer holds ${buffer} bytes.`);
  return errs;
}
const SF_OK = { "layer1.weight": { dtype: "F32", shape: [2, 3], data_offsets: [0, 24] }, "layer1.bias": { dtype: "F16", shape: [4], data_offsets: [24, 32] }, "ids": { dtype: "I64", shape: [5], data_offsets: [32, 72] } };
const SF_CASES = [["A hole", { ...SF_OK, "layer1.bias": { ...SF_OK["layer1.bias"], data_offsets: [28, 36] } }], ["Wrong shape", { ...SF_OK, "layer1.weight": { ...SF_OK["layer1.weight"], shape: [2, 4] } }], ["Cut short", { ...SF_OK, "ids": { ...SF_OK.ids, data_offsets: [32, 64] } }]];
function SfHeader({ onPass }) {
  const [i, setI] = useState(0); const [texts, setTexts] = useState(() => SF_CASES.map(([, h]) => JSON.stringify(h, null, 1))); const [won, setWon] = useState({}); const text = texts[i]; const setText = (v) => setTexts(texts.map((t, k) => k === i ? v : t));
  const res = useMemo(() => { let h; try { h = JSON.parse(text); } catch (e) { return { bad: "Not valid JSON: " + e.message }; } try { return { errs: headerErrors(h, 72) }; } catch { return { bad: "Valid JSON, but not a header: each tensor needs dtype, shape and data_offsets." }; } }, [text]); const clean = res.errs && !res.errs.length;
  useEffect(() => { if (clean && !won[i]) { const w = { ...won, [i]: true }; setWon(w); if (Object.keys(w).length === SF_CASES.length) onPass(); } }, [clean, i]);
  return html`<div class="cu-seg" role="group" aria-label="Which damaged header">${SF_CASES.map(([n], k) => html`<button type="button" aria-pressed=${i === k} onClick=${() => setI(k)}>${won[k] ? "✓ " : ""}${n}</button>`)}</div>
    <div class="cu-play-grid"><label class="cu-ctl wide"><span>The JSON header. The buffer behind it holds 72 bytes. Edit it.</span><textarea class="cu-json" spellcheck="false" rows="14" value=${text} onInput=${(e) => setText(e.target.value)}></textarea></label>
    <div class="cu-errs" role="status">${res.bad ? html`<p class="cu-err">${res.bad}</p>` : clean ? html`<p class="cu-pass">✓ Every byte is accounted for.</p>` : res.errs.map((m) => html`<p class="cu-errline">${m}</p>`)}</div></div>
    <p class="cu-play-note">These checks follow the safetensors README: bytes = shape times the width of the type, offsets with no holes, and a buffer fully indexed. We wrote the messages. F32 is 4 bytes, F16 is 2, I64 is 8.</p>`;
}

/* ---------- CU-109: the pixel budget ---------- */
const SDXL_HW = [[512, 2048], [512, 1984], [512, 1920], [512, 1856], [576, 1792], [576, 1728], [576, 1664], [640, 1600], [640, 1536], [704, 1472], [704, 1408], [704, 1344], [768, 1344], [768, 1280], [832, 1216], [832, 1152], [896, 1152], [896, 1088], [960, 1088], [960, 1024], [1024, 1024], [1024, 960], [1088, 960], [1088, 896], [1152, 896], [1152, 832], [1216, 832], [1280, 768], [1344, 768], [1408, 704], [1472, 704], [1536, 640], [1600, 640], [1664, 576], [1728, 576], [1792, 576], [1856, 512], [1920, 512], [1984, 512], [2048, 512]];
/* The sum in ImageScaleToTotalPixels.execute, comfy_extras/nodes_post_processing.py, for an input whose sides are in ratio r. */
export function totalPixels(r, megapixels, step) { const h0 = 1000, w0 = 1000 * r; const scale = Math.sqrt(megapixels * 1024 * 1024 / (w0 * h0)); return [Math.round(w0 * scale / step) * step, Math.round(h0 * scale / step) * step]; }
const RATIOS = [["1", "1:1"], [String(4 / 3), "4:3"], [String(3 / 2), "3:2"], [String(16 / 9), "16:9"], [String(21 / 9), "21:9"], [String(9 / 16), "9:16"]];
function PixBudget({ onPass }) {
  const [r, setR] = useState("1"); const [mp, setMp] = useState(1); const [step, setStep] = useState("8"); const ratio = +r; const [w, h] = totalPixels(ratio, mp, +step); const used = w * h / (mp * 1024 * 1024); const onList = SDXL_HW.some(([a, b]) => a === h && b === w); const lat = [Math.floor(h / 8), Math.floor(w / 8)];
  const ok = Math.abs(ratio - 16 / 9) < 1e-6 && w === 1344 && h === 768; useEffect(() => { if (ok) onPass(); }, [ok]);
  return html`<div class="cu-ctlrow"><${Seg} label="Shape" value=${r} opts=${RATIOS} onPick=${setR}/><${Slider} label="Megapixels" value=${mp} min=${.25} max=${2} step=${.01} show=${mp.toFixed(2)} onInput=${setMp}/><${Seg} label="Round to a multiple of" value=${step} opts=${[["1", "1"], ["8", "8"], ["32", "32"], ["64", "64"]]} onPick=${setStep}/></div>
    <p class="cu-shape"><code>${w} x ${h}</code></p>
    <${Read} items=${[["Share of the budget used", (used * 100).toFixed(1) + "%", used > 1 ? "bad" : ""], ["Shape you get", (w / h).toFixed(3) + " for " + ratio.toFixed(3)], ["Latent grid, SD and SDXL", `${lat[0]} x ${lat[1]}`], ["On SDXL's training list", onList ? "yes" : "no", onList ? "good" : ""]]}/>
    <p class="cu-play-note">The sum is the one in ImageScaleToTotalPixels. JavaScript rounds an exact half up where Python rounds to even, which only matters on an exact half. The list is Appendix I of the SDXL paper.</p>`;
}

/* ---------- CU-111: a real PNG, built here ---------- */
const CRC_T = (() => { const t = []; for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; } return t; })();
export const crc32 = (b) => { let c = 0xffffffff; for (const x of b) c = CRC_T[(c ^ x) & 255] ^ (c >>> 8); return (c ^ 0xffffffff) >>> 0; };
const be32 = (n) => [(n >>> 24) & 255, (n >>> 16) & 255, (n >>> 8) & 255, n & 255]; const ascii = (s) => Array.from(s, (c) => c.charCodeAt(0));
export function chunk(type, data) { const body = [...ascii(type), ...data]; return { type, data: [...data], crc: crc32(body) }; }
function pixelsIdat(S) { const raw = []; for (let y = 0; y < S; y++) { raw.push(0); for (let x = 0; x < S; x++) raw.push(x * 16, y * 16, 96); } let a = 1, b = 0; for (const v of raw) { a = (a + v) % 65521; b = (b + a) % 65521; } const n = raw.length; return [0x78, 1, 1, n & 255, n >> 8, ~n & 255, (~n >> 8) & 255, ...raw, (b >> 8) & 255, b & 255, (a >> 8) & 255, a & 255]; }
export function pngChunks(S = 16) { const text = (k, v) => chunk("tEXt", [...ascii(k), 0, ...ascii(v)]); return [chunk("IHDR", [...be32(S), ...be32(S), 8, 2, 0, 0, 0]), text("prompt", '{"3":{"class_type":"KSampler","inputs":{"seed":42}}}'), text("workflow", '{"last_node_id":9,"nodes":[]}'), chunk("IDAT", pixelsIdat(S)), chunk("IEND", [])]; }
export function pngBytes(chunks) { const out = [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]; for (const c of chunks) out.push(...be32(c.data.length), ...ascii(c.type), ...c.data, ...be32(c.crc)); return out; }
const crcOk = (c) => crc32([...ascii(c.type), ...c.data]) === c.crc;
const isText = (c) => c.type === "tEXt"; const keyword = (c) => String.fromCharCode(...c.data.slice(0, c.data.indexOf(0)));
function PngCut({ onPass }) {
  const base = useMemo(() => pngChunks(), []); const [strip, setStrip] = useState(false); const [flip, setFlip] = useState("none"); const [seen, setSeen] = useState({}); const [bad, setBad] = useState(false);
  const chunks = useMemo(() => { const list = base.map((c) => ({ ...c, data: [...c.data] })); const hit = flip === "prompt" ? list[1] : flip === "pixels" ? list[3] : null; if (hit) hit.data[hit.data.length >> 1] ^= 1; return strip ? list.filter((c) => !isText(c)) : list; }, [base, strip, flip]);
  const bytes = useMemo(() => pngBytes(chunks), [chunks]); const src = useMemo(() => "data:image/png;base64," + btoa(String.fromCharCode(...bytes)), [bytes]); useEffect(() => setBad(false), [src]);
  useEffect(() => { if (flip !== "none") setSeen((v) => v[flip] ? v : { ...v, [flip]: true }); }, [flip]); const ok = seen.prompt && strip && flip === "none"; useEffect(() => { if (ok) onPass(); }, [ok]);
  return html`<div class="cu-ctlrow"><${Seg} label="Text chunks" value=${strip ? "cut" : "keep"} opts=${[["keep", "Keep them"], ["cut", "Cut them"]]} onPick=${(v) => setStrip(v === "cut")}/><${Seg} label="Flip one bit in" value=${flip} opts=${[["none", "nothing"], ["prompt", "the prompt text"], ["pixels", "the pixel data"]]} onPick=${setFlip}/></div>
    <div class="cu-play-grid"><div>${bad ? html`<p class="cu-err">Your browser refused this file.</p>` : html`<img src=${src} width="128" height="128" style="image-rendering:pixelated;display:block" alt="The picture this PNG decodes to" onError=${() => setBad(true)}/>`}<p class="cu-play-note">A real PNG built in this page: ${bytes.length} bytes. What your browser does with a damaged one is up to it.</p></div>
    <div class="cu-table"><table><thead><tr><th>Chunk</th><th>Bytes</th><th>CRC</th><th>Kind</th></tr></thead><tbody>${chunks.map((c, k) => html`<tr key=${k}><td><code>${c.type}${isText(c) ? " " + keyword(c) : ""}</code></td><td>${c.data.length}</td><td class=${crcOk(c) ? "" : "cu-err"}>${crcOk(c) ? "ok" : "FAILS"}</td><td>${c.type[0] === c.type[0].toUpperCase() ? "critical" : "ancillary"}</td></tr>`)}</tbody></table></div></div>
    <${Read} items=${[["Workflow in the file", chunks.some((c) => isText(c) && keyword(c) === "workflow") ? "yes" : "no"], ["Pixel data unchanged", chunks.find((c) => c.type === "IDAT").data.join() === base[3].data.join() ? "yes" : "no"]]}/>`;
}

/* ---------- CU-112: where a file lands ---------- */
export function normpath(p) { const abs = p.startsWith("/"); const out = []; for (const s of p.split("/")) { if (!s || s === ".") continue; if (s === ".." && out.length && out[out.length - 1] !== "..") out.pop(); else if (s === ".." && abs) continue; else out.push(s); } return (abs ? "/" : "") + out.join("/") || (abs ? "/" : "."); }
const pad = (n) => String(n).padStart(2, "0");
/* The editor's step: applyTextReplacements turns %date:...% into text before the graph is sent. Only these tokens are handled here. */
export const editorStep = (p, d) => p.replace(/%date:([^%]*)%/g, (_, f) => f.replace("yyyy", d.getFullYear()).replace("MM", pad(d.getMonth() + 1)).replace("dd", pad(d.getDate())));
/* The server's step: get_save_image_path in folder_paths.py. */
export function savePath(prefix, width, height, d, existing) {
  let p = prefix; if (p.includes("%")) p = p.replaceAll("%width%", width).replaceAll("%height%", height).replaceAll("%year%", d.getFullYear()).replaceAll("%month%", pad(d.getMonth() + 1)).replaceAll("%day%", pad(d.getDate())).replaceAll("%hour%", pad(d.getHours())).replaceAll("%minute%", pad(d.getMinutes())).replaceAll("%second%", pad(d.getSeconds()));
  const n = normpath(p); const cut = n.lastIndexOf("/"); const sub = cut < 0 ? "" : n.slice(0, cut) || "/"; const name = cut < 0 ? n : n.slice(cut + 1);
  if (sub.startsWith("/") || sub === ".." || sub.startsWith("../")) return { refused: true };
  let counter = 0; for (const f of existing[sub] || []) { if (!f.startsWith(name + "_")) continue; const m = parseInt(f.slice(name.length + 1).split(".")[0].split("_")[0], 10); counter = Math.max(counter, isNaN(m) ? 0 : m); }
  return { sub, name, counter: counter + 1, file: `${name.replaceAll("%batch_num%", "0")}_${String(counter + 1).padStart(5, "0")}_.png` };
}
const EXISTING = { "": ["ComfyUI_00001_.png", "ComfyUI_00002_.png", "ComfyUI_00009_.png"] };
function SavePath({ onPass }) {
  const [p, setP] = useState("ComfyUI"); const [saw, setSaw] = useState(false); const [got, setGot] = useState(false); const now = useMemo(() => new Date(), []); const sent = editorStep(p, now); const r = savePath(sent, 512, 512, now, EXISTING);
  useEffect(() => { if (r.refused) setSaw(true); }, [r.refused]); const here = !r.refused && r.sub === "portraits" && r.name.startsWith("fox"); useEffect(() => { if (here) setGot(true); }, [here]); const ok = saw && got; useEffect(() => { if (ok) onPass(); }, [ok]);
  return html`<label class="cu-ctl wide"><span>filename_prefix</span><input class="cu-text" spellcheck="false" value=${p} onInput=${(e) => setP(e.target.value)}/></label>
    <p class="cu-shape"><code>${r.refused ? "refused" : "output/" + (r.sub ? r.sub + "/" : "") + r.file}</code></p>
    <${Read} items=${[["The editor sends", sent], ["Subfolder", r.refused ? "-" : r.sub || "(none)"], ["Counter", r.refused ? "-" : r.counter], ["Result", r.refused ? "Saving image outside the output folder is not allowed." : "saved", r.refused ? "bad" : "good"]]}/>
    <${Check} items=${[["Save into a subfolder called portraits, with a file name starting fox", got], ["Then try to get out of the output folder", saw]]}/>
    <p class="cu-play-note">The output folder here already holds ComfyUI_00001_, 00002_ and 00009_. Width and height are taken as 512. Try %year%, %width%, %date:yyyy-MM-dd% or ../ in the box. The rules are those of get_save_image_path, and a real run here matched them.</p>`;
}

/* ---------- CU-113: what Mute and Bypass send ---------- */
const N = (type, inputs, outputs, widgets = {}, extra = {}) => ({ type, inputs, outputs, widgets, mode: 0, ...extra });
export const CHAIN = () => ({ 1: N("EmptyImage", [], ["IMAGE"], { width: 512, height: 512, batch_size: 1, color: 0 }), 2: N("ImageBlur", [{ name: "image", type: "IMAGE", from: [1, 0] }], ["IMAGE"], { blur_radius: 4, sigma: 2 }), 3: N("Reroute", [{ name: "", type: "*", from: [2, 0] }], ["*"], {}, { virtual: true }), 4: N("ImageInvert", [{ name: "image", type: "IMAGE", from: [3, 0] }], ["IMAGE"]), 5: N("PreviewImage", [{ name: "images", type: "IMAGE", from: [4, 0] }], [], {}, { output: true }), 6: N("Note", [], [], { text: "Blur first." }, { virtual: true }) });
export const DECODE = () => ({ 1: N("CheckpointLoaderSimple", [], ["MODEL", "CLIP", "VAE"], { ckpt_name: "model.safetensors" }), 2: N("EmptyLatentImage", [], ["LATENT"], { width: 512, height: 512, batch_size: 1 }), 3: N("VAEDecode", [{ name: "samples", type: "LATENT", from: [2, 0] }, { name: "vae", type: "VAE", from: [1, 2] }], ["IMAGE"]), 4: N("PreviewImage", [{ name: "images", type: "IMAGE", from: [3, 0] }], [], {}, { output: true }) });
const okType = (a, b) => a === "*" || b === "*" || a === b;
/* resolveOutput and _getBypassSlotIndex in ExecutableNodeDTO of the ComfyUI front end, without subgraphs. */
export function bypassSlot(n, slot, type) {
  const { inputs } = n; const opp = inputs[slot]; const outT = n.outputs[slot];
  if (type === "*" || type === "") return inputs.length > slot ? slot : 0;
  if (opp && okType(opp.type, outT) && okType(opp.type, type)) return slot;
  const exact = inputs.findIndex((i) => i.type === type); if (exact !== -1) return exact;
  return inputs.findIndex((i) => okType(i.type, outT) && okType(i.type, type));
}
export function resolveOutput(g, id, slot, type) {
  const n = g[id]; if (n.mode === 2) return null;
  if (n.mode === 4) { const k = bypassSlot(n, slot, type); return k === -1 ? null : resolveInput(g, id, k); }
  if (n.virtual) return n.inputs[slot] ? resolveInput(g, id, slot, type) : null;
  return [String(id), slot];
}
export function resolveInput(g, id, k, typeOver) { const i = g[id].inputs[k]; if (!i || !i.from) return null; return resolveOutput(g, i.from[0], i.from[1], typeOver && i.type === "*" ? typeOver : i.type); }
/* graphToPrompt in src/utils/executionUtil.ts of the ComfyUI front end. */
export function toApi(g) {
  const out = {};
  for (const id of Object.keys(g)) { const n = g[id]; if (n.virtual || n.mode === 2 || n.mode === 4) continue; const inputs = { ...n.widgets }; n.inputs.forEach((inp, k) => { const r = resolveInput(g, id, k); if (r) inputs[inp.name] = r; }); out[id] = { inputs, class_type: n.type }; }
  for (const { inputs } of Object.values(out)) for (const [k, v] of Object.entries(inputs)) if (Array.isArray(v) && v.length === 2 && !Object.hasOwn(out, v[0])) delete inputs[k];
  return out;
}
/* The two checks of validate_prompt this graph can fail. */
export function checkApi(api, g) {
  const outs = Object.keys(api).filter((id) => g[id].output); if (!outs.length) return ["prompt_no_outputs: Prompt has no outputs"];
  const errs = []; const need = new Set(outs); const stack = [...outs];
  while (stack.length) { const id = stack.pop(); for (const inp of g[id].inputs) { if (!(inp.name in api[id].inputs)) errs.push(`required_input_missing on ${g[id].type} ${id}: ${inp.name}`); } for (const v of Object.values(api[id].inputs)) if (Array.isArray(v) && !need.has(v[0])) { need.add(v[0]); stack.push(v[0]); } }
  return errs;
}
const MODES = [[0, "Always"], [2, "Mute"], [4, "Bypass"]];
function ModesLab({ onPass }) {
  const [which, setWhich] = useState("chain"); const [modes, setModes] = useState({}); const [seen, setSeen] = useState({}); const g = useMemo(() => { const b = which === "chain" ? CHAIN() : DECODE(); for (const k of Object.keys(b)) if (modes[which + k] != null) b[k].mode = modes[which + k]; return b; }, [which, modes]);
  const api = useMemo(() => toApi(g), [g]); const errs = useMemo(() => checkApi(api, g), [api, g]); const set = (k, m) => setModes({ ...modes, [which + k]: m }); const group = (m) => setModes({ ...modes, [which + 2]: m, [which + 4]: m });
  const m = (k) => g[k].mode; const only = (k) => Object.keys(g).every((x) => g[x].virtual || x === String(k) ? true : g[x].mode === 0); const facts = { byp: which === "chain" && m(2) === 4 && only(2) && !errs.length, mute: which === "chain" && m(2) === 2 && only(2) && errs.length > 0, dec: which === "decode" && m(3) === 4 && only(3) && errs.length > 0 };
  useEffect(() => { const add = Object.keys(facts).filter((k) => facts[k] && !seen[k]); if (add.length) { const v = { ...seen }; add.forEach((k) => { v[k] = true; }); setSeen(v); if (v.byp && v.mute && v.dec) onPass(); } }, [facts.byp, facts.mute, facts.dec]);
  return html`<${Seg} label="Graph" value=${which} opts=${[["chain", "Blur then invert"], ["decode", "Latent to picture"]]} onPick=${setWhich}/>
    <div class="cu-play-grid"><div><div class="cu-table"><table><tbody>${Object.keys(g).map((k) => html`<tr key=${k}><td><code>${k} ${g[k].type}</code></td><td>${g[k].virtual ? html`<em>editor only</em>` : html`<${Seg} label=${"Mode " + k} value=${g[k].mode} opts=${MODES} onPick=${(v) => set(k, v)}/>`}</td></tr>`)}</tbody></table></div>
      ${which === "chain" && html`<div class="cu-ctl"><span>A group holding nodes 2 and 4</span><div class="cu-seg" role="group" aria-label="Group">${[[0, "Set to Always"], [2, "Set to Never"], [4, "Bypass group nodes"]].map(([v, l]) => html`<button type="button" onClick=${() => group(v)}>${l}</button>`)}</div></div>`}</div>
      <label class="cu-ctl wide"><span>What the server receives</span><textarea class="cu-json" readonly rows="16" value=${JSON.stringify(api, null, 1)}></textarea></label></div>
    <div class="cu-errs" role="status">${errs.length ? errs.map((e) => html`<p class="cu-errline">${e}</p>`) : html`<p class="cu-pass">✓ Passes validation.</p>`}</div>
    <${Check} items=${[["Bypass only the blur: the graph still runs without it", seen.byp], ["Mute only the blur: the invert loses its input", seen.mute], ["In the other graph, bypass only VAEDecode: no input has the type IMAGE", seen.dec]]}/>
    <p class="cu-play-note">A small port of the front end's graphToPrompt, with no subgraphs. Read from its main branch and not run in the real editor. Validation here checks only the two errors these graphs can hit, in the same words as validate_prompt.</p>`;
}

/* ---------- CU-114: which file goes where ---------- */
const LOADERS = [["checkpoints", "CheckpointLoaderSimple, models/checkpoints"], ["diffusion_models", "UNETLoader, models/diffusion_models"], ["text_encoders", "CLIPLoader, models/text_encoders"], ["vae", "VAELoader, models/vae"], ["loras", "LoraLoader, models/loras"], ["controlnet", "ControlNetLoader, models/controlnet"]];
export const FILES = [
  { f: "file_a.safetensors", keys: ["double_blocks.0.img_attn.norm.key_norm.scale", "single_blocks.0.linear1.weight", "img_in.weight"], a: "diffusion_models", why: "Only the denoiser. Nothing for text and nothing for pixels, so it needs a text encoder and a VAE beside it." },
  { f: "file_b.safetensors", keys: ["model.diffusion_model.input_blocks.0.0.weight", "cond_stage_model.transformer.text_model.encoder.layers.0.mlp.fc1.weight", "first_stage_model.decoder.conv_in.weight"], a: "checkpoints", why: "Three prefixes, three networks in one file: that is what a checkpoint is." },
  { f: "file_c.safetensors", keys: ["encoder.block.23.layer.1.DenseReluDense.wi.weight", "encoder.block.0.layer.0.SelfAttention.k.weight"], a: "text_encoders", why: "These are the names of a T5 text encoder, which ComfyUI's text-encoder detector looks for." },
  { f: "file_d.safetensors", keys: ["encoder.down.0.block.0.conv1.weight", "decoder.conv_in.weight", "decoder.mid.block_1.norm1.weight"], a: "vae", why: "An encoder and a decoder of pixels, and nothing else: a VAE. A text encoder also says encoder, so read past the first word." },
  { f: "file_e.safetensors", keys: ["lora_unet_down_blocks_0_attentions_0_proj_in.lora_down.weight", "lora_unet_down_blocks_0_attentions_0_proj_in.lora_up.weight"], a: "loras", why: "Pairs of small down and up matrices: a change to weights in another model, useless by itself." },
  { f: "file_f.safetensors", keys: ["control_model.input_hint_block.0.weight", "control_model.zero_convs.0.0.weight"], a: "controlnet", why: "input_hint_block takes the control picture. Only a ControlNet has one." },
];
function LoaderPick({ onPass }) {
  const [pick, setPick] = useState({}); const right = FILES.filter((x) => pick[x.f] === x.a).length; useEffect(() => { if (right === FILES.length) onPass(); }, [right]);
  return html`<ol class="cu-risk">${FILES.map((x) => html`<li key=${x.f}><label class="cu-ctl wide"><span><code>${x.f}</code></span><select class="cu-text" value=${pick[x.f] || ""} onChange=${(e) => setPick({ ...pick, [x.f]: e.target.value })}><option value="">Which loader and folder?</option>${LOADERS.map(([k, l]) => html`<option value=${k}>${l}</option>`)}</select></label><p class="cu-play-note">${x.keys.map((k) => html`<code style="display:block;overflow-wrap:anywhere">${k}</code>`)}</p>${pick[x.f] && html`<p class=${pick[x.f] === x.a ? "cu-why" : "cu-why no"}>${pick[x.f] === x.a ? x.why : "Not that one. Look at what the names describe."}</p>`}</li>`)}</ol>
    <${Read} items=${[["Placed right", `${right} of ${FILES.length}`, right === FILES.length ? "good" : ""]]}/>
    <p class="cu-play-note">We typed these key names from ComfyUI's own detection and loading code and shortened the lists. They are not read from real files, and real files hold many more keys. The file names are useless on purpose: names lie, keys do not.</p>`;
}

/* ---------- CU-115: read it before you run it ---------- */
const WF = [
  { c: 'CheckpointLoaderSimple  ckpt_name: "model.safetensors"', ok: "A core node asking for a file by name. Check you have that file. Nothing here reaches outside." },
  { c: 'AcmePromptBooster  properties.aux_id: "someone/acme-nodes"', risk: "Not a core node. The name and repo here are invented, but the point is real: to run this you must install a pack, and ComfyUI imports a pack's Python when it starts. Read the pack first." },
  { c: "KSampler  seed: 42, steps: 20, cfg: 7", ok: "Core, and only numbers." },
  { c: 'FluxProUltraImageNode  prompt: "a red fox"', risk: "A real partner API node. It runs on someone else's server: your prompt leaves the machine, and it needs a Comfy account and can spend credits." },
  { c: 'models[0]  url: "https://example.invalid/fast_v2.ckpt", directory: "checkpoints"', risk: "The file offers a download link for you to act on. The host is not one the editor allows, and .ckpt is a pickle, the format that can run code when it loads. Find the model from its real publisher." },
  { c: 'SaveImage  filename_prefix: "%year%/fox"', ok: "Core. It builds a path inside the output folder, and the server refuses a path that leaves it." },
  { c: 'Subgraph node "Tidy upscale"  definitions.subgraphs[0]: 12 nodes', risk: "One box on the canvas, twelve nodes inside. Everything on this list could be in there. Open it or read the definitions." },
  { c: 'MarkdownNote  "If this fails, paste this line into your terminal"', risk: "A note is text from the author and it never runs. Nothing stops it asking you to run something. Never paste a command from a workflow without reading what it does." },
  { c: 'LoadImage  image: "example.png"', ok: "Core. It reads from your input folder, and the file must be there." },
];
export const WF_ROWS = WF;
function WfRead({ onPass }) {
  const [sel, setSel] = useState([]); const bad = WF.map((r, k) => r.risk ? k : -1).filter((k) => k >= 0); const all = bad.every((k) => sel.includes(k)); const extra = sel.filter((k) => !bad.includes(k)); const ok = all && !extra.length; useEffect(() => { if (ok) onPass(); }, [ok]);
  const tap = (k) => setSel(sel.includes(k) ? sel.filter((x) => x !== k) : [...sel, k]);
  return html`<p class="cu-q-line">We wrote this workflow for the lab. Tap each line you would stop and check before pressing Queue.</p><ol class="cu-risk">${WF.map((l, k) => html`<li key=${k}><button type="button" class=${"cu-riskl" + (sel.includes(k) ? (l.risk ? " hit" : " miss") : "")} aria-pressed=${sel.includes(k)} onClick=${() => tap(k)}><code>${l.c}</code></button>${sel.includes(k) && html`<p class=${l.risk ? "cu-why" : "cu-why no"}>${l.risk || l.ok}</p>`}</li>`)}</ol><${Read} items=${[["Found", `${bad.filter((k) => sel.includes(k)).length} of ${bad.length}`, all ? "good" : ""], ["False alarms", extra.length, extra.length ? "bad" : ""]]}/>`;
}

export const MORE = {
  fitgap: { title: "Learn it or copy it", task: "Try each model. Finish on the one whose samples are new and which leaves the gap empty.", C: FitGap, after: "The copier looked fine on the chart, and none of its samples were new. Good-looking samples alone don't show that a model learned anything." },
  seedwalk: { title: "What a seed holds still", task: "With 20 steps or fewer, compare euler and euler ancestral. Read how often the run still ends in the same blob.", C: SeedWalk, after: "A deterministic path bends but keeps its destination. Ancestral steps draw new noise each time, so changing the step count sends the run somewhere else." },
  sfheader: { title: "Repair a safetensors header", task: "Fix each damaged header until every byte is accounted for.", C: SfHeader },
  pixbudget: { title: "Spend a pixel budget", task: "Get a 16:9 picture of about one megapixel that lands exactly on one of SDXL's training sizes.", C: PixBudget, after: "Rounding to 64 gives up some exactness in the shape for a size the model trained on." },
  pngcut: { title: "Cut a workflow out of a PNG", task: "Flip a bit in the prompt text and see what catches it. Then undo the flip and cut the text chunks so the workflow is gone and the pixels are not.", C: PngCut, after: "The picture never needed those chunks. This is why a re-saved or re-encoded image can lose its workflow." },
  savepath: { title: "Where does the file land?", task: "Save into a subfolder called portraits, with a file name starting fox. Then try to escape the output folder.", C: SavePath },
  modes: { title: "What Mute and Bypass send", task: "Change a node's mode and read what the server would get. Do the three things on the list.", C: ModesLab, after: "Neither mode tells the server anything. The editor rewrites the graph first, and the server sees only what is left." },
  loaderpick: { title: "Which loader, which folder?", task: "Read each file's tensor names. Choose the loader and folder for all six.", C: LoaderPick },
  wfread: { title: "Read a workflow before you run it", task: "Find every line worth stopping for, with no false alarms.", C: WfRead },
};
