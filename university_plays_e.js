/* ComfyUniversity labs for video, audio and 3D. Pure maths first, checked against the ComfyUI v0.43.0 functions named beside each one. */
import { useEffect, useMemo, useRef, useState } from "preact/hooks";
import { html } from "./common.js";

const Slider = ({ label, value, min, max, step = 1, onInput, show }) => html`<label class="cu-ctl"><span>${label} <b>${show != null ? show : value}</b></span><input type="range" min=${min} max=${max} step=${step} value=${value} onInput=${(e) => onInput(+e.target.value)}/></label>`;
const Seg = ({ label, value, opts, onPick }) => html`<div class="cu-ctl"><span>${label}</span><div class="cu-seg" role="group" aria-label=${label} style=${{ alignSelf: "flex-start" }}>${opts.map(([k, l]) => html`<button type="button" aria-pressed=${value === k} onClick=${() => onPick(k)}>${l}</button>`)}</div></div>`;
const Read = ({ items }) => html`<dl class="cu-read">${items.map(([k, v, cls]) => html`<div class=${cls || ""}><dt>${k}</dt><dd>${v}</dd></div>`)}</dl>`;
const INK = "#f5c518", BLUE = "#5a9bf0", DIM = "rgba(128,128,128,.35)";

/* tile positions: comfy/utils.py tiled_scale_multidim */
export const tileStarts = (D, S, O) => { const out = []; if (D <= S) return [0]; for (let p = 0; p < D - O; p += S - O) out.push(p); return out; };
export const tileWork = (D, S, O) => tileStarts(D, S, O).reduce((a, p) => a + Math.min(S, D - p), 0) / D;
/* noise layout: comfy/sample.py draws one block in memory order, channel, frame, height, width */
export const noiseKept = (C, T1, H1, W1, T2, H2, W2) => (T1 === T2 && H1 === H2 && W1 === W2) ? 1 : (H1 === H2 && W1 === W2) ? (T2 > T1 ? 1 / C : 1 / C * T2 / T1) : (W1 === W2 ? W1 * Math.min(H1, H2) : Math.min(W1, W2)) / (C * T1 * H1 * W1);
/* receptive field: r = 1 + sum (k - 1) * product of earlier strides */
export const receptive = (layers, k, s) => { let r = 1, j = 1; for (let i = 0; i < layers; i++) { r += (k - 1) * j; j *= s; } return [r, j]; };
/* music 3: comfy/ldm/minimax_music/dit.py latent_length and the window loop in MiniMaxMusic3DiT.forward */
export const latentLength = (f) => Math.max(1, Math.trunc(f * 44100 / 24000 * 960 / 512));
export const ditWindows = (L) => { const win = latentLength(200), hop = latentLength(100); let n = 0, s = 0; while (s < L) { n++; if (Math.min(s + win, L) === L) break; s += hop; } return n; };
/* h3: comfy_extras/nodes_minimax_h3.py temporal_shape */
export const h3Shape = (n) => { let f = Math.max(5, n); while (f % 17 !== 5) f++; const T = f <= 5 ? 2 : Math.floor((f - 5) / 17) * 5 + 2; return [f, T, Math.round(f / 24 * 40)]; };
/* ltx: comfy_extras/nodes_lt.py LTXVScheduler.execute */
export function ltxvScheduler(steps, tokens, terminal = 0.1) {
  const mm = (2.05 - 0.95) / (4096 - 1024), b = 0.95 - mm * 1024, shift = tokens * mm + b, e = Math.exp(shift);
  const raw = []; for (let i = 0; i <= steps; i++) { const s = 1 - i / steps; raw.push(s === 0 ? 0 : e / (e + (1 / s - 1))); }
  const last = 1 - raw[steps - 1], scale = last / (1 - terminal);
  return [shift, raw.map((s) => s === 0 ? 0 : 1 - (1 - s) / scale)];
}
export const DISTILLED = [1, 0.99375, 0.9875, 0.98125, 0.975, 0.909375, 0.725, 0.421875, 0];
/* wan: ModelSamplingSD3's shift, on a plain even grid */
export const shiftGrid = (steps, s) => Array.from({ length: steps }, (_, i) => { const t = 1 - i / steps; return s * t / (1 + (s - 1) * t); });
/* a chain of clips joined by dropping the overlap */
export const chain = (total, clip, ov) => { let n = 1, have = clip; while (have < total) { have += clip - ov; n++; } return [n, have]; };
/* flicker scores: studio/vset/qc.py second difference, on rows of a 1D texture */
const tex1 = (x) => 121 + 60 * Math.sin(x * 0.31) + 40 * Math.sin(x * 0.83 + 1) + 25 * Math.sin(x * 1.9 + 2);
export function flickerScores(pan, strobe, noise) {
  const N = 24, W = 96; let r = 7; const rnd = () => { r = (r * 16807) % 2147483647; return (r / 2147483647 - 0.5) * 2; };
  const v = []; for (let t = 0; t < N; t++) { const row = []; for (let x = 0; x < W; x++) row.push(tex1(x + t * pan) * (1 + strobe * (t % 2 ? -1 : 1)) + noise * rnd()); v.push(row); }
  let vs = 0; for (let x = 0; x < W; x++) { let m = 0, q = 0; for (let t = 0; t < N; t++) m += v[t][x]; m /= N; for (let t = 0; t < N; t++) q += (v[t][x] - m) ** 2; vs += q / N; } vs /= W;
  let d2 = 0, al = 0, c = 0, R = 12; for (let t = 1; t < N - 1; t++) {
    const best = (a, b) => { let bd = 0, be = 1e18; for (let d = -R; d <= R; d++) { let e = 0; for (let x = R; x < W - R; x++) e += Math.abs(a[x] - b[x + d]); if (e < be) { be = e; bd = d; } } return bd; };
    const dp = best(v[t], v[t - 1]), dn = best(v[t], v[t + 1]);
    for (let x = R; x < W - R; x++) { d2 += Math.abs(v[t + 1][x] - 2 * v[t][x] + v[t - 1][x]); al += Math.abs(v[t + 1][x + dn] - 2 * v[t][x] + v[t - 1][x + dp]); c++; }
  }
  return [vs, d2 / c, al / c];
}
/* block outline against an interpolated contour on a 2D grid */
export function isoLengths(res, radius) {
  const h = 2.4 / res, f = (i, j) => radius - Math.hypot(-1.2 + i * h, -1.2 + j * h); let block = 0; const segs = [];
  const cell = (i, j) => f(i + 0.5, j + 0.5) > 0;
  for (let i = 0; i < res; i++) for (let j = 0; j < res; j++) { if (i + 1 < res && cell(i, j) !== cell(i + 1, j)) block += h; if (j + 1 < res && cell(i, j) !== cell(i, j + 1)) block += h; }
  for (let i = 0; i < res; i++) for (let j = 0; j < res; j++) {
    const c = [[i, j], [i + 1, j], [i + 1, j + 1], [i, j + 1]], v = c.map(([a, b]) => f(a, b)), p = [];
    for (let e = 0; e < 4; e++) { const n = (e + 1) % 4; if ((v[e] > 0) !== (v[n] > 0)) { const t = v[e] / (v[e] - v[n]); p.push([c[e][0] + t * (c[n][0] - c[e][0]), c[e][1] + t * (c[n][1] - c[e][1])]); } }
    if (p.length === 2) segs.push(p);
  }
  const contour = segs.reduce((a, [p, q]) => a + Math.hypot(p[0] - q[0], p[1] - q[1]) * h, 0);
  return { h, block, contour, segs, cell };
}
/* collapse the cheapest corner of a closed curve: a 2D stand-in for the edge collapse in qem_decimate.py */
export function simplifyCurve(n, target) {
  let pts = Array.from({ length: n }, (_, i) => { const a = i / n * 2 * Math.PI, r = 1 + 0.15 * Math.sin(5 * a) + 0.04 * Math.sin(17 * a); return [r * Math.cos(a), r * Math.sin(a)]; }); const orig = pts.slice();
  const area = (a, b, c) => Math.abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])) / 2;
  while (pts.length > target) { let bi = 0, be = 1e18; for (let i = 0; i < pts.length; i++) { const e = area(pts[(i - 1 + pts.length) % pts.length], pts[i], pts[(i + 1) % pts.length]); if (e < be) { be = e; bi = i; } } pts.splice(bi, 1); }
  const dseg = (p, a, b) => { const dx = b[0] - a[0], dy = b[1] - a[1], t = Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy || 1))); return Math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy); };
  let err = 0; for (const p of orig) { let d = 1e9; for (let i = 0; i < pts.length; i++) d = Math.min(d, dseg(p, pts[i], pts[(i + 1) % pts.length])); err = Math.max(err, d); }
  return { pts, err };
}

