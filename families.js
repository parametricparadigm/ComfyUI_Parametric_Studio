/* Families: every model family this studio can run, as a gallery of what each one really made here. A family page holds its samples, its crew member, its templates as forms that run on that family's own ComfyUI, and start or stop behind the VRAM gate. A family with no render shows what it needs, never a stand-in image. */
import { useEffect, useMemo, useRef, useState } from "preact/hooks";
import { html, api, post } from "./common.js";
import { Drop, LiveMedia } from "./showcase.js";

const KINDS = [["all", "All"], ["image", "Image"], ["video", "Video"], ["audio", "Audio"], ["3d", "3D"], ["utility", "Utility"], ["llm", "LLM"]];
const STATES = [["all", "Any state"], ["render", "Rendered here"], ["ready", "Template ready"], ["up", "Running"], ["todo", "Not rendered yet"], ["download", "Needs download"]];
const GLYPH = { image: "▧", video: "▶", audio: "♫", "3d": "◈", utility: "⚙", llm: "…" };
const KIND_LABEL = { image: "Image", video: "Video", audio: "Audio", "3d": "3D", utility: "Utility", llm: "LLM" };
const flagCls = (s) => (s === "render" ? "gflag" : s === "download" || s === "pack" || s === "orphan" || s === "nodir" ? "gflag warn" : "gflag dim");
const matchState = (f, s) => s === "all" || (s === "render" ? f.level === "render" : s === "ready" ? f.templates_ready > 0 : s === "up" ? f.up : s === "download" ? f.state === "download" : f.level !== "render");

function Card({ f, onOpen }) {
  const m = f.media && f.media[0], visual = m && m.kind !== "audio";
  const sub = f.state === "download" ? (f.repos.length ? "Needs its files: " + f.repos[0] : "Needs its model files") : [f.est_vram_gb ? `about ${f.est_vram_gb} GB VRAM` : "", f.templates ? `${f.templates_ready} of ${f.templates} templates ready` : "no template yet"].filter(Boolean).join(", ") + (f.media_library ? ". Sample from ComfyUI's library" : "");
  return html`<button class="gcard" onClick=${() => onOpen(f.slug)} aria-label=${`${f.family}: ${f.state_label}`}>
    ${visual ? html`<${LiveMedia} item=${m} cls="gmedia"/>` : html`<div class=${"gmedia gblank f" + f.kind}>${GLYPH[f.kind] || ""}</div>`}
    <span class="gshade"></span><span class=${flagCls(f.state)}>${f.state_label}</span><span class=${"glic" + (f.up ? " on" : "")}>${f.up ? "Running" : KIND_LABEL[f.kind] || f.kind}</span>
    <span class="gtext"><b>${f.family}</b><small>${sub}</small></span></button>`;
}

