/* Sampling Lab: the page's pure logic, so tests can run it with no browser. */
export const FAMILIES = [["sampler", "Samplers"], ["scheduler", "Schedulers"], ["guidance", "Guidance"], ["noise", "Noise"], ["latent", "Latent ops"], ["math", "Math"], ["patch", "Model patches"]];
export const WHERE = [["all", "Everywhere"], ["core", "In ComfyUI core"], ["live", "Live pack here"], ["pack", "Needs a pack"]];
export const LABELS = { "from code": "From code", "measured here": "Measured here", "from pack README claim": "README claim", inference: "Inference", "qwen draft": "Qwen draft, unchecked" };

export function whereOf(e) { return e.in_core ? "core" : e.live ? "live" : "pack"; }
export function whereWord(e) { return e.in_core ? "In core, runs here" : e.live ? "Live pack on this box" : "Needs a pack"; }

const words = (q) => String(q || "").toLowerCase().split(/\s+/).filter(Boolean);
/* Name matches beat text matches. Every word has to hit somewhere, so a longer search narrows. */
export function score(e, q) {
  const w = words(q); if (!w.length) return 1;
  const name = String(e.name || "").toLowerCase(), id = String(e.id || "").toLowerCase(), hay = [e.subfamily, e.plain, e.family, (e.core_ref && Object.values(e.core_ref).join(" "))].join(" ").toLowerCase(); let s = 0;
  for (const x of w) { if (name.startsWith(x)) s += 6; else if (name.includes(x) || id.includes(x)) s += 4; else if (hay.includes(x)) s += 1; else return 0; }
  return s;
}
export const PROOFS = [["all", "Any proof"], ["rendered", "Rendered here"], ["from code", "From code"], ["inference", "Inference"], ["from pack README claim", "README claim"]];
const proofHit = (e, p) => p === "all" || (p === "rendered" ? !!e.rendered : e.label === p);
export function filterEntries(list, { q = "", family = "all", where = "all", proof = "all", sort = "match" } = {}) {
  const rows = [];
  for (const e of list || []) {
    if (family !== "all" && e.family !== family) continue;
    if (where !== "all" && whereOf(e) !== where) continue;
    if (!proofHit(e, proof)) continue;
    const s = score(e, q); if (s > 0) rows.push([s, e]);
  }
  /* Runs-here first, because that is what someone can try now; then by match, then by name. */
  const rank = { core: 0, live: 1, pack: 2 };
  if (sort === "name") rows.sort((a, b) => String(a[1].name).localeCompare(String(b[1].name)));
  else if (sort === "packs") rows.sort((a, b) => ((b[1].providers_n || 0) - (a[1].providers_n || 0)) || String(a[1].name).localeCompare(String(b[1].name)));
  else rows.sort((a, b) => (b[0] - a[0]) || (rank[whereOf(a[1])] - rank[whereOf(b[1])]) || String(a[1].name).localeCompare(String(b[1].name)));
  return rows.map((r) => r[1]);
}
export function familyCounts(list) { const c = {}; for (const e of list || []) c[e.family] = (c[e.family] || 0) + 1; return c; }

/* A sigma curve as an SVG path. Log needs positive numbers, so the final sigma of 0 stays off the log chart and the page says so. */
export function curvePoints(sigmas, { w = 100, h = 100, log = false, max = null, min = null } = {}) {
  if (!Array.isArray(sigmas) || sigmas.length < 2) return [];
  const pts = []; const hi = max ?? Math.max(...sigmas); const pos = sigmas.filter((s) => s > 0); const lo = min ?? (pos.length ? Math.min(...pos) : 0.001);
  const n = sigmas.length - 1;
  sigmas.forEach((s, i) => {
    if (log && !(s > 0)) return;
    const f = log ? (hi === lo ? 0 : (Math.log(hi) - Math.log(s)) / (Math.log(hi) - Math.log(lo))) : (hi === 0 ? 0 : 1 - s / hi);
    pts.push([i / n * w, Math.max(0, Math.min(1, f)) * h, s, i]);
  });
  return pts;
}
export const toPath = (pts) => pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(2) + " " + p[1].toFixed(2)).join("");
/* One colour per series for as long as it stays picked: picking another never repaints the ones already on the chart. Eight at most, then the page asks for one to be dropped. */
export const MAX_SERIES = 8;
export function assignSlots(prev, picked) {
  const next = {}, used = new Set();
  for (const k of picked) if (prev[k] !== undefined) { next[k] = prev[k]; used.add(prev[k]); }
  for (const k of picked) if (next[k] === undefined) { let s = 0; while (used.has(s)) s++; if (s >= MAX_SERIES) continue; next[k] = s; used.add(s); }
  return next;
}
export function togglePick(picked, k) { return picked.includes(k) ? picked.filter((x) => x !== k) : picked.length >= MAX_SERIES ? picked : [...picked, k]; }

