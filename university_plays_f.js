/* ComfyUniversity labs for the custom node and debugging tracks. Behaviour shown here was checked by running ComfyUI v0.43.0's real engine on a CPU with small test nodes, as each lesson's verified list says. Nothing here talks to a server. */
import { useEffect, useMemo, useRef, useState } from "preact/hooks";
import { html } from "./common.js";

const Slider = ({ label, value, min, max, step = 1, onInput, show }) => html`<label class="cu-ctl"><span>${label} <b>${show != null ? show : value}</b></span><input type="range" min=${min} max=${max} step=${step} value=${value} onInput=${(e) => onInput(+e.target.value)}/></label>`;
const Seg = ({ label, value, opts, onPick }) => html`<div class="cu-ctl"><span>${label}</span><div class="cu-seg" role="group" aria-label=${label} style=${{ alignSelf: "flex-start" }}>${opts.map(([k, l]) => html`<button type="button" aria-pressed=${value === k} onClick=${() => onPick(k)}>${l}</button>`)}</div></div>`;
const Read = ({ items }) => html`<dl class="cu-read">${items.map(([k, v, cls]) => html`<div class=${cls || ""}><dt>${k}</dt><dd>${v}</dd></div>`)}</dl>`;

/* ---------- pure logic ---------- */
/* The visits a lazy switch makes, in the order a real run logged them. */
export function lazyTrace(useA, lazy) {
  const want = useA ? "A" : "B";
  if (!lazy) return ["branch A runs", "branch B runs", "switch runs with both values, and uses " + want];
  return ["check_lazy_status: a=None, b=None. It returns ['" + want.toLowerCase() + "']", "the node goes back in the list, pending", "branch " + want + " runs", "check_lazy_status again: " + want.toLowerCase() + " has a value now", "execute runs, with the other input still None"];
}
/* _async_map_node_over_list: one call per longest list, a shorter list repeats its last value. */
export function listCalls(a, b, inputIsList) {
  const A = Array.from({ length: a }, (_, i) => i + 1), B = Array.from({ length: b }, (_, i) => (i + 1) * 10);
  if (inputIsList) return [{ a: A, b: B }];
  return Array.from({ length: Math.max(a, b) }, (_, i) => ({ a: A[i < a ? i : a - 1], b: B[i < b ? i : b - 1] }));
}
/* The ids GraphBuilder gave in a real run of node 2, first call: prefix 2.0.0. then a counter. */
export const expandIds = (times, parent = "2") => Array.from({ length: times }, (_, i) => `${parent}.0.0.${i + 1}`);
export function versionTuple(v) { return v.split(".").map(Number); }
export function cmpVersion(a, b) { const x = versionTuple(a), y = versionTuple(b); for (let i = 0; i < Math.max(x.length, y.length); i++) { const d = (x[i] || 0) - (y[i] || 0); if (d) return d; } return 0; }
export function satisfies(version, spec) { const m = /^(==|>=|<=|<|>)(.+)$/.exec(spec); if (!m) return true; const c = cmpVersion(version, m[2]); return { "==": c === 0, ">=": c >= 0, "<=": c <= 0, "<": c < 0, ">": c > 0 }[m[1]]; }
/* A 3 by 3 average. NaN in any of the 9 makes the result NaN, as in a real convolution. */
export function blurStep(g) { const n = g.length; return g.map((row, y) => row.map((_, x) => { let s = 0, k = 0; for (let j = -1; j <= 1; j++) for (let i = -1; i <= 1; i++) { const v = (g[y + j] || [])[x + i]; if (v !== undefined) { s += v; k++; } } return s / k; })); }
export function nanGrid(steps, n = 15, at = [4, 5]) { let g = Array.from({ length: n }, (_, y) => Array.from({ length: n }, (_, x) => 0.25 + 0.5 * ((x + y) % 2))); g[at[1]][at[0]] = NaN; for (let i = 0; i < steps; i++) g = blurStep(g); return g; }
export function chainState(bad, i) { return i >= bad ? "bad" : "good"; }

