/* Project File: pack a board or recipe runs into one file, or open one and see what this machine is missing. Nothing renders without a click. */
import { useEffect, useRef, useState } from "preact/hooks";
import { html, api, post } from "./common.js";
import { FxHero } from "./fx.js";

const IN = ["Graphs", "Seeds", "Model hashes", "Where to get each model", "Pictures, clips and sound, if you tick it"], OUT = ["Model weights", "Your folder paths", "Anything from your home folder"];

const size = (n) => (n == null ? "" : n > 2 ** 30 ? (n / 2 ** 30).toFixed(1) + " GB" : n > 2 ** 20 ? (n / 2 ** 20).toFixed(1) + " MB" : Math.max(1, Math.round(n / 1024)) + " KB");
const board = () => { try { return JSON.parse(localStorage.getItem("shotboard_v1")) || {}; } catch { return {}; } };

function Pack() {
  const b = useRef(board()).current, jobs = b.jobs || [];
  const [runs, setRuns] = useState(null), [picked, setPicked] = useState({}), [useBoard, setUseBoard] = useState(jobs.length > 0), [name, setName] = useState("My shoot"), [media, setMedia] = useState(false), [job, setJob] = useState(null), [err, setErr] = useState("");
  useEffect(() => { api("/api/project/runs").then((d) => setRuns(d.runs)).catch(() => setRuns([])); }, []);
  useEffect(() => { if (!job || job.state !== "working") return; const t = setInterval(() => api("/api/project/export/" + job.id).then(setJob).catch((e) => setErr(e.message)), 1200); return () => clearInterval(t); }, [job && job.id, job && job.state]);
  const chosen = Object.keys(picked).filter((k) => picked[k]); const ready = (useBoard && jobs.length > 0) || chosen.length > 0;
  const go = async () => { setErr(""); try { const r = await post("/api/project/export", { name, include_media: media, board: useBoard ? { jobs } : null, runs: chosen }); setJob({ id: r.id, state: "working", note: "Starting" }); } catch (e) { setErr(e.message); } };
  return html`<section class="fx-card" aria-label="Pack a project"><span class="fx-kick">Pack</span><h2>Make a project file</h2>
    <label class="fx-lab">Name<input class="fx-in" value=${name} maxlength="120" onInput=${(e) => setName(e.target.value)}/></label>
    <fieldset class="pj-set"><legend>What goes in</legend>
      <label class="pj-pick"><input type="checkbox" disabled=${!jobs.length} checked=${useBoard} onChange=${() => setUseBoard(!useBoard)}/> ${jobs.length ? `Your Shot Board: ${jobs.length} ${jobs.length === 1 ? "shot" : "shots"}` : html`<span>Your Shot Board is empty. <a href="#shots">Open it</a></span>`}</label>
      ${runs === null ? html`<p class="small">Reading your recipe runs.</p>` : runs.length === 0 ? html`<p class="small">No finished recipe runs yet.</p>` : runs.map((r) => html`<label class="pj-pick" key=${r.run}><input type="checkbox" checked=${!!picked[r.run]} onChange=${() => setPicked({ ...picked, [r.run]: !picked[r.run] })}/> ${r.title} <small>${new Date((r.created || 0) * 1000).toLocaleDateString()}</small></label>`)}
    </fieldset>
    <label class="pj-pick"><input type="checkbox" checked=${media} onChange=${() => setMedia(!media)}/> Include pictures, clips and sound <small>Up to 2 GB. Their metadata is removed.</small></label>
    <div class="fx-note"><b>Never in the file</b><p>Model weights, your folder paths, or anything from your home folder. If a path would slip through, no file gets written.</p></div>
    <div class="fx-row"><button class="fx-go" type="button" disabled=${!ready || (job && job.state === "working")} onClick=${go}>${job && job.state === "working" ? "Packing" : "Pack it"}</button>${job && job.state === "working" && html`<span class="small" role="status">${job.note}</span>`}</div>
    ${err && html`<div class="fx-note bad" role="alert"><p>${err}</p></div>`}
    ${job && job.state === "error" && html`<div class="fx-note bad" role="alert"><b>No file was made</b><p>${job.error}</p></div>`}
    ${job && job.state === "done" && html`<div class="fx-note" role="status"><b>${job.file}, ${size(job.bytes)}</b><p>${job.shots} ${job.shots === 1 ? "shot" : "shots"}, ${job.with_graph} with a graph, ${job.models} ${job.models === 1 ? "model record" : "model records"}, ${job.media} media ${job.media === 1 ? "file" : "files"}.</p>${(job.notes || []).map((n) => html`<p class="small">${n}</p>`)}<a class="fx-go" href=${`/api/project/export/${job.id}/file`} download=${job.file}>Download the file</a></div>`}
  </section>`;
}