/* The solver bench rows from measures.json. A stochastic sampler has no single exact answer, so it is judged on the variance of what it lands on, never on distance to one path. */
export function benchRows(solvers, space = "eps") {
  return Object.entries(solvers || {}).map(([name, r]) => {
    const m = (r || {})[space] || {};
    if (m.error) return { name, error: m.error };
    const det = !!m.same_answer_with_other_noise_seed;
    return { name, calls20: (m.calls || {})["20"], perStep: (m.calls || {})["20"] ? +((m.calls["20"]) / 20).toFixed(2) : null, det, rmse: det ? (m.rmse_to_exact || {})["20"] : null, rmseCurve: det ? [5, 10, 20, 40].map((n) => (m.rmse_to_exact || {})[n]) : null, varErr: (m.variance_error || {})["20"], slope: m.slope_vs_calls };
  });
}
export function sortBench(rows, key = "calls20", dir = 1) {
  const v = (r) => r[key]; return [...rows].sort((a, b) => { const x = v(a), y = v(b); if (x == null && y == null) return String(a.name).localeCompare(String(b.name)); if (x == null) return 1; if (y == null) return -1; return (typeof x === "string" ? x.localeCompare(y) : x - y) * dir; });
}
export function groupRenders(list) { const g = {}; for (const r of list || []) { if (r.status === "rendered") (g[r.set] = g[r.set] || []).push(r); } return g; }
export function baselineFor(rows) { return (rows || []).find((r) => r.baseline) || (rows || [])[0] || null; }
export function runRequest(e, model) {
  const ref = e.core_ref || {}; const q = { model };
  if (ref.sampler_name) q.sampler = ref.sampler_name;
  if (ref.scheduler) q.scheduler = ref.scheduler;
  if (e.run_patch) q.patch = e.run_patch;
  if (e.run_guider) q.guider = e.run_guider;
  if (q.scheduler && !q.sampler) q.sampler = "dpmpp_2m";
  return q;
}
export function canRun(e) { const r = e.core_ref || {}; return !!(e.in_core && (r.sampler_name || r.scheduler || e.run_patch || e.run_guider)); }

/* ---------- the look: everything below is pure so tests can run it with no browser ---------- */
const WORDS_LOWER = (s) => String(s || "").toLowerCase();
export const VIEW_KEYS = ["methods", "curves", "bench", "renders", "finds", "credits"];
/* #sampling, #sampling/curves, #sampling/renders/guidance/a/b, #sampling/<method id> */
export function parseRoute(route) {
  const p = String(route || "sampling").split("/").slice(1).filter(Boolean);
  if (!p.length) return { view: "methods", id: null, rest: [] };
  if (VIEW_KEYS.includes(p[0])) return { view: p[0], id: null, rest: p.slice(1).map(decodeURIComponent) };
  return { view: "methods", id: decodeURIComponent(p[0]), rest: [] };
}
/* Which rows a virtual list draws. top is how far the list has scrolled past the top of the view, negative while it is still below it. */
export function windowRange(top, view, rowH, n, over = 8) {
  if (!(rowH > 0) || !n) return [0, 0];
  const a = Math.floor(top / rowH) - over, b = Math.ceil((top + view) / rowH) + over;
  return [Math.max(0, Math.min(n, a)), Math.max(0, Math.min(n, b))];
}