function Gallery({ onOpen }) {
  const [d, setD] = useState(null), [err, setErr] = useState(""), [q, setQ] = useState(""), [kind, setKind] = useState("all"), [st, setSt] = useState("all");
  useEffect(() => { let on = true; const load = () => api("/api/families").then((x) => { if (on) { setD(x); setErr(""); } }).catch((e) => on && setErr(e.message)); load(); const t = setInterval(load, 20000); return () => { on = false; clearInterval(t); }; }, []);
  if (!d) return html`<p class="small">${err || "Reading the instances folder"}</p>`;
  const fams = d.families, ql = q.trim().toLowerCase();
  const shown = fams.filter((f) => (kind === "all" || f.kind === kind) && matchState(f, st) && (!ql || [f.family, f.kind, f.licence, f.what, f.crew && f.crew.name, f.state_label].filter(Boolean).join(" ").toLowerCase().includes(ql))).sort((a, b) => (b.media_count > 0) - (a.media_count > 0));
  const rc = d.reconcile || {}, odd = [...(rc.dir_without_family_entry || []), ...(rc.family_entry_without_dir || []), ...(rc.no_instance_file || []), ...(rc.in_registry_without_dir || []), ...(rc.model_folder_without_dir || [])];
  const cnt = { render: fams.filter((f) => f.level === "render").length, ready: fams.filter((f) => f.templates_ready > 0).length, up: fams.filter((f) => f.up).length };
  return html`<div>
    <div class="fstats"><div><b class="g">${rc.dirs_on_disk ?? fams.length}</b><span>instances on disk, ${rc.shown ?? fams.length} shown</span></div><div><b>${cnt.render}</b><span>rendered here</span></div><div><b>${cnt.ready}</b><span>with a template ready</span></div><div><b>${cnt.up}</b><span>running now</span></div>${d.free_gb != null && html`<div><b>${d.free_gb} GB</b><span>VRAM free, ${d.floor_gb} GB stays free</span></div>`}</div>
    ${odd.length > 0 && html`<p class="fnote" style="margin:-6px 0 14px">On one side only: ${[["folder with no family entry", rc.dir_without_family_entry], ["family entry with no folder", rc.family_entry_without_dir], ["folder with no instance file", rc.no_instance_file], ["in the port registry with no folder", rc.in_registry_without_dir], ["model folder with no instance", rc.model_folder_without_dir]].filter(([, v]) => v && v.length).map(([l, v]) => `${l}: ${v.join(", ")}`).join("; ")}. They are listed below with their real state.</p>`}
    <div class="fbar"><input type="search" placeholder="Search families" value=${q} onInput=${(e) => setQ(e.target.value)} aria-label="search families"/>
      <div class="chips" role="group" aria-label="kind">${KINDS.map(([k, l]) => html`<button class=${"chip" + (kind === k ? " on" : "")} onClick=${() => setKind(k)}>${l} ${k === "all" ? fams.length : fams.filter((f) => f.kind === k).length}</button>`)}</div>
      <div class="chips" role="group" aria-label="state">${STATES.map(([k, l]) => html`<button class=${"chip" + (st === k ? " on" : "")} onClick=${() => setSt(k)}>${l}</button>`)}</div></div>
    ${shown.length ? html`<div class="fgrid">${shown.map((f) => html`<${Card} key=${f.slug} f=${f} onOpen=${onOpen}/>`)}</div>` : html`<div class="empty"><h2>No family matches</h2>Try another word or clear the filters.</div>`}
  </div>`;
}

/* the deck on the Create page: any family, one click away */
export function FamilyDeck({ goTab }) {
  const [d, setD] = useState(null);
  useEffect(() => { api("/api/families").then(setD).catch(() => {}); }, []);
  if (!d) return null;
  const list = [...d.families].sort((a, b) => (!!(b.media && b.media.length) - !!(a.media && a.media.length)) || (b.templates_ready > 0) - (a.templates_ready > 0)).slice(0, 18);
  return html`<section class="sect"><h2>All families</h2><div class="sectsub">Every model on this machine has its own ComfyUI. ${d.families.length} families, each with a real status. <a href="#families" onClick=${(e) => { e.preventDefault(); goTab("families"); }}>See them all</a></div>
    <div class="gdeck" aria-label="model families">${list.map((f) => html`<${Card} key=${f.slug} f=${f} onOpen=${(s) => goTab("families/" + s)}/>`)}</div></section>`;
}

