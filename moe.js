/* Inside a mixture of experts: real per-token routing from Qwen3-Omni-30B-A3B, recorded once and read here as static JSON.
   Routes: #moe, #moe/<prompt id>. Data: /api/moe, /api/moe/prompt/<id>, /api/moe/load (studio/feature_moe.py, packed by scripts/pack_moe_routing.py). */
import { useEffect, useMemo, useRef, useState } from "preact/hooks";
import { html, api } from "./common.js";
import { pct, parseRoute, showPiece, pick, overlap, spread, combine, shares, balance, heat, heatRGB, specialists, cellAt, fmtB, expertParams } from "./moe_logic.js";

const said = (e) => (e && e.message) || String(e || "");
const rgb = (h) => `rgb(${heatRGB(h).join(",")})`;
const nf = (n) => Number(n).toLocaleString("en");

/* ---------- 1. what top-k routing is */
function Explain({ meta }) {
  const p = expertParams(meta), even = 1 / meta.experts;
  return html`<section class="fx-card moe-explain" aria-labelledby="moe-how">
    <p class="fx-kick">How it works</p><h2 id="moe-how">A router, then ${meta.top_k} of ${meta.experts}</h2>
    <ol class="moe-steps">
      <li><b>Every layer has ${meta.experts} experts.</b> Each one is a small feed-forward network of the same shape. In this model, ${meta.layers} layers each hold ${meta.experts} of them.</li>
      <li><b>A router scores them all.</b> For each word piece (a token), a single matrix turns the token's ${nf(meta.hidden)} numbers into ${meta.experts} scores, and softmax turns the scores into shares that add up to 1.</li>
      <li><b>Only the top ${meta.top_k} run.</b> The ${meta.top_k} highest shares are kept and the rest are dropped.${meta.norm_topk_prob ? ` The ${meta.top_k} kept shares are scaled back up so they add up to 1.` : ""} The layer's output is the ${meta.top_k} experts' outputs, mixed in those proportions.</li>
      <li><b>So most of the model sits still.</b> Each token wakes ${meta.top_k} / ${meta.experts} = ${pct(meta.top_k / meta.experts, 2)} of each layer's experts. That is ${fmtB(p.activeLayers)} of the ${fmtB(p.allLayers)} expert weights for each token, counted from the shapes in the config, while attention and embeddings run for every token.</li>
    </ol>
    <p class="small">If routing were perfectly even, every expert would get 1 in ${meta.experts} of a layer's picks (${pct(even, 2)}). Training adds a small penalty that pushes towards that, so no expert is left idle. The heatmap further down shows how close it gets.</p>
  </section>`;
}

/* ---------- 2. one prompt, token by token */
function Fingerprint({ prompt, t, layer, setLayer, E }) {
  const L = prompt.experts[t].length;
  const cells = [];
  for (let l = 0; l < L; l++) pick(prompt, t, l).forEach(({ e, w }) => cells.push(html`<rect key=${l + ":" + e} x=${e} y=${l} width="1" height="1" fill=${rgb(0.35 + 0.65 * Math.min(1, w * 3))}/>`));
  const click = (ev) => { const r = ev.currentTarget.getBoundingClientRect(); setLayer(Math.max(0, Math.min(L - 1, Math.floor(((ev.clientY - r.top) / r.height) * L)))); };
  return html`<figure class="moe-fp">
    <svg viewBox=${`0 0 ${E} ${L}`} preserveAspectRatio="none" role="img" aria-label=${`Token ${showPiece(prompt.tokens[t])}: the ${prompt.experts[t][0].length} experts it went to in each of ${L} layers. Layer ${layer + 1} is marked.`} onClick=${click}>
      <rect x="0" y="0" width=${E} height=${L} class="moe-fp-bg"/>${cells}<rect x="0" y=${layer} width=${E} height="1" class="moe-fp-row"/>
    </svg>
    <figcaption class="small">Rows are layers 1 to ${L}, top to bottom. Columns are experts 0 to ${E - 1}. A lit cell is an expert this token went to, and brighter means a bigger share. Click a row to read that layer below.</figcaption>
  </figure>`;
}

