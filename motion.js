/* Motion: grouped by what a person wants to move. Every row shows only what ran on this machine, with its numbers, licence and faults. Routes that show a person ask for the same confirmation the server insists on. */
import { useEffect, useRef, useState } from "preact/hooks";
import { html, api, post } from "./common.js";
import { Media, Strip, Stats, Head } from "./look.js";

const COMMERCIAL = { true: ["ok", "Commercial use allowed"], false: ["bad", "Research only"], conditional: ["warn", "Commercial use has conditions"] };
const HOW = { tool: "A tool in its own process, not a ComfyUI graph", runner: "A small program in its own process, not a ComfyUI graph", family: "A ComfyUI graph on its family's own server" };
const ACCEPT = { image: "image/png,image/jpeg,image/webp", video: "video/mp4,video/quicktime,video/webm", audio: "audio/*" };
const WORD = { image: "A picture of the person", video: "A clip", audio: "A speech track" };
const NUMBER = { foot_slide_mean_cm_s: ["Foot slide, mean", "cm/s"], foot_slide_p95_cm_s: ["Foot slide, worst 5%", "cm/s"], jitter_rms_m_s3: ["Jitter", "m/s³"], best_lag_ms: ["Mouth to voice lag", "ms"], corr_at_best: ["Mouth to voice match", "of 1"] };
export const seconds = (s) => (s == null ? "not measured" : s >= 90 ? `${Math.round(s / 6) / 10} min` : `${Math.round(s)} s`);
export const gib = (g) => (g == null ? "not measured" : `${g} GB`);
const viewUrl = (file) => "/api/view?filename=" + encodeURIComponent(file.split("/").pop()) + "&subfolder=" + encodeURIComponent(file.split("/").slice(0, -1).join("/")) + "&type=output";

function Sample({ s, label }) {
  return html`<figure class="mo-shot film" style=${{ "--ar": s.ar }}>${s.sound ? html`<video src=${s.src} poster=${s.poster} controls playsinline preload="metadata" aria-label=${s.alt || label}></video>` : html`<${Media} src=${s.src} poster=${s.poster} alt=${s.alt || label} kind=${s.kind}/>`}
    <figcaption><b>${s.title || label}</b>${s.prompt && html`<small>${s.prompt}</small>`}</figcaption></figure>`;
}

function Facts({ r, s }) {
  const c = COMMERCIAL[r.commercial] || COMMERCIAL.false;
  return html`<dl class="mo-facts">
    <div><dt>Model</dt><dd>${r.model}</dd></div>
    ${s && html`<div><dt>Seed</dt><dd>${s.seed ?? "none"}</dd></div>
    <div><dt>Time</dt><dd>${seconds(s.seconds)}</dd></div>
    <div><dt>Peak on the card</dt><dd>${gib(s.peak_vram_gib)}</dd></div>`}
    ${s && Object.entries(s.numbers || {}).map(([k, v]) => NUMBER[k] && html`<div key=${k}><dt>${NUMBER[k][0]}</dt><dd>${v} ${NUMBER[k][1]}</dd></div>`)}
    <div><dt>Runs as</dt><dd>${HOW[r.via]}${r.via === "family" && html`: <a href=${"/api/family-graphs/" + r.family_slug + "/" + r.template}>the graph</a>`}</dd></div>
    <div class="wide"><dt>Licence</dt><dd><span class=${"fx-tag " + c[0]}>${c[1]}</span> ${r.licence}</dd></div>
  </dl>`;
}

function Upload({ kind, value, onDone }) {
  const [err, setErr] = useState("");
  const pick = async (e) => {
    const f = e.target.files[0]; if (!f) return; setErr("");
    const fd = new FormData(); fd.append("file", f);
    try { const r = await api("/api/upload", { method: "POST", body: fd }); onDone(r.name); } catch (x) { setErr(x.message); }
  };
  return html`<label class="fx-lab">${WORD[kind]}<input class="fx-in" type="file" accept=${ACCEPT[kind]} onChange=${pick}/>${value && html`<small>Added: ${value}</small>`}${err && html`<small class="fx-err" role="alert">${err}</small>`}</label>`;
}

