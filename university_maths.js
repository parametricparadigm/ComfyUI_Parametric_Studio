/* ComfyUniversity maths: ports of ComfyUI's own formulas so a lab can run in the browser. No DOM here. tests/test_university_maths.py compares these results to the real Python functions. */

/* ---------- noise levels: comfy/model_sampling.py ---------- */
export function discreteSigmas(start = 0.00085, end = 0.012, n = 1000) { // ModelSamplingDiscrete: "linear" betas are linear in sqrt(beta)
  const out = new Array(n); let cum = 1; const a = Math.sqrt(start), b = Math.sqrt(end);
  for (let i = 0; i < n; i++) { const r = a + (b - a) * (n === 1 ? 0 : i / (n - 1)); cum *= 1 - r * r; out[i] = Math.fround(Math.sqrt((1 - cum) / cum)); }
  return out;
}
export const timeSnrShift = (alpha, t) => alpha === 1 ? t : alpha * t / (1 + (alpha - 1) * t);
export function flowSigmas(shift = 1, n = 1000) { const out = new Array(n); for (let i = 0; i < n; i++) out[i] = Math.fround(timeSnrShift(shift, Math.fround((i + 1) / n))); return out; }
/* A small stand-in for a model_sampling object: the table, how a sigma maps to a timestep and back. */
export function discreteModel() {
  const sigmas = discreteSigmas(), logs = sigmas.map((s) => Math.fround(Math.log(s)));
  return { kind: "discrete", sigmas, min: sigmas[0], max: sigmas[sigmas.length - 1],
    timestep(s) { const l = Math.log(s); let best = 0, d = Infinity; for (let i = 0; i < logs.length; i++) { const x = Math.abs(l - logs[i]); if (x < d) { d = x; best = i; } } return best; },
    sigma(t) { t = Math.min(Math.max(t, 0), sigmas.length - 1); const lo = Math.floor(t), hi = Math.ceil(t), w = t - lo; return Math.exp((1 - w) * logs[lo] + w * logs[hi]); },
    percent(p) { if (p <= 0) return 999999999.9; if (p >= 1) return 0; return this.sigma((1 - p) * 999); } };
}
export function flowModel(shift = 3) {
  const sigmas = flowSigmas(shift);
  return { kind: "flow", shift, sigmas, min: sigmas[0], max: sigmas[sigmas.length - 1], timestep: (s) => s * 1000, sigma: (t) => timeSnrShift(shift, t / 1000),
    percent(p) { if (p <= 0) return 1; if (p >= 1) return 0; return timeSnrShift(shift, 1 - p); } };
}