/* One dot per method. The kinds never overlap, so the legend adds up to the whole atlas. */
export const DOT_ORDER = ["rendered", "core", "live", "pack"];
export const dotKind = (e) => e.rendered ? "rendered" : e.in_core ? "core" : e.live ? "live" : "pack";
export function dotCounts(list) { const c = { rendered: 0, core: 0, live: 0, pack: 0 }; for (const e of list || []) c[dotKind(e)]++; return c; }
export function dotsOf(list) { return [...(list || [])].sort((a, b) => DOT_ORDER.indexOf(dotKind(a)) - DOT_ORDER.indexOf(dotKind(b)) || String(a.name).localeCompare(String(b.name))); }

/* Squarified treemap: rectangles in the same order as the weights, each with area in proportion to its weight. */
export function squarify(weights, W, H) {
  const total = weights.reduce((a, b) => a + b, 0); const out = new Array(weights.length); if (!total || !(W > 0) || !(H > 0)) return weights.map(() => ({ x: 0, y: 0, w: 0, h: 0 }));
  const items = weights.map((v, i) => ({ i, a: v / total * W * H })).sort((a, b) => b.a - a.a);
  let x = 0, y = 0, w = W, h = H;
  const worst = (row, side) => { const s = row.reduce((t, r) => t + r.a, 0); return Math.max(...row.map((r) => Math.max(side * side * r.a / (s * s), s * s / (side * side * r.a)))); };
  while (items.length) {
    const side = Math.min(w, h); const row = [items.shift()];
    while (items.length && worst([...row, items[0]], side) <= worst(row, side)) row.push(items.shift());
    const s = row.reduce((t, r) => t + r.a, 0);
    if (w >= h) { const cw = s / h; let cy = y; for (const r of row) { const ch = r.a / cw; out[r.i] = { x, y: cy, w: cw, h: ch }; cy += ch; } x += cw; w -= cw; }
    else { const ch = s / w; let cx = x; for (const r of row) { const cw = r.a / ch; out[r.i] = { x: cx, y, w: cw, h: ch }; cx += cw; } y += ch; h -= ch; }
  }
  return out;
}
/* The map: every dot is the same size in every tile, so a bigger family really is more dots. Below `stackUnder` the tiles stack, because a phone can't hold a treemap with readable labels. */
export function mapLayout(counts, W, { H = Math.max(340, Math.min(430, W * .33)), label = 66, narrowLabel = 92, narrow = 170, pad = 14, allow = 34, stackUnder = 720, stackDot = 8 } = {}) {
  const fams = counts.filter((c) => c.n > 0);
  if (W < stackUnder) {
    const cols = Math.max(1, Math.floor((W - pad * 2) / stackDot)); let y = 0;
    const tiles = fams.map((f) => { const rows = Math.ceil(f.n / cols), h = label + rows * stackDot + pad; const t = { ...f, x: 0, y, w: W, h, cols, dotY: label }; y += h; return t; });
    return { tiles, dot: stackDot, W, H: y, stacked: true };
  }
  /* A treemap can leave one tile too short for its label at an unlucky size, so try a little more height until the squares stay readable. */
  const top = (r) => r.w < narrow ? narrowLabel : label; let best = null;
  for (let tall = H; tall <= H + 200; tall += 20) {
    const rects = squarify(fams.map((f) => f.n + allow), W, tall); let dot = 30;
    const fits = (d) => rects.every((r, i) => Math.floor((r.w - pad * 2) / d) * Math.floor((r.h - top(r) - pad) / d) >= fams[i].n);
    while (dot > 3 && !fits(dot)) dot -= .5;
    if (!best || dot > best.dot) best = { rects, dot, tall };
    if (dot >= 14) break;
  }
  const { rects, dot, tall } = best;
  return { tiles: fams.map((f, i) => ({ ...f, ...rects[i], cols: Math.max(1, Math.floor((rects[i].w - pad * 2) / dot)), dotY: top(rects[i]), narrow: rects[i].w < narrow })), dot, W, H: tall, stacked: false };
}