/* ---------- lazy ---------- */
function LazyFlow({ onPass }) {
  const [useA, setUseA] = useState(true); const [lazy, setLazy] = useState(true); const [step, setStep] = useState(0); const [seen, setSeen] = useState({});
  const t = useMemo(() => lazyTrace(useA, lazy), [useA, lazy]); const end = step >= t.length; const runs = lazy ? 1 : 2;
  useEffect(() => { if (end) { const n = { ...seen, [lazy ? "on" : "off"]: true }; setSeen(n); if (n.on && n.off) onPass(); } }, [end]);
  return html`<div class="cu-ctlrow"><${Seg} label="use_a" value=${useA ? "y" : "n"} opts=${[["y", "True"], ["n", "False"]]} onPick=${(k) => { setUseA(k === "y"); setStep(0); }}/><${Seg} label="Inputs a and b" value=${lazy ? "y" : "n"} opts=${[["y", "lazy"], ["n", "ordinary"]]} onPick=${(k) => { setLazy(k === "y"); setStep(0); }}/></div><ol class="cu-risk">${t.slice(0, step).map((l, k) => html`<li key=${k}><code>${l}</code></li>`)}</ol><div class="cu-lab-acts"><button type="button" class="cu-btn primary" disabled=${end} style=${end ? { cursor: "default" } : null} onClick=${() => setStep(step + 1)}>${end ? "Finished" : "Next step"}</button></div><${Read} items=${[["Branches that ran", end ? runs : "..."], ["Node visits", end ? (lazy ? 2 : 1) : "..."]]}/><p class="cu-play-note">The order is what a real run logged on a CPU, with two small test nodes on the branches.</p>`;
}

/* ---------- lists ---------- */
function ListMap({ onPass }) {
  const [a, setA] = useState(3); const [b, setB] = useState(1); const [all, setAll] = useState(false); const [seen, setSeen] = useState({});
  const calls = useMemo(() => listCalls(a, b, all), [a, b, all]);
  useEffect(() => { const n = { ...seen }; if (!all && a === 5 && b < a) n.each = 1; if (all && a === 5) n.whole = 1; setSeen(n); if (n.each && n.whole) onPass(); }, [a, b, all]);
  return html`<div class="cu-ctlrow"><${Slider} label="Items wired to a" value=${a} min=${1} max=${6} onInput=${setA}/><${Slider} label="Items wired to b" value=${b} min=${1} max=${6} onInput=${setB}/><${Seg} label="INPUT_IS_LIST" value=${all ? "y" : "n"} opts=${[["n", "False"], ["y", "True"]]} onPick=${(k) => setAll(k === "y")}/></div><ol class="cu-risk">${calls.map((c, k) => html`<li key=${k}><code>call ${k + 1}: execute(a=${JSON.stringify(c.a)}, b=${JSON.stringify(c.b)})</code></li>`)}</ol><${Read} items=${[["Calls", calls.length, !all && calls.length === 5 ? "good" : ""], ["Longest list", Math.max(a, b)]]}/>`;
}

/* ---------- expansion ---------- */
function Expand({ onPass }) {
  const [t, setT] = useState(3); const ids = useMemo(() => expandIds(t), [t]); const mean = t % 2 ? 0.8745 : 0.1255; useEffect(() => { if (t === 6) onPass(); }, [t]);
  const code = `g = GraphBuilder()\nlast = None\nfor i in range(times):        # times = ${t}\n    last = g.node("ImageInvert", image=last.out(0) if last else image)\nreturn {"result": (last.out(0),), "expand": g.finalize()}`;
  return html`<div class="cu-ctlrow"><${Slider} label="times" value=${t} min=${1} max=${8} onInput=${setT}/></div><pre class="cu-code" tabindex="0"><code>${code}</code></pre><div class="cu-chips" role="group" aria-label="The nodes this call adds">${ids.map((i) => html`<span class="cu-chip" style=${{ cursor: "default" }} key=${i}>${i}</span>`)}</div><${Read} items=${[["Nodes on your canvas", 3], ["Nodes the engine ran", 3 + t], ["Mean of the result", mean.toFixed(4)]]}/><p class="cu-play-note">Those ids and that mean came from running this node for real with <code>times=3</code>, on a picture whose mean is 0.1255. The other rows follow the same counter, and inverting twice gives the picture back.</p>`;
}

