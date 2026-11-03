/* ComfyUniversity: the shared pieces of a lesson. Quiz, lab runner, graph viewer, picture wipe, and the block renderer. */
import { useEffect, useMemo, useState } from "preact/hooks";
import { html, post } from "./common.js";
import { layoutGraph, isLink, WIRE } from "./university_logic.js";
import { PLAYS } from "./university_plays.js";

/* ---------- quiz ---------- */
const isRight = (q, o, i) => { const a = String(q.answer || "").trim(); const la = a.toLowerCase(), lo = String(o).toLowerCase(); return a === o || la.startsWith(String.fromCharCode(97 + i) + ")") || la.startsWith(String.fromCharCode(97 + i) + ".") || a === String.fromCharCode(65 + i) || (a.length > 3 && lo.includes(la)) || (o.length > 3 && la.includes(lo)); };
export function Quiz({ items, onPass, passed }) {
  const [pick, setPick] = useState({}); const [open, setOpen] = useState({}); const list = items || [];
  const state = (q, i) => { if (!q.options) return open[i] ? "ok" : ""; if (pick[i] == null) return ""; return isRight(q, q.options[pick[i]], pick[i]) ? "ok" : "no"; };
  const right = list.filter((q, i) => state(q, i) === "ok").length; const answered = list.filter((q, i) => q.options ? pick[i] != null : open[i]).length;
  useEffect(() => { if (list.length && right === list.length && onPass) onPass(); }, [right, list.length]);
  return html`<div class="cu-quiz"><p class="cu-quiz-score" role="status"><b>${right}</b> of ${list.length} right${answered > right ? ". Wrong answers can be tried again." : ""}${passed && right < list.length ? " You passed this before." : ""}</p>
    ${list.map((q, qi) => { const s = state(q, qi); return html`<fieldset class=${"cu-q " + s} key=${qi}><legend>${qi + 1}. ${q.q}</legend>
      ${q.options ? html`<div class="cu-opts">${q.options.map((o, oi) => { const on = pick[qi] === oi; const r = on && isRight(q, o, oi); return html`<button type="button" class=${"cu-opt" + (on ? (r ? " ok" : " no") : "")} aria-pressed=${on} onClick=${() => setPick({ ...pick, [qi]: oi })}>${o}${on ? html`<span class="cu-vh">${r ? " Right." : " Not this one."}</span>` : null}</button>`; })}</div>` : html`<button type="button" class="cu-ghost" onClick=${() => setOpen({ ...open, [qi]: true })}>Show the answer</button>`}
      ${(s === "ok" || open[qi]) && html`<p class="cu-why" role="status"><b>${q.options ? "Yes." : ""}</b> ${q.options ? "" : q.answer + ". "}${q.why}</p>`}${s === "no" && html`<p class="cu-why no" role="status">Not that one. Reread the lab numbers and try again.</p>`}</fieldset>`; })}</div>`;
}

/* ---------- running the lab ---------- */
export function LabRunner({ c }) {
  const [run, setRun] = useState(null); const [busy, setBusy] = useState(false); const [showCode, setShowCode] = useState(false);
  const start = async () => { setBusy(true); setRun(null); try { setRun(await post(`/api/university/${c.code}/run-lab`, {})); } catch (e) { setRun({ error: e.message }); } setBusy(false); };
  return html`<div class="cu-lab"><p>This lab is plain Python and torch with fixed seeds. It runs on the CPU in under a minute, so anyone can check the numbers in this lesson. Press Run, or save the code as <code>lab.py</code> and run <code>python lab.py</code>.</p>
    <div class="cu-lab-acts"><button type="button" class="cu-btn primary" disabled=${busy} onClick=${start}>${busy ? "Running on the CPU" : "Run it here"}</button><button type="button" class="cu-ghost" aria-expanded=${showCode} onClick=${() => setShowCode(!showCode)}>${showCode ? "Hide the code" : "Read the code"}</button></div>
    ${run && run.error && html`<p class="cu-err" role="status">Could not run it here: ${run.error}. The stored output below is from our last run.</p>`}
    ${run && !run.error && html`<p class=${"cu-lab-verdict " + (run.same ? "ok" : "no")} role="status">${run.ok ? (run.same ? `Finished in ${run.seconds} s. Every line matches the stored output.` : `Finished in ${run.seconds} s. The output differs from ours, which can happen on a different torch build. The asserts inside the lab still passed.`) : `The lab failed: ${run.error_tail || "see the log"}`}</p>`}
    ${showCode && html`<pre class="cu-code" tabindex="0"><code>${c.lab}</code></pre>`}
    ${run && run.ok ? html`<h3>What it printed, just now</h3><pre class="cu-code out" tabindex="0"><code>${run.output}</code></pre>` : html`<details class="cu-printed"><summary>Everything it printed on our last run</summary><pre class="cu-code out" tabindex="0"><code>${c.lab_output}</code></pre></details>`}</div>`;
}