function LayerDetail({ prompt, t, layer, E }) {
  const ps = pick(prompt, t, layer), on = new Map(ps.map((x) => [x.e, x.w])), sp = spread(prompt.entropy[t][layer], E);
  return html`<div class="moe-layer">
    <div class="moe-dots" role="img" aria-label=${`Layer ${layer + 1}: experts ${ps.map((x) => `${x.e} (${pct(x.w)})`).join(", ")}`}>
      ${Array.from({ length: E }, (_, e) => html`<i key=${e} class=${on.has(e) ? "on" : ""} style=${on.has(e) ? { "--s": 0.45 + 0.55 * Math.min(1, on.get(e) * 3) } : null} title=${on.has(e) ? `expert ${e}: ${pct(on.get(e), 1)}` : `expert ${e}`}></i>`)}
    </div>
    <ul class="moe-picks">${ps.map((x, i) => html`<li key=${x.e}><span class="moe-rank">${i + 1}</span><b>Expert ${x.e}</b><span class="moe-bar" aria-hidden="true"><em style=${{ width: x.w * 100 + "%" }}></em></span><span class="moe-w">${pct(x.w, 1)}</span></li>`)}</ul>
    <p class="small">Router spread at this layer: <b>${pct(sp)}</b> of the most it could be. Near 0% means one expert takes almost everything; near 100% means all ${E} looked about the same before the top ${ps.length} were cut.</p>
  </div>`;
}

function Prompts({ index, route, goTab }) {
  const want = parseRoute(route).prompt, ids = index.prompts.map((p) => p.id), pid = ids.includes(want) ? want : ids[0];
  const [prompt, setPrompt] = useState(null), [err, setErr] = useState(""), [t, setT] = useState(0), [hover, setHover] = useState(null), [layer, setLayer] = useState(Math.floor(index.meta.layers / 2));
  useEffect(() => { setPrompt(null); setErr(""); setT(0); setHover(null); api("/api/moe/prompt/" + encodeURIComponent(pid)).then(setPrompt).catch((e) => setErr(said(e))); }, [pid]);
  const E = index.meta.experts, cur = hover ?? t;
  return html`<section class="fx-card" aria-labelledby="moe-tok">
    <p class="fx-kick">Real routing, token by token</p><h2 id="moe-tok">Hover a word piece</h2>
    <p>Pick a sample. Each was run through the model once, and every token's ${index.meta.top_k} experts in every layer were written down. Hover or tap a piece to see where it went.</p>
    <div class="fx-row moe-chips" role="group" aria-label="Sample text">${index.prompts.map((p) => html`<button key=${p.id} class=${"chip" + (p.id === pid ? " on" : "")} aria-pressed=${p.id === pid} onClick=${() => goTab && goTab("moe/" + p.id)}>${p.label}</button>`)}</div>
    ${err ? html`<div class="fx-note bad" role="alert"><p>${err}</p></div>` : !prompt ? html`<p class="small" role="status">Reading the record.</p>` : html`
      <div class="moe-toks" role="group" aria-label=${"Tokens of: " + prompt.text} onMouseLeave=${() => setHover(null)}>
        ${prompt.tokens.map((s, i) => { const o = i === cur ? null : overlap(prompt, cur, i, layer);
          return html`<button key=${i} class=${"moe-tok" + (i === t ? " on" : "") + (i === cur ? " cur" : "")} aria-pressed=${i === t} onMouseEnter=${() => setHover(i)} onFocus=${() => setHover(i)} onClick=${() => { setT(i); setHover(null); }} style=${o == null ? null : { "--o": o / index.meta.top_k }} title=${o == null ? "" : `shares ${o} of ${index.meta.top_k} experts with the chosen piece at layer ${layer + 1}`}><span>${showPiece(s)}</span><i aria-hidden="true"></i></button>`; })}
      </div>
      <p class="small">Piece <b>${showPiece(prompt.tokens[cur])}</b>, token ${cur + 1} of ${prompt.tokens.length}. The bar under each other piece shows how many of its ${index.meta.top_k} experts at layer ${layer + 1} it shares with this one. ↳ marks the rest of a character that is split over two tokens.</p>
      <div class="fx-two moe-tokview">
        <${Fingerprint} prompt=${prompt} t=${cur} layer=${layer} setLayer=${setLayer} E=${E}/>
        <div class="moe-side">
          <label class="moe-slider"><span>Layer <b>${layer + 1}</b> of ${index.meta.layers}</span>
            <input type="range" min="1" max=${index.meta.layers} value=${layer + 1} onInput=${(e) => setLayer(Number(e.currentTarget.value) - 1)} aria-label="Layer"/></label>
          <${LayerDetail} prompt=${prompt} t=${cur} layer=${layer} E=${E}/>
        </div>
      </div>`}
  </section>`;
}

