import { useState, useEffect, useRef } from "preact/hooks";
import { html, api, post } from "./common.js";
import { applyPatch, cancelOpen, canRetry, stoppedStatus } from "./shotboard_logic.js";

const KEY = "shotboard_v1";
import { Board } from "./shotboard_view.js";
const CAMERAS = ["orbit_right", "orbit_left", "dolly_in", "dolly_out", "crane_up", "crane_down", "pan_left", "pan_right", "tilt_up", "tracking", "handheld"];
const TRANSFORMS = [
  { id: "reshoot", label: "Reshoot", goal: "reshoot", about: "A new camera move on the same scene (MiniMax H3)." },
  { id: "orbit", label: "Orbit 360", goal: "orbit360", about: "Frozen time, full turn around one frame (MiniMax H3)." },
  { id: "recast", label: "Recast", goal: "recast", about: "Your character takes the lead, same walk and set (MiniMax H3).", needsCharacter: true },
  { id: "water", label: "VFX: water", goal: "vfx_ltx", options: { effect: "water" }, strength: true, words: { label: "The water", placeholder: "a fast flood of clear water up to the knees" }, about: "Adds water to the scene (LTX-2.5)." },
  { id: "plate", label: "VFX: clean plate", goal: "vfx_ltx", options: { effect: "clean_plate" }, words: { label: "The empty place", placeholder: "parked bicycles by the doors" }, about: "Paints people out (LTX-2.5). Check the last frames: traces can remain when a subject fills the shot." },
  { id: "night", label: "VFX: day to night", goal: "vfx_ltx", options: { effect: "day_to_night" }, strength: true, words: { label: "The night", placeholder: "cold blue moonlight, warm lamps in the windows" }, about: "Relights the clip as night (LTX-2.5)." },
  { id: "transition", label: "Transition", goal: "ltx_transition", needsSecond: true, about: "LTX-2.5 bridges the end of your clip into the start of a second clip, joined into one take." },
  { id: "matte", label: "VFX: matte", goal: "vfx_ltx", options: { effect: "matte" }, about: "A black and white matte for compositing (LTX-2.5). One click turns it into a cutout of your clip with real alpha (ProRes 4444)." },
];
const inputUrl = (name) => "/api/view?" + new URLSearchParams({ filename: name, type: "input" });
const load = () => { try { return JSON.parse(localStorage.getItem(KEY)) || {}; } catch { return {}; } };
// A job's file list can echo the uploaded source; only a video the job saved counts as its result.
export const resultVideo = (files) => (files || []).filter((f) => /\.(mp4|webm|mov)$/i.test(f.filename) && f.type !== "input" && !/^studio_/.test(f.filename)).pop();

// VFX settings a board can change. Sizes and strengths are the studio's own option names (studio/goals.py: VFX_SIZES, VFX_INTENSITY).
export const VFX_QUALITY = [{ value: "draft", label: "Draft, 768x448 (fastest)" }, { value: "standard", label: "Standard, 960x544" }, { value: "high", label: "High, 1280x704 (720p)" }];
export const VFX_STRENGTH = [{ value: "auto", label: "Auto (our tested pick)" }, { value: "natural", label: "Natural" }, { value: "strong", label: "Strong" }, { value: "max", label: "Max" }];
export const DEFAULT_VFX = { quality: "standard", water: { intensity: "auto", text: "" }, night: { intensity: "auto", text: "" }, plate: { text: "" } };

export function buildBody(t, { source, character, second, scene, camera, seed, vfx = DEFAULT_VFX }) {
  const mine = (vfx && vfx[t.id]) || {};
  const options = t.id === "reshoot" ? { camera } : t.goal === "vfx_ltx" ? { ...t.options, quality: (vfx && vfx.quality) || "standard", ...(t.strength ? { intensity: mine.intensity || "auto" } : {}) } : t.options || {};
  const body = { goal: t.goal, prompt: t.words ? String(mine.text || "").trim() : "", seed, options, video: source.name };
  if (t.goal === "vfx_ltx" && scene) body.scene = scene;
  if (t.needsCharacter) body.image = character.name;
  if (t.needsSecond && second) body.video_b = second.name;
  return body;
}

export function jobLabel(t, camera, vfx = DEFAULT_VFX) {
  if (t.id === "reshoot") return `Reshoot: ${camera.replace(/_/g, " ")}`;
  if (t.goal !== "vfx_ltx") return t.label;
  const bits = [t.strength && (vfx[t.id] || {}).intensity && vfx[t.id].intensity !== "auto" ? vfx[t.id].intensity : "", vfx.quality && vfx.quality !== "standard" ? vfx.quality : ""].filter(Boolean);
  return bits.length ? `${t.label} (${bits.join(", ")})` : t.label;
}