function Gate({ refusal, onFreed }) {
  const [busy, setBusy] = useState(false), [res, setRes] = useState(null), [err, setErr] = useState("");
  const free = async () => { setBusy(true); setErr(""); try { const r = await post("/api/families/free-idle", {}); setRes(r); onFreed && onFreed(r); } catch (e) { setErr(e.message); } setBusy(false); };
  return html`<div class="fcardx fwarn" role="status"><h3>Not enough VRAM right now</h3><p>${refusal.message}</p>
    ${refusal.busy && refusal.busy.length > 0 && html`<p class="fnote">Busy, so left alone: ${refusal.busy.join(", ")}.</p>`}
    <div class="frow">${refusal.idle && refusal.idle.length > 0 ? html`<button class="btn small" disabled=${busy} onClick=${free}>${busy ? "Freeing" : `Free what is idle (${refusal.idle.join(", ")})`}</button>` : html`<span class="fnote">No idle ComfyUI to free. LLM servers are never stopped from here; put them to sleep yourself if you want the room.</span>`}</div>
    ${res && html`<p class="fnote" style="margin-top:8px">Freed ${res.freed.join(", ") || "nothing"}. ${res.free_gb} GB free now.${res.left.length ? " Left alone: " + res.left.map((x) => `${x.name} (${x.why})`).join(", ") + "." : ""}</p>`}${err && html`<p class="small" style="color:var(--err);margin:8px 0 0">${err}</p>`}</div>`;
}

