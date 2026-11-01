// RES4LYF page: sampler arithmetic and the beta curve, kept apart from the page so plain node tests can run them.
export const REPO = "https://github.com/ClownsharkBatwing/RES4LYF";
export const exampleUrl = (name) => `${REPO}/blob/main/example_workflows/${encodeURIComponent(name)}.json`;

// The README's naming rule: "2s" runs two stages a step, so two model calls. "m" samplers reuse earlier steps, one call a step.
export function stagesOf(name) {
  if (name === "euler" || name === "ddim" || /_\d+m$/.test(name)) return 1;
  const s = /_(?:\d+h)?(\d+)s(?:_|$)/.exec(name);
  return s ? Number(s[1]) : null;
}
export const modelCalls = (steps, stages) => steps * stages;

export function flatten(families) {
  return families.flatMap((f) => f.samplers.map((name) => ({ name, family: f.key, label: f.label, stages: stagesOf(name) })));
}
export function filterSamplers(list, family, query) {
  const q = query.trim().toLowerCase();
  return list.filter((s) => (family === "all" || s.family === family) && (!q || s.name.toLowerCase().includes(q)));
}
export function filterNames(names, query) {
  const q = query.trim().toLowerCase();
  return q ? names.filter((n) => n.toLowerCase().includes(q)) : names;
}

export const STATE_LABEL = { rendered: "Rendered", ran: "Ran, text output", error: "Failed in our test", rejected: "Rejected by ComfyUI", needs: "Needs a partner", skipped: "Not run alone", timeout: "Timed out", untested: "Not tested" };
export const sourceUrl = (sha, file, line) => `${REPO}/blob/${sha}/${file}${line ? "#L" + line : ""}`;
export function filterNodes(nodes, group, state, query) {
  const q = query.trim().toLowerCase();
  return nodes.filter((n) => (group === "all" || n.g === group) && (state === "all" || n.s === state) && (!q || (n.n + " " + n.d).toLowerCase().includes(q)));
}
export function stateCounts(nodes) {
  const c = {};
  for (const n of nodes) c[n.s] = (c[n.s] || 0) + 1;
  return c;
}

// Quantiles of a beta distribution, from a table of its integral. Substituting t = sin^2(u) removes the poles at both ends.
const TABLE = 4000;
const tables = new Map();
function table(a, b) {
  const key = a + "/" + b;
  if (tables.has(key)) return tables.get(key);
  const f = (u) => Math.pow(Math.sin(u), 2 * a - 1) * Math.pow(Math.cos(u), 2 * b - 1);
  const du = Math.PI / 2 / TABLE, c = new Float64Array(TABLE + 1);
  // Midpoints, so the integrand is never evaluated exactly on a pole.
  for (let i = 0; i < TABLE; i++) c[i + 1] = c[i] + f((i + 0.5) * du) * du;
  tables.set(key, c);
  return c;
}
export function betaPpf(p, a, b) {
  if (p <= 0) return 0;
  if (p >= 1) return 1;
  const c = table(a, b), target = p * c[TABLE];
  let lo = 0, hi = TABLE;
  while (hi - lo > 1) { const mid = (lo + hi) >> 1; if (c[mid] < target) lo = mid; else hi = mid; }
  const u = (lo + (target - c[lo]) / (c[hi] - c[lo])) * (Math.PI / 2 / TABLE);
  return Math.sin(u) ** 2;
}

// The same positions ComfyUI's beta_scheduler asks for, before it rounds them to a model's timesteps: 1 is the noisiest end.
export const betaSchedule = (steps, a, b) => Array.from({ length: steps }, (_, i) => betaPpf(1 - i / steps, a, b));
export const countBelow = (schedule, limit) => schedule.filter((t) => t < limit).length;

export function curvePath(schedule, w, h) {
  const last = Math.max(schedule.length - 1, 1);
  return schedule.map((t, i) => `${i ? "L" : "M"}${(i / last * w).toFixed(1)} ${((1 - t) * h).toFixed(1)}`).join(" ");
}

