/* ComfyUniversity labs for the guidance and conditioning tracks. No model and no GPU. The sums are ports of ComfyUI v0.43.0 functions, named beside each one, and were compared with the real functions on a CPU. A lab calls onPass when the learner has done its task. */
import { useEffect, useMemo, useState } from "preact/hooks";
import { html } from "./common.js";

const Slider = ({ label, value, min, max, step = 1, onInput, show }) => html`<label class="cu-ctl"><span>${label} <b>${show != null ? show : value}</b></span><input type="range" min=${min} max=${max} step=${step} value=${value} onInput=${(e) => onInput(+e.target.value)}/></label>`;
const Seg = ({ label, value, opts, onPick }) => html`<div class="cu-ctl"><span>${label}</span><div class="cu-seg" role="group" aria-label=${label}>${opts.map(([k, l]) => html`<button type="button" aria-pressed=${value === k} onClick=${() => onPick(k)}>${l}</button>`)}</div></div>`;
const Read = ({ items }) => html`<dl class="cu-read">${items.map(([k, v, cls]) => html`<div class=${cls || ""}><dt>${k}</dt><dd>${v}</dd></div>`)}</dl>`;

/* ---------- pure sums ---------- */
const add = (a, b) => [a[0] + b[0], a[1] + b[1]]; const sub = (a, b) => [a[0] - b[0], a[1] - b[1]]; const mul = (a, s) => [a[0] * s, a[1] * s]; const dot = (a, b) => a[0] * b[0] + a[1] * b[1];
const unit = (deg) => [Math.cos(deg * Math.PI / 180), Math.sin(deg * Math.PI / 180)];
/* cfg_function in comfy/samplers.py */
export const cfgSum = (c, u, s) => add(u, mul(sub(c, u), s));
/* perp_neg in comfy_extras/nodes_perpneg.py, measured from the empty prediction e = origin */
export const perpNeg = (pos, neg, s, negScale = 1) => { const perp = sub(neg, mul(pos, dot(neg, pos) / dot(pos, pos))); return mul(sub(pos, mul(perp, negScale)), s); };