/* Readable maths: symbols apart from the working, and tokens the page can set like an equation. Nothing is rewritten: flatten() gives back what the atlas says, so a styling bug can't change the maths. */
const SUBS = "₀₁₂₃₄₅₆₇₈₉₊₋ₒᵢ", SUB_TO = "0123456789+−oi", SUPS = "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻ⁱ", SUP_TO = "0123456789+−i";
const mapRun = (s, from, to) => [...s].map((c) => to[[...from].indexOf(c)]).join("");
const GREEK = "α-ωΑ-Ωℓ∇∂";
const TOKEN = new RegExp([
  `(?<sup>\\^(?:\\{[^{}]*\\}|\\((?:[^()]|\\([^()]*\\))*\\)|[${GREEK}A-Za-z0-9−+'.]+))`, `(?<usup>[${SUPS}]+)`, `(?<usub>[${SUBS}]+)`,
  `(?<sub>_(?:\\{[^{}]*\\}|[${GREEK}A-Za-z0-9]{1,5}(?![A-Za-z0-9_])))`,
  `(?<code>[A-Za-z][A-Za-z0-9]*(?:[._][A-Za-z0-9]+){1,}(?:\\(\\))?|[a-z]+[A-Z][A-Za-z]+|[A-Z][a-z]+[A-Z][A-Za-z]*)`,
  `(?<lim>[σtTsΣ](?:min|max)(?![A-Za-z]))`, `(?<word>[A-Za-z]{2,})`, `(?<num>\\d+(?:\\.\\d+)?)`, `(?<v>[${GREEK}A-Za-z][\\u0302\\u0303\\u0304]?[′″']*)`, `(?<op>[=+−×·≈≠≤≥←→↦∝∈∉±∓])`, `(?<ws>\\s+)`, `(?<x>.)`,
].join("|"), "gu");
export function mathTokens(line) {
  const out = []; let m; const re = new RegExp(TOKEN.source, "gu"); const s = String(line || ""); let prevVar = false;
  while ((m = re.exec(s))) {
    const g = m.groups; const was = prevVar; prevVar = false;
    if (g.sup) { const inner = g.sup.slice(1).replace(/^\{|\}$/g, "").replace(/^\((.*)\)$/, "$1"); out.push({ t: "sup", s: g.sup, kids: mathTokens(inner) }); prevVar = true; }
    else if (g.usup) out.push({ t: "sup", s: g.usup, kids: mathTokens(mapRun(g.usup, SUPS, SUP_TO)) });
    else if (g.usub) { out.push({ t: "sub", s: g.usub, kids: mathTokens(mapRun(g.usub, SUBS, SUB_TO)) }); prevVar = true; }
    else if (g.sub) { if (was) { const inner = g.sub.slice(1).replace(/^\{|\}$/g, ""); out.push({ t: "sub", s: g.sub, kids: mathTokens(inner) }); prevVar = true; } else out.push({ t: "x", s: g.sub }); }
    else if (g.code) {
      /* x_pred is a variable with a subscript; compute_ratio is a name from the code. */
      const short = /^[A-Za-z]{1,2}_[A-Za-z0-9]{1,5}$/.exec(g.code);
      if (short) { const [head, tail] = g.code.split("_"); out.push({ t: head.length === 1 ? "v" : "word", s: head }, { t: "sub", s: "_" + tail, kids: mathTokens(tail) }); prevVar = true; }
      else out.push({ t: "code", s: g.code });
    }
    else if (g.lim) { const u = [...g.lim]; out.push({ t: "v", s: u[0] }, { t: "sub", s: u.slice(1).join(""), kids: [{ t: "word", s: u.slice(1).join("") }] }); prevVar = true; }
    else if (g.word) out.push({ t: "word", s: g.word });
    else if (g.num) { out.push({ t: "num", s: g.num }); }
    else if (g.v) {
      /* "gets a fresh tensor": an English a or I between words is not a variable. */
      const prose = /^[aAI]$/.test(g.v) && s[m.index - 1] === " " && /^ [a-z]{2,}/.test(s.slice(m.index + 1));
      if (prose) out.push({ t: "word", s: g.v }); else { out.push({ t: "v", s: g.v }); prevVar = true; }
    }
    else if (g.op) out.push({ t: "op", s: g.op });
    else if (g.ws) out.push({ t: "ws", s: g.ws });
    else { out.push({ t: "x", s: g.x }); prevVar = g.x === ")" || g.x === "]"; }
  }
  return out;
}
export const flatten = (tokens) => tokens.map((t) => t.s).join("");
const eqWords = (l) => (l.match(/[A-Za-z]{4,}/g) || []).length;
export function mathParts(text) {
  const lines = String(text || "").split(/\n+/).map((l) => l.trim()).filter(Boolean); let symbols = [];
  if (lines[0] && /^Symbols:/.test(lines[0])) {
    symbols = lines.shift().replace(/^Symbols:\s*/, "").replace(/\.\s*$/, "").split(/;\s*/).map((p) => { const m = /^(\S+?)(?:=|\s+)(.*)$/.exec(p.trim()); return m ? [m[1], m[2]] : [p.trim(), ""]; });
  }
  return { symbols, lines: lines.map((s) => ({ s, eq: /[=→←≈]/.test(s) && eqWords(s) <= 3 })) };
}