function RunForm({ r, ask, characters }) {
  const [v, setV] = useState({ seed: "", seconds: 5, text: "", character: "" }), [ok, setOk] = useState(false), [job, setJob] = useState(null), [err, setErr] = useState(""), [note, setNote] = useState("");
  useEffect(() => { if (!job || job.status !== "running") return undefined; const t = setInterval(() => api("/api/motion/jobs/" + job.job).then(setJob).catch(() => {}), 2000); return () => clearInterval(t); }, [job]);
  const filled = r.needs.every((k) => (k === "text" && r.via !== "tool") || v[k]) && (!r.person || ok);
  const go = async (e) => {
    e.preventDefault(); setErr(""); setNote("");
    try {
      if (r.via === "tool" && v.character) {
        const name = (v.text.toLowerCase().match(/[a-z]+/g) || ["clip"]).slice(1, 3).join("_").slice(0, 20) || "clip";
        const a = await api("/api/worldkit/assets/" + v.character);
        await post(`/api/worldkit/assets/${v.character}/clips`, { clips: [...(a.recipe.clips || []).slice(-3), { name, text: v.text }] });
        setNote(`Adding "${name}" to ${a.name}. Follow it on the World Kit page.`); return;
      }
      setJob(await post("/api/motion/run", { route: r.id, ...v, seed: v.seed === "" ? undefined : +v.seed, permission: r.person ? ok : undefined }));
    } catch (x) { setErr(x.message); }
  };
  return html`<form class="mo-form" onSubmit=${go}>
    ${r.needs.includes("text") && html`<label class="fx-lab">${r.via === "tool" ? "What happens" : "Describe the scene (optional)"}<textarea class="fx-in" rows="2" value=${v.text} onInput=${(e) => setV({ ...v, text: e.target.value })} placeholder=${r.via === "tool" ? "a person walks forward, stops, and waves" : ""}></textarea></label>`}
    ${r.needs.filter((k) => k !== "text").map((k) => html`<${Upload} key=${k} kind=${k} value=${v[k]} onDone=${(n) => setV((x) => ({ ...x, [k]: n }))}/>`)}
    ${r.via === "tool" && html`<label class="fx-lab">Put it on a character (optional)<select class="fx-in" value=${v.character} onChange=${(e) => setV({ ...v, character: e.target.value })}><option value="">No, just the motion file</option>${characters.map((c) => html`<option value=${c.id}>${c.name}</option>`)}</select></label>`}
    <label class="fx-lab">Seed (optional)<input class="fx-in" type="text" inputmode="numeric" value=${v.seed} onInput=${(e) => setV({ ...v, seed: e.target.value })}/></label>
    ${r.person && html`<label class="mo-ask"><input type="checkbox" checked=${ok} onChange=${(e) => setOk(e.target.checked)}/><span>${ask}</span></label>`}
    <div class="fx-row"><button class="fx-go" type="submit" disabled=${!filled || (job && job.status === "running")}>${job && job.status === "running" ? "Running" : `Run ${r.label}`}</button></div>
    ${err && html`<p class="fx-err" role="alert">${err}</p>`}${note && html`<p role="status">${note}</p>`}
    ${job && job.status === "error" && html`<p class="fx-err" role="alert">${job.error}</p>`}
    ${job && job.status === "done" && (/\.mp4$/.test(job.file) ? html`<video class="mo-result" src=${viewUrl(job.file)} controls playsinline></video>` : html`<p role="status"><a href=${viewUrl(job.file)} download>Download the motion file</a> (${seconds(job.seconds)}).</p>`)}
  </form>`;
}

