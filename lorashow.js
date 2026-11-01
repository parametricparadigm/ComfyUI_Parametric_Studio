/* LoRA Showcase: the proof, the card and a bundle, all from Train's run record. Nothing on this page uploads. */
import { useEffect, useState } from "preact/hooks";
import { html, api, post } from "./common.js";
import { copyText } from "./fx.js";

const val = (v, u = "") => (v == null ? "not measured" : v + u);
const mb = (b) => (b == null ? "not measured" : (b / 2 ** 20).toFixed(1) + " MB");

function Curve({ points }) {
  const pts = (points || []).filter((p) => p[1] != null);
  if (pts.length < 2) return html`<p class="small">No loss curve on record.</p>`;
  const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]), x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
  const d = pts.map((p, i) => `${i ? "L" : "M"}${(((p[0] - x0) / (x1 - x0 || 1)) * 400).toFixed(1)} ${(100 - ((p[1] - y0) / (y1 - y0 || 1)) * 100).toFixed(1)}`).join("");
  return html`<figure class="ls-curve"><svg viewBox="0 0 400 100" preserveAspectRatio="none" role="img" aria-label=${`Loss per step, from ${ys[0].toFixed(3)} to ${ys[ys.length - 1].toFixed(3)} over ${x1 - x0} steps`}><path d=${d} fill="none" stroke="currentColor" stroke-width="1.5" vector-effect="non-scaling-stroke"/></svg><figcaption class="small">Loss from the run's record, step ${x0} to ${x1}. <span class="fx-tag measured">measured</span></figcaption></figure>`;
}

function AB({ job, a }) {
  const [pos, setPos] = useState(50);
  if (a.state !== "done") return html`<div class="fx-note warn"><b>No proof yet</b><p>${a.said}</p>${a.error && html`<p class="small">${a.error}</p>`}<a class="btn small" href=${"#train/" + job}>Run an A/B test on the Train page</a></div>`;
  const base = `/api/lorashow/card/${job}/image/`;
  return html`<section class="fx-card" aria-label="A and B"><span class="fx-kick">A/B proof</span>
    <div class="ls-wipe"><img src=${base + "without"} alt="Without the LoRA"/><img class="ls-top" src=${base + "with"} alt="With the LoRA" style=${{ clipPath: `inset(0 ${100 - pos}% 0 0)` }}/><i style=${{ left: pos + "%" }} aria-hidden="true"></i><span class="l">With</span><span class="r">Without</span></div>
    <label class="fx-lab">Wipe between with and without<input type="range" min="0" max="100" value=${pos} onInput=${(e) => setPos(+e.target.value)}/></label>
    <p>${a.said}</p><dl class="ls-facts"><dt>Prompt</dt><dd>${a.prompt}</dd><dt>Seed</dt><dd>${a.seed}</dd><dt>Strength</dt><dd>${a.strength}</dd><dt>Mean pixel difference, 0 to 255</dt><dd>${val(a.pixel_diff)} <span class="fx-tag measured">measured</span></dd><dt>Keys that did not attach</dt><dd>${val(a.unbound_keys)} <span class="fx-tag measured">measured</span></dd></dl>
    ${a.warn.map((w) => html`<div class="fx-note warn" key=${w}><p>${w}</p></div>`)}</section>`;
}

