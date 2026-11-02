/* Models layer: what every goal and AI-edit tool needs, whether this machine has it, and one-press downloads with live progress. One small store is shared by the Models page, AI Edits and the Create panel, so a download started anywhere shows everywhere. */
import { useState, useEffect } from "preact/hooks";
import { html, api, post } from "./common.js";
import { LiveMedia, useShowcase, LicBadge } from "./showcase.js";
import { Stats } from "./look.js";

const store = { ready: null, dl: { state: "idle" }, err: "", subs: new Set(), timer: 0, tries: 0 };
const emit = () => store.subs.forEach((f) => f());
const busy = () => store.dl.state === "running" || store.dl.state === "cancelling";
async function loadReady() { try { store.ready = await api("/api/models/readiness"); store.dl = store.ready.download; store.err = ""; } catch (e) { store.err = e.message; } emit(); schedule(); }
function schedule() {
  clearTimeout(store.timer); const sizing = store.ready && Object.values(store.ready.edits || {}).some((e) => e.sizes_pending) && store.tries < 5;
  if (busy()) store.timer = setTimeout(tick, 1200); else if (sizing) { store.tries++; store.timer = setTimeout(loadReady, 3000); }
}
async function tick() { const was = busy(); try { store.dl = await api("/api/models/download"); } catch {} if (was && !busy()) return loadReady(); emit(); schedule(); }
export async function startDownload(body) { store.err = ""; try { await post("/api/models/download", body); store.dl = { state: "running", ...body, done: 0, cur: 0 }; emit(); await tick(); } catch (e) { store.err = e.message; emit(); } }
export async function cancelDownload() { try { store.dl = await post("/api/models/download/cancel", {}); } catch {} emit(); schedule(); }
export function useModels() {
  const [, bump] = useState(0);
  useEffect(() => { const f = () => bump((n) => n + 1); store.subs.add(f); if (!store.ready) loadReady(); else schedule(); return () => store.subs.delete(f); }, []);
  return { ready: store.ready, dl: store.dl, err: store.err, refresh: loadReady };
}
export const gbText = (n) => (n == null ? "" : n >= 10 ? `${Math.round(n)} GB` : `${n.toFixed(1)} GB`);
const mine = (dl, kind, id) => dl && dl.kind === kind && dl.id === id;
const eta = (s) => (s == null ? "" : s > 3600 ? `${Math.round(s / 3600)} h left` : s > 90 ? `${Math.round(s / 60)} min left` : `${s}s left`);

/* the one status line under a download: progress while it runs, the reason when it stopped */
export function DlStatus({ dl, kind, id, err }) {
  const m = mine(dl, kind, id);
  if (m && (dl.state === "running" || dl.state === "cancelling")) return html`<div class="dlst"><div class="dlbar" role="progressbar" aria-valuenow=${dl.pct || 0} aria-valuemin="0" aria-valuemax="100"><i style=${{ width: `${dl.pct || 0}%` }}></i></div>
    <small>${dl.phase === "verifying" ? "Checking the file" : dl.state === "cancelling" ? "Stopping" : dl.note || `File ${dl.index} of ${dl.count}`}${dl.pct != null ? ` · ${dl.pct}%` : ""}${dl.mb_s ? ` · ${dl.mb_s} MB/s` : ""}${dl.eta_s ? ` · ${eta(dl.eta_s)}` : ""}</small></div>`;
  if (m && dl.state === "needs_license") return html`<small class="dlbad">${dl.error} <a href=${dl.license_url} target="_blank" rel="noopener noreferrer">Open the model page</a></small>`;
  if (m && dl.state === "error") return html`<small class="dlbad">${dl.error}</small>`;
  if (m && dl.state === "cancelled") return html`<small>Stopped. Press Resume to carry on where it left off.</small>`;
  return err ? html`<small class="dlbad">${err}</small>` : null;
}