/* ---------- graph viewer ---------- */
export const GraphTag = ({ g }) => { const v = g.verified || {}; const packs = (g.meta.packs || []).length; return v.ran ? html`<span class="cu-pill ink">Ran here on a CPU</span>` : v.validate === "ok" ? html`<span class="cu-pill ink">Passes ComfyUI's validation</span>` : packs ? html`<span class="cu-pill warn">Needs a pack</span>` : html`<span class="cu-pill warn">Not validated</span>`; };
const shortVal = (v) => { const s = typeof v === "string" ? v : JSON.stringify(v); return s.length > 34 ? s.slice(0, 32) + "…" : s; };
export function GraphView({ g }) {
  const prompt = g.graph; const defs = g.defs || {}; const L = useMemo(() => layoutGraph(prompt, defs), [g.id]); const [sel, setSel] = useState(null); const [copied, setCopied] = useState(false); const notes = g.meta.notes || {};
  const json = useMemo(() => JSON.stringify(prompt, null, 1), [g.id]); const href = useMemo(() => "data:application/json;charset=utf-8," + encodeURIComponent(json), [json]);
  const n = sel && prompt[sel]; const d = n && defs[n.class_type];
  const copy = async () => { try { await navigator.clipboard.writeText(json); setCopied(true); setTimeout(() => setCopied(false), 1600); } catch { setCopied(false); } };
  const P = 12; const path = (e) => { const a = L.pos[e.from], b = L.pos[e.to]; const x1 = a.x + a.w + P, y1 = a.y + a.h / 2 + P, x2 = b.x + P, y2 = b.y + b.h / 2 + P, m = (x2 - x1) / 2; return `M${x1} ${y1}C${x1 + m} ${y1} ${x2 - m} ${y2} ${x2} ${y2}`; };
  return html`<figure class="cu-graph cu-film" aria-label=${"Graph: " + g.meta.title}>
    <header class="cu-graph-top"><div><h3>${g.meta.title}</h3>${g.meta.about && html`<p>${g.meta.about}</p>`}</div><div class="cu-graph-tags"><${GraphTag} g=${g}/><span class="cu-pill plain">${Object.keys(prompt).length} nodes</span></div></header>
    <div class="cu-graph-scroll" tabindex="0" role="group" aria-label="Graph canvas, scrolls sideways">
      <div class="cu-graph-canvas" style=${{ width: L.width + 2 * P + "px", height: L.height + 2 * P + "px" }}>
        <svg width=${L.width + 2 * P} height=${L.height + 2 * P} aria-hidden="true">${L.edges.map((e, i) => html`<path key=${i} d=${path(e)} stroke=${WIRE[e.type] || "#8a8f88"} fill="none" stroke-width="2" opacity=${sel && e.from !== sel && e.to !== sel ? .22 : .9}/>`)}</svg>
        ${L.order.map((id) => { const nd = prompt[id], p = L.pos[id], df = defs[nd.class_type] || {}; const vals = Object.entries(nd.inputs || {}).filter(([, v]) => !isLink(v)).slice(0, 3); const inp = Object.entries(nd.inputs || {}).filter(([, v]) => isLink(v)); return html`<button type="button" key=${id} class=${"cu-node" + (sel === id ? " on" : "") + (df.is_output ? " out" : "")} aria-pressed=${sel === id} style=${{ left: p.x + P + "px", top: p.y + P + "px", width: p.w + "px", height: p.h + "px" }} onClick=${() => setSel(sel === id ? null : id)}>
          <b>${nd.class_type}</b>${inp.map(([k]) => html`<i>${k}</i>`)}${vals.map(([k, v]) => html`<em>${k} <u>${shortVal(v)}</u></em>`)}</button>`; })}
      </div></div>
    <div class="cu-graph-detail" role="status">${n ? html`<div class="cu-node-d"><h4>${n.class_type}</h4>${notes[sel] && html`<p class="cu-node-note">${notes[sel]}</p>`}<dl>${Object.entries(n.inputs || {}).map(([k, v]) => html`<dt>${k}</dt><dd>${isLink(v) ? html`wire from ${prompt[String(v[0])] ? prompt[String(v[0])].class_type : v[0]}${d ? "" : ""}` : shortVal(v)}</dd>`)}</dl>${d && d.output && d.output.length > 0 && html`<p class="cu-node-out">Outputs: ${d.output.join(", ")}</p>`}</div>` : html`<p class="cu-graph-hint">Tap a node to read what it does.</p>`}</div>
    ${(g.meta.needs || []).length > 0 && html`<div class="cu-needs"><b>You will need</b><ul>${g.meta.needs.map((x) => html`<li>${x}</li>`)}</ul></div>`}
    ${(g.meta.packs || []).length > 0 && html`<div class="cu-needs warn"><b>This graph needs a node pack</b><ul>${g.meta.packs.map((x) => html`<li>${x}</li>`)}</ul></div>`}
    <footer class="cu-graph-acts"><a class="cu-btn primary" href=${href} download=${g.id + ".json"}>Download graph</a><button type="button" class="cu-ghost" onClick=${copy}>${copied ? "Copied" : "Copy JSON"}</button><p>API format. Drag the file onto the ComfyUI canvas to open it, or send it to <code>/prompt</code>.</p></footer>
  </figure>`;
}