function SeedLayout({ onPass }) {
  const [C, setC] = useState(16); const [T, setT] = useState(21); const [W, setW] = useState(104); const seen = useRef({}); const k = noiseKept(C, 21, 60, 104, T, 60, W); const cv = useRef(null);
  useEffect(() => { if (T === 21 && W === 104) seen.current.same = 1; if (T !== 21 && W === 104) seen.current.frames = 1; if (W !== 104) seen.current.width = 1; if (seen.current.same && seen.current.frames && seen.current.width) onPass(); }, [T, W]);
  useEffect(() => { if (!cv.current) return; const x = cv.current.getContext("2d"), w = 420, h = 60; x.clearRect(0, 0, w, h); x.fillStyle = DIM; x.fillRect(0, 10, w, 40); x.fillStyle = INK; x.fillRect(0, 10, Math.max(k < .01 ? 2 : 0, w * k), 40); x.strokeStyle = "rgba(0,0,0,.4)"; for (let i = 1; i < C && C < 40; i++) { const p = i / C * w; x.beginPath(); x.moveTo(p, 10); x.lineTo(p, 50); x.stroke(); } }, [k, C]);
  return html`<div class="cu-ctlrow"><${Seg} label="Channels" value=${C} opts=${[[16, "16"], [24, "24"], [48, "48"], [128, "128"]]} onPick=${setC}/><${Slider} label="Latent frames, second render" value=${T} min=${11} max=${41} onInput=${setT}/><${Slider} label="Latent width, second render" value=${W} min=${88} max=${120} step=${8} onInput=${setW}/></div>
    <figure class="cu-canvas wide"><canvas ref=${cv} width="420" height="60" role="img" aria-label=${`Share of the first noise kept: ${(k * 100).toFixed(2)} percent`}></canvas></figure><${Read} items=${[["First render", `[${C}, 21, 60, 104]`], ["Second render", `[${C}, ${T}, 60, ${W}]`], ["Same numbers in the same place", (k * 100).toFixed(k < .01 ? 3 : 1) + "%", k === 1 ? "good" : ""]]}/><p class="cu-play-note">The seed fills the block channel by channel, then frame by frame. Each bar segment is one channel. Change the frame count and only the first channel survives.</p>`;
}
function Tiles({ onPass }) {
  const [D, setD] = useState(1024); const [S, setS] = useState(512); const [O, setO] = useState(64); const st = tileStarts(D, S, O); const w = tileWork(D, S, O) ** 2; const cv = useRef(null); const ok = D === 1024 && st.length > 1 && O >= 32 && w <= 1.15; useEffect(() => { if (ok) onPass(); }, [ok]);
  useEffect(() => { if (!cv.current) return; const x = cv.current.getContext("2d"), W = 480, H = 110, k = W / D; x.clearRect(0, 0, W, H); st.forEach((p, i) => { const l = Math.min(S, D - p); const g = x.createLinearGradient(p * k, 0, (p + l) * k, 0), f = Math.min(.5, O / l); g.addColorStop(0, "rgba(245,197,24,.05)"); g.addColorStop(f, "rgba(245,197,24,.9)"); g.addColorStop(1 - f, "rgba(245,197,24,.9)"); g.addColorStop(1, "rgba(245,197,24,.05)"); x.fillStyle = g; x.fillRect(p * k, 8 + (i % 3) * 32, l * k, 26); }); }, [D, S, O]);
  return html`<div class="cu-ctlrow"><${Slider} label="Side in pixels" value=${D} min=${256} max=${2048} step=${64} onInput=${setD}/><${Seg} label="Tile" value=${S} opts=${[[256, "256"], [512, "512"], [1024, "1024"]]} onPick=${setS}/><${Slider} label="Overlap" value=${O} min=${0} max=${128} step=${16} onInput=${setO}/></div>
    <figure class="cu-canvas wide"><canvas ref=${cv} width="480" height="110" role="img" aria-label=${`${st.length} tiles along a side of ${D} pixels`}></canvas></figure><${Read} items=${[["Tiles per side", st.length], ["Model calls, square image", st.length ** 2], ["Last tile length", Math.min(S, D - st[st.length - 1])], ["Pixels fed in / pixels", w.toFixed(3), ok ? "good" : ""]]}/><p class="cu-play-note">Positions from <code>tiled_scale_multidim</code>. The fade on each bar is its weight mask: edges count least.</p>`;
}
function Flow({ onPass }) {
  const [u, setU] = useState(0); const [v, setV] = useState(0); const [kind, setKind] = useState("pan"); const cv = useRef(null); const TU = 7, TV = -4, S = 120;
  const tx = (x, y) => 127 + 50 * Math.sin(x * .19 + y * .07) + 40 * Math.sin(y * .23 - x * .05) + 30 * Math.sin((x + y) * .41);
  const [err, grid] = useMemo(() => { let e = 0; const g = new Float32Array(S * S); for (let y = 0; y < S; y++) for (let x = 0; x < S; x++) { const b = kind === "pan" ? tx(x - TU, y - TV) : tx(x, y) * 1.1; const d = Math.abs(tx(x - u, y - v) - b); e += d; g[y * S + x] = d; } return [e / (S * S), g]; }, [u, v, kind]);
  useEffect(() => { if (!cv.current) return; const c = cv.current.getContext("2d"), o = c.createImageData(S, S); for (let i = 0; i < S * S; i++) { const p = 4 * i; o.data[p] = o.data[p + 1] = o.data[p + 2] = Math.min(255, grid[i] * 3); o.data[p + 3] = 255; } c.putImageData(o, 0, 0); }, [grid]);
  const ok = kind === "pan" && err < .5; useEffect(() => { if (ok) onPass(); }, [ok]);
  return html`<div class="cu-play-grid"><div class="cu-ctls"><${Seg} label="What changed" value=${kind} opts=${[["pan", "The camera moved"], ["flick", "Brightness jumped"]]} onPick=${setKind}/><${Slider} label="Your guess, sideways" value=${u} min=${-10} max=${10} onInput=${setU}/><${Slider} label="Your guess, up and down" value=${v} min=${-10} max=${10} onInput=${setV}/><${Read} items=${[["Left over per pixel", err.toFixed(2), ok ? "good" : ""]]}/><p class="cu-play-note">The picture is frame 2 minus frame 1 moved by your guess. The right guess makes real motion vanish. No guess makes a brightness jump vanish: that is what flicker looks like.</p></div><figure class="cu-canvas"><canvas ref=${cv} width=${S} height=${S} style="width:100%;image-rendering:pixelated" role="img" aria-label=${`Difference after your guess, mean ${err.toFixed(1)}`}></canvas></figure></div>`;
}
function Rf({ onPass }) {
  const [L, setL] = useState(2); const [k, setK] = useState(3); const [s, setS] = useState(2); const [causal, setC] = useState(true); const [r, j] = receptive(L, k, s); const ok = r >= 63 && L <= 5; useEffect(() => { if (ok) onPass(); }, [ok]);
  const W = 460, mid = causal ? W - 20 : W / 2, px = Math.min(W - 40, r * 3); const left = causal ? mid - px : mid - px / 2;
  return html`<div class="cu-ctlrow"><${Slider} label="Layers" value=${L} min=${1} max=${8} onInput=${setL}/><${Seg} label="Kernel" value=${k} opts=${[[3, "3"], [5, "5"]]} onPick=${setK}/><${Seg} label="Stride" value=${s} opts=${[[1, "1"], [2, "2"]]} onPick=${setS}/><${Seg} label="In time" value=${causal ? "c" : "n"} opts=${[["c", "Causal"], ["n", "Centred"]]} onPick=${(x) => setC(x === "c")}/></div>
    <svg viewBox=${`0 0 ${W} 60`} width="100%" role="img" aria-label=${`One output sees ${r} inputs`}><rect x=${left} y="16" width=${px} height="24" fill=${INK} rx="3"/><line x1=${mid} x2=${mid} y1="6" y2="50" stroke=${BLUE} stroke-width="2"/></svg>
    <${Read} items=${[["One output sees", r + " inputs", ok ? "good" : ""], ["Outputs are spaced", j + " inputs apart"], ["Runs into the future", causal ? "No" : (r - 1) / 2 + " inputs"]]}/><p class="cu-play-note">The blue line is the frame being computed. The bar is to scale up to 140 inputs, then stops growing. Formula checked by experiment in this lesson's lab. Strides multiply how far every later layer reaches.</p>`;
}
function Flicker({ onPass }) {
  const [pan, setPan] = useState(0); const [st, setSt] = useState(0); const [n, setN] = useState(0); const [vs, d2, al] = useMemo(() => flickerScores(pan, st / 100, n), [pan, st, n]); const ok = pan >= 3 && st === 0 && n === 0; useEffect(() => { if (ok && d2 > 5 && al < 1) onPass(); }, [ok, d2, al]);
  return html`<div class="cu-ctlrow"><${Slider} label="Camera pan, pixels a frame" value=${pan} min=${0} max=${8} onInput=${setPan}/><${Slider} label="Brightness strobe, percent" value=${st} min=${0} max=${8} onInput=${setSt}/><${Slider} label="Boiling noise, levels" value=${n} min=${0} max=${10} onInput=${setN}/></div>
    <${Read} items=${[["Temporal variance", vs.toFixed(1)], ["Second difference", d2.toFixed(2)], ["Second difference, aligned first", al.toFixed(2), al < 1 ? "good" : ""]]}/><p class="cu-play-note">A pan makes both plain scores jump though nothing flickers. Aligning the frames first removes the motion and keeps strobing and boiling. This runs on one row of texture, so read the pattern and not the size of the numbers.</p>`;
}
function AudioCalls({ onPass }) {
  const [sec, setSec] = useState(30); const [steps, setSteps] = useState(30); const [cfg, setCfg] = useState(true); const fr = Math.min(9000, Math.max(1, Math.round(sec * 25))); const L = latentLength(fr), w = ditWindows(L), mul = cfg ? 2 : 1; const ok = sec >= 360; useEffect(() => { if (ok) onPass(); }, [ok]);
  return html`<div class="cu-ctlrow"><${Slider} label="Seconds" value=${sec} min=${5} max=${420} step=${5} onInput=${setSec}/><${Slider} label="Sampling steps" value=${steps} min=${8} max=${60} onInput=${setSteps}/><${Seg} label="CFG" value=${cfg ? "y" : "n"} opts=${[["y", "On"], ["n", "1.0"]]} onPick=${(k) => setCfg(k === "y")}/></div>
    <${Read} items=${[["WaveNet, a call per sample at 16 kHz", (16000 * sec).toLocaleString("en")], ["MusicGen, 50 frames a second, 4 codebooks", (200 * sec).toLocaleString("en")], ["Music 3 AR frames", fr.toLocaleString("en"), ok ? "good" : ""], ["Music 3 latent [1, 128, L]", L.toLocaleString("en")], ["Music 3 DiT windows per pass", w], ["Music 3 DiT window passes, whole render", (steps * mul * w).toLocaleString("en")]]}/><p class="cu-play-note">Music 3 ceiling: 9000 frames at 25 a second. Past 360 seconds the numbers stop growing. WaveNet and MusicGen rows are from their papers and are not limited here.</p>`;
}
function Iso({ onPass }) {
  const [res, setRes] = useState(16); const [t, setT] = useState(0); const radius = .8 - t; const cv = useRef(null); const q = useMemo(() => isoLengths(res, radius), [res, radius]); const truth = 2 * Math.PI * radius; const ok = res >= 48 && t === 0 && q.block / truth > 1.2 && q.contour / truth < 1.02; useEffect(() => { if (ok) onPass(); }, [ok]);
  useEffect(() => { if (!cv.current) return; const x = cv.current.getContext("2d"), S = 300, k = S / res; x.clearRect(0, 0, S, S); x.fillStyle = "rgba(90,155,240,.35)"; for (let i = 0; i < res; i++) for (let j = 0; j < res; j++) if (q.cell(i, j)) x.fillRect(i * k, j * k, k, k); x.strokeStyle = INK; x.lineWidth = 2; x.beginPath(); for (const [p, r] of q.segs) { x.moveTo(p[0] * k, p[1] * k); x.lineTo(r[0] * k, r[1] * k); } x.stroke(); }, [q]);
  return html`<div class="cu-play-grid"><div class="cu-ctls"><${Slider} label="Grid size" value=${res} min=${8} max=${64} step=${8} onInput=${setRes}/><${Slider} label="Threshold" value=${t} min=${0} max=${.5} step=${.1} onInput=${setT}/><${Read} items=${[["Blocks, outline / true", (q.block / truth).toFixed(3)], ["Contour, length / true", (q.contour / truth).toFixed(3), ok ? "good" : ""]]}/><p class="cu-play-note">A flat slice through a sphere. Stairs stay about 4/π too long in 2D at any grid size. In 3D the same effect is 3/2. Reading values between grid points, as Surface Nets does, fixes it.</p></div><figure class="cu-canvas"><canvas ref=${cv} width="300" height="300" role="img" aria-label=${`A circle on a ${res} grid, as blocks and as a contour`}></canvas></figure></div>`;
}
function AvTime({ onPass }) {
  const [n, setN] = useState(100); const [f, T, A] = h3Shape(n); const ok = n === f && f > 124 && f <= 362; useEffect(() => { if (ok) onPass(); }, [ok]); const W = 460, sh = Math.min(T, 37), px = W / (f <= 124 ? 124 : Math.min(f, 124)); let c = 0; const bars = []; for (let i = 0; i < sh && c < 124; i++) { const l = i % 5 === 0 ? 1 : 4; bars.push(html`<rect x=${c * px} y="4" width=${Math.max(1, l * px - 1)} height="18" fill=${i % 5 === 0 ? BLUE : INK}/>`); c += l; }
  const ticks = []; for (let i = 0; i < Math.min(A, 207); i++) ticks.push(html`<rect x=${i * 3 / 5 * px} y="30" width=${Math.max(1, px / 2)} height="12" fill=${DIM}/>`);
  return html`<div class="cu-ctlrow"><${Slider} label="Frames you ask for" value=${n} min=${5} max=${400} onInput=${setN}/></div><svg viewBox=${`0 0 ${W} 46`} width="100%" role="img" aria-label=${`Up to the first 124 frames: video latent frames above, audio latent frames below`}>${bars}${ticks}</svg>
    <${Read} items=${[["Snapped to", `${f} = ${(f - 5) / 17}×17 + 5`, n === f ? "good" : ""], ["Seconds at 24 fps", (f / 24).toFixed(3)], ["Video latent", `[24, ${T}, H/16, W/16]`], ["Audio latent", `[32, 2, ${A}]`], ["Inside the tooltip's 124 to 362", f >= 124 && f <= 362 ? "Yes" : "No", ok ? "good" : ""]]}/><p class="cu-play-note">Top row: each video latent frame, one frame (blue) then four groups of four. Bottom row: audio latent frames, 40 a second, on the same clock. Shown up to frame 124.</p>`;
}
function LtxSigmas({ onPass }) {
  const [steps, setSteps] = useState(8); const [n, setN] = useState(81); const [w, setW] = useState(640); const h = 480; const tokens = ((n - 1 - (n - 1) % 8) / 8 + 1) * Math.floor(h / 32) * Math.floor(w / 32); const [sh, sig] = useMemo(() => ltxvScheduler(steps, tokens), [steps, tokens]); const ok = steps === 8 && sh > 2.05; useEffect(() => { if (ok) onPass(); }, [ok]);
  const path = (a) => a.map((v, i) => `${i ? "L" : "M"}${10 + i / (a.length - 1) * 400} ${10 + (1 - v) * 120}`).join(" ");
  return html`<div class="cu-ctlrow"><${Slider} label="Scheduler steps" value=${steps} min=${4} max=${30} onInput=${setSteps}/><${Slider} label="Frames" value=${n} min=${9} max=${241} step=${8} onInput=${setN}/><${Slider} label="Width" value=${w} min=${320} max=${1920} step=${32} onInput=${setW}/></div>
    <svg viewBox="0 0 420 140" width="100%" role="img" aria-label="Two noise schedules from 1 down to 0"><path d=${path(DISTILLED)} fill="none" stroke=${INK} stroke-width="2.5"/><path d=${path(sig)} fill="none" stroke=${BLUE} stroke-width="2.5"/></svg>
    <${Read} items=${[["Latent positions", tokens.toLocaleString("en")], ["LTXVScheduler shift", sh.toFixed(3), ok ? "good" : ""], ["Blue, last step before 0", sig[steps - 1].toFixed(3)], ["Gold, the graph's list, last step before 0", "0.422"]]}/><p class="cu-play-note">Gold is the fixed list in the graph, the same in Lightricks' code. Blue is <code>LTXVScheduler</code>, whose shift grows with the number of positions and which the graph does not use.</p>`;
}
function HighLow({ onPass }) {
  const [steps, setSteps] = useState(20); const [s, setS] = useState(8); const g = useMemo(() => shiftGrid(steps, s), [steps, s]); const hi = g.filter((v) => v >= .875).length; const ok = steps === 40 && s === 12; useEffect(() => { if (ok) onPass(); }, [ok]);
  return html`<div class="cu-ctlrow"><${Slider} label="Steps" value=${steps} min=${10} max=${50} step=${5} onInput=${setSteps}/><${Slider} label="Shift" value=${s} min=${1} max=${16} onInput=${setS}/></div><svg viewBox="0 0 420 44" width="100%" role="img" aria-label=${`${hi} of ${steps} steps above the boundary`}>${g.map((v, i) => html`<rect x=${i / steps * 420} y=${40 - v * 36} width=${420 / steps - 1} height=${v * 36} fill=${v >= .875 ? INK : BLUE}/>`)}</svg>
    <${Read} items=${[["Above 0.875: high-noise model on a 14B pair", hi, ok ? "good" : ""], ["Below: low-noise model", steps - hi], ["On 5B", `one model, all ${steps}`]]}/><p class="cu-play-note">Gold bars go to the high-noise model, blue to the low-noise one. An even grid bent by shift. Wan's 14B config sets boundary 0.875, shift 12, 40 steps. Its real sampler may space steps differently, so treat the split as close, not exact.</p>`;
}
function Chunks({ onPass }) {
  const [sec, setSec] = useState(30); const [clip, setClip] = useState(124); const [ov, setOv] = useState(22); const total = sec * 24; const [n, have] = chain(total, clip, ov); const work = n * clip / have; const ok = sec >= 60 && ov >= 5 && work <= 1.05; useEffect(() => { if (ok) onPass(); }, [ok]);
  return html`<div class="cu-ctlrow"><${Slider} label="Video length, seconds" value=${sec} min=${5} max=${120} step=${5} onInput=${setSec}/><${Seg} label="Clip, frames" value=${clip} opts=${[[73, "73"], [124, "124"], [226, "226"], [362, "362"]]} onPick=${setClip}/><${Slider} label="Overlap, frames" value=${ov} min=${1} max=${39} onInput=${setOv}/></div>
    <${Read} items=${[["Clips", n], ["Seams to hide", n - 1], ["Work against the kept frames", work.toFixed(3), ok ? "good" : ""], ["Frames in RAM at 1344 x 768, float32", (have * 1344 * 768 * 12 / 1024 ** 3).toFixed(1) + " GiB"]]}/><p class="cu-play-note">More overlap carries more motion across a seam and costs more renders. The peak sampler memory is one clip's, however long the chain. Longer clips mean fewer seams and a higher peak.</p>`;
}
function Decimate({ onPass }) {
  const [t, setT] = useState(120); const r = useMemo(() => simplifyCurve(240, t), [t]); const ok = t <= 40 && r.err < .03; useEffect(() => { if (ok) onPass(); }, [ok]);
  const d = r.pts.map((p, i) => `${i ? "L" : "M"}${(p[0] * 120 + 160).toFixed(1)} ${(p[1] * 120 + 160).toFixed(1)}`).join(" ") + "Z";
  return html`<div class="cu-play-grid"><div class="cu-ctls"><${Slider} label="Segments left" value=${t} min=${6} max=${240} onInput=${setT}/><${Read} items=${[["Of the original", (t / 240 * 100).toFixed(0) + "%"], ["Worst distance from the original", r.err.toFixed(3), ok ? "good" : ""]]}/><p class="cu-play-note">A 2D stand-in for decimation: remove the corner that changes the shape least, again and again. Flat stretches go first. Real QEM does this with edges on a surface.</p></div><figure class="cu-canvas"><svg viewBox="0 0 320 320" width="100%" role="img" aria-label=${`A wavy loop drawn with ${t} segments`}><path d=${d} fill="rgba(90,155,240,.2)" stroke=${INK} stroke-width="1.5"/>${r.pts.map((p) => html`<circle cx=${p[0] * 120 + 160} cy=${p[1] * 120 + 160} r="2" fill=${BLUE}/>`)}</svg></figure></div>`;
}

