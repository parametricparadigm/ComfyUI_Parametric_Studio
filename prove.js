/* Prove It: pick a render of ours, re-run its exact graph and seed here, then wipe between the two. Every figure comes from the two files; the page never calls a comparison proof of more than it is. */
import { useEffect, useState } from "preact/hooks";
import { html, api, post } from "./common.js";
import { Wipe } from "./prove_wipe.js";

const POLL_MS = 2500;
const short = (h) => (h ? String(h).slice(0, 12) : "none");
const val = (v) => (v == null ? "not known" : String(v));
const secs = (s) => (s == null ? "not measured" : s >= 90 ? `${Math.round(s / 60)} min` : `${Math.round(s)} s`);

function Hardware({ rows, captured }) {
  return html`<div class="fx-card"><h3>Our machine, your machine</h3><div class="pv-scroll"><table class="fx-table"><thead><tr><th>What</th><th>Ours</th><th>Yours</th><th>Same?</th></tr></thead><tbody>${rows.map((r) => html`<tr key=${r.what}><td>${r.what}</td><td>${val(r.ours)}</td><td>${val(r.yours)}</td><td>${r.same == null ? html`<span class="fx-tag">cannot tell</span>` : r.same ? html`<span class="fx-tag ok">same</span>` : html`<span class="fx-tag warn">different</span>`}</td></tr>`)}</tbody></table></div>${captured && html`<p class="small">Ours as recorded on ${captured} on the machine that made these renders.</p>`}</div>`;
}

function Models({ rows }) {
  if (!rows.length) return html`<div class="fx-card"><h3>Model files</h3><p class="small">No model list on record for this render, because its graphs were not kept.</p></div>`;
  const tag = { same: "ok", different: "bad", missing: "bad", hashing: "", "no hash of ours": "warn" };
  return html`<div class="fx-card"><h3>Model files</h3><div class="pv-scroll"><table class="fx-table"><thead><tr><th>File</th><th>Our hash</th><th>Your hash</th><th></th></tr></thead><tbody>${rows.map((m) => html`<tr key=${m.file}><td><code>${m.file}</code></td><td><code>${short(m.ours)}</code></td><td><code>${m.yours ? short(m.yours) : "none yet"}</code></td><td><span class=${"fx-tag " + tag[m.state]}>${m.state === "hashing" ? "working it out" : m.state}</span></td></tr>`)}</tbody></table></div><p class="small">A different hash means a different file, and a different file can change everything. A big file takes a while to hash; this fills in by itself once a run has started.</p></div>`;
}

function Steps({ steps }) {
  return html`<div class="fx-card"><h3>Graph and seed, step by step</h3><ul class="pv-steps">${steps.map((s) => html`<li key=${s.id}><b>${s.label || s.id}</b>
    <span>${s.seed_ours == null ? "no seed in this step" : s.seed_ours === s.seed_yours ? html`seed <code>${s.seed_ours}</code> <span class="fx-tag ok">same</span>` : html`seed <code>${s.seed_ours}</code> then <code>${val(s.seed_yours)}</code> <span class="fx-tag bad">different</span>`}</span>
    <span>graph ${s.graph === "same" ? html`<span class="fx-tag ok">same</span>` : html`<span class=${"fx-tag " + (s.graph === "different" ? "warn" : "")}>${s.graph}</span>`}</span>
    ${s.changes && s.changes.length > 0 && html`<details><summary>${s.changes.length} ${s.changes.length === 1 ? "input" : "inputs"} changed</summary><ul class="pv-changes">${s.changes.map((c) => html`<li><code>${c.class || "node " + c.node}.${c.input}</code>: <code>${JSON.stringify(c.ours)}</code> then <code>${JSON.stringify(c.yours)}</code>${c.note && html` <small>${c.note}</small>`}</li>`)}</ul></details>`}</li>`)}</ul></div>`;
}