function Show({ job }) {
  const [c, setC] = useState(null), [err, setErr] = useState(""), [desc, setDesc] = useState(""), [use, setUse] = useState(""), [saved, setSaved] = useState(""), [weights, setWeights] = useState(false), [copied, setCopied] = useState("");
  useEffect(() => { api("/api/lorashow/card/" + job).then((x) => { setC(x); setDesc(x.description); setUse(x.use); }).catch((e) => setErr(e.message)); }, [job]);
  const save = async (b) => { setErr(""); try { setC(await post("/api/lorashow/card/" + job, b)); setSaved("Saved."); setTimeout(() => setSaved(""), 2000); } catch (e) { setErr(e.message); } };
  if (err && !c) return html`<div class="fx"><div class="fx-note bad" role="alert"><p>${err}</p></div><a class="btn" href="#lorashow">All LoRAs</a></div>`;
  if (!c) return html`<div class="fx"><p class="small" role="status">Reading the run.</p></div>`;
  const f = c.facts;
  return html`<div class="fx">
    <header class="ls-head"><span class="fx-kick">LoRA</span><h2>${c.name}</h2><div class="fx-row">${c.trigger ? html`<button class="ls-trigger" type="button" title="Copy the trigger word" onClick=${async () => setCopied((await copyText(c.trigger)) ? "Copied." : "The browser would not copy it.")}>${c.trigger}</button>` : html`<span class="small">No trigger word</span>`}<span class="small" role="status">${copied}</span></div></header>
    <${AB} job=${job} a=${c.ab}/>
    <div class="fx-two">
      <section class="fx-card" aria-label="Model card"><span class="fx-kick">Model card</span>
        <label class="fx-lab">What it does, in your words<textarea class="fx-in ls-text" rows="4" maxlength="4000" value=${desc} onInput=${(e) => setDesc(e.target.value)}></textarea></label>
        <label class="fx-lab">How to use it<textarea class="fx-in ls-text" rows="3" maxlength="4000" value=${use} onInput=${(e) => setUse(e.target.value)}></textarea></label>
        <label class="fx-lab">Licence of this LoRA<select class="fx-in" value=${c.licence || ""} onChange=${(e) => save({ licence: e.target.value || null })}><option value="">Not chosen</option>${c.licences.map((l) => html`<option value=${l}>${l}</option>`)}</select></label>
        ${f.base_licence && html`<p class="small">Base model licence: <a href=${f.base_licence.url} rel="noreferrer noopener" target="_blank">${f.base_licence.name}</a>. It still applies. This is not legal advice, and you need the right to share whatever you trained on.</p>`}
        <div class="fx-row"><button class="btn small" type="button" onClick=${() => save({ description: desc, use })}>Save the card</button><span class="small" role="status">${saved}</span></div>${err && html`<p class="fx-err" role="alert">${err}</p>`}</section>
      <section class="fx-card" aria-label="The run"><span class="fx-kick">From the run's record</span>
        <dl class="ls-facts"><dt>Base model</dt><dd>${f.base || f.base_id}</dd><dt>Steps</dt><dd>${val(f.steps)}</dd><dt>Rank</dt><dd>${val(f.rank)}</dd><dt>Size</dt><dd>${val(f.size)}</dd><dt>Batch</dt><dd>${val(f.batch)}</dd><dt>Learning rate</dt><dd>${val(f.learning_rate)}</dd><dt>Last loss</dt><dd>${val(f.last_loss)}</dd><dt>Seconds per step</dt><dd>${val(f.s_per_step)}</dd><dt>Peak VRAM, whole card</dt><dd>${val(f.peak_vram_gib, " GiB")}</dd><dt>GPU</dt><dd>${val(f.gpu)}</dd>${f.rights && html`<dt>You confirmed</dt><dd>${f.rights}</dd>`}<dt>File size</dt><dd>${mb(f.bytes)}</dd><dt>SHA-256</dt><dd><code>${f.sha256}</code></dd></dl><${Curve} points=${c.curve}/></section></div>
    <section class="fx-card ls-bundle" aria-label="Share-ready bundle"><span class="fx-kick">Share</span><h2>A bundle to share yourself</h2><p>The model card, the A/B pictures and graph, the loss curve and the run record, in one zip you download. Nothing is uploaded anywhere. Your training pictures and captions never go in.</p>
      <label class="ls-pick"><input type="checkbox" checked=${weights} onChange=${() => setWeights(!weights)}/> Include the LoRA file (${mb(f.bytes)})</label>
      ${c.ready ? html`<a class="fx-go" href=${`/api/lorashow/card/${job}/bundle?weights=${weights}`} download>Download the bundle</a>` : html`<p class="fx-warn" role="status">Still needed: ${c.missing.join(", ")}.</p>`}</section>
  </div>`;
}

function All() {
  const [rows, setRows] = useState(null), [err, setErr] = useState("");
  useEffect(() => { api("/api/lorashow/loras").then((d) => setRows(d.loras)).catch((e) => setErr(e.message)); }, []);
  if (err) return html`<div class="fx"><div class="fx-note bad" role="alert"><p>${err}</p></div></div>`;
  if (!rows) return html`<div class="fx"><p class="small" role="status">Reading your runs.</p></div>`;
  if (!rows.length) return html`<div class="fx"><div class="fx-card"><h2>Nothing to show yet</h2><p>A LoRA appears here once a Train run finishes and its file is still on this machine.</p><a class="fx-go" href="#train">Train one</a></div></div>`;
  return html`<div class="fx"><ul class="ls-list">${rows.map((r) => html`<li key=${r.job}><a href=${"#lorashow/" + r.job}>${r.ab === "done" && r.with_lora ? html`<img src=${`/api/lorashow/card/${r.job}/image/with`} alt="" loading="lazy"/>` : html`<span class="ls-noart">No A/B yet</span>`}<b>${r.name}</b><small>${r.base_label}, ${r.total_steps} steps</small><small>${r.ab === "done" ? `A/B difference ${val(r.pixel_diff)}, measured` : "No proof yet"}. ${r.licence || "No licence chosen"}.</small></a></li>`)}</ul></div>`;
}

export function LoraShowcase({ route }) {
  const id = String(route || "").split("/")[1];
  return id ? html`<${Show} key=${id} job=${id}/>` : html`<${All}/>`;
}
