/* Hardware Fit: your card and memory against every goal, family template and recipe. Every figure says measured or estimate. */
import { useEffect, useMemo, useState } from "preact/hooks";
import { html, api } from "./common.js";

const KEY = "hardware_fit_v1"; const PAGE_SIZE = 40;
const SECTIONS = [["goal", "Goals"], ["family", "Family templates"], ["recipe", "Recipes"]];
const VERDICTS = [["", "Everything"], ["runs", "Runs"], ["offload", "May run, slower"], ["no", "Won't run"], ["unknown", "Not known"]];
const tone = { runs: "ok", offload: "warn", no: "bad", unknown: "" };
const load = () => { try { return JSON.parse(localStorage.getItem(KEY)) || null; } catch { return null; } };
const save = (v) => { try { localStorage.setItem(KEY, JSON.stringify(v)); } catch {} };

function Row({ r }) {
  return html`<li class="ft-row"><div class="ft-main"><span class=${"fx-tag " + tone[r.verdict]}>${r.word}</span><a href=${"#" + r.open}><b>${r.label}</b></a><small>${r.sub}</small></div>
    <div class="ft-num">${r.need != null ? html`<b>${r.need} GiB</b> <span class=${"fx-tag " + r.basis}>${r.basis}</span>` : html`<span class="small">no figure</span>`}</div>
    <p class="small ft-why">${r.why}${r.note ? " " + r.note : ""}</p>
    ${r.try && html`<p class="ft-try"><b>Try instead, same kind and it fits:</b> <a href=${"#" + r.try.open}>${r.try.label}</a>, ${r.try.need} GiB <span class="fx-tag measured">measured</span></p>`}</li>`;
}

export function HardwareFit({ route }) {
  const saved = useMemo(load, []);
  const [vram, setVram] = useState(saved ? String(saved.vram ?? "") : ""), [ram, setRam] = useState(saved ? String(saved.ram ?? "") : ""), [found, setFound] = useState(null), [d, setD] = useState(null), [err, setErr] = useState(""), [sec, setSec] = useState("goal"), [want, setWant] = useState(""), [q, setQ] = useState(""), [n, setN] = useState(PAGE_SIZE), [basis, setBasis] = useState("");
  useEffect(() => { api("/api/fit/detect").then((x) => { setFound(x); if (!saved) { if (x.vram_gib != null) setVram(String(x.vram_gib)); if (x.ram_gib != null) setRam(String(x.ram_gib)); } }).catch(() => setFound({})); }, []);
  useEffect(() => { const t = setTimeout(() => { save({ vram, ram }); api(`/api/fit/table?vram=${encodeURIComponent(vram)}&ram=${encodeURIComponent(ram)}`).then((x) => { setD(x); setErr(""); }).catch((e) => setErr(e.message)); }, 200); return () => clearTimeout(t); }, [vram, ram]);
  useEffect(() => setN(PAGE_SIZE), [sec, want, q, basis]);
  const shown = useMemo(() => { if (!d) return []; const w = q.trim().toLowerCase(); return d.rows.filter((r) => r.section === sec && (!want || r.verdict === want) && (!basis || r.basis === basis) && (!w || (r.label + " " + r.sub).toLowerCase().includes(w))); }, [d, sec, want, q, basis]);
  const useDetected = () => { if (found) { setVram(found.vram_gib != null ? String(found.vram_gib) : ""); setRam(found.ram_gib != null ? String(found.ram_gib) : ""); } };
  const t = d && d.tally[sec];
  return html`<div class="fx">
    <section class="fx-card" aria-label="Your machine"><span class="fx-kick">Your machine</span>
      <p>${found && found.vram_gib != null ? html`Detected <b>${found.gpu || "a GPU"}</b> with <b>${found.vram_gib} GiB</b>${found.ram_gib != null ? html` and <b>${found.ram_gib} GiB</b> of memory` : ""}, from ${found.from}.` : found ? "Nothing answered about a GPU here, so tell us yours." : "Looking for your GPU."}</p>
      <div class="ft-form"><label class="fx-lab">Video memory, GiB<input class="fx-in" type="number" inputmode="numeric" min="0" max="4096" value=${vram} onInput=${(e) => setVram(e.target.value)}/></label><label class="fx-lab">System memory, GiB<input class="fx-in" type="number" inputmode="numeric" min="0" max="4096" value=${ram} onInput=${(e) => setRam(e.target.value)}/></label></div>
      <div class="fx-row" role="group" aria-label="Common card sizes">${(d ? d.presets : []).map((p) => html`<button key=${p} class=${"btn small" + (String(p) === vram ? " on" : "")} aria-pressed=${String(p) === vram} type="button" onClick=${() => setVram(String(p))}>${p === 0 ? "No GPU" : p + " GB"}</button>`)}${found && found.vram_gib != null && html`<button class="btn small" type="button" onClick=${useDetected}>Use what was detected</button>`}</div>
    </section>
    ${err && html`<div class="fx-note bad" role="alert"><p>${err}</p></div>`}
    ${!d && !err && html`<p class="small" role="status">Reading every goal, family and recipe.</p>`}
    ${d && html`<div class="ft-sum">${SECTIONS.map(([k, l]) => html`<button key=${k} type="button" class=${"ft-tile" + (sec === k ? " on" : "")} aria-pressed=${sec === k} onClick=${() => setSec(k)}><b>${d.tally[k].runs}</b><span>of ${d.tally[k].all} ${l.toLowerCase()} run in full</span><small>${d.tally[k].offload} may run slower. ${d.tally[k].no} won't. ${d.tally[k].measured} measured, the rest estimated or unknown.</small></button>`)}</div>
    <div class="fx-note"><b>How to read these</b><p>${d.caveat} An estimate is the size of its files times ${d.ratio}, the median of our own measured runs.</p></div>
    <div class="ft-filters"><label class="fx-lab">Find<input class="fx-in" type="search" value=${q} onInput=${(e) => setQ(e.target.value)}/></label><label class="fx-lab">Show<select class="fx-in" value=${want} onChange=${(e) => setWant(e.target.value)}>${VERDICTS.map(([k, l]) => html`<option value=${k}>${l}</option>`)}</select></label><label class="fx-lab">Figures<select class="fx-in" value=${basis} onChange=${(e) => setBasis(e.target.value)}><option value="">All</option><option value="measured">Measured only</option><option value="estimate">Estimates only</option></select></label></div>
    <p class="small" role="status">${shown.length} ${shown.length === 1 ? "row" : "rows"}${t ? ` in ${SECTIONS.find(([k]) => k === sec)[1].toLowerCase()}` : ""}.</p>
    <ul class="ft-list">${shown.slice(0, n).map((r) => html`<${Row} key=${r.key} r=${r}/>`)}</ul>
    ${shown.length > n && html`<button class="btn" type="button" onClick=${() => setN(n + PAGE_SIZE)}>Show ${Math.min(PAGE_SIZE, shown.length - n)} more</button>`}`}
  </div>`;
}