function ShotRow({ pid, s }) {
  const [job, setJob] = useState(null), [err, setErr] = useState(""), [state, setState] = useState(null);
  useEffect(() => { if (!job || (state && !["running", "queued", "unknown"].includes(state.status))) return; const t = setInterval(() => api("/api/jobs/" + job).then(setState).catch(() => {}), 2500); return () => clearInterval(t); }, [job, state && state.status]);
  const go = async () => { setErr(""); try { setJob((await post(`/api/project/open/${pid}/render`, { confirm: true, shot: s.id })).job); } catch (e) { setErr(e.message); } };
  const out = state && state.files && state.files[0];
  return html`<li class="fx-card pj-shot"><div class="fx-row"><span class=${"fx-tag " + (s.ready ? "ok" : "bad")}>${s.ready ? "Ready here" : "Not ready"}</span>${s.seed != null && html`<span class="small">seed <code>${s.seed}</code></span>`}${s.graph_source && html`<span class="small">graph ${s.graph_source}</span>`}</div><h3>${s.label}</h3>
    ${s.problems.length > 0 && html`<ul class="pj-probs">${s.problems.map((p) => html`<li key=${p}>${p}</li>`)}</ul>`}
    ${s.ready && !job && html`<button class="fx-go" type="button" onClick=${go}>Render this shot</button>`}
    ${job && html`<p role="status" class="small">${state ? state.status : "Sent to ComfyUI"}${state && state.error ? `: ${state.error}` : ""}</p>`}
    ${out && (out.kind === "video" ? html`<video src=${out.url} controls playsinline class="pj-out"></video>` : out.kind === "audio" ? html`<audio src=${out.url} controls></audio>` : html`<img src=${out.url} alt=${"Your render of " + s.label} class="pj-out"/>`)}
    ${err && html`<p class="fx-err" role="alert">${err}</p>`}</li>`;
}

function Opened({ p }) {
  const r = p.report; const hashTone = { same: "ok", different: "bad", missing: "bad" };
  return html`<section class="fx" aria-label=${"Project " + p.name}>
    <div class="fx-card"><span class="fx-kick">Opened${p.made ? `, made ${p.made}` : ""}</span><h2>${p.name}</h2>
      <dl class="pj-sum"><div><dd>${r.ready} of ${r.shots.length}</dd><dt>shots ready on this machine</dt></div><div><dd>${r.missing_models.length}</dd><dt>model files missing</dt></div><div><dd>${r.media.length}</dd><dt>media files inside</dt></div></dl>
      ${!r.comfy_up && html`<div class="fx-note bad" role="alert"><b>ComfyUI is not reachable</b><p>So nothing could be checked. Start it and open the file again.</p></div>`}
      ${p.notes.map((n) => html`<p class="small" key=${n}>${n}</p>`)}
      <div class="fx-note warn"><b>This file may be someone else's</b><p>A graph can only use nodes you already have, and we check it first. But it still runs on your machine, so render what you trust.</p></div></div>
    ${r.models.length > 0 && html`<div class="fx-card"><h3>Model files</h3><div class="pj-scroll"><table class="fx-table"><thead><tr><th>File</th><th>On this machine</th><th>Hash</th><th>Get it</th></tr></thead><tbody>${r.models.map((m) => html`<tr key=${m.file}><td><code>${m.file}</code></td><td>${m.here ? html`<span class="fx-tag ok">yes</span>` : html`<span class="fx-tag bad">missing</span>`}</td><td><span class=${"fx-tag " + (hashTone[m.hash_state] || "")}>${m.hash_state}</span></td><td>${m.url ? html`<a href=${m.url} rel="noreferrer noopener" target="_blank">${new URL(m.url).hostname}</a>${m.folder ? html`<small> into ${m.folder}</small>` : ""}${m.gated ? html`<small> (licence to accept first)</small>` : ""}` : html`<span class="small">no source known</span>`}</td></tr>`)}</tbody></table></div></div>`}
    <ul class="pj-shots">${r.shots.map((s) => html`<${ShotRow} key=${s.id} pid=${p.id} s=${s}/>`)}</ul>
  </section>`;
}

export function ProjectFile() {
  const [opened, setOpened] = useState(null), [err, setErr] = useState(""), [busy, setBusy] = useState(false), [drag, setDrag] = useState(false);
  const open = async (f) => { if (!f) return; setBusy(true); setErr(""); setOpened(null); try { const fd = new FormData(); fd.append("file", f); setOpened(await api("/api/project/open", { method: "POST", body: fd })); } catch (e) { setErr(e.message); } setBusy(false); };
  return html`<div class="fx">
    <${FxHero} kicker="One .psproject file" line="Everything to remake it. Nothing private." lede="Pack your Shot Board or finished recipe runs on one machine, open the file on another, and see what that machine has and what it is missing before anything renders."
      art=${html`<div class="pj-anat"><div class="pj-in"><span class="fx-kick">In the file</span><ul>${IN.map((x) => html`<li key=${x}>${x}</li>`)}</ul></div><div class="pj-out"><span class="fx-kick">Never in the file</span><ul>${OUT.map((x) => html`<li key=${x}>${x}</li>`)}</ul></div></div>`}/>
    <div class="fx-two"><${Pack}/>
    <section class=${"fx-card pj-drop" + (drag ? " on" : "")} aria-label="Open a project" onDragOver=${(e) => { e.preventDefault(); setDrag(true); }} onDragLeave=${() => setDrag(false)} onDrop=${(e) => { e.preventDefault(); setDrag(false); open(e.dataTransfer.files[0]); }}><span class="fx-kick">Open</span><h2>Open a project file</h2><p>Drop a <code>.psproject</code> here. You see what this machine has and what it is missing, with where to get it. Nothing renders until you ask.</p>
      <label class="fx-go pj-file">${busy ? "Reading" : "Choose a file"}<input type="file" accept=".psproject,.zip" disabled=${busy} onChange=${(e) => open(e.target.files[0])}/></label>
      ${err && html`<div class="fx-note bad" role="alert"><b>Not opened</b><p>${err}</p></div>`}</section></div>
    ${opened && html`<${Opened} p=${opened}/>`}</div>`;
}