export const MORE = {
  seedlayout: { title: "What one seed keeps", task: "Read the kept share with the same shape. Then change only the frames, then the width.", C: SeedLayout, after: "Same seed with a new shape is new noise, apart from the first channel when only frames change." },
  tiles: { title: "Cut a side into tiles", task: "With a side of 1024 cut into at least two tiles, keep at least 32 overlap and feed the model no more than 1.15 times the pixels.", C: Tiles, after: "Bigger tiles and smaller overlaps cost less. Smaller overlaps also hide seams less well." },
  flow: { title: "Undo the motion", task: "With the camera move selected, find the shift that turns the picture black.", C: Flow, after: "Now pick the brightness jump and try the same. No shift helps." },
  rf: { title: "How far one output sees", task: "Make one output see at least 63 inputs with 5 layers or fewer.", C: Rf, after: "Strides make the reach grow fast. With stride 1, each layer adds only k - 1." },
  flicker: { title: "Motion or flicker?", task: "Find a clip with no strobe or noise where the plain score reads above 5 and the aligned score reads under 1.", C: Flicker, after: "That clip does not flicker at all. Only the aligned score says so." },
  audiocalls: { title: "Where audio models spend their calls", task: "Push the seconds until Music 3's AR frames stop growing.", C: AudioCalls, after: "That is the ceiling written in the source: 9000 frames at 25 a second." },
  isosurface: { title: "Blocks against a contour", task: "With threshold 0, raise the grid to 48 or more and compare the two lengths.", C: Iso, after: "A finer grid makes more, smaller stairs. Their total length stays the same." },
  avtime: { title: "Picture and sound on one clock", task: "Ask for a frame count exactly on the grid, above 124 and at most 362.", C: AvTime, after: "Snapped counts cost you nothing. Asking on the grid means you get what you typed." },
  ltxsigmas: { title: "Two ways to spend 8 steps", task: "Keep 8 steps. Make the video big enough that the scheduler's shift passes 2.05.", C: LtxSigmas, after: "The graph's fixed list does not change with size. The scheduler does." },
  highlow: { title: "Where a 14B pair hands over", task: "Set Wan's own numbers: 40 steps, shift 12. Read the split.", C: HighLow, after: "Lower the shift to 5 and see how much the hand-over moves." },
  longchunks: { title: "Plan a long video as a chain", task: "Reach 60 seconds with at least 5 frames of overlap and no more than 1.05 times the work.", C: Chunks, after: "Work is cheap to keep low. Seams are what cost you, and this number can't show them." },
  decimate: { title: "Remove what matters least", task: "Get to 40 segments or fewer with a worst distance under 0.03.", C: Decimate, after: "Keep going down and watch where the shape breaks first: the tight curves." },
};
