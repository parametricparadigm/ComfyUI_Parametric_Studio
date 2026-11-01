import { useState, useEffect, useRef } from "preact/hooks";
import { html, api, post } from "./common.js";

const KEY = "shotboard_v1";
const CAMERAS = ["orbit_right", "orbit_left", "dolly_in", "dolly_out", "crane_up", "crane_down", "pan_left", "pan_right", "tilt_up", "tracking", "handheld"];
const TRANSFORMS = [
  { id: "reshoot", label: "Reshoot", goal: "reshoot", about: "A new camera move on the same scene (MiniMax H3)." },
  { id: "orbit", label: "Orbit 360", goal: "orbit360", about: "Frozen time, full turn around one frame (MiniMax H3)." },
  { id: "recast", label: "Recast", goal: "recast", about: "Your character takes the lead, same walk and set (MiniMax H3).", needsCharacter: true },
  { id: "water", label: "VFX: water", goal: "vfx_ltx", options: { effect: "water", intensity: "natural" }, about: "Adds water to the scene (LTX-2.5)." },
  { id: "plate", label: "VFX: clean plate", goal: "vfx_ltx", options: { effect: "clean_plate" }, about: "Paints people out (LTX-2.5). Check the last frames: traces can remain when a subject fills the shot." },
  { id: "night", label: "VFX: day to night", goal: "vfx_ltx", options: { effect: "day_to_night", intensity: "natural" }, about: "Relights the clip as night (LTX-2.5)." },
  { id: "matte", label: "VFX: matte", goal: "vfx_ltx", options: { effect: "matte" }, about: "A black and white matte for compositing (LTX-2.5)." },
];
const inputUrl = (name) => "/api/view?" + new URLSearchParams({ filename: name, type: "input" });
const load = () => { try { return JSON.parse(localStorage.getItem(KEY)) || {}; } catch { return {}; } };
// A job's file list can echo the uploaded source; only a video the job saved counts as its result.
export const resultVideo = (files) => (files || []).filter((f) => /\.(mp4|webm|mov)$/i.test(f.filename) && f.type !== "input" && !/^studio_/.test(f.filename)).pop();

export function buildBody(t, { source, character, scene, camera, seed }) {
  const options = t.id === "reshoot" ? { camera } : t.options || {};
  const body = { goal: t.goal, prompt: "", seed, options, video: source.name };
  if (t.goal === "vfx_ltx" && scene) body.scene = scene;
  if (t.needsCharacter) body.image = character.name;
  return body;
}