/* ---------- 3. expert load across many texts */
function Heatmap({ grid, L, E, cell, setCell, label }) {
  const ref = useRef(null), [w, setW] = useState(0);
  useEffect(() => { const el = ref.current; if (!el) return; const ro = new ResizeObserver(() => setW(el.clientWidth)); ro.observe(el); setW(el.clientWidth); return () => ro.disconnect(); }, []);
  const H = Math.round(Math.max(L * 5, Math.min(L * 9, w * 0.42)));
  useEffect(() => {
    const c = ref.current; if (!c || !w) return; const dpr = window.devicePixelRatio || 1; c.width = Math.round(w * dpr); c.height = Math.round(H * dpr);
    const g = c.getContext("2d"); g.setTransform(dpr, 0, 0, dpr, 0, 0); const cw = w / E, ch = H / L;
    for (let l = 0; l < L; l++) for (let e = 0; e < E; e++) { g.fillStyle = rgb(heat(grid[l][e], E)); g.fillRect(e * cw, l * ch, Math.ceil(cw), Math.ceil(ch)); }
    if (cell) { g.strokeStyle = "#fff"; g.lineWidth = 2; g.strokeRect(cell.e * cw - 1, cell.l * ch - 1, cw + 2, ch + 2); g.strokeStyle = "rgba(255,255,255,.35)"; g.lineWidth = 1; g.strokeRect(0.5, cell.l * ch, w - 1, ch); }
  }, [grid, w, H, cell]);
  const at = (ev) => { const r = ev.currentTarget.getBoundingClientRect(); return cellAt(ev.clientX - r.left, ev.clientY - r.top, r.width, r.height, L, E); };
  const key = (ev) => { const c = cell || { l: 0, e: 0 }, mv = { ArrowLeft: [0, -1], ArrowRight: [0, 1], ArrowUp: [-1, 0], ArrowDown: [1, 0] }[ev.key]; if (!mv) return; ev.preventDefault(); setCell({ l: Math.max(0, Math.min(L - 1, c.l + mv[0])), e: Math.max(0, Math.min(E - 1, c.e + mv[1])) }); };
  return html`<canvas ref=${ref} class="moe-heat" style=${{ height: H + "px" }} tabindex="0" role="img" aria-label=${label} onPointerMove=${(ev) => ev.pointerType === "mouse" && setCell(at(ev) || cell)} onClick=${(ev) => setCell(at(ev) || cell)} onKeyDown=${key}></canvas>`;
}