// A one-number toy for the math section: two possible "images", -1 and +1, whose ideal denoiser has a closed form. Our own arithmetic from the published formulas, not the pack's code, and it says nothing about pictures.
const toyDenoise = (x, s) => Math.tanh(x / (s * s));
const toySlope = (x, s) => (x - toyDenoise(x, s)) / s;
export const phi1 = (h) => (Math.abs(h) < 1e-8 ? 1 : (1 - Math.exp(-h)) / h);
export const phi2 = (h) => (Math.abs(h) < 1e-5 ? 0.5 : (h - 1 + Math.exp(-h)) / (h * h));
export const toySigmas = (steps, from, to) => Array.from({ length: steps + 1 }, (_, i) => from * Math.pow(to / from, i / steps));
export const TOY_METHODS = {
  euler: { label: "euler", calls: 1, step(x, s, n) { return x + (n - s) * toySlope(x, s); } },
  heun_2s: { label: "heun_2s", calls: 2, step(x, s, n) { const k = toySlope(x, s), d = n - s; return x + d * 0.5 * (k + toySlope(x + d * k, n)); } },
  res_2s: { label: "res_2s", calls: 2, step(x, s, n) {
    const h = -Math.log(n / s), c = 0.5, d1 = toyDenoise(x, s);
    const d2 = toyDenoise(x + h * c * phi1(c * h) * (d1 - x), s * Math.exp(-c * h));
    const b2 = phi2(h) / c, b1 = phi1(h) - b2;
    return x + h * (b1 * (d1 - x) + b2 * (d2 - x));
  } },
};
// The path a method takes for a budget of model calls: it gets as many steps as the budget buys, at least one.
export function toyPath(method, start, calls, from, to) {
  const m = TOY_METHODS[method], sig = toySigmas(Math.max(1, Math.floor(calls / m.calls)), from, to), path = [[sig[0], start]];
  for (let i = 0; i + 1 < sig.length; i++) path.push([sig[i + 1], m.step(path[i][1], sig[i], sig[i + 1])]);
  return path;
}
// The reference answer: the same formula with far more steps than anyone would run.
export const toyExact = (start, from, to, steps = 12000) => toyPath("res_2s", start, steps * 2, from, to);

// The node map's regions. Groups the pack's notes name go in one region each; a group nobody has placed yet lands in "Everything else", so new notes can't vanish from the map.
export const NODE_REGIONS = [
  { t: "Sampling", d: "The samplers, their options, and the state they carry.", g: ["Samplers", "General options", "Noise and step options", "Sampler state", "Legacy samplers and options"] },
  { t: "Guides and style", d: "Pulling a render toward a reference, and patching models to allow it.", g: ["Image guides", "Style guides", "Style layer controls", "Regional and style patchers"] },
  { t: "Prompts and regions", d: "Conditioning, regional prompts and the masks behind them.", g: ["Regional prompting", "Conditioning tools", "Flux conditioning tweaks", "Text and seeds", "Mask tools", "Color-swatch masks"] },
  { t: "Sigmas", d: "Making, bending and combining the noise schedule itself.", g: ["Schedule makers", "Reshaping curves", "Arithmetic", "Chaos and science-themed curves", "Cutting and joining", "Formulas, ranges and blending", "Floors and cleanup", "Special maths functions", "Viewing and counting"] },
  { t: "Latents and noise", d: "The working image and the noise that goes into it.", g: ["Noise", "Create and move", "Channel edits", "Frequency edits"] },
  { t: "Images and video", d: "Pixels, frames and the steps between them and latents.", g: ["Image filters and frequency separation", "Image size and cropping", "VAE and images", "Video frames", "Video frames and temporal masks"] },
  { t: "Model plumbing", d: "Loading, precision, compiling and timestep shift.", g: ["Loaders", "Precision", "Compile for speed", "Swap and save weights", "Timestep shift"] },
];
export function nodeMap(nodes, regions = NODE_REGIONS) {
  const placed = new Set(regions.flatMap((r) => r.g)), byGroup = new Map();
  for (const n of nodes) { if (!byGroup.has(n.g)) byGroup.set(n.g, []); byGroup.get(n.g).push(n); }
  const rest = [...byGroup.keys()].filter((g) => !placed.has(g)).sort();
  const all = rest.length ? [...regions, { t: "Everything else", d: "Groups not placed on the map yet.", g: rest }] : regions;
  return all.map((r) => {
    const groups = r.g.filter((g) => byGroup.has(g)).map((g) => ({ name: g, nodes: byGroup.get(g), rendered: byGroup.get(g).filter((n) => n.s === "rendered").length }));
    return { t: r.t, d: r.d, groups, count: groups.reduce((a, g) => a + g.nodes.length, 0) };
  }).filter((r) => r.count);
}

// A comparison can only be offered when both of its renders exist for that model.
export const findRender = (gallery, family, name) => gallery.find((r) => r.family === family && r.name === name);
export function storiesFor(stories, gallery, family) {
  return stories.filter((s) => findRender(gallery, family, s.a) && findRender(gallery, family, s.b));
}