export function ShotBoard() {
  const saved = useRef(load()).current;
  const [source, setSource] = useState(saved.source || null), [character, setCharacter] = useState(saved.character || null), [scene, setScene] = useState(saved.scene || "");
  const [camera, setCamera] = useState(saved.camera || "orbit_right"), [picked, setPicked] = useState(saved.picked || { reshoot: true, orbit: true, water: true, night: true, matte: true });
  const [jobs, setJobs] = useState(saved.jobs || []), [exported, setExported] = useState(saved.exported || null), [err, setErr] = useState(""), [busy, setBusy] = useState(""), [lib, setLib] = useState([]), [, setClock] = useState(0);
  const inFlight = useRef(false), latest = useRef(jobs); latest.current = jobs;

  useEffect(() => { try { localStorage.setItem(KEY, JSON.stringify({ source, character, scene, camera, picked, jobs, exported })); } catch {} }, [source, character, scene, camera, picked, jobs, exported]);
  useEffect(() => { api("/api/history?limit=60").then((h) => setLib((h || []).map((r) => ({ ...r, video: resultVideo(r.files) })).filter((r) => r.video).slice(0, 12))).catch(() => {}); }, []);

  useEffect(() => {
    const change = (id, patch) => setJobs((js) => js.map((j) => (j.id === id ? { ...j, ...patch } : j)));
    const step = async () => {
      setClock((c) => c + 1);
      if (inFlight.current) return;
      const js = latest.current, run = js.find((j) => j.status === "running"), next = js.find((j) => j.status === "queued");
      if (!run && !next) return;
      inFlight.current = true;
      try {
        if (run) {
          const s = await api("/api/jobs/" + run.job);
          if (s.status === "done") change(run.id, { status: "done", files: s.files || [], seconds: Math.round((Date.now() - run.started) / 1000) });
          else if (s.status === "error") change(run.id, { status: "error", error: s.error || "The render failed." });
        } else {
          try {
            const r = await post("/api/generate", next.body);
            change(next.id, { status: "running", job: r.job, seed: r.seed, graphHash: r.graph_hash, started: Date.now() });
          } catch (e) { change(next.id, { status: "error", error: e.message }); }
        }
      } catch (e) { if (run && /404|no such/i.test(e.message)) change(run.id, { status: "error", error: e.message }); } finally { inFlight.current = false; }
    };
    const t = setInterval(step, 2500); step(); return () => clearInterval(t);
  }, []);

  const send = async (file) => { const fd = new FormData(); fd.append("file", file); return (await api("/api/upload", { method: "POST", body: fd })).name; };
  const useFile = async (f, set, what) => { if (!f) return; setBusy(what); setErr(""); try { const name = await send(f); set({ name, label: f.name, url: inputUrl(name) }); } catch (e) { setErr(e.message); } setBusy(""); };
  const fromLibrary = async (r) => { setBusy("clip"); setErr(""); try { const blob = await (await fetch(r.video.url)).blob(); const name = await send(new File([blob], r.video.filename, { type: blob.type || "video/mp4" })); setSource({ name, label: r.prompt || r.video.filename, url: inputUrl(name) }); } catch (e) { setErr(e.message); } setBusy(""); };

  const chosen = TRANSFORMS.filter((t) => picked[t.id]);
  const active = jobs.some((j) => j.status === "queued" || j.status === "running");
  const blocked = !source ? "Add a clip first." : !chosen.length ? "Pick at least one job." : chosen.some((t) => t.needsCharacter) && !character ? "Recast needs a character picture." : active ? "This board is still rendering." : "";
  const start = () => { const seed = Math.floor(Math.random() * 2 ** 31); setExported(null); setJobs(chosen.map((t) => ({ id: t.id, label: t.id === "reshoot" ? `Reshoot: ${camera.replace(/_/g, " ")}` : t.label, status: "queued", seed, body: buildBody(t, { source, character, scene, camera, seed }) }))); };
  const retry = (id) => setJobs((js) => js.map((j) => (j.id === id ? { ...j, status: "queued", error: "", job: null, files: null } : j)));
  const graph = (j) => dispatchEvent(new CustomEvent("studio-graph", { detail: { ...j.body, seed: j.seed } }));
  const finished = jobs.filter((j) => j.status === "done" && resultVideo(j.files));
  const doExport = async () => { setBusy("export"); setErr(""); try { setExported(await post("/api/shotboard/export", { items: [{ filename: source.name, type: "input", label: "Source" }, ...finished.map((j) => { const f = resultVideo(j.files); return { filename: f.filename, subfolder: f.subfolder, type: "output", label: j.label }; })] })); } catch (e) { setErr(e.message); } setBusy(""); };
  const reset = () => { setJobs([]); setExported(null); };
  const done = jobs.filter((j) => j.status === "done").length;

  return html`<div class="shotboard">
    <section class="card" style="margin-bottom:16px"><h3 style="margin-top:0">One clip in. A whole shoot out.</h3>
      <p class="small" style="margin:0 0 12px">Each job runs on your GPU, one at a time. Keep this tab open while they run; if you reload or come back to this page, the queue picks up where it left off. Every result keeps its exact graph and seed.</p>
      <div class="row" style="flex-wrap:wrap;gap:16px;align-items:flex-start">
        <label class="small" style="min-width:260px">Your clip<div style="margin-top:4px"><input type="file" accept="video/mp4,video/webm,video/quicktime,video/x-matroska" onChange=${(e) => useFile(e.target.files[0], setSource, "clip")}/></div></label>
        <label class="small" style="min-width:260px">Character picture, for Recast<div style="margin-top:4px"><input type="file" accept="image/png,image/jpeg,image/webp" onChange=${(e) => useFile(e.target.files[0], setCharacter, "character")}/></div>${character && html`<img src=${character.url} alt="Your character" style="display:block;height:64px;margin-top:6px;border-radius:6px"/>`}</label>
        <label class="small" style="flex:1;min-width:260px">What the clip shows, for VFX<input type="text" value=${scene} onInput=${(e) => setScene(e.target.value)} placeholder="a wet cobblestone street at dusk" style="display:block;width:100%;margin-top:4px"/></label>
      </div>
      ${lib.length > 0 && html`<div class="small" style="margin-top:14px">Or pick one from your Library<div class="row" style="gap:8px;overflow-x:auto;margin-top:6px;padding-bottom:4px">${lib.map((r) => html`<button class="btn small" title=${r.prompt || r.video.filename} onClick=${() => fromLibrary(r)} style="padding:0;overflow:hidden;flex:none"><video src=${r.video.url} muted preload="metadata" style="display:block;width:112px;height:63px;object-fit:cover"></video></button>`)}</div></div>`}
      <div class="chips" style="margin-top:16px">${TRANSFORMS.map((t) => html`<button class=${"chip" + (picked[t.id] ? " on" : "")} title=${t.about} aria-pressed=${!!picked[t.id]} onClick=${() => setPicked({ ...picked, [t.id]: !picked[t.id] })}>${t.label}</button>`)}</div>
      ${picked.reshoot && html`<label class="small" style="display:inline-block;margin-top:10px">Reshoot camera <select value=${camera} onChange=${(e) => setCamera(e.target.value)}>${CAMERAS.map((c) => html`<option value=${c}>${c.replace(/_/g, " ")}</option>`)}</select></label>`}
      <div class="row" style="margin-top:14px;gap:10px;flex-wrap:wrap;align-items:center">
        <button class="btn primary" disabled=${!!blocked || !!busy} onClick=${start}>Run ${chosen.length} job${chosen.length === 1 ? "" : "s"}</button>
        ${jobs.length > 0 && !active && html`<button class="btn" onClick=${reset}>Clear the board</button>`}
        ${finished.length > 0 && !active && html`<button class="btn" disabled=${!!busy} onClick=${doExport}>${busy === "export" ? "Exporting..." : "Export contact video"}</button>`}
        <span class="small">${busy && busy !== "export" ? `Uploading your ${busy}...` : blocked}${jobs.length > 0 ? ` ${done} of ${jobs.length} done.` : ""}</span>
      </div>
      ${err && html`<p class="small" role="alert" style="color:#e88;margin:10px 0 0">${err}</p>`}
    </section>
    ${exported && html`<section class="card" style="margin-bottom:16px"><h3 style="margin-top:0">Contact video</h3><video src=${exported.url} controls loop playsinline style="width:100%;border-radius:8px"></video><p class="small" style="margin:8px 0 0"><a href=${exported.url} download=${exported.filename}>Download ${exported.filename}</a></p></section>`}
    ${source && html`<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px">
      <article class="card" style="margin:0"><video src=${source.url} controls muted loop playsinline preload="metadata" style="width:100%;aspect-ratio:16/9;background:#000;border-radius:6px"></video><div style="margin-top:8px"><b>Source</b></div><div class="small" style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${source.label}</div></article>
      ${jobs.map((j) => { const v = resultVideo(j.files); return html`<article class="card" style="margin:0" key=${j.id}>
        ${v ? html`<video src=${v.url} controls muted loop playsinline preload="metadata" style="width:100%;aspect-ratio:16/9;background:#000;border-radius:6px"></video>` : html`<div class="rstage" style="position:relative;aspect-ratio:16/9;display:grid;place-items:center;border-radius:6px;overflow:hidden;background:#000">${j.status === "running" && html`<div class="shimmer"></div>`}<span class="small" style="position:relative;padding:12px;text-align:center">${j.status === "queued" ? "Queued" : j.status === "running" ? `Rendering ${j.started ? Math.round((Date.now() - j.started) / 1000) : 0}s` : j.error || "No video came back."}</span></div>`}
        <div style="margin-top:8px"><b>${j.label}</b></div>
        <div class="small">${j.seed != null && html`seed ${j.seed}`}${j.seconds != null && html` · ${j.seconds}s`}</div>
        <div class="row" style="gap:8px;margin-top:8px;flex-wrap:wrap"><button class="btn small" onClick=${() => graph(j)}>See the graph</button>${v && html`<a class="btn small" href=${v.url} download=${v.filename}>Download</a>`}${j.status === "error" && html`<button class="btn small" onClick=${() => retry(j.id)}>Try again</button>`}</div>
      </article>`; })}
    </div>`}
  </div>`;
}
