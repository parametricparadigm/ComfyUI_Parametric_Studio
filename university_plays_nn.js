/* ComfyUniversity: train a tiny network live in the browser. The maths is university_mlp.js, plain JavaScript checked against finite differences and PyTorch. Nothing is fetched and nothing leaves the page. */
import { useEffect, useMemo, useRef, useState } from "preact/hooks";
import { html } from "./common.js";
import * as N from "./university_mlp.js";

const Slider = ({ label, value, min, max, step = 1, onInput, show }) => html`<label class="cu-ctl"><span>${label} <b>${show != null ? show : value}</b></span><input type="range" min=${min} max=${max} step=${step} value=${value} onInput=${(e) => onInput(+e.target.value)}/></label>`;
const Seg = ({ label, value, opts, onPick }) => html`<div class="cu-ctl"><span>${label}</span><div class="cu-seg" role="group" aria-label=${label}>${opts.map(([k, l]) => html`<button type="button" aria-pressed=${value === k} onClick=${() => onPick(k)}>${l}</button>`)}</div></div>`;
const Read = ({ items }) => html`<dl class="cu-read">${items.map(([k, v, cls]) => html`<div class=${cls || ""}><dt>${k}</dt><dd>${v}</dd></div>`)}</dl>`;
const RATES = [0.003, 0.01, 0.03, 0.1, 0.3, 1, 3];
const C0 = [90, 155, 240], C1 = [245, 197, 24];            // class 0 blue, class 1 gold
const RES = 48, LIM = 1.2, BUDGET_MS = 9;

function drawField(cv, net, d) {
  if (!cv) return; const x = cv.getContext("2d"), S = cv.width, f = N.field(net, RES, LIM), img = x.createImageData(RES, RES);
  for (let i = 0; i < RES * RES; i++) { const p = f[i], k = Math.abs(p - 0.5) * 2, c = p >= 0.5 ? C1 : C0, s = 0.18 + 0.42 * k; img.data[4 * i] = 16 + c[0] * s; img.data[4 * i + 1] = 16 + c[1] * s; img.data[4 * i + 2] = 18 + c[2] * s; img.data[4 * i + 3] = 255; }
  const off = document.createElement("canvas"); off.width = RES; off.height = RES; off.getContext("2d").putImageData(img, 0, 0);
  x.imageSmoothingEnabled = true; x.drawImage(off, 0, 0, S, S);
  const P = (v) => (v / LIM + 1) / 2 * S;
  for (const [set, hollow] of [[d.train, false], [d.test, true]]) set.X.forEach((p, i) => { const c = set.y[i] ? C1 : C0; x.beginPath(); x.arc(P(p[0]), S - P(p[1]), hollow ? 4 : 3.4, 0, 6.2832); if (hollow) { x.lineWidth = 1.6; x.strokeStyle = `rgb(${c})`; x.stroke(); } else { x.fillStyle = `rgb(${c})`; x.fill(); x.lineWidth = 0.8; x.strokeStyle = "rgba(0,0,0,.55)"; x.stroke(); } });
}

/* Every weight as a line between two neurons: colour is the sign, thickness the size. */
function drawNet(cv, net) {
  if (!cv) return; const x = cv.getContext("2d"), W = cv.width, H = cv.height, s = net.sizes; x.clearRect(0, 0, W, H);
  const col = (l) => 18 + l / (s.length - 1) * (W - 36), row = (l, i) => H / 2 + (i - (s[l] - 1) / 2) * Math.min(22, (H - 24) / Math.max(1, s[l] - 1));
  let big = 1e-9; for (const w of net.W) for (const v of w) big = Math.max(big, Math.abs(v));
  for (let l = 0; l < net.W.length; l++) for (let o = 0; o < s[l + 1]; o++) for (let i = 0; i < s[l]; i++) {
    const v = net.W[l][o * s[l] + i], t = Math.abs(v) / big; x.strokeStyle = v >= 0 ? `rgba(245,197,24,${0.15 + 0.85 * t})` : `rgba(90,155,240,${0.15 + 0.85 * t})`; x.lineWidth = 0.4 + 3.2 * t;
    x.beginPath(); x.moveTo(col(l), row(l, i)); x.lineTo(col(l + 1), row(l + 1, o)); x.stroke();
  }
  for (let l = 0; l < s.length; l++) for (let i = 0; i < s[l]; i++) { x.beginPath(); x.arc(col(l), row(l, i), 4.5, 0, 6.2832); x.fillStyle = "#f6f6f1"; x.fill(); }
}