export function ShotBoard() {
  const saved = useRef(load()).current;
  const [source, setSource] = useState(saved.source || null), [character, setCharacter] = useState(saved.character || null), [scene, setScene] = useState(saved.scene || "");
  const [vfx, setVfx] = useState({ ...DEFAULT_VFX, ...(saved.vfx || {}) }), [second, setSecond] = useState(saved.second || null);
  const [camera, setCamera] = useState(saved.camera || "orbit_right"), [picked, setPicked] = useState(saved.picked || { reshoot: true, orbit: true, water: true, night: true, matte: true });
  const [jobs, setJobs] = useState(saved.jobs || []), [exported, setExported] = useState(saved.exported || null), [err, setErr] = useState(""), [busy, setBusy] = useState(""), [lib, setLib] = useState([]), [, setClock] = useState(0);
  const inFlight = useRef(false), latest = useRef(jobs); latest.current = jobs;

  useEffect(() => { try { localStorage.setItem(KEY, JSON.stringify({ source, character, scene, camera, picked, jobs, exported, vfx, second })); } catch {} }, [source, character, scene, camera, picked, jobs, exported, vfx, second]);
  useEffect(() => { api("/api/history?limit=60").then((h) => setLib((h || []).map((r) => ({ ...r, video: resultVideo(r.files) })).filter((r) => r.video).slice(0, 12))).catch(() => {}); }, []);

  useEffect(() => {
    const change = (id, patch) => setJobs((js) => applyPatch(js, id, patch));
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
          else if (s.status === "error") change(run.id, { status: stoppedStatus(s), error: s.error || "The render failed." });
        } else {
          try {
            const r = await post("/api/generate", next.body);
            if (latest.current.find((j) => j.id === next.id)?.status === "cancelled") { post(`/api/jobs/${r.job}/cancel`, {}).catch(() => {}); return; }      // cancelled while this was on its way
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
  const blocked = !source ? "Add a clip first." : !chosen.length ? "Pick at least one job." : chosen.some((t) => t.needsCharacter) && !character ? "Recast needs a character picture." : chosen.some((t) => t.needsSecond) && !second ? "Transition needs a second clip." : active ? "This board is still rendering." : "";
  const start = () => { const seed = Math.floor(Math.random() * 2 ** 31); setExported(null); setJobs(chosen.map((t) => ({ id: t.id, label: jobLabel(t, camera, vfx), status: "queued", seed, body: buildBody(t, { source, character, second, scene, camera, seed, vfx }) }))); };
  const retry = (id) => setJobs((js) => js.map((j) => (j.id === id ? { ...j, status: "queued", error: "", job: null, files: null } : j)));
  const graph = (j) => dispatchEvent(new CustomEvent("studio-graph", { detail: { ...j.body, seed: j.seed } }));
  const finished = jobs.filter((j) => j.status === "done" && resultVideo(j.files));
  const doExport = async () => { setBusy("export"); setErr(""); try { setExported(await post("/api/shotboard/export", { items: [{ filename: source.name, type: "input", label: "Source" }, ...finished.map((j) => { const f = resultVideo(j.files); return { filename: f.filename, subfolder: f.subfolder, type: "output", label: j.label }; })] })); } catch (e) { setErr(e.message); } setBusy(""); };
  const reset = () => { setJobs([]); setExported(null); };
  // A matte take becomes a cutout: the clip it was made from, with the matte as its alpha (ProRes 4444), plus a preview over a checkerboard.
  // A postable before/after of one take: 9:16, 1:1 and 16:9, each with an AI-generated label and an end card (studio/shot_board.py reel).
  const makeReel = async (id) => { const j = latest.current.find((x) => x.id === id), f = j && resultVideo(j.files); if (!f) return; setBusy("reel"); setErr(""); try { const r = await post("/api/shotboard/reel", { source: { filename: j.body.video }, take: { filename: f.filename, subfolder: f.subfolder }, label: j.label.replace(/^VFX: /, "") }); setJobs((js) => applyPatch(js, id, { reel: r })); } catch (e) { setErr("The reel failed: " + e.message); } setBusy(""); };
  const makeCutout = async (id) => { const j = latest.current.find((x) => x.id === id), f = j && resultVideo(j.files); if (!f) return; setBusy("cutout"); setErr(""); try { const r = await post("/api/shotboard/cutout", { source: { filename: j.body.video }, matte: { filename: f.filename, subfolder: f.subfolder } }); setJobs((js) => applyPatch(js, id, { cutout: r })); } catch (e) { setErr("The cutout failed: " + e.message); } setBusy(""); };
  const cancelBoard = () => { const js = latest.current; latest.current = cancelOpen(js); setJobs(cancelOpen); for (const j of js) if (j.status === "running" && j.job) post(`/api/jobs/${j.job}/cancel`, {}).catch(() => {}); };
  const done = jobs.filter((j) => j.status === "done").length;

  return html`<${Board} ...${{ source, setSource, character, setCharacter, scene, setScene, camera, setCamera, picked, setPicked, jobs, exported, err, busy, lib, chosen, active, blocked, finished, done, useFile, fromLibrary, start, retry, graph, doExport, reset, makeCutout, makeReel, onCancel: cancelBoard, resultVideo, transforms: TRANSFORMS, cameras: CAMERAS, vfx, setVfx, second, setSecond, qualities: VFX_QUALITY, strengths: VFX_STRENGTH }}/>`;
}
