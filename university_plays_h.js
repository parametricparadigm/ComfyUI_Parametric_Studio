/* ComfyUniversity labs for the automation, architecture, research and history tracks. Pure maths lives here, in the browser, with no server calls. Each lab says in its lesson what it was checked against. */
import { useEffect, useMemo, useState } from "preact/hooks";
import { html } from "./common.js";

const Slider = ({ label, value, min, max, step = 1, onInput, show }) => html`<label class="cu-ctl"><span>${label} <b>${show != null ? show : value}</b></span><input type="range" min=${min} max=${max} step=${step} value=${value} onInput=${(e) => onInput(+e.target.value)}/></label>`;
const Seg = ({ label, value, opts, onPick }) => html`<div class="cu-ctl"><span>${label}</span><div class="cu-seg" role="group" aria-label=${label}>${opts.map(([k, l]) => html`<button type="button" aria-pressed=${value === k} onClick=${() => onPick(k)}>${l}</button>`)}</div></div>`;
const Read = ({ items }) => html`<dl class="cu-read">${items.map(([k, v, cls]) => html`<div class=${cls || ""}><dt>${k}</dt><dd>${v}</dd></div>`)}</dl>`;

/* SECTION automation */
const H2Actions = [["GET /object_info", "free", "Reads node definitions. Changes nothing."], ["GET /history/<id>", "free", "Reads a result. Changes nothing."], ["POST /prompt", "budget", "Runs a job. It uses the GPU and writes files, so cap how many."], ["POST /queue with clear", "ask", "Removes everybody's waiting jobs."], ["POST /interrupt", "ask", "Stops a running job, which may not be yours."], ["POST /free", "ask", "Unloads models. Other jobs slow down."], ["A graph with a paid API node", "ask", "Spends real credits on another company's service."], ["A shell command", "deny", "ComfyUI's API doesn't need it. Keep it out of the agent's tools."]];
function H2Gate({ onPass }) {
  const [p, setP] = useState({}); const right = H2Actions.filter(([a, k]) => p[a] === k).length; useEffect(() => { if (right === H2Actions.length) onPass(); }, [right]);
  return html`${H2Actions.map(([a, k, why]) => html`<div class="cu-ctlrow cu-policy-row" key=${a}><${Seg} label=${a} value=${p[a]} opts=${[["free", "free"], ["budget", "budget"], ["ask", "ask"], ["deny", "deny"]]} onPick=${(v) => setP({ ...p, [a]: v })}/>${p[a] && html`<span class="cu-play-note">${p[a] === k ? "Agreed. " : "We chose " + k + ". "}${why}</span>`}</div>`)}<${Read} items=${[["agreed with this lesson's policy", right + " of " + H2Actions.length, right === H2Actions.length ? "good" : ""]]}/><p class="cu-play-note">This is a policy, ours. Routes are as in server.py, and the server itself checks none of them.</p>`;
}
const h2Rng = (seed) => () => { seed = (seed + 0x6D2B79F5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
/* The simulator of this lesson's lab: 3 models, one job every gap seconds, a job takes 5 s, a load takes load seconds. */
export function h2Serve(workers, route, gap, load) { const r = h2Rng(1), free = Array(workers).fill(0), have = Array(workers).fill(-1); let t = 0, rr = 0, sum = 0, loads = 0; const n = 300; for (let j = 0; j < n; j++) { t += -Math.log(1 - r()) * gap; const m = Math.floor(r() * 3); let w = 0; if (route === "rr") w = rr++ % workers; else { let best = Infinity; free.forEach((f, i) => { const c = route === "sticky" ? f + (have[i] === m ? 0 : load) : f; if (c < best) { best = c; w = i; } }); } const s = Math.max(t, free[w]); let c = 5; if (have[w] !== m) { c += load; have[w] = m; loads++; } free[w] = s + c; sum += free[w] - t; } return { wait: sum / n, loads }; }
function H2Serving({ onPass }) {
  const [w, setW] = useState(4); const [route, setRoute] = useState("rr"); const [gap, setGap] = useState(2.5); const [load, setLoad] = useState(20); const r = useMemo(() => h2Serve(w, route, gap, load), [w, route, gap, load]); const rr = useMemo(() => h2Serve(w, "rr", gap, load), [w, gap, load]);
  useEffect(() => { if (route !== "rr" && w === 4 && gap === 2.5 && load === 20 && r.wait < rr.wait / 4) onPass(); }, [r, rr]);
  return html`<div class="cu-ctlrow"><${Slider} label="Workers" value=${w} min=${1} max=${8} onInput=${setW}/><${Slider} label="Seconds between jobs" value=${gap} min=${1} max=${20} step=${0.5} onInput=${setGap}/><${Slider} label="Model load, seconds" value=${load} min=${0} max=${60} onInput=${setLoad}/><${Seg} label="Routing" value=${route} opts=${[["rr", "round robin"], ["least", "least busy"], ["sticky", "sticky"]]} onPick=${setRoute}/></div><${Read} items=${[["mean wait", r.wait.toFixed(1) + " s"], ["round robin at these settings", rr.wait.toFixed(1) + " s"], ["model loads in 300 jobs", r.loads]]}/><p class="cu-play-note">A simulation with sizes we chose. It's the shape that carries over, not the seconds.</p>`;
}
const H2Prov = [["Keys in another order", false, "A sorted dump gives the same text."], ["Seed 42 to 43", true, "The seed is in the graph."], ["Renumbered node ids", true, "Ids are in the graph, though the engine's cache key ignores them."], ["New weights, same file name", false, "The graph only holds the name. Hash the file too."], ["A pack updated on disk", false, "The graph names the class, not its code."], ["Sampler euler to heun", true, "It's an input."]];
function H2Prov2({ onPass }) {
  const [p, setP] = useState({}); const right = H2Prov.filter(([a, k]) => p[a] === k).length; useEffect(() => { if (right === H2Prov.length) onPass(); }, [right]);
  return html`<p class="cu-q-line">Does a sorted hash of the API graph change?</p>${H2Prov.map(([a, k, why]) => html`<div class="cu-ctlrow cu-policy-row" key=${a}><${Seg} label=${a} value=${p[a] === undefined ? "" : p[a] ? "y" : "n"} opts=${[["y", "yes"], ["n", "no"]]} onPick=${(v) => setP({ ...p, [a]: v === "y" })}/>${p[a] !== undefined && html`<span class="cu-play-note">${p[a] === k ? "Right. " : "It " + (k ? "does" : "doesn't") + ". "}${why}</span>`}</div>`)}<${Read} items=${[["right", right + " of " + H2Prov.length, right === H2Prov.length ? "good" : ""]]}/>`;
}
/* App Mode form: which nodes a field re-runs, by walking the wires of the seven-node graph. */
const H1_WIRES = { loader: [], pos: ["loader"], neg: ["loader"], latent: [], sampler: ["loader", "pos", "neg", "latent"], decode: ["sampler", "loader"], save: ["decode"] };
export function h1Downstream(node) { const out = new Set([node]); let grew = true; while (grew) { grew = false; for (const [k, ups] of Object.entries(H1_WIRES)) if (!out.has(k) && ups.some((u) => out.has(u))) { out.add(k); grew = true; } } return out; }
const H1_FIELDS = [["text", "Describe the image", "pos", "user"], ["seed", "Seed", "sampler", "user"], ["width", "Width", "latent", "user"], ["neg", "Negative prompt", "neg", "author"], ["steps", "Steps", "sampler", "author"], ["sampler_name", "Sampler", "sampler", "author"], ["ckpt_name", "Checkpoint file", "loader", "author"], ["filename_prefix", "File name prefix", "save", "author"]];
function H1AppForm({ onPass }) {
  const [on, setOn] = useState([]); const flip = (k) => setOn(on.includes(k) ? on.filter((x) => x !== k) : [...on, k]);
  const rows = H1_FIELDS.filter((f) => on.includes(f[0])).map((f) => [f[1], `re-runs ${h1Downstream(f[2]).size} of 7 nodes`]);
  const users = on.filter((k) => H1_FIELDS.find((f) => f[0] === k)[3] === "user").length; const ok = on.length === 3 && users === 3;
  useEffect(() => { if (ok) onPass(); }, [ok]);
  return html`<div class="cu-ctl"><span>Fields on the form</span><div class="cu-chips">${H1_FIELDS.map((f) => html`<button type="button" class="cu-chip" aria-pressed=${on.includes(f[0])} onClick=${() => flip(f[0])}>${f[1]}</button>`)}</div></div>
    ${rows.length ? html`<${Read} items=${rows}/>` : html`<p class="cu-play-note">Pick a field to see what changing it costs.</p>`}
    <p class="cu-play-note">${ok ? "Three fields, all decisions the person using the app makes. The file menu and the sampler stay with the author." : `${on.length} fields, ${users} of them a choice for the person using the app.`} The counts assume everything is already in the cache and walk the wires. The wires never change.</p>`;
}

/* The messages one job sends. Order from a real PromptExecutor run on a CPU, plus the last line from prompt_worker in main.py. */
const H1_RUNS = {
  first: { label: "First run", status: "success", msgs: ["execution_start", "execution_cached nodes: []", "executing node 1", "executing node 2", "progress 1 of 2", "progress 2 of 2", "executing node 3", "executed node 3, with the file", "execution_success", "executing node null"] },
  cached: { label: "Same again", status: "success", msgs: ["execution_start", "execution_cached nodes: 1 2 3", "executed node 3, with the file", "execution_success", "executing node null"] },
  error: { label: "A node raises", status: "error", msgs: ["execution_start", "execution_cached nodes: 1", "executing node 2", "execution_error node 2, ValueError", "executing node null"] },
  stop: { label: "Interrupted", status: "error", msgs: ["execution_start", "execution_cached nodes: 1", "executing node 2", "execution_interrupted node 2", "executing node null"] },
};
function H1WsOrder({ onPass }) {
  const [run, setRun] = useState("first"); const [pick, setPick] = useState({}); const r = H1_RUNS[run]; const last = r.msgs.length - 1; const chosen = pick[run];
  const done = Object.keys(H1_RUNS).filter((k) => pick[k] === H1_RUNS[k].msgs.length - 1).length; const ok = done === 4;
  useEffect(() => { if (ok) onPass(); }, [ok]);
  return html`<${Seg} label="Job" value=${run} opts=${Object.entries(H1_RUNS).map(([k, v]) => [k, v.label])} onPick=${setRun}/>
    <p class="cu-q-line">Tap the message after which your script may safely stop waiting and read the history.</p>
    <div class="cu-chips">${r.msgs.map((m, i) => html`<button type="button" class="cu-chip" key=${run + i} aria-pressed=${chosen === i} onClick=${() => setPick({ ...pick, [run]: i })}>${m}</button>`)}</div>
    <${Read} items=${[["Your pick", chosen == null ? "none yet" : chosen === last ? "right: every job ends with this" : r.msgs[chosen].startsWith("execution_success") ? "too narrow: a failed job never sends this" : "too early, or only on some jobs", chosen === last ? "good" : ""], ["history status_str after this job", chosen === last ? r.status : "read the history to find out"], ["Jobs done", `${done} of 4`]]}/>
    <p class="cu-play-note">The list leaves out progress_state, which the real server sends around each node. It shows no timing.</p>`;
}

/* The widgets_values of the KSampler in ComfyUI's default_workflow.json. Order from object_info. */
const H1_VALUES = [42, "fixed", 8, 1, "res_multistep", "simple", 1]; const H1_RIGHT = ["seed", "(editor only)", "steps", "cfg", "sampler_name", "scheduler", "denoise"];
const H1_NAMES = ["seed", "(editor only)", "steps", "cfg", "sampler_name", "scheduler", "denoise"];
function H1UiToApi({ onPass }) {
  const [map, setMap] = useState(["seed", "steps", "cfg", "sampler_name", "scheduler", "denoise", "(editor only)"]);
  const inputs = {}; map.forEach((n, i) => { if (n !== "(editor only)") inputs[n] = H1_VALUES[i]; }); inputs.model = ["69", 0]; inputs.positive = ["67", 0]; inputs.negative = ["71", 0]; inputs.latent_image = ["68", 0];
  const ok = map.every((n, i) => n === H1_RIGHT[i]); const setAt = (i, n) => setMap(map.map((x, j) => j === i ? n : x));
  useEffect(() => { if (ok) onPass(); }, [ok]);
  const typeBad = typeof inputs.steps !== "number" || typeof inputs.seed !== "number" || typeof inputs.cfg !== "number" || typeof inputs.denoise !== "number";
  return html`<div class="cu-ctlrow">${H1_VALUES.map((v, i) => html`<label class="cu-ctl" key=${i}><span>value ${i}: <b>${String(v)}</b></span><select class="cu-text" value=${map[i]} onChange=${(e) => setAt(i, e.target.value)}>${H1_NAMES.map((n) => html`<option value=${n}>${n}</option>`)}</select></label>`)}</div>
    <pre class="cu-code" tabindex="0"><code>${JSON.stringify({ 70: { class_type: "KSampler", inputs } }, null, 1)}</code></pre>
    <${Read} items=${[["Would the server take it?", ok ? "these values, yes" : typeBad ? "no: a number input got text (invalid_input_type) or nothing" : "maybe, and that is worse: right types, wrong meanings", ok ? "good" : ""]]}/>
    <p class="cu-play-note">widgets_values has no names. The seed widget brings a helper value that the editor keeps for itself. In a real workflow, let Export (API) do this.</p>`;
}

/* What the flags change. The answers follow a run of the real create_origin_only_middleware and create_cors_middleware with mocked requests, which the lesson reports. */
function H1Exposed({ onPass }) {
  const [listen, setListen] = useState("all"); const [cors, setCors] = useState("on"); const [tls, setTls] = useState("off"); const [multi, setMulti] = useState("off"); const [proxy, setProxy] = useState("off");
  const open = listen === "all"; const c = cors === "on"; const yes = (b) => b ? "yes" : "no";
  const rows = [
    ["A script on this computer can queue", "yes"],
    ["A web page you visit can queue, modern browser", yes(c), c ? "bad" : "good"],
    ["A web page you visit can queue, browser with no fetch headers", c ? "yes" : open ? "yes, at your network address" : "no", c || open ? "bad" : "good"],
    ["Another device can reach it directly", yes(open), open ? "bad" : "good"],
    ["That device needs a password", open ? "no, ComfyUI has none" : proxy === "on" ? "only through your proxy" : "it cannot reach it", open ? "bad" : "good"],
    ["Traffic on the network is encrypted", tls === "on" ? "yes, TLS" : proxy === "on" ? "only if your proxy does it" : open ? "no" : "it stays on this computer", tls === "off" && open ? "bad" : ""],
    ["The comfy-user header proves who someone is", "no" + (multi === "on" ? ", --multi-user only sorts storage" : ""), multi === "on" ? "bad" : ""],
  ];
  const ok = !open && !c && proxy === "on"; useEffect(() => { if (ok) onPass(); }, [ok]);
  return html`<div class="cu-ctlrow"><${Seg} label="--listen" value=${listen} opts=${[["local", "127.0.0.1"], ["all", "0.0.0.0"]]} onPick=${setListen}/><${Seg} label="--enable-cors-header" value=${cors} opts=${[["off", "off"], ["on", "*"]]} onPick=${setCors}/><${Seg} label="TLS files" value=${tls} opts=${[["off", "none"], ["on", "both given"]]} onPick=${setTls}/><${Seg} label="--multi-user" value=${multi} opts=${[["off", "off"], ["on", "on"]]} onPick=${setMulti}/><${Seg} label="Your own login proxy" value=${proxy} opts=${[["off", "no"], ["on", "yes"]]} onPick=${setProxy}/></div>
    <${Read} items=${rows}/>
    <p class="cu-play-note">${ok ? "ComfyUI stays on loopback, the browser check stays on, and the login is someone else's job: yours." : "Task: let other people in, with a login, while no address but your proxy can reach ComfyUI."} This table sums up the lesson's lab. The proxy is your own software: this page does not test one.</p>`;
}

/* SECTION architecture */
/* The same angle rule as rope() in comfy/ldm/flux/math.py: position times 1 / theta^(i / (d/2)). */
export const h3Omega = (d, theta = 10000) => Array.from({ length: d / 2 }, (_, i) => 1 / Math.pow(theta, i / (d / 2)));
export function h3RopeScore(q, k, pq, pk, om) { let s = 0; om.forEach((w, i) => { const a = pq * w, b = pk * w, c1 = Math.cos(a), s1 = Math.sin(a), c2 = Math.cos(b), s2 = Math.sin(b); const q0 = q[2 * i], q1 = q[2 * i + 1], k0 = k[2 * i], k1 = k[2 * i + 1]; s += (c1 * q0 - s1 * q1) * (c2 * k0 - s2 * k1) + (s1 * q0 + c1 * q1) * (s2 * k0 + c2 * k1); }); return s; }
const H3Q = [0.8, -0.3, 0.2, 0.9, -0.6, 0.4, 0.5, 0.5], H3K = [0.1, 0.7, -0.8, 0.2, 0.3, -0.5, 0.9, 0.1];
function H3Rope({ onPass }) {
  const [pq, setPq] = useState(0); const [pk, setPk] = useState(3); const [seen, setSeen] = useState({}); const om = useMemo(() => h3Omega(8), []); const score = h3RopeScore(H3Q, H3K, pq, pk, om); const gap = pk - pq;
  useEffect(() => { const n = { ...seen, [gap]: { ...(seen[gap] || {}), [pq]: true } }; setSeen(n); if (Object.keys(n[3] || {}).length >= 3 && gap !== 3) onPass(); }, [pq, pk]);
  const dial = (i) => { const r = 34, a = pq * om[i], b = pk * om[i], qa = Math.atan2(H3Q[2 * i + 1], H3Q[2 * i]) + a, ka = Math.atan2(H3K[2 * i + 1], H3K[2 * i]) + b; return html`<g key=${i} transform=${`translate(${50 + i * 100} 45)`}><circle r=${r} fill="none" stroke="currentColor" opacity=".3"/><line x2=${r * Math.cos(qa)} y2=${-r * Math.sin(qa)} stroke="#f5c518" stroke-width="3"/><line x2=${r * Math.cos(ka)} y2=${-r * Math.sin(ka)} stroke="#5a9bf0" stroke-width="3"/></g>`; };
  return html`<div class="cu-ctlrow"><${Slider} label="Query position" value=${pq} min=${0} max=${60} onInput=${setPq}/><${Slider} label="Key position" value=${pk} min=${0} max=${60} onInput=${setPk}/></div><svg class="cu-chart cu-chart-cap" viewBox="0 0 400 90" role="img" aria-label="Four dials, one per pair of channels. The query arrow is yellow, the key arrow blue.">${[0, 1, 2, 3].map(dial)}</svg><${Read} items=${[["gap", gap], ["score", score.toFixed(4)], ["places tried at this gap", Object.keys(seen[gap] || {}).length]]}/><p class="cu-play-note">Each dial is one pair of channels. Fast pairs on the left, slow on the right. Move both sliders together and every arrow turns, yet the angle between the two stays put.</p>`;
}
function H3Patches({ onPass }) {
  const [side, setSide] = useState(512); const [p, setP] = useState(2); const [f, setF] = useState(8); const [hit, setHit] = useState(false); const n = Math.floor(side / f / p) ** 2;
  useEffect(() => { if (side === 1024 && p === 2 && f === 8) setHit(true); if (hit && side === 2048 && p === 2 && f === 8) onPass(); }, [side, p, f]);
  return html`<div class="cu-ctlrow"><${Slider} label="Image side" value=${side} min=${256} max=${2048} step=${64} onInput=${setSide}/><${Seg} label="VAE factor" value=${f} opts=${[[8, "8"], [16, "16"]]} onPick=${setF}/><${Seg} label="Patch" value=${p} opts=${[[1, "1"], [2, "2"], [4, "4"]]} onPick=${setP}/></div><${Read} items=${[["latent side", Math.floor(side / f)], ["tokens", n.toLocaleString()], ["token pairs", (n * n).toLocaleString()], ["one attention matrix at fp16", (n * n * 2 / 2 ** 30).toFixed(3) + " GiB"]]}/><p class="cu-play-note">One matrix, one head, one layer. A real backend may never hold the whole matrix at once, so read this as how the work scales.</p>`;
}
function H3Bands({ onPass }) {
  const [a, setA] = useState(0); const [b, setB] = useState(10); const [n, setN] = useState(1); const [one, setOne] = useState(false); const om = h3Omega(2 * n); const sim = om.reduce((t, w) => t + Math.cos((a - b) * w), 0) / n;
  useEffect(() => { if (n === 1 && a !== b && sim > 0.99) setOne(true); if (one && n === 4 && a !== b && sim < 0.9) onPass(); }, [a, b, n, sim]);
  return html`<div class="cu-ctlrow"><${Slider} label="Position A" value=${a} min=${0} max=${200} onInput=${setA}/><${Slider} label="Position B" value=${b} min=${0} max=${200} onInput=${setB}/><${Seg} label="Frequencies" value=${n} opts=${[[1, "1"], [4, "4"]]} onPick=${setN}/></div><${Read} items=${[["similarity of the two codes", sim.toFixed(4), sim > 0.99 && a !== b ? "bad" : ""], ["longest wavelength", (2 * Math.PI / om[om.length - 1]).toFixed(1) + " positions"], ["look-alike found with one frequency", one ? "yes, over 0.99" : "not yet", one ? "good" : ""]]}/><p class="cu-play-note">Try a gap near a whole number of wavelengths. Similarity here is the mean of cos((A minus B) times each frequency), which is what the dot product of two sine and cosine codes works out to.</p>`;
}
function H3KvCache({ onPass }) {
  const [n, setN] = useState(40); const [layers, setLayers] = useState(24); const [kv, setKv] = useState(8); const full = n * (n + 1) * (n + 2) / 6, cached = n * (n + 1) / 2, save = 1 - cached / full, mem = 2 * n * kv * 128 * 2 * layers / 2 ** 30;
  useEffect(() => { if (save >= 0.99) onPass(); }, [save]);
  return html`<div class="cu-ctlrow"><${Slider} label="Tokens generated" value=${n} min=${1} max=${2000} onInput=${setN}/><${Slider} label="Layers" value=${layers} min=${1} max=${48} onInput=${setLayers}/><${Slider} label="Key/value heads" value=${kv} min=${1} max=${16} onInput=${setKv}/></div><${Read} items=${[["attention pairs, no cache", full.toLocaleString()], ["attention pairs, KV cache", cached.toLocaleString()], ["pairs saved", (save * 100).toFixed(1) + "%", save >= 0.99 ? "good" : ""], ["cache memory at head width 128, bf16", mem.toFixed(3) + " GiB"]]}/><p class="cu-play-note">The counts are one layer's, the sums from this lesson's lab. Memory is the price, and it grows with tokens, layers and key/value heads.</p>`;
}
const h3Rng = (seed) => () => { seed = (seed + 0x6D2B79F5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
const H3Tokens = (() => { const r = h3Rng(7); const g = () => Math.sqrt(-2 * Math.log(r() + 1e-9)) * Math.cos(2 * Math.PI * r()); return Array.from({ length: 400 }, () => [g(), g()]); })();
const H3Gates = [[1, 0], [0, 1], [-1, 0], [0, -1]];
export function h3GateLoad(k, tilt) { const load = [0, 0, 0, 0]; H3Tokens.forEach(([x, y]) => { const s = H3Gates.map(([a, b], i) => a * x + b * y + (i === 0 ? tilt : 0)); s.map((v, i) => [v, i]).sort((p, q) => q[0] - p[0]).slice(0, k).forEach(([, i]) => { load[i]++; }); }); return load; }
function H3Gate({ onPass }) {
  const [k, setK] = useState(1); const [tilt, setTilt] = useState(0); const [lop, setLop] = useState(false); const load = useMemo(() => h3GateLoad(k, tilt), [k, tilt]); const top = Math.max(...load) / (400) ;
  useEffect(() => { if (k === 1 && top > 0.8) setLop(true); if (lop && k === 1 && top < 1 / 3) onPass(); }, [k, tilt]);
  return html`<div class="cu-ctlrow"><${Slider} label="Tilt the gate toward expert 0" value=${tilt} min=${0} max=${4} step=${0.1} onInput=${setTilt}/><${Seg} label="Experts per token" value=${k} opts=${[[1, "1"], [2, "2"]]} onPick=${setK}/></div><svg class="cu-chart cu-chart-cap" viewBox="0 -12 400 122" role="img" aria-label=${"Tokens handled by each expert: " + load.join(", ")}>${load.map((v, i) => html`<g key=${i}><rect x=${20 + i * 95} y=${100 - v / 400 * 90} width="70" height=${v / 400 * 90} fill="#5a9bf0"/><text x=${55 + i * 95} y=${96 - v / 400 * 90} text-anchor="middle" fill="currentColor" font-size="12">${v}</text></g>`)}</svg><p class="cu-play-note">400 made-up tokens and four gate vectors at right angles. Total calls are always 400 times the experts per token, wherever they land. A lopsided gate leaves most of the stored experts idle.</p>`;
}
/* Same counting as this lesson's lab: a window spreads what it has seen to every member. */
export function h3Reach(side, ws, layers, shift) { const key = (i, off) => Math.floor((i + off) / ws); let seen = Array.from({ length: side }, () => Array(side).fill(false)); seen[0][0] = true; for (let L = 0; L < layers; L++) { const off = shift && L % 2 ? Math.floor(ws / 2) : 0; const hot = new Set(); for (let y = 0; y < side; y++) for (let x = 0; x < side; x++) if (seen[y][x]) hot.add(key(y, off) + "," + key(x, off)); seen = seen.map((r, y) => r.map((_, x) => hot.has(key(y, off) + "," + key(x, off)))); } return seen; }
function H3Windows({ onPass }) {
  const [ws, setWs] = useState(8); const [layers, setLayers] = useState(2); const [shift, setShift] = useState(false); const side = 32; const seen = useMemo(() => h3Reach(side, ws, layers, shift), [ws, layers, shift]); const count = seen.flat().filter(Boolean).length; const n = side * side; const share = (n * ws * ws) / (n * n);
  useEffect(() => { if (ws === 8 && shift && count === n) onPass(); }, [ws, shift, count]);
  return html`<div class="cu-ctlrow"><${Seg} label="Window" value=${ws} opts=${[[4, "4"], [8, "8"], [16, "16"]]} onPick=${setWs}/><${Slider} label="Layers" value=${layers} min=${1} max=${12} onInput=${setLayers}/><${Seg} label="Shift every second layer" value=${shift ? "y" : "n"} opts=${[["n", "no"], ["y", "yes"]]} onPick=${(k) => setShift(k === "y")}/></div><svg class="cu-chart" viewBox="0 0 320 320" role="img" aria-label=${count + " of " + n + " tokens can reach the corner"} style=${{ maxWidth: "320px" }}>${seen.map((r, y) => r.map((v, x) => v ? html`<rect x=${x * 10} y=${y * 10} width="9.5" height="9.5" fill="#f5c518"/>` : null))}</svg><${Read} items=${[["tokens that can reach the corner token", count + " of " + n, count === n ? "good" : ""], ["pairs per layer, against full", (share * 100).toFixed(2) + "%"]]}/>`;
}

/* SECTION research */
const h4Rng = (seed) => () => { seed = (seed + 0x6D2B79F5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
const h4Gauss = (r) => Math.sqrt(-2 * Math.log(r() + 1e-12)) * Math.cos(2 * Math.PI * r());
/* The same set-up as CU-470's lab: seed effect sd 5, noise sd 1. Returns the mean difference and a range of 2 standard errors. */
export function h4Compare(n, diff, same, draw) { const r = h4Rng(1000 * draw + n); const d = []; const a = [], b = []; for (let i = 0; i < n; i++) { const s = 5 * h4Gauss(r), x = s + h4Gauss(r), y = (same ? s : 5 * h4Gauss(r)) + diff + h4Gauss(r); d.push(y - x); a.push(x); b.push(y); } const mean = (v) => v.reduce((p, q) => p + q, 0) / v.length, m = mean(d); if (n < 2) return { m, range: null }; const v = (x) => { const u = mean(x); return x.reduce((p, q) => p + (q - u) ** 2, 0) / (x.length - 1); }; return { m, range: 2 * Math.sqrt(same ? v(d) / n : v(a) / n + v(b) / n) }; }
function H4Seeds({ onPass }) {
  const [n, setN] = useState(1); const [diff, setDiff] = useState(0); const [same, setSame] = useState(false); const [draw, setDraw] = useState(4); const [fooled, setFooled] = useState(false); const r = useMemo(() => h4Compare(n, diff, same, draw), [n, diff, same, draw]); const clear = r.range != null && Math.abs(r.m) > r.range;
  useEffect(() => { if (diff === 0 && n === 1 && Math.abs(r.m) > 1) setFooled(true); if (fooled && diff === 1 && same && clear && r.m > 0) onPass(); }, [r]);
  const W = 400, x = (v) => Math.max(5, Math.min(W - 5, W / 2 + v * 20));
  return html`<div class="cu-ctlrow"><${Slider} label="True difference" value=${diff} min=${0} max=${2} step=${0.5} onInput=${setDiff}/><${Slider} label="Seeds" value=${n} min=${1} max=${128} onInput=${setN}/><${Seg} label="Seeds used" value=${same ? "y" : "n"} opts=${[["n", "different for each"], ["y", "same for both"]]} onPick=${(k) => setSame(k === "y")}/></div><button type="button" class="cu-chip cu-seeds-again" onClick=${() => setDraw(draw + 1)}>Run the experiment again</button><svg class="cu-chart" viewBox=${`0 0 ${W} 50`} role="img" aria-label=${"Measured difference " + r.m.toFixed(2)}><line x1=${W / 2} x2=${W / 2} y1="2" y2="48" stroke="currentColor" opacity=".4"/>${r.range != null && html`<line x1=${x(r.m - r.range)} x2=${x(r.m + r.range)} y1="25" y2="25" stroke="#5a9bf0" stroke-width="4"/>`}<circle cx=${x(r.m)} cy="25" r="6" fill="#f5c518"/></svg><${Read} items=${[["measured difference", r.m.toFixed(2)], ["range", r.range == null ? "none with one seed" : "plus or minus " + r.range.toFixed(2)], ["verdict", r.range == null ? "no basis" : clear ? "clear of 0" : "includes 0", clear ? "good" : ""], ["one-seed gap over 1 with no true difference", fooled ? "found" : "not yet", fooled ? "good" : ""]]}/><p class="cu-play-note">Simulated scores. Each seed shifts the score with sd 5 and each render adds noise with sd 1, chosen by us. Real sizes depend on your model and your measure.</p>`;
}
function H4BestOf({ onPass }) {
  const [k, setK] = useState(1); const gain = useMemo(() => { const r = h4Rng(11 + k); let t = 0; for (let i = 0; i < 3000; i++) { let b = -Infinity; for (let j = 0; j < k; j++) b = Math.max(b, h4Gauss(r)); t += b - (h4Gauss(r) + h4Gauss(r) + h4Gauss(r)) / 3; } return t / 3000; }, [k]);
  useEffect(() => { if (gain > 1) onPass(); }, [k, gain]);
  return html`<div class="cu-ctlrow"><${Slider} label="Runs tried, best one reported" value=${k} min=${1} max=${50} onInput=${setK}/></div><${Read} items=${[["true gain", "0"], ["average apparent gain, in units of run-to-run noise", gain.toFixed(2), gain > 1 ? "bad" : ""]]}/><p class="cu-play-note">Two equal methods. The new one reports its best of k runs, and the baseline reports the mean of three.</p>`;
}
const h4Img = (() => { const n = 32, out = []; for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) { const u = x / (n - 1), v = y / (n - 1); out.push(Math.max(0, Math.min(1, 0.35 + 0.25 * Math.sin(u * 9) * Math.cos(v * 7) + (((u - .5) ** 2 + (v - .5) ** 2 < .08) ? .25 : 0)))); } return out; })();
export function h4Psnr(a, b) { let s = 0; a.forEach((v, i) => { s += (v - b[i]) ** 2; }); s /= a.length; return s === 0 ? Infinity : 10 * Math.log10(1 / s); }
export function h4Corr(a, b) { const m = (x) => x.reduce((p, q) => p + q, 0) / x.length, ma = m(a), mb = m(b); let n = 0, da = 0, db = 0; a.forEach((v, i) => { n += (v - ma) * (b[i] - mb); da += (v - ma) ** 2; db += (b[i] - mb) ** 2; }); return (da * db) === 0 ? 0 : n / Math.sqrt(da * db); }
function H4Metrics({ onPass }) {
  const [kind, setKind] = useState("bright"); const [amt, setAmt] = useState(0); const [hits, setHits] = useState({}); const n = 32;
  const out = useMemo(() => { if (kind === "bright") return h4Img.map((v) => v + amt * 0.04); if (kind === "shift") return h4Img.map((_, i) => { const y = Math.floor(i / n), x = i % n; return h4Img[y * n + ((x - amt) % n + n) % n]; }); const r = h4Rng(5); return h4Img.map((v) => v + amt * 0.04 * h4Gauss(r)); }, [kind, amt]); const p = h4Psnr(h4Img, out), c = h4Corr(h4Img, out);
  useEffect(() => { if (amt > 0 && p > 18 && p < 22) { const m = { ...hits, [kind]: true }; setHits(m); if (Object.keys(m).length >= 2) onPass(); } }, [p]);
  const grid = (d) => d.map((v, i) => html`<rect x=${i % n} y=${Math.floor(i / n)} width="1" height="1" fill=${`hsl(40 30% ${Math.round(Math.max(0, Math.min(1, v)) * 100)}%)`}/>`);
  return html`<div class="cu-ctlrow"><${Seg} label="Change" value=${kind} opts=${[["bright", "brighter"], ["shift", "shifted"], ["noise", "noisy"]]} onPick=${(k) => { setKind(k); setAmt(0); }}/><${Slider} label="Amount" value=${amt} min=${0} max=${12} onInput=${setAmt}/></div><svg class="cu-chart cu-chart-cap" shape-rendering="crispEdges" viewBox="0 0 68 32" role="img" aria-label="The original on the left, the changed one on the right"><g>${grid(h4Img)}</g><g transform="translate(36 0)">${grid(out)}</g></svg><${Read} items=${[["PSNR", p === Infinity ? "infinite" : p.toFixed(1) + " dB", p > 18 && p < 22 ? "good" : ""], ["Pearson r", c.toFixed(3)], ["kinds found near 20 dB", Object.keys(hits).length]]}/>`;
}
const H4Items = [["brass astrolabe"], ["oak table"], ["stack of sea charts"], ["window light"], ["shallow depth of field"]];
function H4Check({ onPass }) {
  const [e, setE] = useState({}); const [a, setA] = useState({}); const done = Object.keys(e).length === 5 && Object.keys(a).length === 5; const tot = (m) => Object.values(m).filter(Boolean).length; useEffect(() => { if (done) onPass(); }, [done]);
  const row = (name, m, set) => html`<div class="cu-seg" role="group" aria-label=${name}>${[[true, "yes"], [false, "no"]].map(([k, l]) => html`<button type="button" aria-pressed=${m[name] === k} onClick=${() => set({ ...m, [name]: k })}>${l}</button>`)}</div>`;
  return html`<p class="cu-q-line">Mark what you can see. There's no answer key, because each reader's marks are data. Compare yours with ours in the lab.</p><div class="cu-ctlrow"><figure><img src="sampling_lab/sampler-euler.jpg" alt="Render A, sampler euler" style=${{ width: "100%", maxWidth: "240px" }}/><figcaption>A: euler</figcaption></figure><figure><img src="sampling_lab/sampler-euler_ancestral.jpg" alt="Render B, sampler euler ancestral" style=${{ width: "100%", maxWidth: "240px" }}/><figcaption>B: euler ancestral</figcaption></figure></div>${H4Items.map(([n]) => html`<div class="cu-checklist-row" key=${n}><span>${n}</span><span>A ${row(n, e, setE)}</span><span>B ${row(n, a, setA)}</span></div>`)}<${Read} items=${[["A", tot(e) + " of 5"], ["B", tot(a) + " of 5"]]}/>`;
}

/* SECTION history */
/* The GAN game on a grid: data is N(1, 0.6), the generator is N(m, s). Same formulas as CU-501's lab: D* = p / (p + q), V(D*, G) = -log 4 + 2 JSD. */
const H5_N = (x, m, s) => Math.exp(-((x - m) ** 2) / (2 * s * s)) / (s * Math.sqrt(2 * Math.PI));
export function h5Gan(m, s) {
  const dx = 12 / 600; let v = 0, kl1 = 0, kl2 = 0; const curve = [];
  for (let i = 0; i <= 600; i++) { const x = -6 + i * dx, p = H5_N(x, 1, 0.6), q = H5_N(x, m, s), d = p + q > 1e-300 ? p / (p + q) : 0.5, a = (p + q) / 2; if (p > 1e-300) { v += p * Math.log(d) * dx; kl1 += p * Math.log(p / a) * dx; } if (q > 1e-300) { v += q * Math.log(1 - d) * dx; kl2 += q * Math.log(q / a) * dx; } if (i % 6 === 0) curve.push([x, p, q, d]); }
  const jsd = (kl1 + kl2) / 2, atG = H5_N(m, 1, 0.6) / (H5_N(m, 1, 0.6) + H5_N(m, m, s)); return { v, jsd, bound: -Math.log(4) + 2 * jsd, atG, curve };
}
function H5GanValue({ onPass }) {
  const [m, setM] = useState(-2); const [s, setS] = useState(1); const r = h5Gan(m, s), ok = Math.abs(r.v + Math.log(4)) < 0.01; useEffect(() => { if (ok) onPass(); }, [ok]);
  const X = (x) => (x + 6) / 12 * 400, Y = (y) => Math.max(2, 96 - y * 110), Yd = (d) => 96 - d * 90, line = (i, f) => r.curve.map((c) => `${X(c[0]).toFixed(1)},${f(c[i]).toFixed(1)}`).join(" ");
  return html`<div class="cu-ctlrow"><${Slider} label="Generator mean" value=${m} min=${-4} max=${4} step=${0.1} onInput=${setM}/><${Slider} label="Generator spread" value=${s} min=${0.2} max=${2} step=${0.05} onInput=${setS}/></div><svg class="cu-chart" viewBox="0 0 400 100" role="img" aria-label=${"Data, generator and best discriminator. The discriminator reads " + r.atG.toFixed(2) + " at the generator's centre."}><polyline points=${line(1, Y)} fill="none" stroke="#5a9bf0" stroke-width="2"/><polyline points=${line(2, Y)} fill="none" stroke="#f5c518" stroke-width="2"/><polyline points=${line(3, Yd)} fill="none" stroke="currentColor" opacity=".55" stroke-dasharray="4 3"/></svg><${Read} items=${[["JSD between data and generator", r.jsd.toFixed(4)], ["value with the best judge", r.v.toFixed(4), ok ? "good" : ""], ["the floor, minus log 4", (-Math.log(4)).toFixed(4)], ["judge's D at the generator's centre", r.atG.toFixed(3)], ["pull on G from log(1 - D), which equals D", r.atG.toFixed(3)], ["pull on G from -log D, which equals 1 - D", (1 - r.atG).toFixed(3)]]}/><p class="cu-play-note">Blue is the data, yellow the generator, the dashed line the best possible judge. This is the exact sum on a grid, with a judge rebuilt for every position. Real training has neither.</p>`;
}
/* The VAE bound on CU-502's lab model: z ~ N(0, 1), x | z ~ N(2z + 1, 0.25), x = 2.5, so the posterior is known. */
export function h5Elbo(qm, qs, x = 2.5) {
  const pm = 2 * (x - 1) / 4.25, ps = Math.sqrt(0.25 / 4.25), logp = -0.5 * Math.log(2 * Math.PI * 4.25) - (x - 1) ** 2 / (2 * 4.25), gap = Math.log(ps / qs) + (qs * qs + (qm - pm) ** 2) / (2 * ps * ps) - 0.5; return { pm, ps, logp, gap, bound: logp - gap };
}
function H5ElboGap({ onPass }) {
  const [m, setM] = useState(0); const [s, setS] = useState(1); const r = h5Elbo(m, s), ok = r.gap < 0.01; useEffect(() => { if (ok) onPass(); }, [ok]); const X = (x) => (x + 3) / 6 * 400, pts = (a, b) => Array.from({ length: 121 }, (_, i) => { const x = -3 + i / 20; return `${X(x).toFixed(1)},${(96 - Math.min(H5_N(x, a, b) / 1.8, 1) * 90).toFixed(1)}`; }).join(" ");
  return html`<div class="cu-ctlrow"><${Slider} label="Mean of q" value=${m} min=${-2} max=${2} step=${0.01} onInput=${setM}/><${Slider} label="Spread of q" value=${s} min=${0.05} max=${1.5} step=${0.005} onInput=${setS}/></div><svg class="cu-chart" viewBox="0 0 400 100" role="img" aria-label=${"Your q against the true posterior. The gap is " + r.gap.toFixed(3)}><polyline points=${pts(r.pm, r.ps)} fill="none" stroke="#5a9bf0" stroke-width="2"/><polyline points=${pts(m, s)} fill="none" stroke="#f5c518" stroke-width="2"/></svg><${Read} items=${[["log p(x), which q cannot change", r.logp.toFixed(4)], ["the bound L", r.bound.toFixed(4)], ["the gap, KL to the posterior", r.gap.toFixed(4), ok ? "good" : ""]]}/><p class="cu-play-note">Blue is the true posterior for x = 2.5, the same model as the lab. Yellow is your q. Starting here, q is the prior, a q that ignores x. Every change moves the bound and the gap by the same amount in opposite directions.</p>`;
}
/* AdaIN against shift + x(1 + scale) on one small feature map. Same two formulas as CU-504's lab. */
const H5_MAP = [0.2, -0.9, 1.4, 0.3, -1.1, 0.8, -0.2, -0.5];
export function h5Style(gain, off, ys, yb) {
  const x = H5_MAP.map((v) => gain * v + off), mu = x.reduce((a, b) => a + b, 0) / x.length, sd = Math.sqrt(x.reduce((a, b) => a + (b - mu) ** 2, 0) / x.length), ada = x.map((v) => ys * (v - mu) / sd + yb), mod = x.map((v) => yb + v * (1 + (ys - 1))), most = (a) => Math.max(...a.map((v, i) => Math.abs(v - x[i])));
  return { x, ada, mod, changeAda: most(ada), changeMod: most(mod) };
}
function H5AdaIn({ onPass }) {
  const [gain, setGain] = useState(1); const [off, setOff] = useState(0); const [ys, setYs] = useState(2); const [yb, setYb] = useState(1); const r = h5Style(gain, off, ys, yb), idle = ys === 1 && yb === 0, ok = idle && (gain >= 3 || Math.abs(off) >= 2); useEffect(() => { if (ok) onPass(); }, [ok]);
  const bars = (a, y, col) => a.map((v, i) => html`<rect key=${i} x=${10 + i * 48} y=${v >= 0 ? y - Math.min(v * 4, 24) : y} width="38" height=${Math.min(Math.abs(v) * 4, 24)} fill=${col}/>`);
  return html`<div class="cu-ctlrow"><${Slider} label="Input gain" value=${gain} min=${0.5} max=${5} step=${0.5} onInput=${setGain}/><${Slider} label="Input offset" value=${off} min=${-4} max=${4} step=${0.5} onInput=${setOff}/><${Slider} label="Style scale" value=${ys} min=${0.5} max=${3} step=${0.5} onInput=${setYs}/><${Slider} label="Style shift" value=${yb} min=${-2} max=${2} step=${0.5} onInput=${setYb}/></div><svg class="cu-chart cu-chart-cap" viewBox="0 0 400 170" role="img" aria-label="Three rows of bars: the input, AdaIN's output and the (1 + scale) output."><g>${bars(r.x, 28, "#888")}</g><g>${bars(r.ada, 85, "#f5c518")}</g><g>${bars(r.mod, 142, "#5a9bf0")}</g></svg><${Read} items=${[["AdaIN, largest change to the input", r.changeAda.toFixed(2)], ["(1 + scale) form, largest change", r.changeMod.toFixed(2), idle && r.changeMod === 0 ? "good" : ""], ["AdaIN output, std", (Math.sqrt(r.ada.reduce((a, v) => a + (v - yb) ** 2, 0) / 8)).toFixed(2) + " (the style scale)"]]}/><p class="cu-play-note">Grey is the input, yellow AdaIN, blue shift + x(1 + scale), with scale = style scale minus 1. Bars are clipped at the edge of each row. With the style at 1 and 0 the blue row copies the input. AdaIN doesn't.</p>`;
}
/* CLIP's loss with no idea and at best, as in CU-505's lab. */
export function h5Clip(n, tau) { const wrong = (n - 1) * Math.exp(-(1 + 1 / (n - 1)) / tau); return { chance: Math.log(n), best: Math.log(1 + wrong), right: 1 / (1 + wrong) }; }
function H5ClipFloor({ onPass }) {
  const [n, setN] = useState(32); const [i, setI] = useState(70); const tau = Math.pow(10, -2 + 2 * i / 100), r = h5Clip(n, tau); const [high, setHigh] = useState(false); useEffect(() => { if (n === 32 && r.best > 1) setHigh(true); if (high && n === 32 && r.best < 0.01) onPass(); }, [n, i]);
  return html`<div class="cu-ctlrow"><${Seg} label="Batch N" value=${n} opts=${[[8, "8"], [32, "32"], [100, "100"], [1000, "1000"]]} onPick=${setN}/><${Slider} label="Temperature τ" value=${i} min=${0} max=${100} onInput=${setI} show=${tau.toFixed(3)}/></div><${Read} items=${[["no idea, every caption equal: ln N", r.chance.toFixed(4)], ["the very best this τ allows", r.best.toFixed(4), r.best < 0.01 ? "good" : ""], ["chance of the right caption, at best", r.right.toFixed(4)]]}/><p class="cu-play-note">Each image sits exactly on its caption and the captions are spread as far apart as N unit vectors can be. Nothing can score better than this. Cosines stop at 1, so a large τ puts a floor under the loss that no training can break.</p>`;
}


export const MORE = {
  agentgate: { title: "What may an agent do alone?", task: "Set each action to match this lesson's policy.", C: H2Gate, after: "Your policy may differ. What matters is that it's written down and enforced outside the model." },
  serving: { title: "Route jobs to workers", task: "With 4 workers, a job every 2.5 s and a 20 s model load, find a routing that cuts the wait to under a quarter of round robin's.", C: H2Serving, after: "When loads dominate, keeping models in place beats spreading jobs evenly." },
  provhash: { title: "What a graph hash catches", task: "Get all six right.", C: H2Prov2, after: "A graph hash is one part of a record. It says nothing about weights or code." },
  seeds: { title: "How many seeds?", task: "With no true difference and one seed, find a run that shows a gap over 1. Then set the true difference to 1, use the same seeds for both, and raise the seeds until the range is clear of 0.", C: H4Seeds, after: "One seed can name either winner. The same seeds for both samplers cancel most of the seed effect." },
  bestof: { title: "Best of k runs", task: "Find how many runs it takes for a gain over 1 to appear from nothing.", C: H4BestOf, after: "This is why you ask what a paper's number is the mean or the best of." },
  metrics: { title: "Same score, different damage", task: "Reach about 20 dB PSNR with two different kinds of change. Then compare what they look like and read Pearson r.", C: H4Metrics, after: "A score says how far apart two images are, not how." },
  checklist: { title: "Mark a prompt by hand", task: "Mark all five items for both renders.", C: H4Check, after: "One seed each, so this can't rank the samplers. It shows what a single number hides." },
  appform: { title: "Put a form on a graph", task: "Choose exactly three fields, all of them decisions for the person using the app.", C: H1AppForm, after: "A form changes values, never wires. Fields near the end of the chain cost fewer re-runs." },
  wsorder: { title: "When is a job finished?", task: "For each of the four jobs, find the message that means your script can stop waiting.", C: H1WsOrder, after: "Only executing with a null node comes in every case. Then read status_str in the history to learn how it ended." },
  uitoapi: { title: "Names for widgets_values", task: "Give each value of this KSampler its real input name. One value belongs to the editor only.", C: H1UiToApi, after: "A list with no names breaks quietly when it shifts by one. That is why you export rather than convert." },
  exposed: { title: "What each flag really protects", task: "Let other people in with a login, while only your proxy can reach ComfyUI.", C: H1Exposed, after: "ComfyUI has no login. --listen opens the door, CORS turns off the browser check, TLS encrypts, and none of them asks who you are." },
  rope: { title: "Rotate a position", task: "Keep the gap at 3 and try three different places. Then change the gap.", C: H3Rope, after: "Same gap, same score, wherever you stand. That is what makes RoPE relative." },
  patches: { title: "From pixels to tokens", task: "Set a 1024 image with VAE factor 8 and patch 2. Then double the side and read what happens to the pairs.", C: H3Patches, after: "Twice the side, four times the tokens, sixteen times the pairs." },
  bands: { title: "Why many frequencies", task: "With one frequency, find two different positions that look almost the same. Then switch to four frequencies.", C: H3Bands, after: "One wave repeats, so far-apart positions can share a code. More waves with longer wavelengths tell them apart." },
  kvcache: { title: "What a KV cache saves", task: "Find how many tokens it takes for the cache to save 99% of the attention pairs.", C: H3KvCache, after: "The saving is 1 minus 3 over (n + 2), so long runs gain most, and they also hold the most memory." },
  gate: { title: "Balance the experts", task: "With one expert per token, tilt the gate until one expert takes over 80% of the tokens. Then bring it back under a third.", C: H3Gate, after: "Routing costs the same either way, but a lopsided gate wastes the stored experts." },
  windows: { title: "How far a window reaches", task: "With window 8, turn on shifting and find how many layers it takes for every token to reach the corner.", C: H3Windows, after: "Without a shift a fixed window never reaches past its edge, however many layers you stack." },
  ganvalue: { title: "The game with a perfect judge", task: "Move the generator on to the data until the value is within 0.01 of minus log 4. Then read what the judge says.", C: H5GanValue, after: "At the floor the judge says one half everywhere, a coin flip. Note that the pull from log(1 - D) is weakest when the generator is far away, which is when it needs it most." },
  elbogap: { title: "Close the gap in the bound", task: "Move q until the gap is under 0.01. Watch log p(x) while you do it.", C: H5ElboGap, after: "log p(x) never moved. Only the split between the bound and the gap did, and the gap closes only when q is the posterior." },
  adain: { title: "What a style forgets", task: "Set the style to do nothing, scale 1 and shift 0. Then turn up the input's gain to 3 or more, or its offset to 2 or more.", C: H5AdaIn, after: "The (1 + scale) form passes the input through untouched. AdaIN rewrites it to the style's numbers, whatever came in." },
  clipfloor: { title: "The floor under CLIP's loss", task: "At batch 32, find a temperature where even the best case costs more than 1. Then lower it until the best case is under 0.01.", C: H5ClipFloor, after: "Temperature limits how sure the model can be. Too low brings other trouble, which the lab's table shows." },
};