function lossPath(h, W, H) {
  if (h.length < 2) return ""; const lo = Math.log(Math.max(1e-4, Math.min(...h))), hi = Math.log(Math.max(...h, 1e-3)), span = Math.max(hi - lo, 1e-6);
  return h.map((v, i) => (i ? "L" : "M") + (4 + i / (h.length - 1) * (W - 8)).toFixed(1) + " " + (4 + (1 - (Math.log(Math.max(v, 1e-4)) - lo) / span) * (H - 8)).toFixed(1)).join("");
}

function TinyNet({ onPass }) {
  const [kind, setKind] = useState("spiral"); const [layers, setLayers] = useState(2); const [width, setWidth] = useState(8); const [ri, setRi] = useState(4); const [act, setAct] = useState("tanh"); const [noise, setNoise] = useState(0.1); const [seed, setSeed] = useState(1);
  const [run, setRun] = useState(false); const [tick, setTick] = useState(0); const [gc, setGc] = useState(null);
  const lr = RATES[ri]; const data = useMemo(() => N.split(N.dataset(kind, 240, noise, 7)), [kind, noise]);
  const S = useRef(null); const field = useRef(null); const netCv = useRef(null);
  /* A fresh network whenever the shape, activation, data or seed changes. The learning rate can change mid-run, as in the real thing. */
  useEffect(() => { S.current = { net: N.init(N.sizesOf(layers, width), act, seed), steps: 0, hist: [], moved: 0, diverged: false }; setGc(null); setTick((t) => t + 1); }, [layers, width, act, kind, noise, seed]);
  useEffect(() => {
    if (!run) return; let id = 0, on = true;
    const frame = () => {
      if (!on) return; const s = S.current, t0 = performance.now(); let r = null;
      do { r = N.step(s.net, data.train.X, data.train.y, lr); s.steps++; } while (performance.now() - t0 < BUDGET_MS && isFinite(r.loss));
      s.moved = r.moved; if (!isFinite(r.loss)) { s.diverged = true; setRun(false); }
      s.hist.push(r.loss); if (s.hist.length > 400) s.hist = s.hist.filter((_, i) => i % 2 === 0);
      setTick((k) => k + 1); id = requestAnimationFrame(frame);
    };
    id = requestAnimationFrame(frame); return () => { on = false; cancelAnimationFrame(id); };
  }, [run, lr, data]);
  const s = S.current; const net = s && s.net;
  useEffect(() => { if (net) { drawField(field.current, net, data); drawNet(netCv.current, net); } }, [tick, data]);
  const tr = net ? N.accuracy(net, data.train.X, data.train.y) : 0, te = net ? N.accuracy(net, data.test.X, data.test.y) : 0; const L = net ? N.loss(net, data.train.X, data.train.y) : 0;
  const ok = kind === "spiral" && tr >= 0.95 && te >= 0.9; useEffect(() => { if (ok) onPass(); }, [ok]);
  const one = () => { const r = N.step(net, data.train.X, data.train.y, lr); s.steps++; s.moved = r.moved; s.hist.push(r.loss); setTick((k) => k + 1); };
  const check = () => { const sub = { X: data.train.X.slice(0, 24), y: data.train.y.slice(0, 24) }; setGc(N.gradCheck(N.clone(net), sub.X, sub.y)); };
  if (!net) return html`<p class="cu-play-note">Building the network.</p>`;
  return html`<div class="cu-nn">
    <div class="cu-ctlrow"><${Seg} label="Data" value=${kind} opts=${N.DATASETS} onPick=${setKind}/><${Seg} label="Activation" value=${act} opts=${Object.entries(N.ACTS).map(([k, a]) => [k, a.label])} onPick=${setAct}/></div>
    <div class="cu-ctlrow"><${Slider} label="Hidden layers" value=${layers} min=${1} max=${4} onInput=${setLayers}/><${Slider} label="Neurons per layer" value=${width} min=${2} max=${16} onInput=${setWidth}/><${Slider} label="Learning rate" value=${ri} min=${0} max=${RATES.length - 1} show=${lr} onInput=${setRi}/><${Slider} label="Noise" value=${noise} min=${0} max=${0.5} step=${0.05} show=${noise.toFixed(2)} onInput=${setNoise}/></div>
    <div class="cu-lab-acts"><button type="button" class="cu-btn primary" onClick=${() => setRun(!run)} aria-pressed=${run}>${run ? "Pause" : s.steps ? "Keep training" : "Train"}</button><button type="button" class="cu-btn" onClick=${one} disabled=${run}>One step</button><button type="button" class="cu-btn" onClick=${() => { setRun(false); setSeed(seed + 1); }}>New starting weights</button><button type="button" class="cu-btn" onClick=${check} disabled=${run}>Check the gradients</button></div>
    <div class="cu-nn-grid">
      <figure class="cu-canvas"><canvas ref=${field} width="360" height="360" role="img" aria-label=${`Decision boundary after ${s.steps} steps: ${(tr * 100).toFixed(0)}% of training points and ${(te * 100).toFixed(0)}% of held-out points right`}></canvas><figcaption>Gold means the network says class 1, blue class 0; brighter is surer. Filled dots train it. Rings are held out.</figcaption></figure>
      <div class="cu-ctls">
        <${Read} items=${[["Steps", s.steps], ["Loss (cross-entropy)", isFinite(L) ? L.toFixed(4) : "blew up"], ["Training points right", (tr * 100).toFixed(1) + "%", tr >= 0.95 ? "good" : ""], ["Held-out points right", (te * 100).toFixed(1) + "%", te >= 0.9 ? "good" : ""], ["Weights and biases", N.paramCount(net)], ["Mean weight change per step", s.moved ? s.moved.toExponential(1) : "not moved yet"]]}/>
        <svg class="cu-chart low" viewBox="0 0 320 110" role="img" aria-label=${`Loss over ${s.steps} steps, log scale`}><path d=${lossPath(s.hist, 320, 110)} fill="none" stroke="#f5c518" stroke-width="2"/></svg><p class="cu-play-note">Loss over time, log scale.</p>
        ${s.diverged && html`<p class="cu-err" role="alert">The loss became infinite: the learning rate is too big for this network. Lower it and press New starting weights.</p>`}
        ${gc && html`<p class="cu-play-note" role="status">Gradient check on ${gc.checked} weights and biases: the backward pass and a finite-difference estimate differ by at most <b>${gc.worst.toExponential(1)}</b> relative. Under 1e-4 means the calculus is right.${act === "relu" ? " With ReLU, one weight can sit on the bend at 0, where the slope jumps; that one number then disagrees and the rest still hold." : ""}</p>`}
      </div></div>
    <figure class="cu-canvas wide"><canvas ref=${netCv} width="640" height="200" role="img" aria-label=${`The network, ${net.sizes.join(" to ")} neurons, with every weight drawn as a line`}></canvas><figcaption>Every weight as a line. Gold is positive, blue negative, thicker is larger. Watch them move while it trains.</figcaption></figure>
    <p class="cu-play-note">Plain JavaScript in this page: two inputs, ${layers} hidden layer${layers > 1 ? "s" : ""} of ${width} ${N.ACTS[act].label} neurons, one sigmoid output, cross-entropy loss, gradient descent on all ${data.train.y.length} training points at once.</p>
  </div>`;
}

export const MORE = {
  mlp: { title: "Train a tiny network", task: "On the spiral, get at least 95% of the training points and 90% of the held-out points right. Then try a linear activation and see why it can't.", C: TinyNet, after: "A stack of straight-line maps is still a straight line. The bends come from the activation between layers." },
};