function Form({ f, tid, onClose, onDone }) {
  const [form, setForm] = useState(null), [vals, setVals] = useState({}), [err, setErr] = useState(""), [job, setJob] = useState(null), [st, setSt] = useState(null), [files, setFiles] = useState({}); const ref = useRef(null);
  useEffect(() => { setForm(null); setErr(""); setJob(null); setSt(null); setVals({}); setFiles({}); api(`/api/families/${f.slug}/templates/${encodeURIComponent(tid)}`).then((d) => { setForm(d); const v = {}; d.inputs.forEach((i) => { if (i.default !== undefined && i.default !== null && i.type !== "image" && i.type !== "video" && i.type !== "unsupported") v[i.key] = i.default; }); setVals(v); if (ref.current) ref.current.scrollIntoView({ behavior: "smooth", block: "nearest" }); }).catch((e) => setErr(e.message)); }, [tid]);
  useEffect(() => { if (!job) return; let on = true; const t = setInterval(async () => { try { const s = await api(`/api/families/${f.slug}/jobs/${job}`); if (!on) return; setSt(s); if (["done", "error", "refused"].includes(s.status)) { clearInterval(t); if (s.status === "done") onDone && onDone(); } } catch (e) { setErr(e.message); clearInterval(t); } }, 1500); return () => { on = false; clearInterval(t); }; }, [job]);
  const upload = (key) => async (file) => { const fd = new FormData(); fd.append("file", file); try { const r = await api(`/api/families/${f.slug}/upload`, { method: "POST", body: fd }); setVals((v) => ({ ...v, [key]: r.name })); setFiles((x) => ({ ...x, [key]: { name: r.name, url: URL.createObjectURL(file) } })); } catch (e) { setErr(e.message); } };
  const run = async () => { setErr(""); setSt({ status: "queued", step: "Sending" }); try { const r = await post(`/api/families/${f.slug}/templates/${encodeURIComponent(tid)}/run`, { values: vals }); setJob(r.job); } catch (e) { setErr(e.message); setSt(null); } };
  const busy = st && !["done", "error", "refused"].includes(st.status);
  const openGraph = () => { dispatchEvent(new CustomEvent("studio-graph", { detail: { goal: f.family, prompt: st.prompt || form.title, family_job: `${f.slug}/${job}` } })); };
  return html`<div class="fcardx" ref=${ref}><div class="frow" style="margin-bottom:10px"><b style="font-size:15px">${form ? form.title : tid}</b><span class="grow" style="flex:1"></span><button class="btn small" onClick=${onClose}>Close</button></div>
    ${!form && !err && html`<p class="small">Building the form</p>`}${err && html`<p class="small" style="color:var(--err)">${err}</p>`}
    ${form && html`<div class="fform"><div class="fields">
      ${form.desc && html`<p class="fnote" style="margin:0">${form.desc}</p>`}
      ${form.inputs.filter((i) => i.type !== "unsupported").map((i) => i.type === "image" || i.type === "video" ? html`<${Drop} label=${i.label} accept=${i.type === "image" ? "image/png,image/jpeg,image/webp" : "video/mp4,video/quicktime,video/webm"} file=${files[i.key]} onFile=${upload(i.key)}/>` : html`<div class="field"><label>${i.label}</label>
        ${i.type === "choice" ? html`<select value=${vals[i.key] ?? ""} onChange=${(e) => setVals({ ...vals, [i.key]: e.target.value })} aria-label=${i.label}>${(i.options || (vals[i.key] != null ? [vals[i.key]] : [])).map((o) => html`<option value=${o}>${o}</option>`)}</select>` :
        i.type === "number" ? html`<input type="text" inputmode="decimal" value=${vals[i.key] ?? ""} onInput=${(e) => setVals({ ...vals, [i.key]: e.target.value === "" || isNaN(+e.target.value) ? e.target.value : +e.target.value })} aria-label=${i.label}/>` :
        i.type === "bool" ? html`<input type="checkbox" checked=${!!vals[i.key]} onChange=${(e) => setVals({ ...vals, [i.key]: e.target.checked })} aria-label=${i.label}/>` :
        html`<textarea value=${vals[i.key] ?? ""} onInput=${(e) => setVals({ ...vals, [i.key]: e.target.value })} aria-label=${i.label}></textarea>`}</div>`)}
      ${form.inputs.length === 0 && html`<p class="fnote" style="margin:0">This template runs with its own settings.</p>`}
      ${form.problems.length > 0 && html`<p class="fnote">The converter could not carry over: ${form.problems.slice(0, 2).join("; ")}</p>`}
      ${form.unknown_nodes.length > 0 && html`<p class="fnote">Needs nodes this ComfyUI does not have: ${form.unknown_nodes.slice(0, 5).join(", ")}.</p>`}
      <div class="frow"><button class="btn primary" style="padding:10px 18px" disabled=${busy || !form.ready} onClick=${run}>${busy ? "Running" : f.up ? "Run" : "Start and run"}</button><span class="fnote">about ${form.need_gb} GB VRAM${f.up ? "" : ", starts this family's server first"}</span></div>
      ${!form.ready && form.missing.length > 0 && html`<p class="fnote">Missing ${form.missing.length} file${form.missing.length > 1 ? "s" : ""}, so it cannot run yet.</p>`}
    </div><div class="fresult">
      ${st && st.status === "refused" && html`<${Gate} refusal=${st} onFreed=${() => setSt(null)}/>`}
      ${busy && html`<div class="fcardx"><p style="margin:0"><b>${st.step || st.status}</b></p><p class="fnote" style="margin:4px 0 0">${st.elapsed ? Math.round(st.elapsed) + " s" : ""}</p></div>`}
      ${st && st.status === "error" && html`<p class="small" style="color:var(--err)">${st.error}</p>`}
      ${st && st.status === "done" && html`<div>${(st.files || []).map((x) => x.kind === "video" ? html`<video src=${x.url} controls autoplay loop muted playsinline></video>` : x.kind === "audio" ? html`<audio src=${x.url} controls></audio>` : x.kind === "image" ? html`<img src=${x.url} alt=${st.prompt || form.title}/>` : html`<p class="small"><a href=${x.url} download>${x.filename}</a></p>`)}
        <p class="fnote">${st.seconds} s, ran on ${f.family}'s own server. Saved to your Library.</p><div class="frow"><a class="btn small" href="#library">Open the Library</a><button class="btn small" onClick=${openGraph}>Open the graph</button></div></div>`}
    </div></div>`}</div>`;
}

function Media({ item }) {
  if (item.kind === "video") return html`<video key=${item.src} src=${item.src} poster=${item.poster} controls muted loop playsinline autoplay></video>`;
  if (item.kind === "audio") return html`<audio key=${item.src} src=${item.src} controls></audio>`;
  return html`<img key=${item.src} src=${item.src || item.poster} alt=${item.prompt || ""}/>`;
}