const LAT = { c: [1.1, -.6, .4, .9, -1.2, .7, -.3, .5, 1.3, -.9, .2, -.5, .8, -1, .6, -.2], u: [.8, -.5, .5, .7, -.9, .6, -.1, .3, .9, -.7, .3, -.4, .6, -.8, .5, -.1], x: [2.1, -3, .7, 2.6, -1.4, 3.3, -2.2, .4, 2.9, -1.8, 1.2, -3.1, .9, -2.5, 1.7, -.6] };
const std = (a) => { const m = a.reduce((x, y) => x + y, 0) / a.length; return Math.sqrt(a.reduce((x, y) => x + (y - m) ** 2, 0) / (a.length - 1)); };
const norm = (a) => Math.sqrt(a.reduce((x, y) => x + y * y, 0));
/* Each fix on one row of cells: RescaleCFG's flow branch, CFGNorm with a one-channel cell, APG with momentum 0, and CFGZeroStar with a made-up noisy input x. */
export function fixRow(method, s, eta = 0, thr = 3) {
  const { c, u } = LAT; const plain = c.map((v, i) => u[i] + (v - u[i]) * s);
  if (method === "rescale") { const k = std(c) / std(plain); return plain.map((v) => .7 * v * k + .3 * v); }
  if (method === "cfgnorm") return plain.map((v, i) => v * Math.min(1, Math.abs(c[i]) / (Math.abs(v) + 1e-8)));
  if (method === "apg") { let g = c.map((v, i) => v - u[i]); const n = norm(g); if (thr > 0) g = g.map((v) => v * Math.min(1, thr / n)); const nc = norm(c); const along = g.reduce((a, v, i) => a + v * c[i] / nc, 0); const par = c.map((v) => along * v / nc); const orth = g.map((v, i) => v - par[i]); return c.map((v, i) => v + s * (orth[i] + eta * par[i])); }
  if (method === "zero") { const { x } = LAT; const a = c.reduce((t, v, i) => t + (x[i] - v) * (x[i] - u[i]), 0) / u.reduce((t, v, i) => t + (x[i] - v) ** 2, 0); return plain.map((v, i) => v + u[i] * (a - 1) + s * u[i] * (1 - a)); }
  return plain;
}
/* Exact denoisers for two 1-D blobs. The prompt asks for the blob at +1.5. Same toy as the CU-321 lab. */
const den = (x, sg) => { const v = .25 + sg * sg; const c = (.25 * x + sg * sg * 1.5) / v; const a = Math.exp(-.5 * (x + 1) ** 2 / v), b = Math.exp(-.5 * (x - 1.5) ** 2 / v); const u = (a * (.25 * x - sg * sg) + b * (.25 * x + sg * sg * 1.5)) / ((a + b) * v); return [c, u]; };
const karras = (n, lo = .03, hi = 14.6, rho = 7) => { const r = []; for (let i = 0; i < n; i++) r.push((hi ** (1 / rho) + (i / (n - 1)) * (lo ** (1 / rho) - hi ** (1 / rho))) ** rho); r.push(0); return r; };
/* sample_euler_cfg_pp and plain Euler in comfy/k_diffusion/sampling.py. The one difference: which prediction re-noises. */
export function solve(pp, s, x0) { const sg = karras(20); let x = x0; for (let i = 0; i < 20; i++) { const [c, u] = den(x, sg[i]); const d = u + (c - u) * s; x = sg[i + 1] === 0 ? d : pp ? d + sg[i + 1] * (x - u) / sg[i] : x + (x - d) / sg[i] * (sg[i + 1] - sg[i]); } return x; }
const STARTS = [-1.7, -1.2, -.8, -.5, -.2, 0, .2, .5, .8, 1.2, 1.7, 2.1].map((v) => v * 14.6);
/* Predictions per step, from sampling_function and each node's source. */
export function predictions({ cfg, pag, sag, pp, perp }) { if (perp) return 3 + (pag ? 1 : 0) + (sag ? 1 : 0); const second = Math.abs(cfg - 1) > 1e-9 || sag || pp; return 1 + (second ? 1 : 0) + (pag ? 1 : 0) + (sag ? 1 : 0); }
/* The strength ramp of get_area_and_mult in comfy/samplers.py, for one axis. */
export function ramp(size, off, total, fuzz = 8) { const m = new Array(size).fill(1); const rr = Math.min(fuzz, Math.floor(size / 4)); if (off !== 0) for (let t = 0; t < rr; t++) m[t] *= (t + 1) / rr; if (size + off < total) for (let t = 0; t < rr; t++) m[size - 1 - t] *= (t + 1) / rr; return m; }
/* SDTokenizer.tokenize_with_weights reshaping, for single-token words. */
export function clipChunks(t) { return Math.max(1, Math.ceil(t / 75)); }

