/* Graph Doctor: paste or drop a workflow, read what is wrong, tick the fixes you want, and only then get a new graph. The page never changes anything by itself. */
import { useState } from "preact/hooks";
import { html, api, post } from "./common.js";
import { copyText, saveFile } from "./fx.js";

const J = (v) => (v === null || v === undefined ? "nothing" : typeof v === "string" ? v : JSON.stringify(v));
const SEV = { error: ["bad", "Will stop it"], warning: ["warn", "Worth fixing"], info: ["", "For your information"] };

function Change({ f }) {
  if (f.op === "add") return html`<p class="dx-change"><b>Adds</b> <code>${f.after.class_type}</code> as node ${f.node}</p>`;
  if (f.op === "remove") return html`<p class="dx-change"><b>Removes</b> <code>${f.input}</code>, which held <code>${J(f.before)}</code></p>`;
  if (f.op === "remove_node") return html`<p class="dx-change"><b>Removes</b> node ${f.node}</p>`;
  return html`<p class="dx-change"><code class="dx-was">${J(f.before)}</code> <span aria-hidden="true">→</span><span class="dx-sr">becomes</span> <code class="dx-now">${J(f.after)}</code></p>`;
}

function Problem({ p, on, toggle, plain }) {
  const [tone, word] = SEV[p.severity];
  return html`<li class="fx-card dx-p"><div class="fx-row"><span class=${"fx-tag " + tone}>${word}</span>${p.node != null && html`<span class="small">node ${p.node}</span>`}</div>
    <h3>${p.title}</h3><p>${p.why}</p>${plain && html`<p class="small"><span class="fx-tag">reworded by the language model</span> ${plain}</p>`}
    ${p.how && html`<p class="dx-how"><b>Fix:</b> ${p.how}</p>`}
    ${p.fix ? html`<${Change} f=${p.fix}/><label class="dx-pick"><input type="checkbox" checked=${on} onChange=${() => toggle(p.id)}/> Include this change</label>` : p.severity !== "info" && html`<p class="small">This one is yours to do: the doctor will not guess.</p>`}</li>`;
}