/* ---------- schedulers: comfy/samplers.py and comfy/k_diffusion/sampling.py ---------- */
const linspace = (a, b, n) => Array.from({ length: n }, (_, i) => n === 1 ? a : a + (b - a) * i / (n - 1));
export function karras(n, smin, smax, rho = 7) { const lo = Math.pow(smin, 1 / rho), hi = Math.pow(smax, 1 / rho); return [...linspace(0, 1, n).map((r) => Math.pow(hi + r * (lo - hi), rho)), 0]; }
export function exponential(n, smin, smax) { return [...linspace(Math.log(smax), Math.log(smin), n).map(Math.exp), 0]; }
export function simple(m, n) { const out = [], ss = m.sigmas.length / n; for (let x = 0; x < n; x++) out.push(m.sigmas[m.sigmas.length - 1 - Math.trunc(x * ss)]); out.push(0); return out; }
export function normal(m, n, sgm = false) {
  const start = m.timestep(m.max), end = m.timestep(m.min); let ts, zero = true;
  if (sgm) ts = linspace(start, end, n + 1).slice(0, -1);
  else { if (Math.abs(m.sigma(end)) <= 1e-5) { n += 1; zero = false; } ts = linspace(start, end, n); }
  const out = ts.map((t) => m.sigma(t)); if (zero) out.push(0); return out;
}
export function ddimUniform(m, n) {
  let x = 1, out; if (Math.abs(m.sigmas[x]) <= 1e-5) { n += 1; out = []; } else out = [0];
  const ss = Math.max(Math.floor(m.sigmas.length / n), 1); while (x < m.sigmas.length) { out.push(m.sigmas[x]); x += ss; } return out.reverse();
}
export function klOptimal(n, smin, smax) { const out = []; for (let i = 0; i < n; i++) { const a = n === 1 ? 0 : i / (n - 1); out.push(Math.tan(a * Math.atan(smin) + (1 - a) * Math.atan(smax))); } out.push(0); return out; }
export function linearQuadratic(m, n, threshold = 0.025) {
  if (n === 1) return [m.max, 0];
  const ls = Math.floor(n / 2), lin = []; for (let i = 0; i < ls; i++) lin.push(i * threshold / ls);
  const diff = ls - threshold * n, qs = n - ls, qc = diff / (ls * qs * qs), lc = threshold / ls - 2 * diff / (qs * qs), c = qc * ls * ls, quad = []; for (let i = ls; i < n; i++) quad.push(qc * i * i + lc * i + c);
  return [...lin, ...quad, 1].map((x) => (1 - x) * m.max);
}
function logGamma(x) { const g = [76.18009172947146, -86.50532032941677, 24.01409824083091, -1.231739572450155, 0.1208650973866179e-2, -0.5395239384953e-5]; let y = x, t = x + 5.5, s = 1.000000000190015; t -= (x + .5) * Math.log(t); for (const c of g) s += c / ++y; return -t + Math.log(2.5066282746310005 * s / x); }
function betaCf(x, a, b) { let c = 1, d = 1 - (a + b) * x / (a + 1); if (Math.abs(d) < 1e-30) d = 1e-30; d = 1 / d; let h = d; for (let m = 1; m < 300; m++) { const m2 = 2 * m; let aa = m * (b - m) * x / ((a - 1 + m2) * (a + m2)); d = 1 + aa * d; if (Math.abs(d) < 1e-30) d = 1e-30; c = 1 + aa / c; if (Math.abs(c) < 1e-30) c = 1e-30; d = 1 / d; h *= d * c; aa = -(a + m) * (a + b + m) * x / ((a + m2) * (a + 1 + m2)); d = 1 + aa * d; if (Math.abs(d) < 1e-30) d = 1e-30; c = 1 + aa / c; if (Math.abs(c) < 1e-30) c = 1e-30; d = 1 / d; const de = d * c; h *= de; if (Math.abs(de - 1) < 1e-13) break; } return h; }
export function betaCdf(x, a, b) { if (x <= 0) return 0; if (x >= 1) return 1; const bt = Math.exp(logGamma(a + b) - logGamma(a) - logGamma(b) + a * Math.log(x) + b * Math.log(1 - x)); return x < (a + 1) / (a + b + 2) ? bt * betaCf(x, a, b) / a : 1 - bt * betaCf(1 - x, b, a) / b; }
export function betaPpf(p, a, b) { if (p <= 0) return 0; if (p >= 1) return 1; let lo = 0, hi = 1; for (let i = 0; i < 80; i++) { const m = (lo + hi) / 2; if (betaCdf(m, a, b) < p) lo = m; else hi = m; } return (lo + hi) / 2; }
export function betaSched(m, n, alpha = 0.6, beta = 0.6) { const total = m.sigmas.length - 1, out = []; let last = -1; for (let i = 0; i < n; i++) { const t = Math.round(betaPpf(1 - i / n, alpha, beta) * total); if (t !== last) out.push(m.sigmas[t]); last = t; } out.push(0); return out; }
export const SCHEDULERS = [["simple", "simple"], ["normal", "normal"], ["sgm_uniform", "sgm_uniform"], ["karras", "karras"], ["exponential", "exponential"], ["ddim_uniform", "ddim_uniform"], ["beta", "beta"], ["linear_quadratic", "linear_quadratic"], ["kl_optimal", "kl_optimal"]];
export function schedule(name, m, n, opts = {}) {
  switch (name) {
    case "simple": return simple(m, n); case "normal": return normal(m, n); case "sgm_uniform": return normal(m, n, true);
    case "karras": return karras(n, m.min, m.max, opts.rho == null ? 7 : opts.rho); case "exponential": return exponential(n, m.min, m.max); case "ddim_uniform": return ddimUniform(m, n);
    case "beta": return betaSched(m, n, opts.alpha == null ? .6 : opts.alpha, opts.beta == null ? .6 : opts.beta); case "linear_quadratic": return linearQuadratic(m, n); case "kl_optimal": return klOptimal(n, m.min, m.max);
    default: throw new Error("unknown scheduler " + name);
  }
}
/* KSampler.set_steps: denoise below 1 builds a longer schedule and keeps its tail. */
export function denoiseWindow(name, m, steps, denoise, opts) {
  if (denoise > 0.9999) { const s = schedule(name, m, steps, opts); return { sigmas: s, full: s, built: steps, kept: s.length - 1 }; }
  if (denoise <= 0) return { sigmas: [], full: [], built: 0, kept: 0 };
  const built = Math.trunc(steps / denoise), full = schedule(name, m, built, opts), sigmas = full.slice(-(steps + 1)); return { sigmas, full, built, kept: sigmas.length - 1 };
}
export function percentToSigma(m, p) { return m.percent(p); }
/* Which sampling steps a [start, end] percent range covers: a step is active when its sigma lies between the two limits, as calc_cond_batch's timestep_start and timestep_end do. */
export function stepsInRange(sigmas, m, start, end) { const hi = m.percent(start), lo = m.percent(end); return sigmas.slice(0, -1).map((s) => s <= hi && s >= lo); }