function Load({ index }) {
  const [load, setLoad] = useState(null), [err, setErr] = useState(""), [cats, setCats] = useState([]), [cell, setCell] = useState({ l: 0, e: 0 }), [spLayer, setSpLayer] = useState(Math.floor(index.meta.layers / 2));
  useEffect(() => { api("/api/moe/load").then(setLoad).catch((e) => setErr(said(e))); }, []);
  const { layers: L, experts: E, top_k: K } = index.meta;
  const comb = useMemo(() => (load ? combine(load.categories, cats) : null), [load, cats]);
  const grid = useMemo(() => (comb ? shares(comb, K) : null), [comb]);
  const bal = useMemo(() => (grid ? grid.map(balance) : []), [grid]);
  const spec = useMemo(() => (load ? specialists(load.categories, spLayer, K) : []), [load, spLayer]);
  if (err) return html`<div class="fx-note bad" role="alert"><p>${err}</p></div>`;
  if (!load || !grid) return html`<p class="small" role="status">Reading the expert load.</p>`;
  const toggle = (n) => setCats(cats.includes(n) ? cats.filter((x) => x !== n) : [...cats, n]);
  const s = grid[cell.l][cell.e], tops = load.top_tokens[cell.l][cell.e] || [], nudge = (dl, de) => setCell({ l: Math.max(0, Math.min(L - 1, cell.l + dl)), e: Math.max(0, Math.min(E - 1, cell.e + de)) });
  const lo = Math.min(...bal), hi = Math.max(...bal);
  return html`<section class="fx-card" aria-labelledby="moe-load">
    <p class="fx-kick">Expert load</p><h2 id="moe-load">Who does the work, layer by layer</h2>
    <p>${nf(index.meta.corpus_tokens || comb.tokens)} tokens of invented text in ${load.categories.length} kinds went through the model. Each cell is one expert in one layer, coloured by its share of that layer's picks. The even share is 1 in ${E}. Pick kinds of text to compare them.</p>
    <div class="fx-row moe-chips" role="group" aria-label="Kinds of text">
      <button class=${"chip" + (!cats.length ? " on" : "")} aria-pressed=${!cats.length} onClick=${() => setCats([])}>All</button>
      ${load.categories.map((c) => html`<button key=${c.name} class=${"chip" + (cats.includes(c.name) ? " on" : "")} aria-pressed=${cats.includes(c.name)} onClick=${() => toggle(c.name)}>${c.name}<small>${c.tokens}</small></button>`)}
    </div>
    <div class="moe-heatwrap">
      <div class="moe-axis small" aria-hidden="true"><span>expert 0</span><span>expert ${E - 1}</span></div>
      <${Heatmap} grid=${grid} L=${L} E=${E} cell=${cell} setCell=${setCell} label=${`Expert load heatmap, ${L} layers by ${E} experts, for ${cats.length ? cats.join(", ") : "all text"}. Use the arrow keys to move between cells; the selected cell is described below.`}/>
      <div class="moe-legend small" aria-hidden="true"><span>never picked</span><i></i><span>even</span><i></i><span>4× even or more</span></div>
    </div>
    <div class="moe-cell" aria-live="polite">
      <div class="fx-row moe-nudge" role="group" aria-label="Move the selected cell">
        <button class="btn small" onClick=${() => nudge(-1, 0)} aria-label="Layer up">▲</button><button class="btn small" onClick=${() => nudge(1, 0)} aria-label="Layer down">▼</button>
        <button class="btn small" onClick=${() => nudge(0, -1)} aria-label="Previous expert">◀</button><button class="btn small" onClick=${() => nudge(0, 1)} aria-label="Next expert">▶</button>
      </div>
      <p><b>Layer ${cell.l + 1}, expert ${cell.e}</b>: ${pct(s, 2)} of the picks, <b>${(s * E).toFixed(2)}×</b> the even share.</p>
      <p class="small">${tops.length ? html`Pieces it was most often the first choice for, across all text: ${tops.map(([p, n], i) => html`<span key=${i} class="fx-tag moe-piece">${showPiece(p)} <small>${n}</small></span>`)}` : "It was nobody's first choice in this text."}</p>
    </div>
    <div class="moe-bal">
      <h3>How evenly each layer spreads its work</h3>
      <div class="moe-balbars" role="img" aria-label=${`Balance per layer, from ${pct(lo)} to ${pct(hi)} of perfectly even`}>${bal.map((b, l) => html`<i key=${l} class=${l === cell.l ? "on" : ""} style=${{ height: Math.max(3, ((b - lo) / ((hi - lo) || 1)) * 100) + "%" }} title=${`layer ${l + 1}: ${pct(b, 1)}`}></i>`)}</div>
      <p class="small">Each bar is one layer, 1 to ${L}, from left to right: the entropy of its expert shares as a share of the most possible. They run from ${pct(lo, 1)} to ${pct(hi, 1)}, so every layer uses nearly all its experts. The bar heights are stretched to show the differences.</p>
    </div>
    <div class="moe-spec">
      <h3>Specialists at layer ${spLayer + 1}</h3>
      <label class="moe-slider"><span>Layer <b>${spLayer + 1}</b></span><input type="range" min="1" max=${L} value=${spLayer + 1} onInput=${(e) => setSpLayer(Number(e.currentTarget.value) - 1)} aria-label="Layer for specialists"/></label>
      <table class="fx-table"><thead><tr><th>Expert</th><th>Kind of text</th><th>Its share there</th><th>Against its usual share</th></tr></thead>
        <tbody>${spec.map((r) => html`<tr key=${r.e}><td><button class="moe-link" onClick=${() => setCell({ l: spLayer, e: r.e })}>Expert ${r.e}</button></td><td>${r.cat}</td><td>${pct(r.share, 2)}</td><td><b>${r.ratio.toFixed(1)}×</b></td></tr>`)}</tbody></table>
      <p class="small">An expert is listed when its share of one kind of text is furthest above its share of all the text, and only if it was picked at least 8 times there. This is a correlation in a small sample of ${nf(comb.tokens)} tokens, not a job description: nobody assigns experts topics, and the router learns its own split during training.</p>
    </div>
  </section>`;
}