/* ---------- labs ---------- */
const VS = 150; const px = (v, k) => VS + v[0] * k; const py = (v, k) => VS - v[1] * k;
const Arrow = ({ to, k, color, label, from = [0, 0], dy = -6 }) => html`<g><line x1=${px(from, k)} y1=${py(from, k)} x2=${px(to, k)} y2=${py(to, k)} stroke=${color} stroke-width="3" stroke-linecap="round"/><circle cx=${px(to, k)} cy=${py(to, k)} r="4" fill=${color}/><text x=${px(to, k) > 230 ? px(to, k) - 6 : px(to, k) + 6} y=${Math.min(294, Math.max(13, py(to, k) + dy))} text-anchor=${px(to, k) > 230 ? "end" : "start"} fill=${color} font-size="13">${label}</text></g>`;
function NegArrow({ onPass }) {
  const [cfg, setCfg] = useState(7); const [ang, setAng] = useState(120); const [low, setLow] = useState([120, 120]); const pos = [1, 0]; const neg = unit(ang); const r = cfgSum(pos, neg, cfg); const k = Math.min(55, 130 / Math.max(1.2, Math.hypot(...r)));
  useEffect(() => { if (cfg === 1) setLow(([a, b]) => [Math.min(a, ang), Math.max(b, ang)]); }, [cfg, ang]); const swung = low[1] - low[0] >= 90;
  useEffect(() => { if (swung && cfg >= 7 && ang === 180) onPass(); }, [swung, cfg, ang]);
  return html`<div class="cu-play-grid"><div class="cu-ctls"><${Slider} label="CFG" value=${cfg} min=${0} max=${14} step=${.5} onInput=${setCfg}/><${Slider} label="Angle of the negative" value=${ang} min=${0} max=${180} step=${5} show=${ang + "°"} onInput=${setAng}/><${Read} items=${[["Result along the positive", r[0].toFixed(2)], ["Result off to the side", (Math.abs(r[1]) < .005 ? 0 : r[1]).toFixed(2)], ["Swing seen at CFG 1", `${low[1] - low[0]}°`, swung ? "good" : ""]]}/><p class="cu-play-note"><code>neg + (pos - neg) * cfg</code>. Two made-up predictions as arrows. Real ones have thousands of numbers, but the sum is the same.</p></div>
    <svg class="cu-chart world" viewBox="0 0 300 300" role="img" aria-label=${`The result arrow reaches ${r[0].toFixed(1)} along the positive`}><${Arrow} to=${pos} k=${k} color="#2bb886" label="pos" dy=${20}/><${Arrow} to=${neg} k=${k} color="#ee7a7a" label="neg"/><${Arrow} to=${r} k=${k} color="#f5c518" label="result"/></svg></div>`;
}
function Perp({ onPass }) {
  const [cfg, setCfg] = useState(7); const [ang, setAng] = useState(60); const [ns, setNs] = useState(1); const pos = [1, 0]; const neg = unit(ang); const plain = cfgSum(pos, neg, cfg); const pn = perpNeg(pos, neg, cfg, ns); const mx = Math.max(1.2, Math.hypot(...plain), Math.hypot(...pn)); const k = 130 / mx; const ok = ang <= 15 && cfg >= 5 && ns > 0 && pn[0] > 3 * plain[0];
  useEffect(() => { if (ok) onPass(); }, [ok]);
  return html`<div class="cu-play-grid"><div class="cu-ctls"><${Slider} label="CFG" value=${cfg} min=${1} max=${14} step=${.5} onInput=${setCfg}/><${Slider} label="Angle between negative and positive" value=${ang} min=${0} max=${180} step=${5} show=${ang + "°"} onInput=${setAng}/><${Slider} label="neg_scale" value=${ns} min=${0} max=${3} step=${.1} show=${ns.toFixed(1)} onInput=${setNs}/><${Read} items=${[["Plain CFG, along the positive", plain[0].toFixed(2)], ["Perp-Neg, along the positive", pn[0].toFixed(2), ok ? "good" : ""]]}/><p class="cu-play-note">Both arrows start from the empty prediction, drawn at the centre. Perp-Neg removes only the part of the negative at right angles to the positive. At neg_scale 0 it ignores the negative.</p></div>
    <svg class="cu-chart world" viewBox="0 0 300 300" role="img" aria-label=${`Plain CFG reaches ${plain[0].toFixed(1)} along the positive, Perp-Neg ${pn[0].toFixed(1)}`}><${Arrow} to=${pos} k=${k} color="#2bb886" label="pos" dy=${20}/><${Arrow} to=${neg} k=${k} color="#ee7a7a" label="neg"/><${Arrow} to=${plain} k=${k} color="#7fb6ff" label="plain" dy=${-24}/><${Arrow} to=${pn} k=${k} color="#f5c518" label="perp-neg"/></svg></div>`;
}
const FIXES = [["plain", "Plain"], ["rescale", "Rescale 0.7"], ["cfgnorm", "CFGNorm"], ["apg", "APG"], ["zero", "Zero-Star"]];
function CfgFix({ onPass }) {
  const [m, setM] = useState("plain"); const [cfg, setCfg] = useState(14); const [eta, setEta] = useState(1); const row = useMemo(() => fixRow(m, cfg, eta), [m, cfg, eta]); const mxC = Math.max(...LAT.c.map(Math.abs)); const mx = Math.max(...row.map(Math.abs)); const [seen, setSeen] = useState(new Set()); const tame = cfg >= 12 && m !== "plain" && mx <= 2.5 * mxC;
  useEffect(() => { if (tame) setSeen((s) => new Set(s).add(m)); }, [tame, m]); useEffect(() => { if (seen.size >= 2) onPass(); }, [seen]); const k = 60 / Math.max(mx, mxC);
  return html`<div class="cu-ctlrow"><${Seg} label="Method" value=${m} opts=${FIXES} onPick=${setM}/><${Slider} label="CFG" value=${cfg} min=${1} max=${20} step=${.5} onInput=${setCfg}/>${m === "apg" ? html`<${Slider} label="eta" value=${eta} min=${0} max=${1} step=${.05} show=${eta.toFixed(2)} onInput=${setEta}/>` : null}</div>
    <svg class="cu-chart" viewBox="0 0 320 130" role="img" aria-label=${`Largest value ${mx.toFixed(2)} against ${mxC.toFixed(2)} for the positive`}><line x1="0" x2="320" y1="65" y2="65" stroke="rgba(255,255,255,.3)"/>${row.map((v, i) => html`<rect key=${i} x=${i * 20 + 3} width="14" y=${v >= 0 ? 65 - v * k : 65} height=${Math.abs(v) * k} fill="#f5c518"/>`)}${LAT.c.map((v, i) => html`<circle key=${i} cx=${i * 20 + 10} cy=${65 - v * k} r="2.5" fill="#2bb886"/>`)}</svg>
    <${Read} items=${[["Largest value", mx.toFixed(2), tame ? "good" : ""], ["The positive's largest", mxC.toFixed(2)], ["Spread (std)", std(row).toFixed(2)], ["The positive's spread", std(LAT.c).toFixed(2)], ["Fixes that tamed CFG 12 or more", String(seen.size)]]}/><p class="cu-play-note">Bars are the result on one made-up row of cells, dots the positive prediction. A row is too small to show what each fix does to a picture, so read the renders above for that.</p>`;
}
function CfgPP({ onPass }) {
  const [pp, setPp] = useState(1); const [s, setS] = useState(7); const res = useMemo(() => STARTS.map((x) => solve(!!pp, s, x)), [pp, s]); const m = res.reduce((a, b) => a + b, 0) / res.length; const off = Math.abs(m - 1.5); const [seen, setSeen] = useState(new Set()); const low = pp === 1 && s < 1 && off <= .25; const calls = predictions({ cfg: s, pp: !!pp });
  useEffect(() => { if (s === 7 && pp === 1) setSeen((v) => new Set(v).add("high")); if (low) setSeen((v) => new Set(v).add("low")); }, [s, pp, low]); useEffect(() => { if (seen.has("high") && seen.has("low")) onPass(); }, [seen]); const sx = (v) => 160 + Math.max(-150, Math.min(150, v * 18));
  return html`<div class="cu-ctlrow"><${Seg} label="Sampler" value=${pp} opts=${[[0, "euler"], [1, "euler_cfg_pp"]]} onPick=${setPp}/><${Slider} label="cfg" value=${s} min=${0} max=${14} step=${.1} show=${s.toFixed(1)} onInput=${setS}/></div>
    <svg class="cu-chart" viewBox="0 0 320 70" role="img" aria-label=${`Samples average ${m.toFixed(2)}. The target is 1.5`}><line x1="0" x2="320" y1="35" y2="35" stroke="rgba(255,255,255,.3)"/><rect x=${sx(1)} width=${sx(2) - sx(1)} y="15" height="40" fill="rgba(245,197,24,.2)" stroke="#f5c518"/>${res.map((v, i) => html`<circle key=${i} cx=${sx(v)} cy=${35 + (i % 3 - 1) * 8} r="3" fill="#7fb6ff"/>`)}</svg>
    <${Read} items=${[["Average of the samples", m.toFixed(2)], ["Distance from the target, 1.5", off.toFixed(2), off <= .25 ? "good" : ""], ["Predictions per step", String(calls)]]}/><p class="cu-play-note">Two blobs with exact predictions, 20 steps from the same 12 starts. Only one thing differs between the samplers: which prediction re-noises the sample.</p>`;
}
function Calls({ onPass }) {
  const [cfg, setCfg] = useState(7); const [o, setO] = useState({ pag: false, sag: false, tcfg: false, pp: false, perp: false }); const flip = (k) => setO({ ...o, [k]: !o[k] }); const n = predictions({ cfg, ...o }); const [seen, setSeen] = useState(new Set());
  useEffect(() => { if (cfg === 1 && n === 1) setSeen((s) => new Set(s).add("one")); if (cfg === 1 && n === 3) setSeen((s) => new Set(s).add("three")); }, [cfg, n]); useEffect(() => { if (seen.size === 2) onPass(); }, [seen]);
  const opts = [["pag", "PAG"], ["sag", "SAG"], ["tcfg", "TCFG"], ["pp", "CFG++ sampler"], ["perp", "Perp-Neg guider"]];
  return html`<div class="cu-ctlrow"><${Slider} label="cfg" value=${cfg} min=${0} max=${14} step=${.5} onInput=${setCfg}/><div class="cu-ctl"><span>Add to the graph</span><div class="cu-seg" role="group" aria-label="Add to the graph">${opts.map(([k, l]) => html`<button type="button" aria-pressed=${o[k]} onClick=${() => flip(k)}>${l}</button>`)}</div></div></div>
    <${Read} items=${[["Predictions per step", String(n), "good"], ["Over 20 Euler steps", String(n * 20)], ["Solved at cfg 1", [...seen].sort().join(" and ") || "not yet"]]}/><p class="cu-play-note">Counted from each node's source. Two predictions may share one batch if memory allows, so this counts work, not always separate trips. TCFG adds an SVD and no prediction.</p>`;
}
function Embed({ onPass }) {
  const [emb, setEmb] = useState(0); const [cfg, setCfg] = useState(7); const [g, setG] = useState(3.5); const [seen, setSeen] = useState(false); const preds = Math.abs(cfg - 1) < 1e-9 ? 1 : 2; const on = emb === 1;
  const moveG = (v) => { setG(v); if (!on) setSeen(true); }; const ok = on && cfg === 1 && seen; useEffect(() => { if (ok) onPass(); }, [ok]);
  return html`<div class="cu-ctlrow"><${Seg} label="The weights file" value=${emb} opts=${[[0, "No guidance_in"], [1, "Has guidance_in"]]} onPick=${setEmb}/><${Slider} label="cfg" value=${cfg} min=${1} max=${8} step=${.5} onInput=${setCfg}/><${Slider} label="FluxGuidance" value=${g} min=${0} max=${10} step=${.5} onInput=${moveG}/></div>
    <${Read} items=${[["Predictions per step", String(preds), preds === 1 ? "good" : ""], ["Does the negative count?", preds === 1 ? "no, it is never run" : "yes"], ["What the model gets from the guidance number", on ? `${g} goes in beside the timestep` : "nothing: it is skipped"]]}/><p class="cu-play-note">From <code>sampling_function</code> and <code>forward_orig</code> in the Flux model. The cfg sum happens outside the model. The guidance number goes inside it.</p>`;
}
const START = () => [{ tokens: 77, keys: ["pooled_output"] }];
function condLab(pass) {
  return function CondKeys({ onPass }) {
    const [c, setC] = useState(START()); const set = (k, ...more) => setC(c.map((e) => ({ ...e, keys: [...new Set([...e.keys, k, ...more])] }))); useEffect(() => { if (pass(c)) onPass(); }, [c]);
    const acts = [["ConditioningSetArea", () => set("area", "strength", "set_area_to_bounds")], ["ConditioningSetMask", () => set("mask", "mask_strength", "set_area_to_bounds")], ["SetTimestepRange", () => set("start_percent", "end_percent")], ["FluxGuidance", () => set("guidance")], ["Combine with a second prompt", () => setC([...c, ...START()])], ["Concat a second prompt", () => setC(c.map((e) => ({ ...e, tokens: e.tokens + 77 })))], ["StyleModelApply (8 tokens)", () => setC(c.map((e) => ({ ...e, tokens: e.tokens + 8 })))], ["unCLIPConditioning", () => set("unclip_conditioning")]];
    return html`<div class="cu-lab-acts">${acts.map(([l, f]) => html`<button type="button" class="cu-btn" onClick=${f}>${l}</button>`)}<button type="button" class="cu-btn primary" onClick=${() => setC(START())}>Start again</button></div><ol class="cu-tokens">${c.map((e, i) => html`<li key=${i}><span>entry ${i}: tensor [1, ${e.tokens}, 768]</span><b>${e.keys.join(", ")}</b></li>`)}</ol><p class="cu-play-note">An SD 1.5 prompt to start with. Each button does what the node does to the list. A node that sets a key changes every entry, and a Combine lengthens the list.</p>`;
  };
}
const CondKeysA = condLab((c) => c.length >= 2 && c.some((e) => e.keys.includes("area") && e.keys.includes("start_percent")));
const CondKeysB = condLab((c) => c.some((e) => e.tokens === 85 && e.keys.includes("unclip_conditioning")));
function CondList({ onPass }) {
  const [op, setOp] = useState("combine"); const [st, setSt] = useState(.6); const [seen, setSeen] = useState(new Set()); useEffect(() => setSeen((s) => new Set(s).add(op)), [op]); useEffect(() => { if (seen.size === 3 && op === "concat") onPass(); }, [seen, op]);
  const rows = { combine: ["2 entries", "[1, 77, 768] each", "3: positive A, positive B, negative", "Blends the model's answers"], concat: ["1 entry", "[1, 154, 768]", "2: positive, negative", "One answer that attends to both texts"], average: ["1 entry", "[1, 77, 768]", "2: positive, negative", `One answer from one blend: ${st.toFixed(2)} of A, ${(1 - st).toFixed(2)} of B`] }[op];
  return html`<div class="cu-ctlrow"><${Seg} label="Node" value=${op} opts=${[["combine", "Combine"], ["concat", "Concat"], ["average", "Average"]]} onPick=${setOp}/>${op === "average" ? html`<${Slider} label="conditioning_to_strength" value=${st} min=${0} max=${1} step=${.01} show=${st.toFixed(2)} onInput=${setSt}/>` : null}</div><${Read} items=${[["The list", rows[0]], ["Tensor", rows[1]], ["Predictions per step at cfg 7", rows[2]], ["What happens", rows[3]], ["Nodes tried", `${seen.size} of 3`]]}/><p class="cu-play-note">Two 75-token-or-fewer SD 1.5 prompts. Read from <code>nodes.py</code> and <code>calc_cond_batch</code>.</p>`;
}
function Regions({ onPass }) {
  const W = 96, H = 64; const [x, setX] = useState(256); const [y, setY] = useState(200); const [w, setW] = useState(256); const [h, setH] = useState(256); const [st, setSt] = useState(1); const cw = Math.min(W - (x >> 3), w >> 3), ch = Math.min(H - (y >> 3), h >> 3); const rx = useMemo(() => ramp(cw, x >> 3, W), [cw, x]); const ry = useMemo(() => ramp(ch, y >> 3, H), [ch, y]); const centre = st / (st + 1); const ok = cw === 32 && ch === 32 && w === 256 && h === 256 && x >= 448 && centre >= .75 - 1e-9; useEffect(() => { if (ok) onPass(); }, [ok]);
  const cells = []; for (let j = 0; j < ch; j += 2) for (let i = 0; i < cw; i += 2) { const m = rx[i] * ry[j] * st; cells.push(html`<rect x=${(x >> 3) + i} y=${(y >> 3) + j} width="2" height="2" fill="#f5c518" opacity=${m / (m + 1)}/>`); }
  return html`<div class="cu-ctlrow"><${Slider} label="x" value=${x} min=${0} max=${704} step=${8} onInput=${setX}/><${Slider} label="y" value=${y} min=${0} max=${448} step=${8} onInput=${setY}/><${Slider} label="width" value=${w} min=${64} max=${768} step=${8} onInput=${setW}/><${Slider} label="height" value=${h} min=${64} max=${512} step=${8} onInput=${setH}/><${Slider} label="strength" value=${st} min=${0} max=${5} step=${.25} show=${st.toFixed(2)} onInput=${setSt}/></div>
    <svg class="cu-chart world" viewBox=${`0 0 ${W} ${H}`} role="img" aria-label=${`The boxed prompt has ${(centre * 100).toFixed(0)} percent of the blend at the box centre`}><rect width=${W} height=${H} fill="#223"/>${cells}</svg>
    <${Read} items=${[["Share of the boxed prompt at the centre", `${(centre * 100).toFixed(0)}%`, ok ? "good" : ""], ["Model sees a crop of", `${cw} by ${ch} cells`], ["Predictions per step", "4: whole, box, negative, negative's copy for the box"]]}/><p class="cu-play-note">A 768 by 512 picture is 96 by 64 latent cells. The blue is the whole-picture prompt. Brighter gold is more boxed prompt. Each cell is <code>sum(prediction times weight) / sum(weight)</code>, and the edge fades over up to 8 cells except where the box meets the picture's edge.</p>`;
}
function Chunks({ onPass }) {
  const [t, setT] = useState(60); const [e, setE] = useState("clip"); const n = clipChunks(t); const [seen, setSeen] = useState(new Set()); const shape = { clip: `[1, ${77 * n}, 768]`, sdxl: `[1, ${77 * n}, 2048]`, t5: `[1, ${Math.max(256, t + 1)}, 4096]`, klein: `[1, ${Math.max(512, t)}, 7680]` }[e]; const parts = { clip: `${n} chunk${n > 1 ? "s" : ""} of 77`, sdxl: `${n} chunk${n > 1 ? "s" : ""}, CLIP-L beside CLIP-G`, t5: "one run, padded to at least 256 on the Flux tokenizer", klein: "one run, padded to at least 512, three layers side by side" }[e];
  const hit = e === "clip" && t === 76; useEffect(() => { if (hit) onPass(); }, [hit]); useEffect(() => { setSeen((s) => new Set(s).add(e)); }, [e]);
  return html`<div class="cu-ctlrow"><${Seg} label="Encoder" value=${e} opts=${[["clip", "CLIP-L"], ["sdxl", "SDXL"], ["t5", "T5-XXL"], ["klein", "Qwen3 (Klein)"]]} onPick=${setE}/><${Slider} label="Tokens in your prompt" value=${t} min=${1} max=${320} onInput=${setT}/></div><${Read} items=${[["Tensor", shape, hit ? "good" : ""], ["How", parts], ["Encoders tried", `${seen.size} of 4`]]}/><p class="cu-play-note">A token is not a word: long words often split. Counted here as if each token stood alone, and without the chat template that Klein adds around your text. Read from <code>tokenize_with_weights</code> and each encoder's tokenizer settings.</p>`;
}