function Row({ r, ask, characters }) {
  const [open, setOpen] = useState(false), s = r.samples[0];
  return html`<article class=${"mo-row" + (s ? "" : " none")} id=${"route-" + r.id}>
    <div class="mo-pics">${s ? r.samples.map((x, i) => html`<${Sample} key=${i} s=${x} label=${r.label}/>`) : html`<div class="mo-noshot"><p><b>Nothing to show.</b> ${r.why_not ? r.why_not[0].toUpperCase() + r.why_not.slice(1) : "No result has passed here yet"}, so this has not been rendered.</p></div>`}</div>
    <div class="mo-info">
      <div class="fx-row"><h3>${r.label}</h3><span class=${"fx-tag " + (s ? "measured" : "estimate")}>${r.proof}</span></div>
      <p>${r.does}</p>
      <${Facts} r=${r} s=${s}/>
      ${r.weak.length > 0 && html`<div class="mo-weak"><b>What is weak</b><ul>${r.weak.map((w) => html`<li key=${w}>${w}</li>`)}</ul></div>`}
      ${r.ready ? html`<button type="button" class="btn small" aria-expanded=${open} onClick=${() => setOpen(!open)}>${open ? "Close" : "Try it"}</button>` : html`<p class="small">${r.why_not}.</p>`}
      ${open && r.ready && html`<${RunForm} r=${r} ask=${ask} characters=${characters}/>`}
    </div></article>`;
}

function Hero({ hero, rows }) {
  const v = useRef();
  if (!hero) return null;
  return html`<section class="mo-hero film" aria-label="One motion, start to finish">
    <div class="mo-heropic" style=${{ "--ar": hero.ar }}><${Media} src=${hero.src} poster=${hero.poster} alt=${hero.alt} eager/></div>
    <div class="mo-herotext"><span class="fx-kick">Rendered here</span><p class="mo-said">“${hero.prompt}”</p><p class="small">${hero.note}</p>
      <${Stats} items=${[[rows.filter((r) => r.samples.length).length, "routes with a real result"], [hero.seconds_label, "for this motion"], [hero.peak_label, "peak on the card"]]}/></div>
  </section>`;
}

export function Motion() {
  const [d, setD] = useState(null), [err, setErr] = useState(""), [at, setAt] = useState("words"), [characters, setCharacters] = useState([]);
  useEffect(() => { api("/api/motion").then(setD).catch((e) => setErr(e.message)); api("/api/worldkit/assets?type=character").then((x) => setCharacters((x.assets || []).filter((a) => a.build === "done"))).catch(() => {}); }, []);
  if (err) return html`<div class="fx"><p class="fx-err" role="alert">${err}</p></div>`;
  if (!d) return html`<div class="fx"><p>Loading</p></div>`;
  const g = d.groups.find((x) => x.id === at), rows = d.routes.filter((r) => r.group === at);
  return html`<div class="fx mo">
    <${Hero} hero=${d.hero} rows=${d.routes}/>
    <${Strip} label="What do you want to move" value=${at} onPick=${setAt} items=${d.groups.map((x) => ({ k: x.id, b: x.title, s: `${d.routes.filter((r) => r.group === x.id && r.samples.length).length} of ${d.routes.filter((r) => r.group === x.id).length} rendered` }))}/>
    <${Head} sub=${g.does}>${g.title}</${Head}>
    <div class="mo-rows">${rows.map((r) => html`<${Row} key=${r.id} r=${r} ask=${d.ask} characters=${characters}/>`)}</div>
    <section class="mo-rules" aria-label="Real people"><h2>Real people</h2><p>Samples show invented adults made here, fully clothed. ${d.limits}</p></section>
    <details class="mo-out"><summary>Models on disk that are not offered here, and why</summary><ul>${d.not_offered.map((n) => html`<li key=${n.model}><b>${n.model}.</b> ${n.why}</li>`)}</ul></details>
  </div>`;
}