/* ---------- 4. what this is */
function About({ meta }) {
  const v = meta.versions || {};
  return html`<section class="fx-card" aria-labelledby="moe-about">
    <p class="fx-kick">The record</p><h2 id="moe-about">What you are looking at</h2>
    <table class="fx-table moe-about"><tbody>
      <tr><th>Model</th><td>${meta.model}. ${meta.layers} layers, ${meta.experts} experts each, top ${meta.top_k}.</td></tr>
      <tr><th>Licence</th><td><b>Apache-2.0</b>, the licence on both the <a href="https://huggingface.co/Qwen/Qwen3-Omni-30B-A3B-Captioner" target="_blank" rel="noopener">Qwen model card</a> and the <a href="https://huggingface.co/cyankiwi/Qwen3-Omni-30B-A3B-Captioner-AWQ-4bit" target="_blank" rel="noopener">4-bit quantisation</a> used here. The weights are not part of this page; only the routing record is.</td></tr>
      <tr><th>What went in</th><td>Text only. Each sample was run as one forward pass through the model's language part, with no generation. This model is a captioner: in normal use it hears audio and writes about it. Its audio and vision encoders were loaded but not used, so this shows how the language layers route text.</td></tr>
      <tr><th>The text</th><td>Written for this page: short invented passages, with no real people.</td></tr>
      <tr><th>How it was read</th><td>A hook on each layer's router (a plain bf16 matrix, left unquantised) took its scores, then applied the same softmax, top-${meta.top_k} and rescale the model does next. Shares are rounded to 0.1%.</td></tr>
      <tr><th>Recorded</th><td>${meta.recorded}, once, on one shared GPU${meta.peak_card_gib ? html`: <span class="fx-tag measured">measured</span> ${meta.peak_card_gib} GiB of card memory at peak` : ""}. torch ${v.torch || "?"}, transformers ${v.transformers || "?"}, compressed-tensors ${v.compressed_tensors || "?"}. 4-bit weights shift the numbers a little from the full-precision model, so routing may differ for some tokens.</td></tr>
    </tbody></table>
  </section>`;
}

export function Moe({ route, goTab }) {
  const [index, setIndex] = useState(null), [err, setErr] = useState("");
  useEffect(() => { api("/api/moe").then(setIndex).catch((e) => setErr(said(e))); }, []);
  if (err) return html`<div class="fx moe"><div class="fx-note bad" role="alert"><p>${err}</p></div></div>`;
  if (!index) return html`<div class="fx moe"><p class="small" role="status">Reading the routing record.</p></div>`;
  const m = index.meta;
  return html`<div class="fx moe">
    <dl class="moe-stats">
      <div><dt>${m.experts}</dt><dd>experts in each layer</dd></div><div><dt>${m.top_k}</dt><dd>run for each token</dd></div>
      <div><dt>${m.layers}</dt><dd>layers, each with its own router</dd></div><div><dt>${pct(m.top_k / m.experts, 1)}</dt><dd>of a layer's experts awake at once</dd></div>
    </dl>
    <${Explain} meta=${m}/>
    <${Prompts} index=${index} route=${route} goTab=${goTab}/>
    <${Load} index=${index}/>
    <${About} meta=${m}/>
  </div>`;
}