/* ---------- pictures ---------- */
export function Wipe({ a, b, la, lb, caption }) {
  const [pos, setPos] = useState(50);
  return html`<figure class="cu-wipe"><div class="cu-wipe-stage" style=${{ "--pos": pos + "%" }}><img src=${b} alt=${lb || "second picture"} loading="lazy"/><img class="a" src=${a} alt=${la || "first picture"} loading="lazy"/><i aria-hidden="true"></i>${la && html`<span class="l">${la}</span>`}${lb && html`<span class="r">${lb}</span>`}<input type="range" min="0" max="100" value=${pos} aria-label=${`Wipe between ${la} and ${lb}`} onInput=${(e) => setPos(+e.target.value)}/></div>${caption && html`<figcaption>${caption}</figcaption>`}</figure>`;
}

/* ---------- lesson blocks ---------- */
function PlayBlock({ name, args, passPlay, entry }) {
  const P = PLAYS[name]; if (!P) return html`<p class="cu-err">Missing lab: ${name}</p>`;
  const done = !!((entry.plays || {})[name]); const [won, setWon] = useState(false); const pass = () => { if (!won) setWon(true); passPlay(name); };
  return html`<section class=${"cu-play cu-film" + (done || won ? " passed" : "")} aria-label=${"Browser lab: " + P.title}><header class="cu-play-head"><p class="cu-kick">Try it, in this browser</p><h3>${P.title}</h3>${P.task && html`<p class="cu-task"><b>Your task.</b> ${P.task}</p>`}</header><${P.C} args=${args || {}} onPass=${pass}/><footer class="cu-play-foot" role="status">${done || won ? html`<span class="cu-pass">✓ Done</span>${P.after ? html` <span>${P.after}</span>` : ""}` : html`<span class="cu-wait">Not done yet</span>`}</footer></section>`;
}
export function Blocks({ blocks, c, passPlay, entry }) {
  return (blocks || []).map((b, i) => {
    switch (b.t) {
      case "p": return html`<p key=${i} dangerouslySetInnerHTML=${{ __html: b.html }}></p>`;
      case "h": return b.level === 3 ? html`<h3 key=${i} dangerouslySetInnerHTML=${{ __html: b.html }}></h3>` : html`<h4 key=${i} dangerouslySetInnerHTML=${{ __html: b.html }}></h4>`;
      case "ul": return html`<ul key=${i}>${b.items.map((x, j) => html`<li key=${j} dangerouslySetInnerHTML=${{ __html: x }}></li>`)}</ul>`;
      case "ol": return html`<ol key=${i}>${b.items.map((x, j) => html`<li key=${j} dangerouslySetInnerHTML=${{ __html: x }}></li>`)}</ol>`;
      case "quote": return html`<blockquote key=${i} dangerouslySetInnerHTML=${{ __html: b.html }}></blockquote>`;
      case "hr": return html`<hr key=${i}/>`;
      case "code": return html`<pre key=${i} class=${"cu-code" + (b.lang === "text" ? " out" : "")} tabindex="0"><code>${b.code}</code></pre>`;
      case "table": return html`<div key=${i} class="cu-table" tabindex="0"><table><thead><tr>${b.head.map((h, j) => html`<th key=${j} dangerouslySetInnerHTML=${{ __html: h }}></th>`)}</tr></thead><tbody>${b.rows.map((r, k) => html`<tr key=${k}>${r.map((x, j) => html`<td key=${j} dangerouslySetInnerHTML=${{ __html: x }}></td>`)}</tr>`)}</tbody></table></div>`;
      case "img": return html`<figure key=${i} class="cu-fig"><img src=${b.src} alt=${b.caption} loading="lazy"/>${b.caption && html`<figcaption>${b.caption}</figcaption>`}</figure>`;
      case "video": return html`<figure key=${i} class="cu-fig"><video src=${b.src} poster=${b.poster || undefined} controls muted playsinline preload=${b.poster ? "none" : "metadata"} aria-label=${b.caption}></video>${b.caption && html`<figcaption>${b.caption}</figcaption>`}</figure>`;
      case "audio": return html`<figure key=${i} class="cu-fig"><audio src=${b.src} controls preload="none" aria-label=${b.caption}></audio>${b.caption && html`<figcaption>${b.caption}</figcaption>`}</figure>`;
      case "wipe": return html`<${Wipe} key=${i} ...${b}/>`;
      case "play": return html`<div key=${i} class="cu-wide"><${PlayBlock} name=${b.name} args=${b.args} passPlay=${passPlay} entry=${entry}/></div>`;
      case "graph": { const g = (c.graphs || []).find((x) => x.id === b.id); return g ? html`<div key=${i} class="cu-wide"><${GraphView} g=${g}/></div>` : html`<p key=${i} class="cu-err">Missing graph: ${b.id}</p>`; }
      default: return null;
    }
  });
}