function Report({ pid, r, card }) {
  const f = r.figures || {};
  return html`<section class="fx" aria-label="The result">
    <div class=${"pv-verdict " + r.verdict.tone} role="status"><span class="fx-kick">The result</span><strong>${r.verdict.word}</strong><p>${r.verdict.text}</p></div>
    <dl class="pv-figs"><div><dd>${f.mean_diff == null ? "n/a" : f.mean_diff}</dd><dt>${r.kind === "audio" ? "mean difference, percent of full scale" : "mean pixel difference from our web copy, 0 to 255"} <span class="fx-tag measured">measured</span></dt></div>
      ${f.noise_floor != null && html`<div><dd>${f.noise_floor}</dd><dt>our web copy against our own original <span class="fx-tag measured">measured</span></dt></div>`}
      <div><dd>${secs(r.seconds_yours)}</dd><dt>your time, ours was ${secs(r.seconds_ours)} <span class="fx-tag measured">measured</span></dt></div>
      <div><dd>${r.peak_yours == null ? "n/a" : r.peak_yours + " GiB"}</dd><dt>peak VRAM of your whole card while it ran. Ours was ${r.peak_ours == null ? "not measured" : r.peak_ours + " GiB"}${r.peak_ours_scope === "card" ? " for the whole card" : " for this render alone"} <span class="fx-tag measured">measured</span></dt></div></dl>
    ${r.frames.map((fr) => html`<${Wipe} key=${fr.i} base=${`/api/prove/runs/${pid}/image`} frame=${fr}/>`)}
    ${r.kind === "audio" && html`<div class="fx-two"><div class="fx-card"><h3>Ours</h3><audio src=${card.file} controls preload="none" style="width:100%"></audio></div><div class="fx-card"><h3>Yours</h3><audio src=${r.output_url} controls preload="none" style="width:100%"></audio></div></div>`}
    <${Steps} steps=${r.steps}/>
  </section>`;
}

function Promise_({ text }) { return html`<div class="fx-note warn"><b>What this can and cannot show</b><p>${text}</p></div>`; }