/* The four labels on a method page. A label lights only when this page really holds something of that kind. */
export const LABEL_MEANS = { "from code": "Read in the source. A script found its file and line on disk.", "from pack README claim": "What an author says. Not checked here.", "measured here": "Ran on this machine, with the numbers kept.", inference: "Our reasoning, not read or measured." };
export function proofFacets(e, { curve = false, bench = false } = {}) {
  const subs = [...(e.claims || []), ...(e.family_fit || [])]; const n = (l) => subs.filter((x) => x.label === l).length; const ev = (e.evidence || []).length; const shots = (e.rendered_ids || []).length;
  const plural = (k, w) => `${k} ${w}${k === 1 ? "" : "s"}`;
  const measures = [shots ? plural(shots, "render") + " on this machine" : "", curve ? "sigma curve computed by core's code" : "", bench ? "toy-problem bench run by core's code" : "", n("measured here") ? plural(n("measured here"), "measured note") : ""].filter(Boolean);
  return [
    { key: "from code", on: e.label === "from code" || n("from code") > 0, main: e.label === "from code", note: ev ? plural(ev, "file and line") + (e.label === "from code" ? "" : " found") : "" },
    { key: "from pack README claim", on: e.label === "from pack README claim" || n("from pack README claim") > 0, main: e.label === "from pack README claim", note: n("from pack README claim") ? plural(n("from pack README claim"), "author claim") : e.label === "from pack README claim" ? "the main description" : "" },
    { key: "measured here", on: measures.length > 0, main: false, note: measures.join(", ") },
    { key: "inference", on: e.label === "inference" || n("inference") > 0, main: e.label === "inference", note: e.label === "inference" ? "the main description" : n("inference") ? plural(n("inference"), "reasoned note") : "" },
  ];
}
/* Plain statement of whether a method runs here. Only core renders exist; Pack Lab's control render failed, so nothing outside core is proven. */
export function runsHere(e) {
  if (e.in_core) return e.rendered ? { tone: "proven", word: "Runs here, and rendered", text: "In ComfyUI core. Fixed-seed renders of it are on this page." } : { tone: "core", word: "Runs here", text: "In ComfyUI core, but not part of the proof renders, so this page describes it from the code." };
  if (e.live) return { tone: "live", word: "Installed, unproven", text: "A pack on this box carries it, but no render proves it." };
  return { tone: "pack", word: "Not installed, unproven", text: "It needs a pack that isn't installed. We describe it from its source and have not run it." };
}