function FamilyPage({ slug, goTab }) {
  const [f, setF] = useState(null), [err, setErr] = useState(""), [pick, setPick] = useState(0), [busy, setBusy] = useState(""), [gate, setGate] = useState(null), [msg, setMsg] = useState(""), [tid, setTid] = useState(() => { try { const x = sessionStorage.getItem("family_tpl"); sessionStorage.removeItem("family_tpl"); return x; } catch { return null; } }), [portrait, setPortrait] = useState(true), [dl, setDl] = useState(null);
  const load = () => api("/api/families/" + slug).then(setF).catch((e) => setErr(e.message));
  useEffect(() => { setF(null); setPick(0); setGate(null); setMsg(""); setTid(null); setPortrait(true); load(); scrollTo({ top: 0 }); }, [slug]);
  useEffect(() => { const t = setInterval(load, 15000); return () => clearInterval(t); }, [slug]);
  useEffect(() => { if (!dl || dl.status !== "running") return; const t = setInterval(() => api("/api/families/downloads/state").then((s) => { setDl(s); if (s.status !== "running") load(); }).catch(() => {}), 3000); return () => clearInterval(t); }, [dl && dl.status]);
  if (!f) return html`<div class="fpage"><button class="btn small fback" onClick=${() => goTab("families")}>All families</button><p class="small">${err || "Reading this family"}</p></div>`;
  const start = async (need, then) => { setBusy("start"); setGate(null); setMsg(""); try { const r = await post(`/api/families/${f.slug}/start`, need ? { need_gb: need } : {}); if (r.status === "refused") setGate(r); else { setMsg(r.status === "started" ? `Started in ${r.secs} s on port ${r.port}.` : r.status === "already running" ? `Running on port ${r.port}.` : `Could not start: ${r.reason || r.status}`); if (then && (r.status === "started" || r.status === "already running")) then(r.port); } await load(); } catch (e) { setMsg(e.message); } setBusy(""); };
  const stop = async () => { setBusy("stop"); setMsg(""); try { await post(`/api/families/${f.slug}/stop`, {}); setMsg("Stopped."); await load(); } catch (e) { setMsg(e.message); } setBusy(""); };
  const comfyUrl = (p) => `${location.protocol}//${location.hostname}:${p}/`;
  const openGraph = () => { if (f.up) { window.open(comfyUrl(f.port), "_blank", "noopener"); return; } const w = window.open("about:blank", "_blank"); start(1.5, (p) => { if (w) w.location = comfyUrl(p); }).then(() => { if (w && w.location.href === "about:blank") w.close(); }); };
  const download = async (t) => { setMsg(""); try { setDl(await post(`/api/families/${f.slug}/templates/${encodeURIComponent(t.name)}/download`, { confirm: true })); } catch (e) { setMsg(e.message); } };
  const media = f.media || [], cur = media[Math.min(pick, media.length - 1)], ready = f.templates_list.filter((t) => t.ready);
  return html`<div class="fpage">
    <button class="btn small fback" onClick=${() => goTab("families")}>All families</button>
    <div class="sect"><h2>${f.family}</h2><div class="sectsub">${[KIND_LABEL[f.kind], f.era && "from about " + f.era, f.licence || "licence not on file here: check the model page"].filter(Boolean).join(" | ")}</div></div>
    <div class="fhead"><div>
      <div class="fstage">${cur ? html`<${Media} item=${cur}/>` : html`<div class="fnone"><b>${f.state === "download" ? "Download its files first" : "No render yet"}</b>${f.state === "download" ? "This family has no model files on this machine, so there is nothing real to show. What it needs is listed below." : f.templates_ready > 0 ? "Its models are here and a template is ready. Run one below and the result lands in your Library." : "Its models are here but no template here runs it yet. Open its graph to wire it up by hand."}</div>`}</div>
      ${media.length > 1 && html`<div class="fthumbs">${media.map((m, i) => html`<button class=${i === pick ? "on" : ""} onClick=${() => setPick(i)} aria-label=${"sample " + (i + 1)}>${m.kind === "audio" ? html`<span style="display:grid;place-items:center;height:100%;color:var(--a2)">♫</span>` : html`<img src=${m.poster || m.src} alt="" loading="lazy"/>`}</button>`)}</div>`}
      ${cur && html`<p class="fnote" style="margin:8px 0 0">${cur.prompt}${cur.seconds ? ` | ${cur.seconds} s` : ""}${cur.peak_vram_gib ? ` | ${cur.peak_vram_gib} GB peak` : ""}${cur.note ? html`<br/>${cur.note}` : ""}</p>`}
    </div><div class="fside">
      <div class="fcardx"><h3>This family's server</h3><p><span class=${"fdot" + (f.up ? " up" : "")}></span>${f.up ? `Running on port ${f.port}` : f.generated ? `Stopped. Port ${f.port} when it runs` : "No instance file yet"}${f.queue && f.queue.busy ? ", busy" : ""}</p>
        <dl class="ffact"><dt>State</dt><dd>${f.state_label}</dd><dt>VRAM</dt><dd>about ${f.est_vram_gb ?? "?"} GB for its largest set, ${f.free_gb ?? "?"} GB free, ${f.floor_gb} GB stays free</dd><dt>Nodes</dt><dd>${f.nodes_live ?? f.nodes ?? "not counted yet"}${f.psn_nodes ? `, ${f.psn_nodes} of them ours` : ""}</dd><dt>Models</dt><dd>${f.models.files} files, ${f.models.gb} GB on this machine</dd></dl>
        <div class="frow" style="margin-top:10px">${f.up ? html`<button class="btn small" disabled=${!!busy} onClick=${stop}>${busy === "stop" ? "Stopping" : "Stop"}</button>` : html`<button class="btn primary small" disabled=${!!busy || !f.generated} onClick=${() => start()}>${busy === "start" ? "Starting" : "Start"}</button>`}<button class="btn small" disabled=${!!busy || !f.generated} onClick=${openGraph}>Open its graph</button></div>
        ${msg && html`<p class="fnote" style="margin:8px 0 0">${msg}</p>`}<p class="fnote" style="margin:8px 0 0">Its own ComfyUI, in the black, gold and green theme. It stops by itself when idle.</p></div>
      ${gate && html`<${Gate} refusal=${gate} onFreed=${load}/>`}
      ${f.crew && f.crew.id && html`<div class="fcardx"><h3>Its crew member</h3><div class="fcrew">${portrait ? html`<img src=${`crew/${f.crew.id}.webp`} alt="" onError=${() => setPortrait(false)}/>` : html`<span class="blank">☺</span>`}<div><b>${f.crew.name || "Comfy Prime"}</b><small>Knows this family and shows sources.</small><div style="margin-top:6px"><button class="btn small" onClick=${() => goTab("crew")}>Ask in Crew</button></div></div></div></div>`}
    </div></div>
    <section class="sect"><h2>What it is good at</h2><div class="fcardx" style="margin-top:10px">${f.what ? html`<p>${f.what}</p>${f.what_source && f.what_source !== "notes" && html`<p class="fnote">From ${f.what_source}.</p>`}` : html`<p class="fnote">No notes on file for this family yet.</p>`}${f.dossier && html`<p class="fnote">From the crew's dossier: ${f.dossier}</p>`}${f.wrap_note && html`<p class="fnote">${f.wrap_note}</p>`}</div></section>
    ${tid && html`<${Form} f=${f} tid=${tid} onClose=${() => setTid(null)} onDone=${load}/>`}
    <section class="sect"><h2>Templates</h2><div class="sectsub">${f.templates_list.length ? `${ready.length} of ${f.templates_list.length} can run here now. Each one opens as a form and runs on this family's own server.` : "No official template names this family yet. Open its graph to build one by hand."}${f.goals.length > 0 && html` Also in Create: ${f.goals.map((g, i) => html`${i ? ", " : ""}<a href="#create" onClick=${(e) => { e.preventDefault(); goTab("create"); setTimeout(() => dispatchEvent(new CustomEvent("prime-action", { detail: { type: "set_goal", goal: g.id } })), 90); }}>${g.label}</a>`)}.`}</div>
      ${dl && html`<p class="fnote">${dl.status === "running" ? `Downloading ${dl.file} (${dl.done + 1} of ${dl.total})` : dl.status === "done" ? "Download finished." : dl.status === "error" ? "Download failed: " + dl.error : ""}</p>`}
      <div class="ftpls">${f.templates_list.map((t) => html`<div class=${"ftpl" + (tid === t.name ? " on" : "")}><b>${t.title}</b>${t.desc && html`<p>${t.desc}</p>`}
        ${t.ready ? html`<small class="ok">Ready, about ${t.need_gb} GB VRAM</small>` : html`<div><small class="no">Needs ${t.missing.length} file${t.missing.length > 1 ? "s" : ""}${t.missing_gb ? `, ${t.missing_gb} GB` : t.gb ? `, template total ${t.gb} GB` : ""}</small><ul class="fmiss">${t.missing.slice(0, 4).map((m) => html`<li>${m.url ? html`<a href=${m.url} target="_blank" rel="noopener noreferrer">${m.name}</a>` : m.name}${m.gb ? ` (${m.gb} GB)` : ""}</li>`)}${t.missing.length > 4 && html`<li>and ${t.missing.length - 4} more</li>`}</ul></div>`}
        <div class="frow"><button class=${"btn small" + (t.ready ? " primary" : "")} onClick=${() => setTid(t.name)}>${t.ready ? "Open the form" : "See the form"}</button>${!t.ready && t.missing.some((m) => m.url) && html`<button class="btn small" disabled=${dl && dl.status === "running"} onClick=${() => download(t)}>Download</button>`}</div></div>`)}</div></section>
    <section class="sect"><h2>On this machine</h2><div class="fcardx" style="margin-top:10px">
      ${f.biggest.length ? html`<ul class="fmiss">${f.biggest.map((b) => html`<li>${b.name} (${b.gb} GB)</li>`)}</ul>` : html`<p class="fnote">No model files for this family on this machine.</p>`}
      ${f.repos.length === 0 && html`<p class="fnote" style="margin-top:8px">Source link coming soon.</p>`}${f.repos.length > 0 && html`<p class="fnote" style="margin-top:8px">Source: ${f.repos.map((r, i) => html`${i ? ", " : ""}<a href=${"https://huggingface.co/" + r} target="_blank" rel="noopener noreferrer">${r}</a>`)}</p>`}
      ${f.packs.length > 0 && html`<p class="fnote">Its own node packs: ${f.packs.join(", ")}</p>`}${f.packs_missing.length > 0 && html`<p class="fnote">Node packs not installed: ${f.packs_missing.join(", ")}</p>`}
      ${f.test && (f.test.tested || f.test.note) && html`<p class="fnote" style="margin-top:8px">Last test${f.test.tested ? ` at ${f.test.tested}` : ""}: ${f.state_label.toLowerCase()}${f.test.tpl ? `, template ${f.test.tpl}` : ""}${f.test.secs ? `, ${f.test.secs} s` : ""}${f.test.peak_gib ? `, ${f.test.peak_gib} GB peak` : ""}${f.test.note ? `. ${f.test.note}` : ""}</p>`}</div></section>
  </div>`;
}

export function Families({ route, goTab }) {
  const slug = String(route || "").split("/")[1];
  return slug ? html`<${FamilyPage} slug=${slug} goTab=${goTab}/>` : html`<${Gallery} onOpen=${(s) => goTab("families/" + s)}/>`;
}