/* ---------- hooks ---------- */
const HOOKS = ["init", "addCustomNodeDefs", "getCustomWidgets", "beforeRegisterNodeDef", "registerCustomNodes", "beforeConfigureGraph", "nodeCreated", "loadedGraphNode", "afterConfigureGraph", "setup"];
const SHUFFLED = ["setup", "nodeCreated", "init", "registerCustomNodes", "afterConfigureGraph", "addCustomNodeDefs", "loadedGraphNode", "beforeRegisterNodeDef", "getCustomWidgets", "beforeConfigureGraph"];
function HookOrder({ onPass }) {
  const [done, setDone] = useState([]); const [miss, setMiss] = useState("");
  const tap = (h) => { if (done.includes(h)) return; if (HOOKS[done.length] === h) { const d = [...done, h]; setDone(d); setMiss(""); if (d.length === HOOKS.length) onPass(); } else setMiss(`${h} comes later. ${done.length} placed so far.`); };
  return html`<p class="cu-q-line">The page has just loaded. Tap the hooks in the order the docs give.</p><div class="cu-chips">${SHUFFLED.map((h) => html`<button type="button" class="cu-chip" key=${h} aria-pressed=${done.includes(h)} onClick=${() => tap(h)}>${h}</button>`)}</div><ol class="cu-risk">${done.map((h) => html`<li key=${h}><code>${h}</code></li>`)}</ol><p class="cu-play-note" role="status">${miss || "beforeRegisterNodeDef runs once per node type, so it is where you patch a node class."}</p>`;
}

/* ---------- pins ---------- */
const HOST = { torch: "2.6.0", numpy: "1.26.4", pillow: "10.4.0" };
function Pins({ onPass }) {
  const [t, setT] = useState("==2.1.0"); const [n, setN] = useState("==1.24.0"); const [cv, setCv] = useState(">=4.8");
  const rows = [["torch", t, HOST.torch], ["numpy", n, HOST.numpy]].filter((r) => r[1]); const moved = rows.filter((r) => !satisfies(r[2], r[1])); const ok = moved.length === 0 && !t && cv === ">=4.8";
  useEffect(() => { if (ok) onPass(); }, [ok]);
  return html`<p class="cu-q-line">A made-up install has torch ${HOST.torch}, numpy ${HOST.numpy} and pillow ${HOST.pillow}. Write your pack's requirements.</p><div class="cu-ctlrow"><${Seg} label="torch" value=${t} opts=${[["==2.1.0", "==2.1.0"], [">=2.0", ">=2.0"], ["", "not listed"]]} onPick=${setT}/><${Seg} label="numpy" value=${n} opts=${[["==1.24.0", "==1.24.0"], [">=1.25", ">=1.25"], ["", "not listed"]]} onPick=${setN}/><${Seg} label="opencv-python" value=${cv} opts=${[["==4.5.0.48", "==4.5.0.48"], [">=4.8", ">=4.8"]]} onPick=${setCv}/></div><${Read} items=${[["Would move", moved.length ? moved.map((r) => `${r[0]} ${r[2]} (you asked ${r[1]})`).join(", ") : "nothing", moved.length ? "bad" : "good"], ["torch", t ? "you claim a say in it" : "left to the host", t ? "" : "good"], ["opencv-python", cv === ">=4.8" ? "a floor, so it can resolve" : "an old exact pin", cv === ">=4.8" ? "good" : "bad"]]}/><p class="cu-play-note">This is a teaching model of one check. The real answer comes from <code>pip install --dry-run</code> on the real install, which also looks at what your dependencies need.</p>`;
}