function Prove({ source, id }) {
  const [card, setCard] = useState(null), [err, setErr] = useState(""), [proof, setProof] = useState(null), [busy, setBusy] = useState(false);
  useEffect(() => { setCard(null); setErr(""); setProof(null); api(`/api/prove/${source}/${encodeURIComponent(id)}`).then((c) => { setCard(c); if (c.last_proof) api(`/api/prove/runs/${c.last_proof}`).then(setProof).catch(() => {}); }).catch((e) => setErr(e.message)); }, [source, id]);
  useEffect(() => {
    if (!proof || proof.state !== "running") return;
    const t = setInterval(() => api(`/api/prove/runs/${proof.id}`).then(setProof).catch((e) => setErr(e.message)), POLL_MS); return () => clearInterval(t);
  }, [proof && proof.id, proof && proof.state]);
  const go = async () => { setBusy(true); setErr(""); try { const d = await post(`/api/prove/recipe/${encodeURIComponent(id)}/start`, { confirm: true }); setProof(await api(`/api/prove/runs/${d.id}`)); } catch (e) { setErr(e.message); } setBusy(false); };
  if (err && !card) return html`<div class="fx"><div class="fx-note bad"><b>Could not open this render</b><p>${err}</p></div><a class="btn" href="#prove">All renders</a></div>`;
  if (!card) return html`<div class="fx"><p class="small" role="status">Reading the record of this render.</p></div>`;
  const live = proof && proof.card ? proof.card : card;
  return html`<div class="fx">
    <div class="fx-two"><figure class="pv-ours">${card.kind === "video" ? html`<video src=${card.file} poster=${card.poster} controls playsinline preload="metadata" aria-label=${"Our render of " + card.title}></video>` : card.kind === "audio" ? html`<audio src=${card.file} controls preload="none" style="width:100%" aria-label=${"Our render of " + card.title}></audio>` : html`<img src=${card.file} alt=${"Our render of " + card.title}/>`}<figcaption class="small">Our web copy. The original was larger and uncompressed.</figcaption></figure>
      <div class="fx-card"><span class="fx-kick">Our render</span><h2>${card.title}</h2>
        ${card.provable ? html`<dl class="pv-facts"><dt>Seeds</dt><dd>${Object.values(card.seeds || {}).join(", ") || "none"}</dd><dt>Graphs</dt><dd>${card.graphs_kept ? card.steps.filter((s) => s.has_graph).length + " on record, exact" : "not kept for this render, so we rebuild from the recipe and can't confirm it is exact"}</dd><dt>Our time</dt><dd>${secs(card.seconds)} <span class="fx-tag measured">measured</span></dd><dt>Our peak</dt><dd>${card.peak_vram_gib == null ? "not measured" : card.peak_vram_gib + " GiB"}${card.peak_scope === "card" ? " across the whole card" : ""} <span class="fx-tag measured">measured</span></dd><dt>Rendered</dt><dd>${card.rendered}</dd></dl>
          ${(!proof || proof.state !== "running") && html`<button class="fx-go" type="button" disabled=${busy} onClick=${go}>${busy ? "Starting" : proof ? "Run it again" : "Re-run it on my machine"}</button><p class="small">This uses your GPU and takes about as long as it took us, or longer. Nothing starts until you press the button.</p>`}
          ${proof && proof.state === "running" && html`<div role="status" aria-live="polite"><p><b>Running.</b> ${proof.position ? `Waiting in line, position ${proof.position}.` : (proof.steps_now || []).map((s) => `${s.label}: ${s.status}`).join(". ")}</p><button class="btn small" type="button" onClick=${() => post(`/api/prove/runs/${proof.id}/cancel`, {}).catch(() => {})}>Cancel</button></div>`}
          ${proof && proof.state === "error" && html`<div class="fx-note bad" role="alert"><b>No comparison</b><p>${proof.error}</p></div>`}` : html`<div class="fx-note warn"><b>This one can't be proved</b><p>${card.why}</p></div><a class="fx-go" href="#prove">Pick one that can</a>`}
        ${err && html`<div class="fx-note bad" role="alert"><p>${err}</p></div>`}
      </div></div>
    ${proof && proof.state === "done" && html`<${Report} pid=${proof.id} r=${proof.report} card=${card}/>`}
    <${Promise_} text=${card.promise}/>
    ${card.same_machine && html`<div class="fx-note"><b>What we measured on our own machine</b><p>${card.same_machine}</p></div>`}
    <div class="fx-two"><${Hardware} rows=${live.hardware} captured=${live.hardware_captured}/><${Models} rows=${live.models}/></div>
  </div>`;
}

function Picker() {
  const [q, setQ] = useState(""), [d, setD] = useState(null), [err, setErr] = useState("");
  useEffect(() => { const t = setTimeout(() => api("/api/prove/renders?limit=36&q=" + encodeURIComponent(q)).then(setD).catch((e) => setErr(e.message)), 180); return () => clearTimeout(t); }, [q]);
  return html`<div class="fx"><label class="fx-lab">Find a render<input class="fx-in" type="search" value=${q} onInput=${(e) => setQ(e.target.value)} placeholder="oil, loop, music"/></label>
    ${err && html`<div class="fx-note bad" role="alert"><p>${err}</p></div>`}
    ${d && html`<p class="small" role="status">${d.total} of our renders have their seed on record and can be re-run. ${d.renders.length < d.total ? `Showing ${d.renders.length}.` : ""}</p>
    <ul class="pv-pick">${d.renders.map((r) => html`<li key=${r.id}><a href=${"#prove/recipe/" + r.id}>${r.poster ? html`<img src=${r.poster} alt="" loading="lazy" decoding="async"/>` : html`<span class="pv-noart" aria-hidden="true">${r.kind === "audio" ? "♪" : ""}</span>`}<b>${r.title}</b><small>${r.kind}, ${secs(r.seconds)} here</small></a></li>`)}</ul>`}
  </div>`;
}

export function ProveIt({ route }) {
  const [, source, id] = String(route || "").split("/");
  return source && id ? html`<${Prove} key=${source + id} source=${source} id=${decodeURIComponent(id)}/>` : html`<${Picker}/>`;
}