/* Download / progress / cancel for one goal or edit tool; shows nothing when it is ready */
export function DlButton({ kind, id, row, small }) {
  const { dl, err } = useModels(); const run = busy() && mine(dl, kind, id), other = busy() && !run;
  if (!row || !row.known) return null;
  const body = kind === "goal" ? { goal: id } : { edit: id };
  if (row.ready && !run) return mine(dl, kind, id) && dl.state === "done" ? html`<small class="dlok">Downloaded</small>` : null;
  return html`<div class="dlbox" onClick=${(e) => e.stopPropagation()}>
    ${run ? html`<button class=${"btn" + (small ? " small" : "")} onClick=${cancelDownload} disabled=${dl.state === "cancelling"}>Cancel</button>`
      : row.downloadable > 0 ? html`<button class=${"btn primary" + (small ? " small" : "")} disabled=${other} title=${other ? "Another download is running" : "Download only the missing files"} onClick=${() => startDownload(body)}>${mine(dl, kind, id) && (dl.state === "cancelled" || dl.state === "error") ? "Resume" : "Download"}${row.missing_gb ? ` ${gbText(row.missing_gb)}` : ""}</button>` : null}
    ${row.manual && row.manual.length > 0 && html`<small class="dlbad">${row.manual.length} file${row.manual.length > 1 ? "s" : ""} with no download source here: ${row.manual.slice(0, 2).join(", ")}${row.manual.length > 2 ? "..." : ""}</small>`}
    ${row.gated && !run && html`<small>Gated model: accept its licence on <a href=${row.license_url} target="_blank" rel="noopener noreferrer">the model page</a>, then log in once with <code>hf auth login</code>.</small>`}
    <${DlStatus} dl=${dl} kind=${kind} id=${id} err=${mine(dl, kind, id) ? "" : err}/></div>`;
}

/* Create panel: when the chosen goal's models are missing, say what is needed and offer the download */
export function NeedsModels({ goal }) {
  const { ready, dl } = useModels(); const row = ready && ready.goals && ready.goals[goal];
  if (!row || !row.known || (row.ready && !(mine(dl, "goal", goal) && dl.state === "done"))) return null;
  return html`<div class="needs"><b>${row.ready ? "Models downloaded" : `Needs ${gbText(row.missing_gb) || "model files"} of models`}</b><small>${row.ready ? "Ready to generate." : `${row.missing} file${row.missing > 1 ? "s" : ""} missing on this machine. Only ${row.missing > 1 ? "those are" : "that is"} downloaded: ${(row.items || []).filter((x) => !x.present).map((x) => x.name).join(", ")}`}</small><${DlButton} kind="goal" id=${goal} row=${row} small/></div>`;
}