/* ---------- NaN ---------- */
function NanSpread({ onPass }) {
  const [s, setS] = useState(0); const g = useMemo(() => nanGrid(s), [s]); const flat = g.flat(); const nans = flat.filter((v) => Number.isNaN(v)).length; const all = nans === flat.length; useEffect(() => { if (all) onPass(); }, [all]);
  return html`<div class="cu-ctlrow"><${Slider} label="Blur passes" value=${s} min=${0} max=${12} onInput=${setS}/></div><div role="img" aria-label=${`${nans} of ${flat.length} pixels are NaN`} style=${{ display: "grid", gridTemplateColumns: "repeat(15,1fr)", gap: "1px", maxWidth: "300px" }}>${flat.map((v, i) => html`<i key=${i} style=${{ aspectRatio: "1", background: Number.isNaN(v) ? "#000" : `hsl(45 60% ${Math.round(v * 80 + 10)}%)` }}></i>`)}</div><${Read} items=${[["NaN pixels", `${nans} of ${flat.length}`, all ? "bad" : ""], ["Saved as", nans ? "0, 0, 0 in those pixels" : "ordinary colours"]]}/><p class="cu-play-note">A 3 by 3 average stands in for a convolution. The black comes from a real run: ComfyUI's <code>SaveImage</code> turned NaN into pixel value 0, with the warning <code>invalid value encountered in cast</code>.</p>`;
}