export const MORE = {
  negarrow: { title: "A negative is one arrow in a sum", task: "At CFG 1, swing the negative through at least 90 degrees and watch the result stay put. Then at CFG 7 or more, point it dead opposite.", C: NegArrow, after: "At CFG 1 the negative cancels out. Above 1, the further it sits from the positive, the longer the result." },
  perp: { title: "Plain CFG against Perp-Neg", task: "Point the negative within 15 degrees of the positive at CFG 5 or more, until Perp-Neg goes at least three times further along the positive than plain CFG.", C: Perp, after: "When two prompts overlap, plain CFG cancels what they share. Perp-Neg keeps it." },
  cfgfix: { title: "Four ways to tame high CFG", task: "At CFG 12 or more, bring the largest value within 2.5 times the positive's, using two different methods.", C: CfgFix, after: "Zero-Star does not try to limit size, and APG at eta 1 limits only through its norm threshold." },
  cfgpp: { title: "Plain Euler against CFG++", task: "With euler_cfg_pp, look at cfg 7. Then find a cfg below 1 that lands near the target.", C: CfgPP, after: "CFG++ has its own scale. Never carry a cfg number across from a plain sampler." },
  calls: { title: "What does a step cost?", task: "At cfg 1, find a setup that costs one prediction per step, and one that costs three.", C: Calls, after: "Cfg 1 is only cheap when nothing has asked for the second branch." },
  embed: { title: "Guidance as a sum or as an input", task: "On a file with no guidance_in, move the guidance number and see nothing change. Then get one prediction per step with a guidance number the model really receives.", C: Embed },
  condkeys: { title: "Build a CONDITIONING by hand", task: "Make a list of two or more entries where one carries both an area and a start_percent.", C: CondKeysA },
  condref: { title: "Two ways in for a picture", task: "Make one entry with 85 tokens and an unclip_conditioning key: a style model and unCLIP together.", C: CondKeysB, after: "A style model lengthens the tensor. unCLIP leaves it alone and sets a key." },
  condlist: { title: "Combine, Concat, Average", task: "Try all three nodes, and end on the one that attends to both prompts in a single prediction.", C: CondList },
  regions: { title: "Where a box prompt wins", task: "Make a 256 by 256 box at the right of the picture, x at least 448 and fully inside the frame, and give it at least 75% at its centre.", C: Regions, after: "Strength is a share against whatever else covers the cell, not a volume knob." },
  chunks: { title: "Prompt length to tensor shape", task: "With CLIP-L, find the exact token count where a second chunk begins.", C: Chunks, after: "75 tokens fit a CLIP chunk, because the start and end tokens take the other two places." },
};