const flagOf = (row) => (!row || !row.known ? null : row.ready ? ["ok", "Ready"] : row.gated ? ["gate", "Gated"] : ["need", row.missing_gb ? `${gbText(row.missing_gb)} to get` : "Needs files"]);
export function GoalTiles({ goals }) {
  const { ready, err } = useModels(); const items = useShowcase();
  const list = Object.values(goals).sort((a, b) => (ready && ready.goals[b.id] && ready.goals[b.id].known ? 1 : 0) - (ready && ready.goals[a.id] && ready.goals[a.id].known ? 1 : 0) || (a.label > b.label ? 1 : -1));
  const known = ready ? list.filter((g) => ready.goals[g.id] && ready.goals[g.id].known) : [], nReady = known.filter((g) => ready.goals[g.id].ready).length;
  return html`<div>${ready && html`<div class="mo-tally"><${Stats} items=${[[list.length, "ways to create"], [`${nReady} of ${known.length}`, "ready, of those with a file list"], ...(ready.free_gb != null ? [[`${Math.round(ready.free_gb)} GB`, "free where models live"]] : [])]}/></div><p class="small" style="margin:0 0 12px">Models live in <code>${ready.root}</code>${ready.free_gb != null ? ` · ${Math.round(ready.free_gb)} GB free there` : ""}${!ready.comfy ? " · ComfyUI is not reachable, so this is a plain file check" : ""}. A download is refused unless ${ready.reserve_gb} GB stay free.</p>`}
    ${err && !ready && html`<p class="small" style="color:var(--err)">${err}</p>`}
    <p class="small" style="margin:0 0 12px">MiniMax H3 goals: its <a href="https://huggingface.co/MiniMaxAI/MiniMax-H3/raw/main/LICENSE" target="_blank" rel="noopener noreferrer">community licence</a> applies to you and your outputs, and it excludes the US, EU, UK and South Korea.</p>
    <div class="mgrid">${list.map((g) => { const row = ready && ready.goals[g.id], m = items.find((x) => x.goal === g.id && x.kind !== "audio"), cover = !m && items.find((x) => x.goal === g.id && x.kind === "audio" && x.poster), fl = flagOf(row);
      return html`<article class="gcard mcard" aria-label=${g.label}>${m ? html`<${LiveMedia} item=${m} cls="gmedia"/>` : cover ? html`<img class="gmedia" src=${cover.poster} alt="" loading="lazy"/>` : html`<div class="gmedia gblank"><em class="mo-glyph" aria-hidden="true">${String(g.label).split(/[\s:(]/)[0]}</em>${g.kind === "audio" ? "♫" : html`<small class="mo-norender">No render of this one here yet</small>`}</div>`}<span class="gshade"></span>
        ${fl && html`<span class=${"gflag " + fl[0]}>${fl[1]}</span>`}<${LicBadge} g=${g}/>
        <span class="gtext"><b>${g.label}</b><small>${g.family}${row && row.known ? ` · ${row.files} files${row.total_gb ? `, ${gbText(row.total_gb)}` : ""}` : ""}</small>
          ${row && !row.known && html`<small>File list not published yet</small>`}<${DlButton} kind="goal" id=${g.id} row=${row} small/></span></article>`; })}</div></div>`;
}