/* ---------- a toy world with an exact denoiser ---------- */
/* Mixture of round Gaussians in 2D. For this distribution the ideal denoiser has a closed form, so the solvers below run the same update rules as comfy/k_diffusion/sampling.py with no network involved. */
export const TOY = { s: 0.35, comps: [{ x: -2.2, y: 1.2, w: .34 }, { x: 2.2, y: 1.6, w: .33 }, { x: 0, y: -2.2, w: .33 }] };
export function denoiser(x, y, sigma, comps = TOY.comps, s = TOY.s) {
  const v = s * s + sigma * sigma; let tot = 0, dx = 0, dy = 0, logs = [], mx = -Infinity;
  for (const c of comps) { const l = Math.log(c.w) - ((x - c.x) ** 2 + (y - c.y) ** 2) / (2 * v); logs.push(l); if (l > mx) mx = l; }
  comps.forEach((c, i) => { const r = Math.exp(logs[i] - mx); tot += r; dx += r * (sigma * sigma * c.x + s * s * x) / v; dy += r * (sigma * sigma * c.y + s * s * y) / v; });
  return [dx / tot, dy / tot];
}
export function rng(seed) { let a = seed >>> 0; const u = () => { a = (a + 0x6D2B79F5) >>> 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; return { u, n: () => Math.sqrt(-2 * Math.log(u() || 1e-12)) * Math.cos(2 * Math.PI * u()) }; }
export function ancestralStep(from, to, eta = 1) { if (!eta) return [to, 0]; const up = Math.min(to, eta * Math.sqrt(to * to * (from * from - to * to) / (from * from))); return [Math.sqrt(to * to - up * up), up]; }
export const SOLVERS = [["euler", "euler", 1], ["heun", "heun", 2], ["dpmpp_2m", "dpmpp_2m", 1], ["euler_ancestral", "euler_ancestral", 1]];
export function solve(name, x0, sigmas, D, r) {
  let [x, y] = x0, calls = 0, old = null; const path = [[x, y]]; const model = (a, b, s) => { calls++; return D(a, b, s); };
  for (let i = 0; i < sigmas.length - 1; i++) {
    const s = sigmas[i], t = sigmas[i + 1];
    if (name === "euler") { const d = model(x, y, s); const dt = t - s; x += (x - d[0]) / s * dt; y += (y - d[1]) / s * dt; }
    else if (name === "heun") { const d = model(x, y, s), dt = t - s, ax = (x - d[0]) / s, ay = (y - d[1]) / s; if (t === 0) { x += ax * dt; y += ay * dt; } else { const x2 = x + ax * dt, y2 = y + ay * dt, e = model(x2, y2, t), bx = (x2 - e[0]) / t, by = (y2 - e[1]) / t; x += (ax + bx) / 2 * dt; y += (ay + by) / 2 * dt; } }
    else if (name === "dpmpp_2m") { const d = model(x, y, s); const ts = -Math.log(s), tn = t === 0 ? Infinity : -Math.log(t), h = tn - ts, ratio = t / s, em = -Math.expm1(-h); if (!old || t === 0) { x = ratio * x + em * d[0]; y = ratio * y + em * d[1]; } else { const hl = ts + Math.log(sigmas[i - 1]), k = hl / h, c = 1 / (2 * k); x = ratio * x + em * ((1 + c) * d[0] - c * old[0]); y = ratio * y + em * ((1 + c) * d[1] - c * old[1]); } old = d; }
    else if (name === "euler_ancestral") { const d = model(x, y, s), [down, up] = ancestralStep(s, t); if (down === 0) { x = d[0]; y = d[1]; } else { const dt = down - s; x += (x - d[0]) / s * dt + r.n() * up; y += (y - d[1]) / s * dt + r.n() * up; } }
    else throw new Error("unknown solver " + name);
    path.push([x, y]);
  }
  return { path, calls, x, y };
}
/* CFG: comfy/samplers.py cfg_function. The "prompt" here picks one mode of the mixture; the unconditional prediction is the whole mixture. */
export function cfgDenoiser(mode, cfg, comps = TOY.comps) { const only = [{ ...comps[mode], w: 1 }]; return (x, y, s) => { const u = denoiser(x, y, s, comps), c = denoiser(x, y, s, only); return [u[0] + (c[0] - u[0]) * cfg, u[1] + (c[1] - u[1]) * cfg]; }; }
export const rmsTo = (xs, c) => Math.sqrt(xs.reduce((t, p) => t + (p[0] - c.x) ** 2 + (p[1] - c.y) ** 2, 0) / Math.max(1, xs.length));
export function exactEndpoint(x0, sigmas, D, sub = 200) { let [x, y] = x0; for (let i = 0; i < sigmas.length - 1; i++) { const a = sigmas[i], b = sigmas[i + 1] || 1e-4; for (let k = 0; k < sub; k++) { const s = a * Math.pow(b / a, k / sub), t = a * Math.pow(b / a, (k + 1) / sub), d = D(x, y, s), dt = t - s; x += (x - d[0]) / s * dt; y += (y - d[1]) / s * dt; } } return [x, y]; }

/* ---------- prompt weights: comfy/sd1_clip.py parse_parentheses, token_weights ---------- */
export function parseParentheses(str) { const out = []; let cur = "", lvl = 0; for (const ch of str) { if (ch === "(") { if (lvl === 0) { if (cur) { out.push(cur); cur = "("; } else cur = "("; } else cur += ch; lvl++; } else if (ch === ")") { lvl--; if (lvl === 0) { out.push(cur + ")"); cur = ""; } else cur += ch; } else cur += ch; } if (cur) out.push(cur); return out; }
export function tokenWeights(str, w = 1) { const out = []; for (let x of parseParentheses(str)) { let weight = w; if (x.length >= 2 && x[x.length - 1] === ")" && x[0] === "(") { x = x.slice(1, -1); const i = x.lastIndexOf(":"); weight *= 1.1; if (i > 0) { const tail = x.slice(i + 1), n = Number(tail); if (tail.trim() !== "" && Number.isFinite(n)) { weight = n; x = x.slice(0, i); } } out.push(...tokenWeights(x, weight)); } else out.push([x, w]); } return out; }

/* ---------- linear algebra for the low-rank lab ---------- */
/* Top singular triplets by power iteration with deflation. Small matrices only. */
export function svdTop(M, k, iters = 40) {
  const h = M.length, w = M[0].length, R = M.map((r) => r.slice()), out = []; const r = rng(7);
  for (let c = 0; c < k; c++) {
    let v = Array.from({ length: w }, () => r.n()), u = new Array(h).fill(0), s = 0;
    for (let it = 0; it < iters; it++) {
      for (let i = 0; i < h; i++) { let t = 0; for (let j = 0; j < w; j++) t += R[i][j] * v[j]; u[i] = t; }
      s = Math.hypot(...u) || 1; u = u.map((x) => x / s);
      const nv = new Array(w).fill(0); for (let i = 0; i < h; i++) for (let j = 0; j < w; j++) nv[j] += R[i][j] * u[i];
      s = Math.hypot(...nv) || 1; v = nv.map((x) => x / s);
    }
    out.push({ s, u: u.slice(), v: v.slice() });
    for (let i = 0; i < h; i++) for (let j = 0; j < w; j++) R[i][j] -= s * u[i] * v[j];
  }
  return out;
}
export function rankApprox(parts, rank, h, w) { const A = Array.from({ length: h }, () => new Array(w).fill(0)); for (const p of parts.slice(0, rank)) for (let i = 0; i < h; i++) { const a = p.s * p.u[i]; for (let j = 0; j < w; j++) A[i][j] += a * p.v[j]; } return A; }
export function rmse(A, B) { let t = 0, n = 0; for (let i = 0; i < A.length; i++) for (let j = 0; j < A[0].length; j++) { t += (A[i][j] - B[i][j]) ** 2; n++; } return Math.sqrt(t / n); }
/* comfy/weight_adapter/lora.py: weight + strength * (alpha / rank) * up * down. */
export const loraScale = (strength, alpha, rank) => strength * (alpha == null ? 1 : alpha / rank);
export const loraParams = (h, w, rank) => (h + w) * rank;

/* ---------- pictures ---------- */
export function toGray(data, w, h) { const g = new Float32Array(w * h); for (let i = 0; i < w * h; i++) g[i] = (.299 * data[4 * i] + .587 * data[4 * i + 1] + .114 * data[4 * i + 2]) / 255; return g; }
export function sobel(g, w, h) { const o = new Float32Array(w * h); for (let y = 1; y < h - 1; y++) for (let x = 1; x < w - 1; x++) { const a = (i, j) => g[(y + j) * w + x + i], gx = a(1, -1) + 2 * a(1, 0) + a(1, 1) - a(-1, -1) - 2 * a(-1, 0) - a(-1, 1), gy = a(-1, 1) + 2 * a(0, 1) + a(1, 1) - a(-1, -1) - 2 * a(0, -1) - a(1, -1); o[y * w + x] = Math.hypot(gx, gy); } return o; }

/* ---------- video and latent sizes, read from each node's execute() ---------- */
export const LATENTS = {
  sd15: { label: "SD 1.5 and SDXL", node: "EmptyLatentImage", ch: 4, sf: 8, source: "nodes.py" },
  sd3: { label: "SD 3 and Flux", node: "EmptySD3LatentImage", ch: 16, sf: 8, source: "comfy_extras/nodes_sd3.py" },
  wan22: { label: "Wan 2.2 5B", node: "Wan22ImageToVideoLatent", ch: 48, sf: 16, tf: 4, source: "comfy_extras/nodes_wan.py" },
  wan21: { label: "Wan 2.1", node: "WanImageToVideo", ch: 16, sf: 8, tf: 4, source: "comfy_extras/nodes_wan.py" },
  ltx: { label: "LTX-2.5", node: "EmptyLTXVLatentVideo", ch: 128, sf: 32, tf: 8, source: "comfy_extras/nodes_lt.py" },
};
export function latentShape(key, width, height, length = 1, batch = 1) { const L = LATENTS[key]; const space = [Math.floor(height / L.sf), Math.floor(width / L.sf)]; const shape = L.tf ? [batch, L.ch, Math.floor((length - 1) / L.tf) + 1, ...space] : [batch, L.ch, ...space]; return { shape, values: shape.reduce((a, b) => a * b, 1), frames: L.tf ? (Math.floor((length - 1) / L.tf)) * L.tf + 1 : 1 }; }
export const fmtBytes = (n) => n >= 1073741824 ? (n / 1073741824).toFixed(2) + " GB" : n >= 1048576 ? (n / 1048576).toFixed(1) + " MB" : n >= 1024 ? (n / 1024).toFixed(0) + " KB" : n + " B";
export const DTYPES = [["fp32", 4], ["fp16", 2], ["bf16", 2], ["fp8", 1], ["int4 (GGUF Q4-style, about half a byte)", .5]];

/* ---------- sound ---------- */
export function fftMag(re) { const n = re.length, x = Float64Array.from(re), y = new Float64Array(n); for (let i = 0, j = 0; i < n; i++) { if (i < j) { [x[i], x[j]] = [x[j], x[i]]; } let m = n >> 1; while (m >= 1 && j & m) { j ^= m; m >>= 1; } j |= m; } for (let s = 2; s <= n; s <<= 1) { const a = -2 * Math.PI / s; for (let k = 0; k < n; k += s) for (let i = 0; i < s / 2; i++) { const c = Math.cos(a * i), d = Math.sin(a * i), p = k + i, q = p + s / 2, tr = c * x[q] - d * y[q], ti = d * x[q] + c * y[q]; x[q] = x[p] - tr; y[q] = y[p] - ti; x[p] += tr; y[p] += ti; } } const o = new Float64Array(n / 2); for (let i = 0; i < n / 2; i++) o[i] = Math.hypot(x[i], y[i]); return o; }
export const hzToMel = (f) => 2595 * Math.log10(1 + f / 700), melToHz = (m) => 700 * (Math.pow(10, m / 2595) - 1);
export function spectrogram(sig, size = 512, hop = 128) { const out = [], win = Array.from({ length: size }, (_, i) => .5 - .5 * Math.cos(2 * Math.PI * i / (size - 1))); for (let s = 0; s + size <= sig.length; s += hop) { const f = new Float64Array(size); for (let i = 0; i < size; i++) f[i] = sig[s + i] * win[i]; out.push(fftMag(f)); } return out; }
export function synth(kind, sr = 16000, seconds = 1) { const n = Math.floor(sr * seconds), o = new Float32Array(n); const r = rng(3); for (let i = 0; i < n; i++) { const t = i / sr; if (kind === "tone") o[i] = Math.sin(2 * Math.PI * 440 * t); else if (kind === "chord") o[i] = (Math.sin(2 * Math.PI * 261.63 * t) + Math.sin(2 * Math.PI * 329.63 * t) + Math.sin(2 * Math.PI * 392 * t)) / 3; else if (kind === "sweep") o[i] = Math.sin(2 * Math.PI * (200 * t + 1800 * t * t)); else if (kind === "noise") o[i] = r.n() * .3; else o[i] = (t % .25 < .03 ? Math.exp(-(t % .25) * 90) : 0) * (Math.sin(2 * Math.PI * 90 * t) + r.n() * .2); } return o; }

/* ---------- 3D: a pinhole camera over Gaussian blobs, back to front ---------- */
export function projectPoints(pts, yaw, pitch, dist, focal, w, h) { const cy = Math.cos(yaw), sy = Math.sin(yaw), cp = Math.cos(pitch), sp = Math.sin(pitch); return pts.map((p) => { const x = cy * p.x + sy * p.z, z1 = -sy * p.x + cy * p.z, y = cp * p.y - sp * z1, z = sp * p.y + cp * z1 + dist; return { sx: w / 2 + focal * x / z, sy: h / 2 - focal * y / z, r: focal * p.r / z, z, c: p.c, a: p.a }; }).filter((p) => p.z > .1).sort((a, b) => b.z - a.z); }

/* ---------- floats ---------- */
export function toFp16(x) { const b = new Float32Array([x]), u = new Uint32Array(b.buffer)[0], s = u >>> 31, e = (u >>> 23) & 255, m = u & 0x7fffff; if (e === 255) return x; const ex = e - 127; if (ex > 15) return s ? -Infinity : Infinity; if (ex < -24) return 0; const bits = ex >= -14 ? 10 : 10 - (-14 - ex), sc = Math.pow(2, ex - bits), v = Math.abs(x) / sc, f = Math.floor(v), d = v - f, rnd = d > .5 || (d === .5 && f % 2) ? f + 1 : f; return (s ? -1 : 1) * rnd * sc; }
export function roundBits(x, bits) { if (x === 0) return 0; const e = Math.floor(Math.log2(Math.abs(x))), sc = Math.pow(2, e - bits); return Math.round(x / sc) * sc; }
