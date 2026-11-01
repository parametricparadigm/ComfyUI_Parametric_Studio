/* AI Edits (the video-editing models, each as a simple form), Schedules (set-and-forget cron jobs), and the box calibration card. */
import { useState, useEffect } from "preact/hooks";
import { html, api, post } from "./common.js";
import { useModels, DlButton, gbText } from "./models_ui.js";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const sel = "width:100%;margin-top:3px;background:var(--panel2);color:var(--text);border:1px solid var(--line);border-radius:10px;padding:8px";
/* the shared download button for one edit tool; reloads the form when the files have arrived */
function EditDl({ id, onDone }) { const { ready, dl } = useModels(), done = dl.state === "done" && dl.id === id; useEffect(() => { if (done) onDone(); }, [done]); return html`<${DlButton} kind="edit" id=${id} row=${ready && ready.edits && ready.edits[id]} small/>`; }
export function RunForm({ base, id, title, blurb, onBack }) {
  const [d, setD] = useState(null), [vals, setVals] = useState({}), [res, setRes] = useState(null), [busy, setBusy] = useState(false), [err, setErr] = useState(""), [ok, setOk] = useState(false), [msg, setMsg] = useState("");
  const load = async () => { try { const x = await api(`${base}/${id}`); setD(x); const v = {}; x.inputs.forEach((i) => { if (i.default != null && i.type !== "image" && i.type !== "video") v[i.key] = i.default; }); setVals(v); } catch (e) { setErr(e.message); } };
  useEffect(() => { load(); }, [id]);
  const upload = async (key, f) => { if (!f) return; const fd = new FormData(); fd.append("file", f); try { const r = await api("/api/upload", { method: "POST", body: fd }); setVals((v) => ({ ...v, [key]: r.name })); } catch (e) { setErr(e.message); } };
  const run = async () => { setBusy(true); setErr(""); setRes(null); try { const { job } = await post(`${base}/${id}/run`, { values: vals }); for (let i = 0; i < 900; i++) { await sleep(1500); const s = await api("/api/jobs/" + job); if (s.status === "done") { setRes(s); break; } if (s.status === "error") { setErr(s.error || "failed"); break; } } } catch (e) { setErr(e.message); } setBusy(false); };
  const fetchM = async () => { setMsg("Downloading, this can take a while..."); try { const r = await post(`${base}/${id}/fetch-models`, { confirm: ok }); setMsg(`Saved ${r.saved.length} file(s).`); await load(); } catch (e) { setMsg(e.message); } };
  if (!d) return html`<div><button class="btn small" onClick=${onBack}>Back</button><p class="small">${err || "Loading..."}</p></div>`;
  return html`<div><button class="btn small" onClick=${onBack}>Back</button><h2 style="margin:12px 0 2px">${title || d.title}</h2><p class="small" style="margin:0 0 10px">${blurb}</p>
    <div class="layout"><div class="card"><h3>Inputs</h3>
      ${d.inputs.map((i) => html`<label class="small" style="display:block;margin:10px 0">${i.label}
        ${i.type === "image" || i.type === "video" ? html`<div class="row" style="margin:4px 0"><input type="file" accept=${i.type === "video" ? "video/mp4,video/webm,video/quicktime,video/x-matroska" : "image/png,image/jpeg,image/webp"} onChange=${(e) => upload(i.key, e.target.files[0])}/>${vals[i.key] && html`<span class="small">${vals[i.key]}</span>`}</div>` :
          i.type === "choice" ? html`<select value=${vals[i.key] ?? ""} onChange=${(e) => setVals({ ...vals, [i.key]: e.target.value })} style=${sel}>${(i.options || []).map((o) => html`<option value=${o}>${o}</option>`)}</select>` :
          i.type === "number" ? html`<input type="text" inputmode="decimal" value=${vals[i.key] ?? ""} onInput=${(e) => setVals({ ...vals, [i.key]: e.target.value === "" || isNaN(+e.target.value) ? e.target.value : +e.target.value })} style="margin-top:3px"/>` :
          i.type === "bool" ? html`<div><input type="checkbox" checked=${!!vals[i.key]} onChange=${(e) => setVals({ ...vals, [i.key]: e.target.checked })}/></div>` :
          html`<textarea value=${vals[i.key] ?? ""} onInput=${(e) => setVals({ ...vals, [i.key]: e.target.value })} style="min-height:70px;margin-top:3px"></textarea>`}</label>`)}
      ${d.downloads && d.downloads.length > 0 && html`<div class="needs"><b>Missing model files</b><ul class="small" style="margin:0;padding-left:18px">${d.downloads.map((x) => html`<li>${x.name}</li>`)}</ul><${EditDl} id=${id} onDone=${load}/></div>`}
      <div class="row"><span class="grow"></span><button class="btn primary" disabled=${busy || !d.ready || (d.downloads || []).length > 0} onClick=${run}>${busy ? "Running..." : "Run"}</button></div>${err && html`<p class="small" style="color:var(--err)">${err}</p>`}</div>
      <div class="card"><h3>Result</h3>${!res && html`<p class="small" style="margin:0">${busy ? "Running on your GPU..." : "The result appears here."}</p>`}${res && res.files.map((f) => f.kind === "video" ? html`<video src=${f.url} controls autoplay loop style="max-width:100%;border-radius:12px;margin-bottom:8px"></video>` : f.kind === "audio" ? html`<audio src=${f.url} controls style="width:100%"></audio>` : html`<img src=${f.url} alt="" style="max-width:100%;border-radius:12px"/>`)}</div></div></div>`;
}
export function AIEdits() {
  const [art, setArt] = useState({}); useEffect(() => { fetch("edit_art/index.json").then((r) => (r.ok ? r.json() : {})).then(setArt).catch(() => {}); }, []);
  const [data, setData] = useState(null), [cat, setCat] = useState("all"), [sel_, setSel] = useState(null), [err, setErr] = useState(""), { ready } = useModels();
  useEffect(() => { api("/api/edits").then((d) => { setData(d); let w = null; try { w = sessionStorage.getItem("edit_open"); sessionStorage.removeItem("edit_open"); } catch {} const t = w && d.tools.find((x) => x.id === w); if (t) setSel(t); }).catch((e) => setErr(e.message)); }, []);
  if (sel_) return html`<${RunForm} base="/api/edits" id=${sel_.id} title=${sel_.label} blurb=${sel_.blurb} onBack=${() => setSel(null)}/>`;
  if (!data) return html`<p class="small">${err || "Loading the editing models..."}</p>`;
  const cats = Object.entries(data.categories), row = (t) => ready && ready.edits && ready.edits[t.id] && ready.edits[t.id].known ? ready.edits[t.id] : null;
  const state = (t) => { const r = row(t); if (t.unknown_nodes.length || (r && r.needs_nodes && r.needs_nodes.length)) return ["nodes", "Needs nodes"]; if (r) return r.ready ? ["ok", "Ready"] : ["need", r.missing_gb ? `Needs ${gbText(r.missing_gb)}` : `Needs ${r.missing} file${r.missing > 1 ? "s" : ""}`]; return t.runnable ? ["ok", "Ready"] : t.missing_models.length ? ["need", `Needs ${t.missing_models.length} file${t.missing_models.length > 1 ? "s" : ""}`] : ["chk", "Checking"]; };
  const shown = data.tools.filter((t) => cat === "all" || t.category === cat), count = (k) => data.tools.filter((t) => k === "all" || t.category === k).length;
  return html`<div><p class="small" style="max-width:780px">AI video editing models, each one a simple form: remove people or objects, upscale, slow motion, extend a clip, restyle, change the camera, fill or widen the frame, or edit by instruction. They run from ComfyUI's official local templates on your own GPU. A card says Ready, or exactly what it still needs and how big that is.</p>
    <div class="tabs"><button class=${"chip" + (cat === "all" ? " on" : "")} onClick=${() => setCat("all")}>All ${count("all")}</button>${cats.map(([k, v]) => html`<button class=${"chip" + (cat === k ? " on" : "")} onClick=${() => setCat(k)}>${v} ${count(k)}</button>`)}</div>
    <div class="egrid">${shown.map((t) => { const st = state(t), r = row(t); return html`<article class="ecard" tabindex="0" role="button" aria-label=${t.label} onClick=${() => setSel(t)} onKeyDown=${(e) => { if (e.key === "Enter") setSel(t); }}>
      ${art[t.id] && html`<video class="eart" src=${"edit_art/" + t.id + ".mp4"} muted loop autoplay playsinline preload="metadata"></video>`}<span class=${"estate " + st[0]} title=${t.unknown_nodes.length ? "Custom nodes needed: " + t.unknown_nodes.join(", ") : ""}>${st[1]}</span><h4>${t.label}</h4><p>${t.blurb}</p>
      ${r && !r.ready && html`<${DlButton} kind="edit" id=${t.id} row=${r} small/>`}<div class="ecat">${t.category_label}${r && r.files ? ` · ${r.files} model files` : ""}</div></article>`; })}</div></div>`;
}
const STARTERS = [{ t: "Morning moodboard", goal: "image", cron: "every morning at 8", prompt: "a calm still life in morning light, soft film grain", n: 3 }, { t: "Nightly video clip", goal: "video", cron: "every night at 2", prompt: "a slow drone shot over a misty coastline at dawn", n: 1 }, { t: "Friday soundtrack", goal: "music", cron: "every Friday at 5", prompt: "warm instrumental lo-fi with soft keys and brushed drums", n: 1 }, { t: "Monday product shot", goal: "product", cron: "every Monday at 9", prompt: "a matte black bottle on wet stone, dramatic studio light", n: 2 }, { t: "Anime frame of the day", goal: "anime", cron: "every evening at 6", prompt: "a lone mecha pilot on a rainy rooftop, neon reflections", n: 1 }, { t: "Weekend hero image", goal: "flux3", cron: "every weekend morning", prompt: "a lighthouse on a cliff in golden hour, cinematic wide shot", n: 2 }];
export function Schedules() {
  const [d, setD] = useState({ jobs: [], presets: {} }), [f, setF] = useState({ name: "", goal: "image", prompt: "", cron: "every morning at 8", max_per_day: 3 }), [err, setErr] = useState(""), [goals, setGoals] = useState({}), [shots, setShots] = useState([]);
  useEffect(() => { fetch("showcase/showcase.json").then((r) => r.json()).then(setShots).catch(() => {}); }, []);
  const load = () => api("/api/schedules").then(setD).catch((e) => setErr(e.message));
  useEffect(() => { load(); api("/api/goals").then((g) => setGoals(Object.fromEntries(Object.entries(g).filter(([, v]) => !v.needs_image)))); }, []);
  const add = async () => { setErr(""); try { await post("/api/schedules", f); setF({ ...f, name: "", prompt: "" }); load(); } catch (e) { setErr(e.message); } };
  const act = async (id, what) => { try { if (what === "del") await api("/api/schedules/" + id, { method: "DELETE" }); else await post(`/api/schedules/${id}/${what}`, {}); load(); } catch (e) { setErr(e.message); } };
  const ideas = STARTERS.filter((x) => goals[x.goal] && d.presets[x.cron]); const label = (g) => (goals[g] && goals[g].label) || g; const active = d.jobs.filter((j) => j.enabled).length;
  const pick = (x) => { setF({ name: x.t, goal: x.goal, prompt: x.prompt, cron: x.cron, max_per_day: x.n }); const el = document.querySelector(".autoform"); if (el) el.scrollIntoView({ behavior: "smooth", block: "center" }); };
  return html`<div>
    <section class="apihero"><div><h2>Set it. <em>Forget it.</em></h2><p>Pick what to make and when. Jobs only start when ComfyUI is idle, never go over your daily cap, and everything lands in your Library.</p></div><div class="apistats"><div><b>${d.jobs.length}</b><span>schedules</span></div><div><b>${active}</b><span>active</span></div><div><b>0</b><span>credits on your GPU</span></div></div></section>
    <div class="psec"><h3>Start from an idea</h3></div><p class="psecnote">Click one to fill in the form below. Nothing runs until you add it.</p>
    <div class="autoideas">${ideas.map((x) => { const art = (shots.find((m) => m.goal === x.goal && m.poster) || {}).poster; return html`<button class="autoidea" onClick=${() => pick(x)}>${art && html`<img src=${art} alt="" loading="lazy" onError=${(e) => e.target.remove()}/>`}<span><b>${x.t}</b><small>${x.cron}</small></span></button>`; })}</div>
    <div class="autogrid"><div class="card autoform"><h3>New schedule</h3>
      <label class="small">Name<input type="text" placeholder="Optional" value=${f.name} onInput=${(e) => setF({ ...f, name: e.target.value })}/></label>
      <label class="small">What to make<select value=${f.goal} onChange=${(e) => setF({ ...f, goal: e.target.value })} style=${sel}>${Object.entries(goals).map(([k, v]) => html`<option value=${k}>${v.label}: ${v.family}</option>`)}</select></label>
      <label class="small">Prompt<textarea placeholder="Describe what to make each time" value=${f.prompt} onInput=${(e) => setF({ ...f, prompt: e.target.value })}></textarea></label>
      <div class="small autolabel">When</div><div class="chips autowhen">${Object.keys(d.presets).map((k) => html`<button class=${"chip" + (f.cron === k ? " on" : "")} onClick=${() => setF({ ...f, cron: k })}>${k}</button>`)}</div>
      <div class="row autofoot"><label class="small autocap">Most per day<input type="text" inputmode="numeric" value=${f.max_per_day} onInput=${(e) => setF({ ...f, max_per_day: +e.target.value || 1 })}/></label><span class="grow"></span><button class="btn primary" disabled=${f.prompt.trim().length < 3} onClick=${add}>Add schedule</button></div>${err && html`<p class="small" style="color:var(--err)">${err}</p>`}</div>
      <div class="card"><h3>Your schedules</h3>${!d.jobs.length && html`<div class="autoempty"><b>Nothing scheduled yet</b><span class="small">Pick an idea above or fill in the form. Your first run will show up here.</span></div>`}
        ${d.jobs.map((j) => html`<div class="autojob"><span class=${"autodot" + (j.enabled ? " on" : "")} aria-hidden="true"></span><div class="autojobt"><b>${j.name}</b><small>${label(j.goal)} · ${j.cron}</small><small>${j.enabled ? "Active" : "Paused"} · last run: ${j.last_status || "not yet"}</small></div><div class="row autojoba"><button class="btn small" onClick=${() => act(j.id, "toggle")}>${j.enabled ? "Pause" : "Resume"}</button><button class="btn small" onClick=${() => act(j.id, "run-now")}>Run now</button><button class="btn small ghost" onClick=${() => act(j.id, "del")}>Delete</button></div></div>`)}</div></div></div>`;
}
export function CalibrateCard() {
  const [s, setS] = useState({ running: false, log: [], profile: null }), [ok, setOk] = useState(false), [err, setErr] = useState("");
  const load = () => api("/api/calibrate").then(setS).catch(() => {});
  useEffect(() => { load(); const t = setInterval(load, 3000); return () => clearInterval(t); }, []);
  const go = async () => { setErr(""); try { await post("/api/calibrate", { confirm: ok }); load(); } catch (e) { setErr(e.message); } };
  const g = (s.profile && s.profile.goals) || {};
  return html`<div class="card" style="margin-bottom:14px"><h3>Optimize this box</h3><p class="small" style="margin:0 0 8px">Runs a small test render of seven goals that fit your free VRAM, twice each (cold and warm), and shows the seconds here. It does not change any settings.</p>
    <label class="small"><input type="checkbox" checked=${ok} onChange=${(e) => setOk(e.target.checked)}/> Yes, run a few small renders on my GPU</label>
    <div class="row"><button class="btn primary" disabled=${!ok || s.running} onClick=${go}>${s.running ? "Calibrating..." : "Calibrate now"}</button>${s.running && html`<button class="btn small" onClick=${() => post("/api/calibrate/cancel", {})}>Cancel</button>`}</div>${err && html`<p class="small" style="color:var(--err)">${err}</p>`}
    ${s.log.length > 0 && html`<p class="small" style="margin:8px 0 0">${s.log.join(" | ")}</p>`}
    ${Object.keys(g).length > 0 && html`<table class="md" style="margin-top:10px"><tr><th>Model</th><th>First run</th><th>Warm</th><th>Note</th></tr>${Object.entries(g).map(([k, v]) => html`<tr><td>${k}</td><td>${v.seconds_cold ?? ""}${v.seconds_cold ? " s" : ""}</td><td>${v.seconds_warm ?? ""}${v.seconds_warm ? " s" : ""}</td><td>${v.skipped || v.error || "ok"}</td></tr>`)}</table>`}</div>`;
}