/* Attach another ComfyUI: test the address, see its GPU, node count and what it lacks, then switch the studio to it. The studio keeps the address; the browser stores nothing. */
export function AttachCard() {
  const [cur, setCur] = useState(null), [url, setUrl] = useState(""), [res, setRes] = useState(null), [busy, setBusy] = useState(""), [msg, setMsg] = useState("");
  const load = () => api("/api/models/attach").then((d) => { setCur(d); setUrl((u) => u || d.default_url); }).catch(() => {});
  useEffect(() => { load(); }, []);
  const run = async (what) => { setBusy(what); setMsg(""); try { const r = await post(what === "use" ? "/api/models/attach" : "/api/models/attach/test", { url }); setRes(r); if (r.ok === false) setMsg(r.error || "Could not reach ComfyUI at that address."); else if (what === "use") { setMsg("The studio now uses this ComfyUI."); await load(); loadReady(); } } catch (e) { setRes(null); setMsg(e.message); } setBusy(""); };
  const reset = async () => { setBusy("reset"); try { const d = await post("/api/models/attach/reset", {}); setCur(d); setUrl(d.url); setRes(null); setMsg("Back on the original ComfyUI."); loadReady(); } catch (e) { setMsg(e.message); } setBusy(""); };
  const lacking = res && res.ok ? res.goals.filter((g) => g.missing_models.length || g.missing_nodes.length) : [];
  return html`<div class="card attach"><h3>Use your own ComfyUI</h3><p class="small" style="margin:0 0 8px">Already running ComfyUI somewhere on this machine or your network? Point the studio at it. ${cur ? html`Now using <code>${cur.url}</code>.` : ""}</p>
    <div class="row" style="margin:0"><input type="text" value=${url} onInput=${(e) => setUrl(e.target.value)} placeholder="http://127.0.0.1:8188" aria-label="ComfyUI address" style="max-width:380px"/><button class="btn" disabled=${!url || busy} onClick=${() => run("test")}>${busy === "test" ? "Testing..." : "Test"}</button>
      <button class="btn primary" disabled=${!res || !res.ok || busy || res.url === (cur && cur.url)} onClick=${() => run("use")}>${busy === "use" ? "Switching..." : "Use this ComfyUI"}</button>${cur && cur.url !== cur.original_url && html`<button class="btn" disabled=${!!busy} onClick=${reset}>Use the original</button>`}</div>
    ${msg && html`<p class="small" style=${res && res.ok ? "margin:8px 0 0" : "color:var(--err);margin:8px 0 0"}>${msg}</p>`}
    ${res && res.ok && html`<div class="attres"><p class="small" style="margin:8px 0 4px"><b>Found it.</b> ${res.gpu.name || "GPU"} · ${res.gpu.vram_free_gb} of ${res.gpu.vram_total_gb} GB free · ${res.nodes} nodes · ComfyUI ${res.version || "?"}. ${res.ready_goals} of ${res.goals.length} ways to create are ready there.</p>
      ${lacking.length > 0 && html`<ul class="small" style="margin:0;padding-left:18px">${lacking.slice(0, 8).map((g) => html`<li><b>${g.label}</b>: ${g.missing_nodes.length ? `needs nodes ${g.missing_nodes.slice(0, 3).join(", ")}${g.missing_nodes.length > 3 ? "..." : ""}` : ""}${g.missing_nodes.length && g.missing_models.length ? "; " : ""}${g.missing_models.length ? `${g.missing_models.length} model file${g.missing_models.length > 1 ? "s" : ""} missing${g.missing_gb ? ` (${gbText(g.missing_gb)})` : ""}` : ""}</li>`)}${lacking.length > 8 ? html`<li>and ${lacking.length - 8} more</li>` : ""}</ul>`}</div>`}</div>`;
}

/* models whose weights are in the cloud right now: their graphs stay, one press brings the file back. Absent when rotation is off, and in the read-only demo */
export function CloudCard() {
  const [st, setSt] = useState(null), [msg, setMsg] = useState("");
  useEffect(() => {
    if (window.STUDIO_DEMO) return; let timer = 0, live = true;
    const load = async () => { try { const d = await api("/api/rotation/status"); if (!live) return; setSt(d); if (d.job && d.job.state === "running") timer = setTimeout(load, 2000); } catch {} };
    window.__rotationReload = load; load(); return () => { live = false; clearTimeout(timer); };
  }, []);
  if (!st || !st.enabled || !st.cloud.length) return null;
  const job = st.job || {}, running = job.state === "running";
  const go = async (path) => { setMsg(""); try { await post("/api/rotation/fetch", { path }); window.__rotationReload(); } catch (e) { setMsg(e.message); } };
  return html`<div class="card attach"><h3>In the cloud</h3><p class="small" style="margin:0 0 8px">These models keep their graphs here. Their weights come back with one press, and the checksum is checked before they count as installed.</p>
    ${st.cloud.map((c) => html`<div class="row" style="margin:0 0 6px;align-items:center"><span style="flex:1;min-width:0;overflow-wrap:anywhere">${c.name} · ${gbText(c.gb)}</span><span class="pill">In cloud, about ${c.eta_min} min</span><button class="btn" disabled=${running} onClick=${() => go(c.path)}>${running && job.path === c.path ? "Fetching..." : "Fetch"}</button></div>`)}
    ${job.state === "error" && html`<p class="small" style="color:var(--err);margin:8px 0 0">${job.error}</p>`}${msg && html`<p class="small" style="color:var(--err);margin:8px 0 0">${msg}</p>`}
    ${!st.rate_measured && html`<p class="small" style="margin:8px 0 0">Times are a rough guess until the first fetch has been measured.</p>`}</div>`;
}