export function GraphDoctor() {
  const [text, setText] = useState(""), [res, setRes] = useState(null), [err, setErr] = useState(""), [busy, setBusy] = useState(""), [picked, setPicked] = useState({}), [fixed, setFixed] = useState(null), [drag, setDrag] = useState(false), [png, setPng] = useState(null), [words, setWords] = useState({}), [note, setNote] = useState(""), [copied, setCopied] = useState("");
  const body = () => (png ? { png: png.b64 } : { text });
  const check = async (b = body()) => { setBusy("check"); setErr(""); setFixed(null); setWords({}); setNote(""); setPicked({}); try { setRes(await post("/api/doctor/check", b)); } catch (e) { setRes(null); setErr(e.message); } setBusy(""); };
  const pickAll = (v) => setPicked(Object.fromEntries((res.problems || []).filter((p) => p.fix).map((p) => [p.id, v])));
  const chosen = Object.keys(picked).filter((k) => picked[k]);
  const build = async () => { setBusy("fix"); setErr(""); try { setFixed(await post("/api/doctor/fix", { ...body(), fixes: chosen })); } catch (e) { setErr(e.message); } setBusy(""); };
  const askWords = async () => { setBusy("reword"); setNote(""); try { const r = await post("/api/doctor/reword", { problems: res.problems }); setWords(r.words || {}); setNote(r.available ? "" : r.why); } catch (e) { setNote(e.message); } setBusy(""); };
  const onFile = async (f) => { if (!f) return; setErr(""); setRes(null); setFixed(null); if (/\.png$/i.test(f.name)) { const buf = new Uint8Array(await f.arrayBuffer()); let s = ""; for (let i = 0; i < buf.length; i += 32768) s += String.fromCharCode(...buf.subarray(i, i + 32768)); const b64 = btoa(s); setPng({ name: f.name, b64 }); setText(""); check({ png: b64 }); } else { const t = await f.text(); setPng(null); setText(t); check({ text: t }); } };
  const example = async () => { try { const d = await api("/api/doctor/example"); setPng(null); setText(d.text); check({ text: d.text }); } catch (e) { setErr(e.message); } };
  const out = fixed && JSON.stringify(fixed.graph, null, 1);
  return html`<div class="fx">
    <section class="fx-card" aria-label="Your workflow">
      <label class="fx-lab" for="dx-in">Your workflow, as JSON. Canvas files, API files and ComfyUI PNGs all work.</label>
      <div class=${"dx-drop" + (drag ? " on" : "")} onDragOver=${(e) => { e.preventDefault(); setDrag(true); }} onDragLeave=${() => setDrag(false)} onDrop=${(e) => { e.preventDefault(); setDrag(false); onFile(e.dataTransfer.files[0]); }}>
        ${png ? html`<p class="dx-pngname"><b>${png.name}</b>: the graph inside this picture. <button class="btn small" type="button" onClick=${() => { setPng(null); setRes(null); }}>Use text instead</button></p>` : html`<textarea id="dx-in" class="fx-in" rows="12" spellcheck="false" value=${text} onInput=${(e) => setText(e.target.value)} placeholder="Paste here, or drop a .json or .png file"></textarea>`}</div>
      <div class="fx-row"><button class="fx-go" type="button" disabled=${!!busy || (!text.trim() && !png)} onClick=${() => check()}>${busy === "check" ? "Checking" : "Check it"}</button><label class="btn small dx-file">Choose a file<input type="file" accept=".json,.png,application/json,image/png" onChange=${(e) => onFile(e.target.files[0])}/></label><button class="btn small" type="button" onClick=${example}>Try a broken example</button></div>
    </section>
    ${err && html`<div class="fx-note bad" role="alert"><b>No answer</b><p>${err}</p></div>`}
    ${res && html`<section class="fx" aria-label="What the doctor found" aria-live="polite">
      <div class="dx-sum"><div><b>${res.errors}</b><span>${res.errors === 1 ? "problem that stops it" : "problems that stop it"}</span></div><div><b>${res.problems.length - res.errors}</b><span>smaller notes</span></div><div><b>${res.fixable}</b><span>with a fix ready to review</span></div><div><b>${res.nodes}</b><span>nodes, checked against this ComfyUI</span></div></div>
      ${res.converted && html`<p class="small">This was a canvas file, so it was converted to API format to check it. A fixed graph comes back in API format.</p>`}
      ${!res.problems.length && html`<div class="fx-note"><b>Nothing wrong that the rules can see</b><p>Every node, link and value fits this ComfyUI. That does not mean the result will be good, or that every model file is whole.</p></div>`}
      ${res.problems.length > 0 && html`<div class="fx-row"><button class="btn small" type="button" disabled=${!!busy} onClick=${askWords}>${busy === "reword" ? "Asking" : "Say it more simply"}</button>${note && html`<span class="small" role="status">${note}</span>`}</div>`}
      <ul class="dx-list">${res.problems.map((p) => html`<${Problem} key=${p.id} p=${p} plain=${words[p.id]} on=${!!picked[p.id]} toggle=${(id) => setPicked({ ...picked, [id]: !picked[id] })}/>`)}</ul>
      ${res.fixable > 0 && html`<div class="fx-card dx-apply"><h2>Your changes</h2><p class="small">Nothing has changed yet. Tick what you want. You get a new copy, and your original stays as it was.</p><div class="fx-row"><button class="btn small" type="button" onClick=${() => pickAll(true)}>Tick all ${res.fixable}</button><button class="btn small" type="button" onClick=${() => pickAll(false)}>Clear</button><button class="fx-go" type="button" disabled=${!chosen.length || !!busy} onClick=${build}>${chosen.length ? `Build it with ${chosen.length} ${chosen.length === 1 ? "change" : "changes"}` : "Tick a change first"}</button></div></div>`}
      ${fixed && html`<div class="fx-card" aria-live="polite"><h2>The new graph</h2><p>${fixed.changes.length} ${fixed.changes.length === 1 ? "change" : "changes"} made, exactly the ones you ticked. ${fixed.errors_left ? html`<b class="fx-warn">${fixed.errors_left} ${fixed.errors_left === 1 ? "problem" : "problems"} left that still stop it.</b>` : "The same check now finds nothing that stops it."}</p>
        <ul class="dx-done">${fixed.changes.map((c) => html`<li key=${c.problem}><b>${c.title}</b><${Change} f=${c}/></li>`)}</ul>
        <div class="fx-row"><button class="btn small" type="button" onClick=${async () => setCopied((await copyText(out)) ? "Copied." : "The browser would not copy it. Select the text below.")}>Copy</button><button class="btn small" type="button" onClick=${() => saveFile("fixed_workflow_api.json", out)}>Download</button><button class="btn small" type="button" onClick=${() => { setPng(null); setText(out); check({ text: out }); }}>Check this one</button><span class="small" role="status">${copied}</span></div>
        <pre class="fx-pre" tabindex="0">${out}</pre></div>`}
      ${res.atlas.length > 0 && html`<section class="fx-card" aria-label="From the Sampling Atlas"><h2>From the Sampling Atlas</h2><p class="small">Facts about the sampling parts of this graph, not faults. Each carries the atlas's own label.</p><ul class="dx-facts">${res.atlas.map((a) => html`<li key=${a.entry}><b>${a.name}</b> <span class="fx-tag">${a.label}</span><p>${a.plain}</p>${a.note && html`<p class="small">${a.note}</p>`}</li>`)}</ul></section>`}
    </section>`}
  </div>`;
}
