/* ComfyUniversity: labs for ControlNet, inpainting, LoRA and training. Pure maths in this file, no model, no GPU. Each maths port names the function it follows. */
import { useEffect, useMemo, useRef, useState } from "preact/hooks";
import { html } from "./common.js";
import { EXAMPLE } from "./train_example.js";

const Slider = ({ label, value, min, max, step = 1, onInput, show }) => html`<label class="cu-ctl"><span>${label} <b>${show != null ? show : value}</b></span><input type="range" min=${min} max=${max} step=${step} value=${value} onInput=${(e) => onInput(+e.target.value)}/></label>`;
const Seg = ({ label, value, opts, onPick }) => html`<div class="cu-ctl"><span>${label}</span><div class="cu-seg" role="group" aria-label=${label} style=${{ alignSelf: "flex-start" }}>${opts.map(([k, l]) => html`<button type="button" aria-pressed=${value === k} onClick=${() => onPick(k)}>${l}</button>`)}</div></div>`;
const Read = ({ items }) => html`<dl class="cu-read">${items.map(([k, v, cls]) => html`<div class=${cls || ""}><dt>${k}</dt><dd>${v}</dd></div>`)}</dl>`;
const greyBox = (v, label, key) => { const c = Math.round(255 * Math.max(0, Math.min(1, v))); return html`<span key=${key} title=${label} style=${{ display: "inline-block", width: "28px", height: "28px", marginRight: "2px", background: `rgb(${c},${c},${c})`, border: "1px solid rgba(255,255,255,.25)" }}></span>`; };
const rng = (seed) => { let s = seed >>> 0; return () => { s = (s + 0x6D2B79F5) >>> 0; let t = s; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; };
const gauss = (r) => Math.sqrt(-2 * Math.log(1 - r())) * Math.cos(2 * Math.PI * r());
const mean = (x) => x.reduce((a, b) => a + b, 0) / x.length;

/* ---------- mask on the latent grid. Follows comfy/utils.py reshape_mask (bilinear, no antialias, factor 8) and the box growth in VAEEncodeForInpaint. ---------- */
export function maskLatent(start, width, grow, cells = 8) {
  const n = cells * 8, px = new Array(n).fill(0);
  for (let i = start; i < start + width && i < n; i++) px[i] = 1;
  let m = px;
  if (grow > 0) { const pad = Math.ceil((grow - 1) / 2); m = new Array(n).fill(0); for (let i = 0; i < n; i++) if (px[i]) for (let j = i + pad - grow + 1; j <= i + pad; j++) if (j >= 0 && j < n) m[j] = 1; }
  return { px: m, cell: Array.from({ length: cells }, (_, c) => (m[8 * c + 3] + m[8 * c + 4]) / 2) };
}
function MaskGrid({ onPass }) {
  const [start, setStart] = useState(25); const [width, setWidth] = useState(3); const [grow, setGrow] = useState(0); const [gone, setGone] = useState(false);
  const r = useMemo(() => maskLatent(start, width, grow), [start, width, grow]); const top = Math.max(...r.cell);
  useEffect(() => { if (grow === 0 && top === 0 && width >= 2 && width <= 3) setGone(true); }, [grow, top, width]);
  const hidden = Math.max(...maskLatent(start, width, 0).cell) === 0; const ok = gone && hidden && grow === 6 && top > 0 && width >= 2 && width <= 3; useEffect(() => { if (ok) onPass(); }, [ok]);
  return html`<div class="cu-ctlrow"><${Slider} label="Stripe starts at pixel" value=${start} min=${0} max=${60} onInput=${setStart}/><${Slider} label="Stripe width" value=${width} min=${1} max=${16} onInput=${setWidth}/><${Seg} label="grow_mask_by" value=${grow} opts=${[[0, "0"], [6, "6"]]} onPick=${setGrow}/></div>
    <div role="img" aria-label=${`The mask in pixels: ${r.px.filter(Boolean).length} of ${r.px.length} set`} style=${{ display: "flex", margin: "8px 0 2px" }}>${r.px.map((v, i) => html`<span key=${i} style=${{ flex: 1, height: "22px", background: v ? "#f5c518" : "#222", borderRight: i % 8 === 7 ? "2px solid #777" : "0" }}></span>`)}</div>
    <div role="img" aria-label=${`The mask on the latent grid, strongest cell ${top.toFixed(1)}`} style=${{ display: "flex" }}>${r.cell.map((v, i) => html`<span key=${i} style=${{ flex: 1, height: "44px", textAlign: "center", lineHeight: "44px", color: v > .4 ? "#000" : "#ccc", background: `rgb(${Math.round(245 * v) + 20},${Math.round(197 * v) + 20},${Math.round(24 * v) + 20})`, borderRight: "2px solid #777" }}>${v.toFixed(1)}</span>`)}</div>
    <${Read} items=${[["Strongest latent cell", top.toFixed(1), top > 0 ? "good" : "bad"], ["Sampler can see the stripe", top > 0 ? "yes" : "no"]]}/>
    <p class="cu-play-note">Top row: your mask, pixel by pixel. Bottom row: what the sampler uses. Each latent cell reads only the 4th and 5th pixel of its eight, because the resize has no antialiasing.</p>`;
}

/* ---------- depth to grey. Follows normalize_depth_min_max and normalize_depth_v2_style in comfy/ldm/depth_anything_3/preprocess.py, and _normalize_disparity in comfy_extras/nodes_moge.py. ---------- */
const quantile = (sorted, q) => { const p = q * (sorted.length - 1), lo = Math.floor(p), hi = Math.ceil(p); return sorted[lo] + (sorted[hi] - sorted[lo]) * (p - lo); };
export function depthGrey(method, skyShare, n = 4000) {
  const scene = Array.from({ length: n }, (_, i) => 2 + 8 * i / (n - 1)), sky = Math.round(skyShare * n / (1 - skyShare)), all = scene.concat(new Array(sky).fill(500)); const sorted = all.slice().sort((a, b) => a - b); const clamp = (v) => Math.max(0, Math.min(1, v));
  let f;
  if (method === "min_max") f = (d) => 1 - (d - sorted[0]) / Math.max(sorted[sorted.length - 1] - sorted[0], 1e-6);
  else if (method === "v2") { const lo = quantile(sorted, .01), hi = quantile(sorted, .99); f = (d) => 1 - clamp((d - lo) / Math.max(hi - lo, 1e-6)); }
  else if (method === "v2sky") { const lo = quantile(scene, .01), hi = quantile(scene, .99); f = (d) => 1 - clamp((d - lo) / Math.max(hi - lo, 1e-6)); }
  else { const disp = all.map((d) => 1 / d).sort((a, b) => a - b), lo = quantile(disp, .001), hi = quantile(disp, .999); f = (d) => clamp((1 / d - lo) / Math.max(hi - lo, 1e-6)); }
  const levels = new Set(scene.map((d) => Math.round(f(d) * 255))).size;
  return { levels, at: [2, 3, 4, 5, 6, 7, 8, 9, 10].map(f) };
}
function DepthNorm({ onPass }) {
  const [method, setMethod] = useState("min_max"); const [sky, setSky] = useState(0); const [seen, setSeen] = useState(false);
  const r = useMemo(() => depthGrey(method, sky / 100), [method, sky]);
  useEffect(() => { if (sky >= 2 && method === "min_max" && r.levels < 16) setSeen(true); }, [sky, method, r.levels]);
  const ok = seen && sky >= 30 && r.levels >= 200; useEffect(() => { if (ok) onPass(); }, [ok]);
  return html`<div class="cu-ctlrow"><${Seg} label="Render" value=${method} opts=${[["min_max", "min_max"], ["v2", "v2_style"], ["v2sky", "v2_style + sky mask"], ["disp", "MoGe disparity"]]} onPick=${setMethod}/><${Slider} label="Pixels that are far sky" value=${sky} min=${0} max=${40} show=${sky + "%"} onInput=${setSky}/></div>
    <p class="cu-play-note">Grey at 2, 3, 4 ... 10 metres, near on the left.</p><div role="img" aria-label=${"Grey ramp for " + method}>${r.at.map((v, i) => greyBox(v, `${i + 2} m: ${v.toFixed(3)}`, i))}</div>
    <${Read} items=${[["8-bit levels left for the scene", r.levels, r.levels >= 200 ? "good" : r.levels < 16 ? "bad" : ""], ["Grey at 6 m", r.at[4].toFixed(3)]]}/>
    <p class="cu-play-note">A scene from 2 m to 10 m, with some pixels at 500 m. All four put near at white.</p>`;
}

/* ---------- outpaint mask. Follows ImagePadForOutpaint.expand_image in nodes.py, plus the rounding and growth in VAEEncodeForInpaint. ---------- */
export function outpad(feather, side) {
  const active = feather > 0 && feather * 2 < side; const v = (d) => { if (!active || d >= feather) return 0; const u = (feather - d) / feather; return u * u; };
  const roundHalfEven = (x) => { const f = Math.floor(x), diff = x - f; return diff > .5 ? f + 1 : diff < .5 ? f : f % 2 === 0 ? f : f + 1; };
  let soft = 0, rounded = 0; for (let d = 1; d < side; d++) { if (v(d) > 0) soft++; if (roundHalfEven(v(d)) > 0) rounded++; }
  return { active, soft, rounded, grown: rounded + 2, v };
}
function OutPad({ onPass }) {
  const [f, setF] = useState(40); const [side, setSide] = useState(512); const r = useMemo(() => outpad(f, side), [f, side]);
  const ok = r.active && r.soft >= 20 && r.rounded <= 8; useEffect(() => { if (ok) onPass(); }, [ok]);
  return html`<div class="cu-ctlrow"><${Slider} label="feathering" value=${f} min=${0} max=${120} onInput=${setF}/><${Slider} label="Picture size" value=${side} min=${64} max=${1024} step=${8} onInput=${setSide}/></div>
    <p class="cu-play-note">Your picture on the left, the padded area on the right. Upper strip: the mask ImagePadForOutpaint makes. Lower strip: after VAEEncodeForInpaint rounds it.</p>
    <div role="img" aria-label=${`The mask from ImagePadForOutpaint: a soft ramp ${r.soft} pixels long`} style=${{ display: "flex", height: "28px" }}>${Array.from({ length: 48 }, (_, i) => { const d = 48 - i, v = r.v(d), c = Math.round(255 * v); return html`<span key=${i} title=${`${d} px from the join: ${v.toFixed(2)}`} style=${{ flex: 1, minWidth: 0, background: `rgb(${c},${c},${c})` }}></span>`; })}<span style=${{ flex: 8, minWidth: 0, background: "#fff" }}></span></div>
    <div role="img" aria-label=${`The mask after rounding: ${r.rounded} pixels of your picture are fully masked`} style=${{ display: "flex", height: "28px", marginTop: "3px" }}>${Array.from({ length: 48 }, (_, i) => { const d = 48 - i, on = r.v(d) > .5; return html`<span key=${i} title=${`${d} px: ${on ? 1 : 0}`} style=${{ flex: 1, minWidth: 0, background: on ? "#fff" : "#000" }}></span>`; })}<span style=${{ flex: 8, minWidth: 0, background: "#fff" }}></span></div>
    <${Read} items=${[["Feather", r.active ? "on" : "off: hard edge", r.active ? "good" : "bad"], ["Soft mask reaches in", r.soft + " px"], ["After rounding", r.rounded + " px", r.rounded <= 8 ? "good" : ""], ["After rounding and growing by 6", r.grown + " px"]]}/>`;
}

/* ---------- adapters: numbers stored. factorization follows comfy/weight_adapter/base.py. ---------- */
export function factorization(dim, factor = -1) {
  if (factor > 0 && dim % factor === 0 && dim >= factor * factor) { const m = factor, n = dim / factor; return m > n ? [n, m] : [m, n]; }
  if (factor < 0) factor = dim; let m = 1, n = dim; const length = m + n;
  while (m < n) { let nm = m + 1; while (dim % nm !== 0) nm++; const nn = dim / nm; if (nm + nn > length || nm > factor) break; m = nm; n = nn; }
  return m > n ? [n, m] : [m, n];
}
function Adapters({ onPass }) {
  const [d, setD] = useState(1280); const [rank, setRank] = useState(8); const [f, setF] = useState(4); const [m, n] = factorization(d, f); const lora = rank * 2 * d, loha = 2 * lora, lokr = m * m + n * n, full = d * d; const [bs, bn] = factorization(d, f); const oft = bn * bs * bs;
  const ok = d === 1280 && rank === 8 && lokr < lora; useEffect(() => { if (ok) onPass(); }, [ok]); const c = (x) => x.toLocaleString("en-US");
  return html`<div class="cu-ctlrow"><${Seg} label="Layer size" value=${d} opts=${[[320, "320"], [640, "640"], [768, "768"], [1280, "1280"]]} onPick=${setD}/><${Slider} label="Rank (LoRA, LoHa)" value=${rank} min=${1} max=${128} onInput=${setRank}/><${Seg} label="Factor (LoKr, OFT)" value=${f} opts=${[[4, "4"], [8, "8"], [16, "16"], [32, "32"]]} onPick=${setF}/></div>
    <${Read} items=${[["Full weight", c(full)], [`LoRA rank ${rank}`, c(lora)], [`LoHa rank ${rank}`, c(loha)], [`LoKr ${m} x ${n}`, c(lokr), lokr < lora ? "good" : ""], [`OFT ${bn} blocks of ${bs}`, c(oft)]]}/>
    <p class="cu-play-note">Fewer numbers does not mean more power. A LoKr change is one small pattern repeated across the layer, and a LoRA change can only point in a few directions. They are limited in different ways.</p>`;
}

/* ---------- the real loss list of our run, averaged over a window ---------- */
function LossRead({ onPass }) {
  const [w, setW] = useState(1); const L = EXAMPLE.loss; const parts = useMemo(() => { const o = []; for (let i = 0; i + w <= L.length; i += w) o.push(mean(L.slice(i, i + w))); return o; }, [w]);
  const W = 640, H = 200, top = 1.15, X = (i) => 8 + i / Math.max(parts.length - 1, 1) * (W - 16), Y = (v) => H - 8 - v / top * (H - 16); const ok = w >= 30; useEffect(() => { if (ok) onPass(); }, [ok]);
  return html`<div class="cu-ctlrow"><${Slider} label="Average over" value=${w} min=${1} max=${100} show=${w + " steps"} onInput=${setW}/></div>
    <svg class="cu-chart" viewBox=${`0 0 ${W} ${H}`} role="img" aria-label=${`Loss of the 300-step run, averaged over ${w} steps`}>${[1, .5].map((v) => html`<g key=${v}><line x1="8" x2=${W - 8} y1=${Y(v)} y2=${Y(v)} stroke="rgba(255,255,255,.2)" stroke-dasharray="4 4"/><text x="10" y=${Y(v) - 4} font-size="12" fill="#9aa39a">${v.toFixed(1)}</text></g>`)}<path d=${parts.map((v, i) => (i ? "L" : "M") + X(i).toFixed(1) + " " + Y(v).toFixed(1)).join("")} fill="none" stroke="#f5c518" stroke-width="1.5"/></svg>
    <${Read} items=${[["First window", parts[0].toFixed(4)], ["Last window", parts[parts.length - 1].toFixed(4)], ["Lowest of these", Math.min(...parts).toFixed(4)], ["Highest of these", Math.max(...parts).toFixed(4)]]}/>
    <p class="cu-play-note">Every value is from the real run: 300 steps, 12 pictures, rank 8. Each step draws one picture and one random noise level, so single values jump. The averages show no clear fall, and the pictures still changed. The dashed lines mark loss 1.0 and 0.5.</p>`;
}

/* ---------- same seed, real pictures: a pixel difference ---------- */
const PAIRS = { light: ["train_art/lighthouse_base.webp", "train_art/lighthouse_lora.webp", "Seed 1234, LoRA off and on"], harb: ["train_art/harbour_base.webp", "train_art/harbour_lora.webp", "Seed 77, LoRA off and on"], other: ["train_art/lighthouse_base.webp", "train_art/harbour_base.webp", "No LoRA, two different prompts and seeds"] };
function DiffPair({ onPass }) {
  const S = 256; const [p, setP] = useState("light"); const [gain, setGain] = useState(2); const [vals, setVals] = useState({}); const cv = useRef(null); const data = useRef(null);
  useEffect(() => { let on = true, left = 2; const ims = PAIRS[p].slice(0, 2).map((src) => { const im = new Image(); im.onload = () => { left--; if (!left && on) { const px = ims.map((m) => { const c = document.createElement("canvas"); c.width = c.height = S; const x = c.getContext("2d", { willReadFrequently: true }); x.drawImage(m, 0, 0, S, S); return x.getImageData(0, 0, S, S).data; }); data.current = px; let t = 0; for (let i = 0; i < S * S * 4; i += 4) t += Math.abs(px[0][i] - px[1][i]) + Math.abs(px[0][i + 1] - px[1][i + 1]) + Math.abs(px[0][i + 2] - px[1][i + 2]); setVals((v) => ({ ...v, [p]: t / (S * S * 3 * 255) })); } }; im.src = src; return im; }); return () => { on = false; }; }, [p]);
  useEffect(() => { if (!data.current || !cv.current) return; const px = data.current, x = cv.current.getContext("2d"), o = x.createImageData(S, S); for (let i = 0; i < S * S * 4; i += 4) { o.data[i] = Math.min(255, Math.abs(px[0][i] - px[1][i]) * gain); o.data[i + 1] = Math.min(255, Math.abs(px[0][i + 1] - px[1][i + 1]) * gain); o.data[i + 2] = Math.min(255, Math.abs(px[0][i + 2] - px[1][i + 2]) * gain); o.data[i + 3] = 255; } x.putImageData(o, 0, 0); }, [vals, gain, p]);
  const ok = Object.keys(vals).length === 3; useEffect(() => { if (ok) onPass(); }, [ok]);
  return html`<div class="cu-ctlrow"><${Seg} label="Pair" value=${p} opts=${[["light", "Lighthouse"], ["harb", "Harbour"], ["other", "Two base pictures"]]} onPick=${setP}/><${Slider} label="Brighten the difference" value=${gain} min=${1} max=${6} show=${"x" + gain} onInput=${setGain}/></div>
    <div class="cu-two"><figure class="cu-canvas"><canvas ref=${cv} width=${S} height=${S} role="img" aria-label=${"Difference for " + PAIRS[p][2]}></canvas><figcaption>${PAIRS[p][2]}</figcaption></figure></div>
    <${Read} items=${[["Lighthouse, off and on", vals.light != null ? vals.light.toFixed(3) : "open it"], ["Harbour, off and on", vals.harb != null ? vals.harb.toFixed(3) : "open it"], ["Two base pictures", vals.other != null ? vals.other.toFixed(3) : "open it"]]}/>
    <p class="cu-play-note">Mean absolute difference per colour channel, on a scale of 0 to 1. It says how much moved, not whether it got better. Look at where the bright parts are.</p>`;
}

/* ---------- merge first or quantize first. Rounding follows torch.float8_e4m3fn and torch.bfloat16 casts, round half to even; the scale follows comfy/quant_ops.py: largest value / 448. ---------- */
const roundEven = (x) => { const f = Math.floor(x), d = x - f; return d > .5 ? f + 1 : d < .5 ? f : f % 2 === 0 ? f : f + 1; };
export function toFloat(x, mant, minExp) { if (x === 0) return 0; const a = Math.abs(x); let e = Math.floor(Math.log2(a)); if (e < minExp) e = minExp; const step = Math.pow(2, e - mant); return Math.sign(x) * roundEven(a / step) * step; }
export const e4m3 = (x) => toFloat(x, 3, -6);
export const bf16 = (x) => toFloat(x, 7, -126);
export function mergeOrder(fmt, frac, n = 6000) {
  const r = rng(424242), base = [], a = [], b = []; for (let i = 0; i < n; i++) { const w = .02 * gauss(r); base.push(w); a.push(w + frac * .02 * gauss(r)); b.push(w + frac * .02 * gauss(r)); }
  const store = (x) => { if (fmt === "bf16") return x.map(bf16); const s = Math.max(...x.map(Math.abs)) / 448; return x.map((v) => e4m3(v / s) * s); };
  const rms = (x) => Math.sqrt(mean(x.map((v) => v * v))); const sub = (p, q) => p.map((v, i) => v - q[i]); const truth = a.map((v, i) => .5 * v + .5 * b[i]); const qa = store(a), qb = store(b), qbase = store(base);
  const once = rms(sub(store(truth), truth)) / rms(truth), twice = rms(sub(store(qa.map((v, i) => .5 * v + .5 * qb[i])), truth)) / rms(truth);
  const dt = sub(b, base), dq = sub(qb, qbase); const corr = dt.reduce((t, v, i) => t + v * dq[i], 0) / (Math.sqrt(dt.reduce((t, v) => t + v * v, 0)) * Math.sqrt(dq.reduce((t, v) => t + v * v, 0)) || 1);
  return { once, twice, corr };
}
function MergeOrder({ onPass }) {
  const [fmt, setFmt] = useState("fp8"); const [pct, setPct] = useState(10); const [saw, setSaw] = useState(false); const r = useMemo(() => mergeOrder(fmt, pct / 100), [fmt, pct]);
  useEffect(() => { if (fmt === "fp8" && r.corr < .7) setSaw(true); }, [fmt, r.corr]); const ok = saw && fmt === "bf16" && r.corr > .95 && pct <= 3; useEffect(() => { if (ok) onPass(); }, [ok]);
  return html`<div class="cu-ctlrow"><${Seg} label="Parents stored as" value=${fmt} opts=${[["fp8", "FP8"], ["bf16", "bf16"]]} onPick=${setFmt}/><${Slider} label="How much the fine-tune moved each weight" value=${pct} min=${1} max=${30} show=${pct + "%"} onInput=${setPct}/></div>
    <${Read} items=${[["Merged first, rounded once: error", r.once.toFixed(4), "good"], ["Rounded, merged, rounded: error", r.twice.toFixed(4), r.twice > r.once * 1.1 ? "bad" : ""], ["Change read back from stored parents: correlation", r.corr.toFixed(3), r.corr < .7 ? "bad" : r.corr > .95 ? "good" : ""]]}/>
    <p class="cu-play-note">Stand-in weights, not a real model. Errors are shares of the weights' size. Rounding to nearest. The difference between two stored files carries both files' rounding errors, and small changes drown in them.</p>`;
}

/* ---------- how often each picture is seen. Each step draws a fresh random subset, as TrainSampler does with torch.randperm. This generator is our own, so counts differ from a real run's. ---------- */
export function coverage(n, steps, batch, seed = 7) { const r = rng(seed), c = new Array(n).fill(0), a = Array.from({ length: n }, (_, i) => i); for (let s = 0; s < steps; s++) for (let j = 0; j < Math.min(batch, n); j++) { const k = j + Math.floor(r() * (n - j)); [a[j], a[k]] = [a[k], a[j]]; c[a[j]]++; } return c; }
function Coverage({ onPass }) {
  const [n, setN] = useState(12); const [steps, setSteps] = useState(300); const [batch, setBatch] = useState(1); const c = useMemo(() => coverage(n, steps, batch), [n, steps, batch]); const lo = Math.min(...c), hi = Math.max(...c);
  const ok = n >= 30 && lo >= 10 && steps * batch <= 1000; useEffect(() => { if (ok) onPass(); }, [ok]); const W = 640, H = 120;
  return html`<div class="cu-ctlrow"><${Slider} label="Pictures" value=${n} min=${5} max=${120} onInput=${setN}/><${Slider} label="Steps" value=${steps} min=${25} max=${2000} step=${25} onInput=${setSteps}/><${Slider} label="Batch size" value=${batch} min=${1} max=${4} onInput=${setBatch}/></div>
    <svg class="cu-chart low" viewBox=${`0 0 ${W} ${H}`} role="img" aria-label=${`Sightings per picture, from ${lo} to ${hi}`}>${c.map((v, i) => html`<rect key=${i} x=${4 + i * (W - 8) / n} y=${H - 4 - v / Math.max(hi, 1) * (H - 8)} width=${Math.max(1, (W - 8) / n - 1)} height=${v / Math.max(hi, 1) * (H - 8)} fill="#f5c518"/>`)}</svg>
    <${Read} items=${[["Average", (steps * batch / n).toFixed(1)], ["Fewest sightings", lo, lo >= 10 ? "good" : lo === 0 ? "bad" : ""], ["Most sightings", hi], ["Never seen", c.filter((x) => x === 0).length]]}/>
    <p class="cu-play-note">A step in core's trainer picks its pictures afresh, so nothing makes the counts even. Our own random generator here, so a real run's counts differ.</p>`;
}

export const MORE = {
  maskgrid: { title: "A mask on the sampler's grid", task: "Hide a stripe 2 or 3 pixels wide from the sampler. Then set grow_mask_by to 6 so that the same stripe shows.", C: MaskGrid, after: "A thin mask can vanish. Growing it, or a wider mask, is what brings it back." },
  depthnorm: { title: "Depth to grey", task: "See min_max collapse with some sky. Then, at 30% sky or more, pick a render that keeps at least 200 grey levels.", C: DepthNorm, after: "One far pixel value can use up the whole grey range. A percentile cut only helps while the sky stays under about 1% of the picture. A sky mask or disparity holds up at any share." },
  outpad: { title: "The outpaint mask", task: "Keep a soft ramp of at least 20 pixels and still repaint no more than 8 pixels of your picture after rounding.", C: OutPad, after: "VAEEncodeForInpaint throws the ramp away. Only the part of it above one half survives." },
  adapters: { title: "What each adapter stores", task: "On a 1280 layer, find a LoKr factor that stores fewer numbers than a rank 8 LoRA.", C: Adapters, after: "Factor 16 and 32 win on size. Factor 8 does not. On a smaller layer the answer changes again." },
  lossread: { title: "Read a real loss curve", task: "Average over at least 30 steps, then compare the first window and the last.", C: LossRead, after: "The average did not fall in this run. That alone tells you nothing about the LoRA. The pictures are the test." },
  diffpair: { title: "How much did it change?", task: "Open all three pairs and compare their numbers.", C: DiffPair, after: "A big number says the picture moved. It cannot say the LoRA is good. The harbour moved about as much as two unrelated pictures." },
  mergeorder: { title: "Merge first or quantize first", task: "Find where FP8 parents lose the change (correlation under 0.7). Then keep the change small, 3% or less, and switch to bf16.", C: MergeOrder, after: "The final file is rounded either way. What you can choose is to round once." },
  coverage: { title: "How often is each picture seen?", task: "With 30 or more pictures, see every picture at least 10 times, in no more than 1000 picture draws.", C: Coverage, after: "The average hides the spread. The rarest picture is what to watch." },
};