/* ---------- traceback ---------- */
const TB = [
  "!!! Exception during processing !!! The size of tensor a (4) must match the size of tensor b (16) at non-singleton dimension 1",
  "Traceback (most recent call last):",
  '  File "execution.py", line 548, in execute',
  '  File "execution.py", line 353, in get_output_data',
  '  File "execution.py", line 327, in _async_map_node_over_list',
  '  File "execution.py", line 315, in process_inputs',
  '  File "comfy_api/internal/__init__.py", line 149, in wrapped_func',
  '  File "comfy_api/latest/_io.py", line 2219, in EXECUTE_NORMALIZED',
  '  File "comfy_extras/nodes_latent.py", line 43, in execute',
  '    samples_out["samples"] = s1 + s2',
  "RuntimeError: The size of tensor a (4) must match the size of tensor b (16) at non-singleton dimension 1",
];
const TBQ = [
  { q: "Tap the frame that belongs to the node, not the engine.", a: [8], why: "The engine's own frames come first. The last file before the error is the code that failed." },
  { q: "Tap the line of code that failed.", a: [9], why: "s1 + s2: two tensors added together." },
  { q: "Tap a line that names the sizes that disagree.", a: [0, 10], why: "4 and 16 at dimension 1. In a latent, dimension 1 is the channels, so two different latent families met." },
];
function Tracer({ onPass }) {
  const [i, setI] = useState(0); const [msg, setMsg] = useState(""); const q = TBQ[Math.min(i, TBQ.length - 1)]; const done = i >= TBQ.length;
  const tap = (k) => { if (done) return; if (q.a.includes(k)) { setMsg(q.why); const n = i + 1; setI(n); if (n >= TBQ.length) onPass(); } else setMsg(k < q.a[0] ? "Not that one. Look further down." : "Not that one. Look further up."); };
  return html`<p class="cu-q-line"><b>${done ? "All found." : q.q}</b></p><ol class="cu-risk">${TB.map((l, k) => html`<li key=${k}><button type="button" class="cu-riskl" onClick=${() => tap(k)}><code style=${{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>${l}</code></button></li>`)}</ol><p class="cu-play-note" role="status">${msg || "A real traceback from LatentAdd, given a 4-channel and a 16-channel latent. We cut the long code lines of the engine's frames."}</p>`;
}

/* ---------- bisect ---------- */
const CHAIN = 16; const BAD = [11, 6, 14, 3];
function Bisect({ onPass }) {
  const [round, setRound] = useState(0); const [probes, setProbes] = useState({}); const bad = BAD[round % BAD.length]; const n = Object.keys(probes).length; const found = probes[bad] === "bad" && probes[bad - 1] === "good"; const good = found && n <= 5;
  useEffect(() => { if (good) onPass(); }, [good]);
  return html`<p class="cu-q-line">The output is wrong. Node 0 is fine. Tap a node to put a preview on it. Find the first bad node with 5 previews or fewer.</p><div class="cu-chips">${Array.from({ length: CHAIN }, (_, i) => html`<button type="button" class="cu-chip" key=${i} aria-pressed=${!!probes[i]} style=${probes[i] ? { borderColor: probes[i] === "bad" ? "#ff8a80" : "#27e07f" } : null} onClick=${() => setProbes({ ...probes, [i]: chainState(bad, i) })}>${i}${probes[i] ? (probes[i] === "bad" ? " bad" : " ok") : ""}</button>`)}</div><${Read} items=${[["Previews used", n, n > 5 ? "bad" : ""], ["Halving needs", "at most 4 for 16 nodes"], ["Result", found ? (good ? `node ${bad} is the first bad one` : `node ${bad}, but that took over 5 previews. Try a new chain.`) : n >= 5 ? "out of previews. Try a new chain." : "keep going", good ? "good" : ""]]}/><div class="cu-lab-acts"><button type="button" class="cu-btn" onClick=${() => { setRound(round + 1); setProbes({}); }}>New chain</button></div>`;
}

/* ---------- pick the answer ---------- */
const pick = (items) => function Pick({ onPass }) {
  const [i, setI] = useState(0); const [got, setGot] = useState(null); const [score, setScore] = useState(0); const it = items[i % items.length]; const right = got === it.a; const box = useRef(null); const moved = useRef(false);
  useEffect(() => { if (moved.current && box.current) { const b = box.current.querySelector("button"); if (b) b.focus(); moved.current = false; } });
  const choose = (o) => { if (got != null) return; setGot(o); if (o === it.a) { const s = score + 1; setScore(s); if (s >= items.length) onPass(); } };
  const next = () => { moved.current = true; if (i + 1 < items.length) { setI(i + 1); setGot(null); } else { setI(0); setScore(0); setGot(null); } };
  return html`<p class="cu-q-line"><b>${i + 1} of ${items.length}.</b> ${it.q}</p>${it.code && html`<pre class="cu-code" style=${{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}><code>${it.code}</code></pre>`}<div class="cu-errs" ref=${box}>${it.o.map((o) => html`<button type="button" key=${o} class=${"cu-opt" + (got === o ? (right ? " ok" : " no") : "")} aria-pressed=${got === o} onClick=${() => choose(o)}>${o}</button>`)}</div>${got != null && html`<p class=${right ? "cu-why" : "cu-why no"} role="status">${right ? "" : `It is: ${it.a}. `}${it.why}</p><div class="cu-lab-acts"><button type="button" class="cu-btn primary" onClick=${next}>${i + 1 < items.length ? "Next" : "Start again"}</button><span class="cu-play-note">${score} of ${items.length} right</span></div>`}`;
};

const RERUN_ITEMS = [
  { q: "No hook at all. You queue again and nothing changed. Does the node run?", o: ["It runs", "It comes from the cache"], a: "It comes from the cache", why: "A real run: 3 queues, 1 execution." },
  { q: "IS_CHANGED returns False every time. You queue again.", o: ["It runs", "It comes from the cache"], a: "It comes from the cache", why: "Returning False does not mean 'never', it means a value that joins the key, and the value is the same. A real run: 3 queues, 1 execution." },
  { q: "IS_CHANGED returns a file's hash, and you overwrote the file. You queue again.", o: ["It runs", "It comes from the cache"], a: "It runs", why: "The hash is in the key, so the key is new." },
  { q: 'IS_CHANGED returns float("NaN"). You queue again.', o: ["It runs", "It comes from the cache"], a: "It runs", why: "NaN never equals itself, so the key never matches. A real run: 3 queues, 3 executions, and everything downstream ran again too." },
  { q: "Two identical copies of an ordinary node in one graph, same inputs. How many run?", o: ["1", "2"], a: "1", why: "They have the same key. A real run: 1 execution." },
  { q: "The same two copies, but the schema sets not_idempotent=True.", o: ["1", "2"], a: "2", why: "The node id joins the key. A real run: 2 executions, and 0 more on the next queue, because it is still cached." },
];
const INPUT_ITEMS = [
  { q: "A required input is left unwired and has no value in the prompt.", o: ["The default is used", "required_input_missing"], a: "required_input_missing", why: "The default is the widget's starting value in the editor. The server does not fill it in." },
  { q: "An optional input is left out of the prompt, and it has default 3 in the schema. What does your function get?", o: ["3", "Nothing: the argument is not passed"], a: "Nothing: the argument is not passed", why: "A real run: our function's own default of None was used, not the 3. So give the argument a default in Python." },
  { q: "force_input=True on a STRING. An API client sends a constant, not a wire.", o: ["It is rejected", "It works"], a: "It works", why: "A real run: the constant arrived. force_input shapes the editor, and the server does not enforce it." },
  { q: "The prompt has an input your node never declared, with a constant value.", o: ["It is rejected", "It is ignored"], a: "It is ignored", why: "A real run: the node ran and never saw it. V3 can opt in with accept_all_inputs." },
  { q: "You mark a required input lazy, and leave it unwired.", o: ["It waits until needed", "required_input_missing"], a: "required_input_missing", why: "A real run. Lazy decides when a wire is evaluated. It does not make the input optional." },
  { q: "You ask for the hidden input UNIQUE_ID. Does that change caching?", o: ["No", "Yes: the node id joins the key"], a: "Yes: the node id joins the key", why: "include_unique_id_in_input in caching.py, so two copies stop sharing a result." },
];
const MISSING_ITEMS = [
  { q: "Which is it?", code: "Node 'SuperKSampler' not found. The custom node may not be installed.", o: ["A missing node class", "A missing model file", "A broken file"], a: "A missing node class", why: "missing_node_type. It stops everything before any other check. Find which pack provides it." },
  { q: "Which is it?", code: "Value not in list: ckpt_name: 'model_a.safetensors' not in []", o: ["A missing node class", "A missing model file", "A broken file"], a: "A missing model file", why: "value_not_in_list on a file menu. Put the file in the right folder or pick one you have. The empty list here means that folder holds no models." },
  { q: "Which is it?", code: "safetensors_rust.SafetensorError: Error while deserializing header: incomplete metadata, file not fully covered", o: ["A missing node class", "A missing model file", "A broken file"], a: "A broken file", why: "The file exists and is cut short. A real run on a truncated file. Download it again and compare the hash." },
  { q: "Which is it?", code: "RuntimeError: ERROR: Could not detect model type of: <path>", o: ["A wrong kind of file", "A missing node class", "An out of memory error"], a: "A wrong kind of file", why: "It opened fine, and ComfyUI could not recognise it as a checkpoint. It may be a LoRA or a bare UNet in the wrong folder and loader." },
  { q: "Which is it?", code: "Error while deserializing header: header too large", o: ["A saved web page or other non-model file", "A missing node class", "A LoRA in the wrong folder"], a: "A saved web page or other non-model file", why: "A real run on a small HTML file renamed to .safetensors. The first bytes are read as a length. Look at the file size." },
];
const REPRO_ITEMS = [
  { q: "Same model, seed, sampler and prompt. You changed only the scheduler from normal to karras. In our one-seed SDXL test, what happened?", o: ["The picture stayed the same", "The picture changed"], a: "The picture changed", why: "Average pixel difference 23.26 on a 0 to 255 scale in the Sampling Lab." },
  { q: "Euler and DDIM on SD 1.5 with the same seed, in our one-seed test:", o: ["Byte-identical files", "Very different pictures"], a: "Byte-identical files", why: "renders.json lists them as identical. So a different name does not always mean a different picture." },
  { q: "You set batch_size 4 and want to reproduce the third image alone. What else must match?", o: ["Nothing, the seed is enough", "The batch index, using LatentFromBatch or a batch of the same size"], a: "The batch index, using LatentFromBatch or a batch of the same size", why: "prepare_noise draws noise for the whole batch from one generator, so the third image's noise is not what batch 1 with that seed gives." },
  { q: "A PNG carries its graph, and you open it. Which of these does the file name in the graph not prove?", o: ["That your file has the same weights", "That the sampler was euler"], a: "That your file has the same weights", why: "The metadata stores a file name. A renamed or re-saved file looks the same. Compare a hash." },
  { q: "Does the seed's noise depend on the graphics card in core KSampler?", o: ["No, it is drawn on the CPU", "Yes, each card draws its own"], a: "No, it is drawn on the CPU", why: "prepare_noise uses device='cpu'. Differences appear later, in the maths on the card." },
];
const TEST_ITEMS = [
  { q: "You swapped min and max in a schema by mistake. The cheapest test that catches it:", o: ["Call validate_prompt on a graph using your node", "Render a picture"], a: "Call validate_prompt on a graph using your node", why: "It needs no GPU and no model, and it returns value_smaller_than_min or value_bigger_than_max." },
  { q: "Two inputs share an id in define_schema. What catches it?", o: ["GET_SCHEMA raises ValueError", "Nothing until a user runs it"], a: "GET_SCHEMA raises ValueError", why: "A real run: Input ids must be unique, but ['a'] are not." },
  { q: "Your V1 function returns x instead of (x,). What catches it?", o: ["Running it through the executor", "Calling the function directly"], a: "Running it through the executor", why: "Calling it directly just returns x. A real run through the engine fails with TypeError: object of type 'int' has no len()." },
  { q: "You changed an input tensor in place. What catches it?", o: ["A test that checks the input is unchanged after the call", "validate_prompt"], a: "A test that checks the input is unchanged after the call", why: "Validation only looks at the graph. In a real run the mean drifted 0.3755, 0.6255, 0.8755 across three queues." },
  { q: "You want to prove your node's fingerprint works.", o: ["Queue twice in one executor and count the calls", "Read the code"], a: "Queue twice in one executor and count the calls", why: "That is how this lesson's numbers were made, and it needs no server." },
];

export const MORE = {
  f_lazy: { title: "Walk a lazy switch", task: "Step to the end with lazy inputs, then with ordinary inputs. Compare how many branches ran.", C: LazyFlow, after: "Lazy costs a second visit to the node, and saves a whole branch." },
  f_lists: { title: "How many calls?", task: "Make exactly 5 calls with b shorter than a. Then turn on INPUT_IS_LIST with a still at 5.", C: ListMap, after: "A shorter list repeats its last item. INPUT_IS_LIST means one call, and every input is a list, widgets too." },
  f_expand: { title: "A node that adds nodes", task: "Set times so the picture comes back to where it started, with 6 inverts.", C: Expand, after: "The canvas never changes. Those nodes exist only inside the run." },
  f_hooks: { title: "Order the extension hooks", task: "Put the ten hooks in the order they fire when the page loads.", C: HookOrder, after: "Most extensions need only setup, beforeRegisterNodeDef or nodeCreated." },
  f_pins: { title: "Requirements that move nothing", task: "Write requirements that move nothing in the host install, and leave torch to the host.", C: Pins, after: "A floor says what you need. An exact pin says what everyone else must have." },
  f_nan: { title: "One bad pixel", task: "Find how many blur passes it takes for one NaN to fill the picture.", C: NanSpread, after: "NaN never goes away by averaging. That is why one bad value can give a fully black image." },
  f_trace: { title: "Read a real traceback", task: "Find the three lines that matter.", C: Tracer, after: "Read from the bottom. The last line is what, and the frame above it is where." },
  f_bisect: { title: "Find the bad node", task: "Find the first bad node in a chain of 16 with at most 5 previews.", C: Bisect, after: "Each preview in the middle halves what is left. Walking from the start could take 14." },
  f_rerun: { title: "Will it run again?", task: "Get all six right. Each answer comes from a real run.", C: pick(RERUN_ITEMS), after: "The hook gives a value for the key. It does not answer yes or no." },
  f_inputs: { title: "What happens to this input?", task: "Get all six right. Five answers come from a real run, and one from the cache code.", C: pick(INPUT_ITEMS), after: "Widgets, defaults and force_input are promises to the editor. Validation checks less than you might guess." },
  f_missing: { title: "Name that error", task: "Get all five right.", C: pick(MISSING_ITEMS), after: "Class missing, file missing, file broken, file of the wrong kind: four errors with four different fixes." },
  f_repro: { title: "Reproducing someone's image", task: "Get all five right.", C: pick(REPRO_ITEMS), after: "Change one thing at a time, and compare hashes when you can." },
  f_tests: { title: "Which test catches it?", task: "Get all five right.", C: pick(TEST_ITEMS), after: "Most node bugs show up without a GPU or a model." },
};