const finite = (v) => typeof v === "number" && isFinite(v);
export function curveStats(sigmas) {
  if (!Array.isArray(sigmas) || !sigmas.length) return null; const pos = sigmas.filter((s) => s > 0);
  return { start: sigmas[0], last: pos.length ? pos[pos.length - 1] : null, end: sigmas[sigmas.length - 1], steps: sigmas.length - 1 };
}
const sched = (m, space, name, steps = "20") => { const s = ((m || {}).schedules || {})[space]; return s && s.by_steps && s.by_steps[steps] ? s.by_steps[steps][name] : null; };
const fig = (v, d = 2) => finite(v) ? v.toFixed(d) : "?";
/* The surprises that have pictures. Every number comes from renders.json or measures.json at read time, and a card with missing data is dropped, never filled in. */
export function evidenceCards(renders, measures) {
  const rows = (renders || {}).renders || []; const r = (id) => rows.find((x) => x.id === id && x.status === "rendered");
  const defs = [
    { key: "ddim", title: "ddim is euler", a: "sampler-euler", b: "sampler-ddim", set: "sampler", method: "core-ddim-alias", code: "ComfyUI/comfy/samplers.py:1395", make: (a, b) => a.sha256 === b.sha256 && b.diff_to_base === 0 ? { stat: fig(b.diff_to_base, 1), unit: "mean pixel difference, of 255", more: `Both files hash to ${a.sha256}.` } : null },
    { key: "karras", title: "karras broke SD 3.5 at 20 steps", a: "flow-euler-simple", b: "flow-euler-karras", set: "flow", method: "sched-karras", curve: { space: "sd3_flow_shift3", names: ["simple", "karras"] }, make: () => { const k = sched(measures, "sd3_flow_shift3", "karras"), s = sched(measures, "sd3_flow_shift3", "simple"); return k && s ? { stat: fig(k[3]), unit: `sigma after 3 of 20 steps, against ${fig(s[3])} for simple`, more: "" } : null; } },
    { key: "cfgnorm", title: "CFGNorm at CFG 14 washed SDXL grey", a: "guidance-cfg-14", b: "guidance-cfgnorm-14", set: "guidance", method: "cfg-norm-core", make: (a, b) => ({ stat: fig(b.contrast, 1), unit: `contrast figure, against ${fig(a.contrast, 1)} at plain CFG 14`, more: "" }) },
    { key: "lq", title: "linear_quadratic smeared SDXL", a: "scheduler-normal", b: "scheduler-linear_quadratic", set: "scheduler", method: "sched-linear-quadratic", curve: { space: "sd_eps", names: ["karras", "linear_quadratic"] }, make: () => { const q = curveStats(sched(measures, "sd_eps", "linear_quadratic")), k = curveStats(sched(measures, "sd_eps", "karras")); return q && k ? { stat: fig(q.last), unit: `last sigma before zero at 20 steps, against ${fig(k.last)} for karras`, more: "" } : null; } },
    { key: "ddimu", title: "ddim_uniform starts lower", a: "scheduler-normal", b: "scheduler-ddim_uniform", set: "scheduler", method: "sched-ddim-uniform", curve: { space: "sd_eps", names: ["normal", "ddim_uniform"] }, minor: true, make: () => { const q = curveStats(sched(measures, "sd_eps", "ddim_uniform")), n = curveStats(sched(measures, "sd_eps", "normal")); return q && n ? { stat: fig(q.start), unit: `first sigma at 20 steps, against ${fig(n.start)} for normal`, more: "" } : null; } },
  ];
  return defs.map((d) => { const a = r(d.a), b = r(d.b); if (!a || !b) return null; const made = d.make(a, b); return made ? { ...d, ra: a, rb: b, seen: b.seen, ...made, make: undefined } : null; }).filter(Boolean);
}
/* Mean absolute difference of two RGBA images, and the difference as a picture (brightened by gain, so small changes can be seen). The picture's alpha stays opaque. */
export function diffPixels(a, b, gain = 4, out = null) {
  const n = Math.min(a.length, b.length); let sum = 0, px = 0;
  for (let i = 0; i < n; i += 4) {
    const r = Math.abs(a[i] - b[i]), g = Math.abs(a[i + 1] - b[i + 1]), l = Math.abs(a[i + 2] - b[i + 2]); sum += r + g + l; px++;
    if (out) { out[i] = Math.min(255, r * gain); out[i + 1] = Math.min(255, g * gain); out[i + 2] = Math.min(255, l * gain); out[i + 3] = 255; }
  }
  return px ? sum / (px * 3) : 0;
}

/* Author and licence wording. An empty author stays visibly unrecorded: a guess at a name would be worse than none. */
export const packName = (p) => String(p || "").split("__").pop().replace(/\.disabled$/, "");
export const licenceWord = (l) => !l || l === "none-found" ? "no licence file found" : String(l).replace(/^other:/, "other: ");
export const authorWord = (p) => p.pack === "core" ? "Comfy Org and contributors" : p.author || "author not recorded here";
export function licenceCounts(credits) {
  const g = {}; for (const c of credits || []) { const l = c.licence || ""; const k = !l || l === "none-found" ? "No licence file found" : l.startsWith("other") ? "Other" : l.startsWith("AGPL") ? "AGPL" : l.startsWith("GPL") ? "GPL" : l; g[k] = (g[k] || 0) + 1; }
  return Object.entries(g).sort((a, b) => b[1] - a[1]);
}
/* Credits by person: one author can hold many packs. Packs with no recorded author are returned apart, so the page can list them by name. */
export function creditWall(credits) {
  const by = {}, unknown = [];
  for (const c of credits || []) { if (!c.author) { unknown.push(c); continue; } const a = by[c.author] = by[c.author] || { name: c.author, packs: 0, methods: 0 }; a.packs++; a.methods += c.methods || 0; }
  return { authors: Object.values(by).sort((a, b) => b.methods - a.methods || a.name.localeCompare(b.name)), unknown: unknown.sort((a, b) => b.methods - a.methods) };
}
/* The notes had pasted code removed, which left empty backticks behind. Tidying them changes no claim. */
export function tidyText(s) { return String(s || "").replace(/[,:]?\s*``(?=\s*[.,;:)])/g, "").replace(/``\s*/g, "").replace(/\s+\./g, ".").replace(/\.\.(?=\s|$)/g, ".").replace(/\s{2,}/g, " ").replace(/^\.\s*/, "").trim(); }
export const FIND_GROUPS = { renders: "Rendered here", core_samplers: "Core samplers", pack_samplers: "Pack samplers", schedulers: "Schedulers", guidance: "Guidance", noise: "Noise", latent_math: "Latent and maths", patches: "Patches", second_patches_noise: "Second pass: patches and noise", second_samplers_guidance: "Second pass: samplers and guidance" };
export function whereFirst(w) { const p = String(w || "").split(/\s+/).filter(Boolean); return { first: p[0] || "", more: Math.max(0, p.length - 1) }; }
/* Neighbours in an encyclopedia: the rows either side in the order the reader was browsing, and the others in the same subfamily. */
export function neighbours(rows, list, e) {
  const i = (rows || []).findIndex((x) => x.id === e.id); const base = i >= 0 ? rows : list || []; const j = base.findIndex((x) => x.id === e.id);
  return { prev: j > 0 ? base[j - 1] : null, next: j >= 0 && j < base.length - 1 ? base[j + 1] : null, siblings: (list || []).filter((x) => x.id !== e.id && x.family === e.family && x.subfamily === e.subfamily).slice(0, 8) };
}
/* Deterministic solvers only: error against model calls, for the log-log chart. Stochastic solvers have no single exact path to be measured against. */
export function convergence(solvers, space = "eps") {
  return Object.entries(solvers || {}).map(([name, r]) => {
    const m = (r || {})[space] || {}; if (m.error || !m.same_answer_with_other_noise_seed) return null;
    const pts = [5, 10, 20, 40].map((n) => [(m.calls || {})[n], (m.rmse_to_exact || {})[n]]).filter(([c, e]) => c > 0 && e > 0); if (pts.length < 2) return null;
    return { name, pts, perStep: (m.calls || {})["20"] ? (m.calls["20"]) / 20 : null, slope: m.slope_vs_calls };
  }).filter(Boolean);
}
export function hilite(name, q) {
  const s = String(name || ""); const w = WORDS_LOWER(q).split(/\s+/).filter(Boolean); if (!w.length) return [[s, false]];
  const low = s.toLowerCase(); const hit = new Array(s.length).fill(false);
  for (const x of w) { let i = low.indexOf(x); while (i >= 0) { hit.fill(true, i, i + x.length); i = low.indexOf(x, i + x.length); } }
  const out = []; let at = 0; for (let i = 1; i <= s.length; i++) if (i === s.length || hit[i] !== hit[at]) { out.push([s.slice(at, i), hit[at]]); at = i; }
  return out.length ? out : [[s, false]];
}
