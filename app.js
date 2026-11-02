import { h, render } from "preact";
import { useState, useEffect, useRef, useMemo } from "preact/hooks";
import { html, api, post } from "./common.js";
import { Crew, Site, Studio3D, Edit, Designers, Apps } from "./extras.js";
import { SECTIONS, firstGraph, hasGraph, loadRow, matches, sectionOf, useAllGraphs } from "./graph_rows.js";
import { installTilt } from "./spectacle.js";
import { PhonePanel } from "./phone.js";
import { ApiPage } from "./apipage.js";
import { ShareButton } from "./share.js";
import { RingHero, GoalDeck, Masonry, LiveMedia, useShowcase, Drop, FLAGSHIPS } from "./showcase.js";
import { Graph3D, useLive } from "./graph3d.js";
import { graphRequest, buildModel, layoutGraph, replayPlan, replayAt } from "./graph3d_math.js";
import { PrimeDock } from "./prime_ui.js";
import { MusicStyles } from "./music_styles.js";
import { Families, FamilyDeck } from "./families.js";
import { Processes } from "./processes.js";
import { Atlas } from "./atlas.js";
import { Recipes } from "./recipes.js";
import { ShotBoard } from "./shotboard.js";
import { WorldKit } from "./worldkit.js";
import { Train, TrainedLoras } from "./train.js";
import { Pipelines } from "./pipelines.js";
import { Future } from "./future.js";
import { University } from "./university.js";
import { SamplingLab } from "./samplinglab.js";
import { Res4lyf } from "./res4lyf.js";
import { VirtualSet } from "./virtualset.js";
import { AIEdits, Schedules, CalibrateCard } from "./pages2.js";
import { GoalTiles, NeedsModels, AttachCard, CloudCard } from "./models_ui.js";
import { Empty, Offline, Stage, Stats, Strip, useHealth } from "./look.js";
import { Palette } from "./palette.js";
import { createToasts, pushToast, expire } from "./toast_logic.js";
import { Toasts } from "./toast.js";
import { ShortcutHelp } from "./shortcuts.js";
import { Tour } from "./tour.js";
import { shouldAutoStart } from "./tour_logic.js";
import { loadFeaturePages } from "./fx.js";
import { FitChip } from "./fit_chip.js";
function EditHub() {
  const [seg, setSeg] = useState("ai");
  return html`<div class="lk"><${Strip} label="Edit" value=${seg} onPick=${setSeg} items=${[{ k: "ai", b: "AI edits", s: "One model, one simple form" }, { k: "timeline", b: "Timeline", s: "Cut your clips into one video" }]}/>${seg === "ai" ? html`<${AIEdits}/>` : html`<${Edit}/>`}</div>`;
}
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

/* ---------- tiny, safe markdown (escape first, then format) ---------- */
function md(src) {
  const blocks = []; src = String(src || "").replace(/```[a-z]*\n([\s\S]*?)```/g, (_, c) => { blocks.push(`<pre><code>${esc(c)}</code></pre>`); return `\u0000${blocks.length - 1}\u0000`; });
  const inline = (t) => esc(t).replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>").replace(/(^|[^*])\*([^*\n]+)\*/g, "$1<em>$2</em>").replace(/\[([^\]]+)\]\((https?:[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
  const out = []; const lines = src.split("\n"); let i = 0;
  while (i < lines.length) {
    const l = lines[i];
    if (/^\u0000\d+\u0000$/.test(l.trim())) { out.push(blocks[+l.trim().slice(1, -1)]); i++; continue; }
    let m;
    if ((m = l.match(/^(#{1,4})\s+(.*)/))) { out.push(`<h${m[1].length}>${inline(m[2])}</h${m[1].length}>`); i++; continue; }
    if (/^\s*[-*]\s+/.test(l)) { const it = []; while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) it.push(`<li>${inline(lines[i++].replace(/^\s*[-*]\s+/, ""))}</li>`); out.push(`<ul>${it.join("")}</ul>`); continue; }
    if (/^\s*\d+[.)]\s+/.test(l)) { const it = []; while (i < lines.length && /^\s*\d+[.)]\s+/.test(lines[i])) it.push(`<li>${inline(lines[i++].replace(/^\s*\d+[.)]\s+/, ""))}</li>`); out.push(`<ol>${it.join("")}</ol>`); continue; }
    if (/^\|.*\|\s*$/.test(l) && /^\|[\s:|-]+\|\s*$/.test(lines[i + 1] || "")) {
      const cells = (r) => r.trim().replace(/^\||\|$/g, "").split("|").map((c) => inline(c.trim())); const head = cells(l); i += 2; const rows = [];
      while (i < lines.length && /^\|.*\|\s*$/.test(lines[i])) rows.push(cells(lines[i++]));
      out.push(`<table><tr>${head.map((c) => `<th>${c}</th>`).join("")}</tr>${rows.map((r) => `<tr>${r.map((c) => `<td>${c}</td>`).join("")}</tr>`).join("")}</table>`); continue;
    }
    if (/^>\s?/.test(l)) { const q = []; while (i < lines.length && /^>\s?/.test(lines[i])) q.push(lines[i++].replace(/^>\s?/, "")); out.push(`<blockquote>${inline(q.join(" "))}</blockquote>`); continue; }
    if (/^---+\s*$/.test(l)) { out.push("<hr>"); i++; continue; }
    if (!l.trim()) { i++; continue; }
    const p = []; while (i < lines.length && lines[i].trim() && !/^(#{1,4}\s|\s*[-*]\s|\s*\d+[.)]\s|>|\||---)/.test(lines[i]) && !/^\u0000\d+\u0000$/.test(lines[i].trim())) p.push(lines[i++]);
    out.push(`<p>${inline(p.join(" "))}</p>`);
  }
  return out.join("\n");
}

const Icon = ({ n }) => {
  const d = { music: "M9 18V6l10-2v12 M9 18a3 3 0 1 1-3-3 3 3 0 0 1 3 3z M19 16a3 3 0 1 1-3-3 3 3 0 0 1 3 3z", voices: "M3 12h2 M7 8v8 M11 5v14 M15 8v8 M19 10v4", motion: "M13 4.5a1.5 1.5 0 1 0 0-.01 M9 21l2.5-6-2.5-2 2-5 3.5 2.5 3 .5 M11 8l-4 1.5-1.5 3 M14 15l1 6", pipelines: "M4 7h5v4H4z M15 13h5v4h-5z M9 9h3a2 2 0 0 1 2 2v2a2 2 0 0 0 2 2 M4 18h5 M15 6h5", future: "M12 3v4 M12 17v4 M3 12h4 M17 12h4 M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6", res4lyf: "M3 19c3-9 6-13 9-13s6 4 9 13 M6 13h.01 M12 6h.01 M18 13h.01", sampling: "M3 19c2-12 5-15 7-15s3 6 5 10 3 5 6 5 M3 19h18", train: "M4 18l5-6 4 3 7-9 M15 6h5v5 M4 21h16", worldkit: "M12 3l8 4.5v9L12 21l-8-4.5v-9z M4 7.5l8 4.5 8-4.5 M12 12v9", virtualset: "M3 7h12v10H3z M15 11l6-3v8l-6-3 M7 7V4h4v3", shots: "M3 5h18v14H3z M3 12h18 M12 5v14 M7 3v2 M17 3v2", api: "M8 7l-5 5 5 5 M16 7l5 5-5 5 M14 4l-4 16", recipes: "M4 6h7v5H4z M13 13h7v5h-7z M11 8.5h4a2 2 0 0 1 2 2V13", processes: "M4 6h16 M4 12h16 M4 18h9 M17 15l4 3-4 3", atlas: "M3 6l6-2 6 2 6-2v14l-6 2-6-2-6 2z M9 4v14 M15 6v14", families:"M4 4h6v6H4z M14 4h6v6h-6z M4 14h6v6H4z M14 14h6v6h-6z M7 10v4 M17 10v4 M10 7h4", create: "M12 3l1.8 4.7L18.5 9.5l-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8z M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z", library: "M4 5h16v14H4z M4 15l4-4 4 3 3-2 5 4", uni: "M3 9l9-5 9 5-9 5z M7 11.5V16c2 1.8 8 1.8 10 0v-4.5", models: "M12 3l8 4.5v9L12 21l-8-4.5v-9z M12 12l8-4.5 M12 12v9 M12 12L4 7.5", apps: "M4 4h7v7H4z M13 4h7v7h-7z M4 13h7v7H4z M15 15h4v4h-4z", auto: "M12 7v5l3 2 M21 12a9 9 0 11-3-6.7 M21 4v5h-5", design: "M12 3l2.5 5 5.5.8-4 3.9.9 5.5L12 15.6 7.1 18.2 8 12.7 4 8.8 9.5 8z", edit: "M3 6h18v12H3z M7 6v12 M17 6v12 M3 10h4 M3 14h4 M17 10h4 M17 14h4", crew: "M16 11a3 3 0 100-6 3 3 0 000 6z M8 12a3 3 0 100-6 3 3 0 000 6z M2 20c0-3 3-5 6-5s6 2 6 5 M14 15c3 0 8 1 8 5", site: "M3 5h18v14H3z M3 9h18 M7 7h.01", viewer: "M12 3l8 4.5v9L12 21l-8-4.5v-9z M4 7.5l8 4.5 8-4.5 M12 12v9", pro: "M5 6h5v4H5z M14 14h5v4h-5z M14 6h5v4h-5z M10 8h4 M7.5 10v6h6.5" };
  return html`<svg viewBox="0 0 24 24"><path d=${d[n]}/></svg>`;
};

/* ---------- pro mode: the exact graph, drawn ---------- */
function GraphView({ graph }) {
  const lay = useMemo(() => {
    if (!graph) return null;
    const ids = Object.keys(graph), depth = {}, links = [];
    const dep = (id, seen = new Set()) => { if (depth[id] != null) return depth[id]; if (seen.has(id)) return 0; seen.add(id); let d = 0; for (const v of Object.values(graph[id].inputs || {})) if (Array.isArray(v) && graph[v[0]]) d = Math.max(d, dep(String(v[0]), seen) + 1); return (depth[id] = d); };
    ids.forEach((id) => dep(id)); const cols = {}; ids.forEach((id) => (cols[depth[id]] ||= []).push(id));
    const pos = {}; const W = 216, GAP = 54;
    Object.entries(cols).forEach(([c, list]) => { let y = 10; list.forEach((id) => { const ins = Object.entries(graph[id].inputs || {}).filter(([, v]) => !Array.isArray(v)).slice(0, 4); const hgt = 38 + ins.length * 15; pos[id] = { x: 10 + c * (W + GAP), y, h: hgt, ins }; y += hgt + 14; }); });
    ids.forEach((id) => Object.entries(graph[id].inputs || {}).forEach(([k, v]) => Array.isArray(v) && pos[v[0]] && links.push([String(v[0]), id, k])));
    const width = Math.max(...Object.values(pos).map((p) => p.x)) + W + 20, height = Math.max(...Object.values(pos).map((p) => p.y + p.h)) + 20;
    return { pos, links, W, width, height };
  }, [graph]);
  if (!lay) return html`<div class="empty">Write a prompt in Create and this will show the exact graph that makes it.</div>`;
  const { pos, links, W, width, height } = lay;
  return html`<div class="graphbox"><svg width=${width} height=${height} viewBox="0 0 ${width} ${height}">
    ${links.map(([a, b]) => { const A = pos[a], B = pos[b]; const x1 = A.x + W, y1 = A.y + 19, x2 = B.x, y2 = B.y + 19, dx = (x2 - x1) / 2; return html`<path class="gw" d="M${x1} ${y1} C${x1 + dx} ${y1} ${x2 - dx} ${y2} ${x2} ${y2}"/>`; })}
    ${Object.entries(pos).map(([id, p]) => html`<g class="gn" transform="translate(${p.x},${p.y})"><rect width=${W} height=${p.h} rx="10"/><text x="10" y="17">${graph[id].class_type}</text><text class="sub" x="10" y="31">node ${id}</text>
      ${p.ins.map(([k, v], i) => html`<text class="sub" x="10" y=${46 + i * 15}>${k}: ${String(v).slice(0, 26)}</text>`)}</g>`)}
  </svg></div>`;
}

const PROMPT_HINT = { product: "What are you selling? For example: a hand-thrown ceramic teapot", recast: "Optional: darker jacket, keep the glasses, less smiling", reshoot: "Optional: what should happen in this new take", vfx_ltx: "What should happen? For example: the street floods with dark water", director: "Describe the action. The camera, lens and light come from the choices below", director_keyframes: "What happens between the two frames?" };
const IDEAS = {
  image: ["a lighthouse on a cliff at dawn, soft fog, cinematic light, 35mm", "a tiny greenhouse city floating in the clouds, golden hour, detailed illustration", "close portrait of an elderly fisherman, weathered skin, natural window light", "neon-lit rainy street market at night, reflections, wide angle"],
  video: ["a slow dolly in on a red fox walking through fresh snow at sunrise, soft breath in the air", "ocean waves rolling onto black sand at dusk, gentle push in, ambient sound of surf", "a street musician playing violin under a bridge, camera slowly orbits, warm lamp light"],
  product: ["a matte black perfume bottle with a gold cap", "a hand-thrown ceramic teapot", "a futuristic running sneaker"],
  director: ["a lighthouse keeper climbs the spiral stairs carrying a lantern, a storm outside the windows", "a street food cook tosses noodles over a roaring flame at night, steam drifting through neon light", "a lone rider crosses a salt flat at dawn, long shadow stretching behind the horse"],
  director_keyframes: ["the scene changes smoothly from the first frame to the last, one continuous move"],
  recast: ["keep the expression and the timing, match the lighting of the scene"], reshoot: ["the camera drifts around the subject, same setting and light"], vfx_ltx: ["the street floods with dark water that rises past the ankles"],
  h3_video: ["a slow dolly in on a red fox walking through fresh snow at sunrise, soft breath in the air, forest ambience", "a chef flambes a pan in a dark kitchen, a tall column of fire lights her face, sizzling sound"], video_ltx: ["macro shot of liquid gold and emerald ink colliding in black water, slow drift, ambient drone", "a black glass sphere shatters on marble and the shards become gold butterflies, slow motion"], music: ["warm acoustic folk, fingerpicked guitar, gentle brushed drums, soft vocals, hopeful and calm", "epic cinematic trailer score, deep brass, driving taiko drums, soaring strings, instrumental"], flux3: ["a futuristic running sneaker floating above wet obsidian, frozen splashes, high end product photograph", "an ancient jungle temple overgrown with luminous moss, shafts of golden light, matte painting"], anime: ["a lone ronin walking through golden grass at dusk, fireflies rising, huge full moon", "a towering mecha kneeling in a rain-soaked neon city, a small pilot looking up"],
  animate: ["the character slowly turns toward the camera and smiles, soft wind in the hair", "gentle camera push in while clouds drift across the sky", "the water ripples and the leaves sway in a light breeze"],
};

/* ---------- Create ---------- */
function Create({ health, onDraft, goTab }) {
  const [ways, setWays] = useState(0);
  useEffect(() => { Promise.allSettled([api("/api/family-graphs"), api("/api/recipes"), api("/api/apps")]).then(([f, r, a]) => setWays((f.status === "fulfilled" ? f.value.graphs.length : 0) + (r.status === "fulfilled" ? (r.value.recipes || r.value).length : 0) + (a.status === "fulfilled" ? a.value.apps.length : 0))); }, []);
  const [goals, setGoals] = useState({}); const [goal, setGoal] = useState("image");
  const [prompt, setPrompt] = useState(""); const [lyrics, setLyrics] = useState(""); const [opts, setOpts] = useState({}); const [seed, setSeed] = useState("");
  const [img, setImg] = useState(null); const [vid, setVid] = useState(null); const [lastImg, setLastImg] = useState(null); const [extra, setExtra] = useState({}); const promptRef = useRef(); const [job, setJob] = useState(null); const [res, setRes] = useState(null); const [err, setErr] = useState(""); const [hist, setHist] = useState([]); const [busy, setBusy] = useState(false); const [tick, setTick] = useState(0);
  const g = goals[goal]; const fileRef = useRef(); const items = useShowcase(); const styleTags = useRef([]);
  useEffect(() => { api("/api/goals").then(setGoals).catch((e) => setErr(e.message)); loadHist(); }, []);
  const keepOpts = useRef(null);
  useEffect(() => { if (g) { setOpts({ ...g.defaults, ...(keepOpts.current || {}) }); keepOpts.current = null; } }, [goal, goals]);
  const loadHist = () => api("/api/history?limit=24&only=main").then(setHist).catch(() => {});
  useEffect(() => { if (!goals[goal]) return; onDraft && onDraft({ goal, prompt, options: opts, seed, image: img && img.name, video: vid && vid.name, last_image: lastImg && lastImg.name, lyrics, ...extra, job: job && job.job }); }, [goal, prompt, opts, seed, img, vid, lastImg, lyrics, extra, job, goals]);
  useEffect(() => {
    if (!job) return; setTick(0); const t0 = Date.now(); const timer = setInterval(() => setTick(Math.round((Date.now() - t0) / 1000)), 500);
    const poll = setInterval(async () => {
      try { const s = await api(`/api/jobs/${job.job}`); setRes(s); if (s.status === "done" || s.status === "error") { clearInterval(poll); clearInterval(timer); setBusy(false); if (s.status === "error") setErr(s.error || "The job failed"); else loadHist(); } } catch (e) { setErr(e.message); }
    }, 1500);
    return () => { clearInterval(poll); clearInterval(timer); };
  }, [job]);
  const missing = () => { if (!g) return ""; if (g.needs_video && !vid) return `Add ${(g.video_label || "a source video").toLowerCase()} first`; if (g.needs_image && !img) return `Add ${(g.image_label || "a start image").toLowerCase()} first`; if (g.needs_last_image && !lastImg) return "Add the last frame first"; return ""; };
  const go = async () => {
    const need = missing(); if (need) { setErr(need); return; }
    if (!prompt.trim() && !(g && g.prompt_optional)) { setErr(""); promptRef.current && promptRef.current.focus(); return; }
    setErr(""); setRes(null); setBusy(true);
    try { const j = await post("/api/generate", { goal, prompt, lyrics, options: opts, seed: seed === "" ? null : +seed, image: img && img.name, video: g.needs_video ? vid && vid.name : undefined, last_image: g.needs_last_image ? lastImg && lastImg.name : undefined, ...extra }); setJob(j); setRes({ status: "queued" }); } catch (e) { setErr(e.message); setBusy(false); }
  };
  const uploadTo = (set) => async (f) => { if (!f) return; const fd = new FormData(); fd.append("file", f); try { const r = await api("/api/upload", { method: "POST", body: fd }); set({ name: r.name, url: URL.createObjectURL(f) }); setErr(""); } catch (e) { setErr(e.message); } };
  useEffect(() => {
    const onAct = (e) => { const a = e.detail || {}; if (a.type === "set_goal") { setGoal(a.goal); setRes(null); } if (a.type === "set_prompt") setPrompt(a.text); };
    const onGo = () => { if (prompt.trim() && !busy) go(); };
    addEventListener("prime-action", onAct); addEventListener("prime-generate", onGo); return () => { removeEventListener("prime-action", onAct); removeEventListener("prime-generate", onGo); };
  });
  const surprise = () => { const l = IDEAS[goal] || IDEAS.image; setPrompt(l[Math.floor(Math.random() * l.length)]); };
  const files = res && res.files || []; const main = (g && g.kind === "audio" ? files.find((f) => f.kind === "audio") : files.find((f) => f.kind !== "audio")) || files[0];
  const running = res && (res.status === "queued" || res.status === "running" || res.status === "unknown");
  const sample = items.find((x) => x.goal === goal && x.kind !== "audio"), measured = items.filter((x) => x.goal === goal && x.seconds);
  const estS = measured.length ? Math.round(measured.reduce((a, x) => a + +x.seconds, 0) / measured.length) : null, estV = measured.length ? Math.max(...measured.map((x) => +x.peak_vram_gib || 0)) : null;
  const pick = (id) => { setGoal(id); setRes(null); scrollTo({ top: 0, behavior: "smooth" }); };
  const openItem = (x) => { keepOpts.current = x.options; setGoal(x.goal); setPrompt(x.prompt); setOpts({ ...(goals[x.goal] || {}).defaults, ...x.options }); setErr(""); setRes({ status: "done", files: [{ url: x.src, kind: x.kind }], seconds: x.seconds, peak: x.peak_vram_gib, options: x.options, seed: null, graph_hash: "", showcase: x.id }); scrollTo({ top: 0, behavior: "smooth" }); };
  const recreate = (x) => { keepOpts.current = x.options; setGoal(x.goal); setPrompt(x.prompt); setOpts({ ...(goals[x.goal] || {}).defaults, ...x.options }); setRes(null); scrollTo({ top: 0, behavior: "smooth" }); };
  const graph = (x) => { recreate(x); setTimeout(() => goTab("pro"), 60); };
  const mine = hist.filter((e) => !e.family && e.files.some((y) => !/\.(glb|gltf)$/i.test(y.filename || ""))).map((e) => { const f = e.files.find((y) => y.kind !== "audio" && !/\.(glb|gltf)$/i.test(y.filename || "")) || e.files[0]; return { id: e.job, goal: e.goal, kind: f.kind, src: f.url, poster: f.kind === "video" ? undefined : f.url, prompt: e.prompt || "", options: e.options || {}, w: 16, h: 9 }; }).filter((x) => x.kind !== "audio" && x.prompt && !items.some((y) => x.prompt.includes(y.prompt)));
  return html`<div class="cwrap">
    <aside class="cpanel" aria-label="create">
      <div class="cscroll">
        <button class="gsel" onClick=${() => document.getElementById("makewhat").scrollIntoView({ behavior: "smooth" })} aria-label="change what to make">
          ${sample ? html`<${LiveMedia} item=${sample}/>` : html`<div class="gblank"></div>`}<i>Change</i><b>${g ? g.label : ""}</b><small>${g ? g.family : ""}</small></button>
        ${g && html`<${FitChip} k=${"goal:" + goal}/>`}
        ${g && g.needs_video && html`<${Drop} label=${g.video_label || "Source video"} accept="video/mp4,video/quicktime,video/webm,video/x-matroska" file=${vid} onFile=${uploadTo(setVid)} hint="MP4 or MOV, one continuous shot" example=${items.find((x) => x.id === "v_h3_chef") || items.find((x) => x.kind === "video")}/>`}
        ${g && g.needs_image && html`<${Drop} label=${g.image_label || "Start image"} accept="image/png,image/jpeg,image/webp" file=${img} onFile=${uploadTo(setImg)} example=${items.find((x) => x.id === "s_portrait") || items.find((x) => x.kind === "image")}/>`}
        ${g && g.needs_last_image && html`<${Drop} label="Last frame" accept="image/png,image/jpeg,image/webp" file=${lastImg} onFile=${uploadTo(setLastImg)} example=${items.find((x) => x.id === "s_greenhouse") || items.find((x) => x.kind === "image")}/>`}
        ${g && Object.entries(g.fields || {}).map(([k, ph]) => html`<div class="field"><label style="text-transform:capitalize">${k}</label><input class="seedin" type="text" placeholder=${ph} value=${extra[k] || ""} onInput=${(e) => setExtra({ ...extra, [k]: e.target.value })} aria-label=${k}/></div>`)}
        <div class="field"><label>${g && g.prompt_optional ? "Direction (optional)" : "Prompt"}</label><textarea ref=${promptRef} placeholder=${(g && g.prompt_hint) || PROMPT_HINT[goal] || (g && g.kind === "audio" ? "Describe the song: genre, mood, instruments, vocals" : g && g.needs_image ? "How should it move?" : "Describe what you want to make")} value=${prompt} onInput=${(e) => setPrompt(e.target.value)} onKeyDown=${(e) => { if ((e.ctrlKey || e.metaKey) && e.key === "Enter") go(); }} aria-label="prompt"></textarea><div class="row" style="margin:6px 0 0"><button class="btn small" onClick=${surprise}>Surprise me</button></div></div>
        ${goal === "music" && html`<${MusicStyles} prompt=${prompt} setPrompt=${setPrompt} appliedRef=${styleTags}/>`}
        ${g && g.kind === "audio" && html`<div class="field"><label>Lyrics (optional)</label><textarea style="min-height:70px" placeholder="Leave empty for an instrumental" value=${lyrics} onInput=${(e) => setLyrics(e.target.value)} aria-label="lyrics"></textarea></div>`}
        <div class="optgrid">
          ${g && Object.entries(g.options).map(([k, vals]) => html`<div class=${"field" + (vals.length > 3 ? " wide" : "")}><label style="text-transform:capitalize">${k}</label><div class="chips">${vals.map((v) => html`<button class=${"chip" + (opts[k] === v ? " on" : "")} onClick=${() => setOpts({ ...opts, [k]: v })}>${k === "seconds" ? v + " s" : v}</button>`)}</div></div>`)}
          <div class="field"><label>Seed</label><input class="seedin" type="text" inputmode="numeric" placeholder="random" value=${seed} onInput=${(e) => { const v = e.target.value.replace(/\D/g, ""); e.target.value = v; setSeed(v); }} aria-label="seed"/></div>
        </div>
        ${health && !health.comfy && html`<div class="lk-warn" role="status"><b>ComfyUI is not reachable at ${health.comfy_url}</b><p>Start it, then try again.</p></div>`}

      </div>
      <div class="gen">${err && html`<p class="small generr" role="alert">${err}</p>`}<${NeedsModels} goal=${goal}/><button class="gobtn" disabled=${busy || !(health && health.comfy)} onClick=${go}>${busy ? "Generating" : g && g.needs_video ? "Run " + g.label : "Generate"}</button>
        <div class="gencost"><b>${health && health.backend && health.backend.spends_credits ? "Comfy credits" : "0 credits"}</b>${estS && html`<span>about ${estS}s on the author's GPU</span>`}${estV ? html`<span>${Math.round(estV)} GB VRAM</span>` : null}</div></div>
    </aside>
    <div class="stagecol">
      ${running ? html`<div class="rstage"><div class="shimmer"></div><div class="run"><b>${tick}s</b><small>${res.status === "queued" ? (res.position ? `in line, position ${res.position}` : "waiting for the GPU") : "generating on your GPU"}</small><button class="btn small" style="margin-top:10px" onClick=${() => post(`/api/jobs/${job.job}/cancel`).catch(() => {})}>Cancel</button><button class="btn small" style="margin-top:6px" onClick=${() => goTab("pro")}>Watch it inside</button></div></div>` :
        main ? html`<div><div class="rstage">${main.kind === "video" ? html`<video key=${main.url} src=${main.url} controls autoplay loop playsinline></video>` : main.kind === "audio" ? html`<div style="padding:30px;text-align:center;width:min(560px,90%)"><div style="font-size:48px;margin-bottom:8px;color:var(--a2)">${"♫"}</div><audio src=${main.url} controls autoplay style="width:100%"></audio></div>` : html`<img src=${main.url} alt=${prompt}/>`}</div>
          <div class="rinfo"><span><b>${g && g.family}</b></span>${res.seed != null && html`<span>seed <b>${res.seed}</b></span>`}${res.seconds && html`<span><b>${res.seconds}s</b></span>`}${res.peak && html`<span><b>${res.peak} GB</b> peak</span>`}${res.graph_hash && html`<span>graph <code>${res.graph_hash}</code></span>`}<span class="grow"></span><button class="btn small" onClick=${() => goTab("pro")}>Open the graph</button><${ShareButton} url=${main.url} prompt=${prompt} family=${g && g.family}/><a class="btn small" href=${main.url} download>Download</a>${res.seed != null && html`<button class="btn small" onClick=${() => setSeed(String(res.seed))}>Reuse seed</button>`}${res.showcase && html`<a class="btn small" href=${"#prove/showcase/" + res.showcase}>Prove it on my machine</a>`}<button class="btn small" onClick=${() => setRes(null)}>Close</button></div></div>` :
        html`<section class="hero"><${RingHero} items=${items} onPick=${openItem}/><div class="heroshade"></div>
          <div class="herocopy"><h2>One clip in. <em>A whole shoot out.</em></h2><p>Runs on your own GPU. Talk to the agents, or open the exact ComfyUI graph behind any frame.</p><div class="herostat">${!(health && health.backend && health.backend.spends_credits) && html`<div><b>0</b><span>credits on your GPU</span></div>`}<div role="link" tabindex="0" title="See every graph" style="cursor:pointer" onClick=${() => { location.hash = "apps"; }} onKeyDown=${(e) => { if (e.key === "Enter") location.hash = "apps"; }}><b>${Object.keys(goals).length + ways}</b><span>ways to create</span></div><div><b>100%</b><span>yours to fork</span></div></div></div>
          <div class="herochips">${health && health.backend && health.backend.backend === "sdk" && html`<span class="pill">Comfy SDK: ${health.backend.target}</span>`}<span class="pill"><span class=${"dot " + (health ? (health.comfy ? "ok" : "bad") : "")}></span>${comfyPill(health)}</span>${health && health.gpu && html`<span class="pill">${health.gpu.vram_free_gb} of ${health.gpu.vram_total_gb} GB free</span>`}</div><div class="herohint">Drag to spin. Click any shot.</div></section>`}
      <section class="sect" id="makewhat"><h2>What do you want to make</h2><div class="sectsub">Start from a flagship app or pick a model. The badge shows its licence.</div><${GoalDeck} goals=${goals} goal=${goal} items=${items} onPick=${pick}/></section>
      <${FamilyDeck} goTab=${goTab}/>
      <section class="sect" id="makewho"><h2>Design something</h2><div class="sectsub">Character maker, fashion and vehicles as whole sheets, and many more designers inside.</div><div class="gdeck">${[["character", "Character Maker", "Original characters, headshot to full body"], ["fashion", "Fashion Designer", "Outfits, shoes and accessories as a sheet"], ["vehicle", "Vehicle Builder", "Cars, bikes and wild builds"], ["more", "All designers", "Products, settings, animals, hair and more"]].map(([id, label, sub]) => html`<button class="gcard" onClick=${() => { location.hash = "design"; if (id !== "more") setTimeout(() => { const t = [...document.querySelectorAll("main .gcard")].find((e) => e.offsetParent && e.innerText.toLowerCase().includes(id === "character" ? "character designer" : id === "fashion" ? "fashion designer" : "vehicle builder")); t && t.click(); }, 900); }}>${id !== "more" ? html`<img class="gmedia" src=${"designer_art/" + id + ".webp"} alt="" loading="lazy" onError=${(e) => { e.target.style.display = "none"; }}/>` : html`<div class="gmedia gblank">+</div>`}<span class="gshade"></span><span class="gtext"><b>${label}</b><small>${sub}</small></span></button>`)}</div></section>
      ${mine.length > 0 && html`<section class="sect"><h2>Your recent work</h2><div class="sectsub">Click to reopen it with the same settings.</div><${Masonry} items=${mine.slice(0, 12)} goals=${goals} onOpen=${openItem} onRecreate=${recreate} onGraph=${graph}/></section>`}
      <section class="sect"><h2>See inside every shot</h2><div class="sectsub">Prompt, model, time and peak VRAM, measured on one machine. Recreate any of them, or open the graph that made it.</div><${Masonry} items=${items} goals=${goals} onOpen=${openItem} onRecreate=${recreate} onGraph=${graph}/></section>
    </div></div>`;
}

/* ---------- Library ---------- */
const LIB_STARTS = [["image", "A picture", "showcase/s_temple.webp", "Text to image"], ["h3_video", "A video", "showcase/v_h3_dragon.webp", "With sound, on MiniMax H3"], ["music", "A song", "showcase/a_score.webp", "Your words, or instrumental"]];
function Library() {
  const [hist, setHist] = useState([]); const [open, setOpen] = useState(null); const [kind, setKind] = useState("all"); const [loaded, setLoaded] = useState(false); const [goals, setGoals] = useState({}); const [view, setView] = useState("work"); const health = useHealth(), up = health && health.comfy;
  useEffect(() => { api("/api/history?limit=200").then((h) => { setHist(h); setLoaded(true); }).catch(() => setLoaded(true)); api("/api/goals").then(setGoals).catch(() => {}); }, [up]);
  const rows = hist.flatMap((e) => e.files.map((f, i) => ({ id: e.job + i, e, f, goal: e.goal, kind: /\.(glb|gltf)$/i.test(f.filename || "") ? "3d" : f.kind, src: f.url, poster: f.kind === "image" ? f.url : undefined, prompt: e.prompt || f.filename, options: e.options || {} })));
  const counts = { all: rows.length, image: rows.filter((x) => x.kind === "image").length, video: rows.filter((x) => x.kind === "video").length, audio: rows.filter((x) => x.kind === "audio").length, "3d": rows.filter((x) => x.kind === "3d").length };
  const shown = rows.filter((x) => kind === "all" || x.kind === kind);
  const toCreate = (x, tab) => { if (x.e && x.e.family) { if (tab) dispatchEvent(new CustomEvent("studio-graph", { detail: { goal: x.e.family_name, prompt: x.e.prompt, family_job: `${x.e.family}/${x.e.job}` } })); else location.hash = "families/" + x.e.family; return; } location.hash = "create"; setTimeout(() => { dispatchEvent(new CustomEvent("prime-action", { detail: { type: "set_goal", goal: x.goal } })); dispatchEvent(new CustomEvent("prime-action", { detail: { type: "set_prompt", text: x.prompt } })); if (tab) location.hash = tab; }, 80); };
  const start = (g) => { location.hash = "create"; setTimeout(() => dispatchEvent(new CustomEvent("prime-action", { detail: { type: "set_goal", goal: g } })), 80); };
  const latest = rows.filter((x) => x.kind === "image" || x.kind === "video").slice(0, 6).map((x) => ({ id: x.id, src: x.src, poster: x.poster, kind: x.kind, title: String(x.prompt).slice(0, 60), sub: x.e.family_name || (goals[x.goal] || {}).label || "", kicker: "Yours" }));
  const away = health && !health.comfy;
  return html`<div class="lk lib-page">
    <${Strip} label="Library" value=${view} onPick=${setView} items=${[{ k: "work", b: "Your work", s: loaded ? `${counts.all} file${counts.all === 1 ? "" : "s"}` : "Reading" }, { k: "loras", b: "LoRAs", s: "What you have trained" }]}/>
    ${view === "loras" ? html`<${TrainedLoras} goTrain=${(id) => { location.hash = "train/" + id; }}/>` : html`<div class="lk lib-work">
      ${loaded && hist.length > 0 && html`<${Offline} health=${health}>This list only has what family instances made. Results from the main ComfyUI come back when it does.<//>`}
      ${latest.length > 0 && html`<${Stage} items=${latest} label="Your latest work"/>`}
      ${rows.length > 0 && html`<div class="lib-bar"><${Stats} items=${[[counts.all, "files"], ...(counts.image ? [[counts.image, "images"]] : []), ...(counts.video ? [[counts.video, "videos"]] : []), ...(counts.audio ? [[counts.audio, "songs and sounds"]] : []), ...(counts["3d"] ? [[counts["3d"], "3D files"]] : [])]}/>
        <div class="chips">${[["all", "Everything"], ["image", "Images"], ["video", "Video"], ["audio", "Audio"], ["3d", "3D"]].filter(([k]) => k === "all" || counts[k]).map(([k, l]) => html`<button class=${"chip" + (kind === k ? " on" : "")} aria-pressed=${kind === k} onClick=${() => setKind(k)}>${l} ${counts[k]}</button>`)}</div></div>`}
      ${shown.filter((x) => x.kind === "audio").length > 0 && html`<div class="alist">${shown.filter((x) => x.kind === "audio").map((x) => html`<div class="acard"><div class="anote">${"♫"}</div><div class="abody"><p>${x.prompt}</p><audio src=${x.src} controls preload="none"></audio></div></div>`)}</div>`}
      ${shown.filter((x) => x.kind === "3d").length > 0 && html`<ul class="lib-3d" aria-label="3D files">${shown.filter((x) => x.kind === "3d").map((x) => html`<li key=${x.id}><a href="#viewer"><i aria-hidden="true">3D</i><b>${x.f.filename}</b><small>Open in the 3D viewer</small></a></li>`)}</ul>`}
      <${Masonry} items=${shown.filter((x) => x.kind === "image" || x.kind === "video")} goals=${goals} onOpen=${setOpen} onRecreate=${(x) => toCreate(x)} onGraph=${(x) => toCreate(x, "pro")}/>
      ${loaded && !hist.length && html`<${Empty} art="showcase/v_h3_foundry.mp4" poster="showcase/v_h3_foundry.webp" kicker="Your library" title=${away ? "Your work can't be listed" : "Nothing here yet"} note="The picture is our own render, not yours.">
        <p>${away ? `The list of what you have made comes from ComfyUI, and it is not reachable at ${health.comfy_url || "its address"}. Your files are not gone. Start ComfyUI and they come back on this page.` : "Make something in Create and it will show up in your library."}</p><div class="lk-acts"><a class="btn primary" href="#create">Go to Create</a><a class="btn" href="#shots">Open Shot Board</a><a class="btn" href="#train">Train a LoRA</a></div><//>
        <section aria-label="Ways to start"><h2 class="lib-startshead">${away ? "When it is back, make" : "Make"}</h2><div class="lk-tiles lib-starts">${LIB_STARTS.map(([g, l, art, sub]) => html`<button key=${g} type="button" class="lk-tile lib-start" onClick=${() => start(g)}><span class="lk-tilepic"><img src=${art} alt="" loading="lazy"/></span><span class="lk-tilebody"><b>${l}</b><small>${sub}</small></span></button>`)}</div></section>`}
    </div>`}
    ${open && html`<div class="modal" role="dialog" aria-modal="true" aria-label=${String(open.prompt).slice(0, 80)} onClick=${() => setOpen(null)} onKeyDown=${(e) => { if (e.key === "Escape") setOpen(null); }}><div class="box" onClick=${(x) => x.stopPropagation()}>${open.kind === "video" ? html`<video src=${open.src} controls autoplay loop></video>` : html`<img src=${open.src} alt=${open.prompt}/>`}
      <p class="small">${open.prompt}${open.e.seed ? " | seed " + open.e.seed : ""}</p><div class="row"><${ShareButton} url=${open.src} prompt=${open.prompt}/><a class="btn small" href=${open.src} download>Download</a><button class="btn small" onClick=${() => { toCreate(open); setOpen(null); }}>Recreate</button><button class="btn small" onClick=${() => { toCreate(open, "pro"); setOpen(null); }}>Open the graph</button><button class="btn small" autofocus onClick=${() => setOpen(null)}>Close</button></div></div></div>`}
  </div>`;
}

/* ---------- Models ---------- */
function Models() {
  const [fams, setFams] = useState(null); const [src, setSrc] = useState("local"); const [q, setQ] = useState(""); const [kind, setKind] = useState(""); const [items, setItems] = useState([]); const [err, setErr] = useState(""); const [busy, setBusy] = useState(false); const [ok, setOk] = useState(false); const [msg, setMsg] = useState("");
  const [goals, setGoals] = useState({}); const [view, setView] = useState("ready");
  useEffect(() => { api("/api/models").then((d) => setFams(d.families)).catch((e) => { setFams([]); setErr(e.message); }); api("/api/goals").then(setGoals).catch(() => {}); }, []);
  const search = async () => { setErr(""); setBusy(true); setMsg(""); try { const d = await api(`/api/browse/${src}?q=${encodeURIComponent(q)}&kind=${encodeURIComponent(kind)}`); setItems(d.items); } catch (e) { setErr(e.message); } setBusy(false); };
  const dl = async (body) => { setMsg("Downloading..."); try { const r = await post("/api/browse/download", { ...body, confirm: ok }); setMsg("Saved to " + r.saved); } catch (e) { setMsg(e.message); } };
  const kinds = src === "civitai" ? ["", "Checkpoint", "LORA", "TextualInversion", "Controlnet", "VAE", "Upscaler"] : ["", "text-to-image", "text-to-video", "image-to-video", "text-to-speech", "image-to-3d"];
  return html`<div class="lk mo-page">
    <${Strip} label="Models" value=${view} onPick=${setView} items=${[{ k: "ready", b: "Ready to make", s: "Every way to create, with its models" }, { k: "box", b: "This machine", s: "Your ComfyUI and this GPU" }, { k: "find", b: "Find more", s: "On disk, Civitai, Hugging Face" }]}/>
    ${view === "ready" && html`<section class="sect"><p class="lk-plain mo-lead">Every way to create, with its models. Press Download and only the missing files come down.</p><${GoalTiles} goals=${goals}/></section>`}
    ${view === "box" && html`<div class="mo-box"><${CloudCard}/><${AttachCard}/><${CalibrateCard}/></div>`}
    ${view === "find" && html`<div class="lk mo-find"><div class="chips">${["local", "civitai", "huggingface"].map((s) => html`<button class=${"chip" + (src === s ? " on" : "")} aria-pressed=${src === s} onClick=${() => { setSrc(s); setItems([]); setErr(""); }}>${s === "local" ? "On this machine" : s === "civitai" ? "Civitai" : "Hugging Face"}</button>`)}</div>
    ${src === "local" ? (err ? html`<p class="small" style="color:var(--err)" role="alert">${err}</p>` : !fams ? html`<p class="small">Reading the models folder...</p>` : fams.length ? html`<div class="grid mo-fams">${fams.map((f) => html`<div class="card"><b>${f.family}</b><p class="small" style="margin:4px 0 0">${f.files} files</p></div>`)}</div>` : html`<${Empty} art="showcase/s_watch.webp" kicker="On this machine" title="No model files found" note="The picture is our own render, not yours."><p>The studio looked in its models folder and found nothing it recognises. Download from Ready to make, or search Civitai and Hugging Face here.</p><div class="lk-acts"><button class="btn primary" onClick=${() => setView("ready")}>See what to download</button></div><//>`) : html`<div class="lk mo-search">
      <div class="mo-searchbar"><input type="search" placeholder=${"Search " + (src === "civitai" ? "Civitai" : "Hugging Face")} value=${q} onInput=${(e) => setQ(e.target.value)} onKeyDown=${(e) => e.key === "Enter" && search()} aria-label="search models"/>
        <select value=${kind} onChange=${(e) => setKind(e.target.value)} aria-label="model type">${kinds.map((k) => html`<option value=${k}>${k || "any type"}</option>`)}</select><button class="btn primary" onClick=${search} disabled=${busy}>${busy ? "Searching..." : "Search"}</button></div>
      <p class="lk-plain">Safe-for-work results only. Check each model's licence before you use it. Downloads only happen when you tick the box and press Download; Civitai downloads need your own token in <code>CIVITAI_TOKEN</code> on this machine.</p>
      <label class="small mo-tick"><input type="checkbox" checked=${ok} onChange=${(e) => setOk(e.target.checked)}/> I want to download files to this machine</label>
      ${err && html`<p class="small" style="color:var(--err)" role="alert">${err}</p>`} ${msg && html`<p class="small" role="status">${msg}</p>`}
      ${items.length > 0 && html`<div class="grid">${items.map((m) => html`<div class="card"><b>${m.name || m.id}</b><p class="small" style="margin:4px 0">${[m.type || m.pipeline_tag, m.license || (Array.isArray(m.commercial_use) ? "commercial: " + m.commercial_use.join("/") : ""), m.downloads != null ? m.downloads.toLocaleString() + " downloads" : ""].filter(Boolean).join(" | ")}</p><a class="small mo-open" href=${m.url} target="_blank" rel="noopener noreferrer">open page</a>
        ${m.versions && m.versions[0] && m.versions[0].files.slice(0, 1).map((f) => html`<div class="row"><span class="small">${f.name} (${f.size_mb} MB)</span><button class="btn small" disabled=${!ok} onClick=${() => dl({ source: "civitai", file: f })}>Download</button></div>`)}</div>`)}</div>`}</div>`}</div>`}</div>`;
}

/* ---------- Pro ---------- */
/* Pro's picker: any row of the one list. A row with a graph shows it on the stage; a runner or a tool says what it is and gives its call. */
function ProPicker({ rows, counts, pick, onPick }) {
  const [q, setQ] = useState(""), [open, setOpen] = useState(false); const shown = useMemo(() => (open ? rows.filter((r) => matches(r, q)).slice(0, 60) : []), [rows, q, open]);
  return html`<div class="g3d-any"><button class="btn small" aria-expanded=${open} onClick=${() => setOpen(!open)}>${pick ? "Graph: " + pick.label : `All ${counts.all || 0}`}</button>${pick && html`<button class="btn small" onClick=${() => onPick(null)}>Back to Create's</button>`}
    ${open && html`<div class="g3d-anybox"><input type="search" placeholder="Search everything the studio runs" aria-label="Search graphs" value=${q} onInput=${(e) => setQ(e.target.value)}/><div role="listbox" aria-label="Every graph">${shown.map((r) => html`<button role="option" key=${r.key} aria-selected=${!!pick && pick.key === r.key} onClick=${() => { onPick(r); setOpen(false); }}><b>${r.label}</b><small>${SECTIONS.find(([k]) => k === sectionOf(r))[1]}${hasGraph(r) ? "" : ", not a ComfyUI graph"}</small></button>`)}</div></div>`}</div>`;
}
function Pro({ draft, health, goals }) {
  const every = useAllGraphs(), [pick, setPick] = useState(null), [picked, setPicked] = useState(null), [pickErr, setPickErr] = useState("");
  useEffect(() => { let k = null; try { k = sessionStorage.getItem("pro_pick"); } catch {} if (!k || !every.rows.length) return; try { sessionStorage.removeItem("pro_pick"); } catch {} setPick(every.rows.find((r) => r.key === k) || null); }, [every.rows]);
  useEffect(() => { setPicked(null); setPickErr(""); if (!pick) return undefined; let on = true; loadRow(pick).then((d) => on && setPicked(d)).catch((e) => on && setPickErr(e.message)); return () => { on = false; }; }, [pick && pick.key]);
  const [view, setView] = useState("3d"), [graph, setGraph] = useState(null), [err, setErr] = useState(""), [noGL, setNoGL] = useState(""), [replay, setReplay] = useState(null), [result, setResult] = useState(null), [watch, setWatch] = useState(null), [drop, setDrop] = useState(null); const items = useShowcase();
  const goal = (draft && draft.goal) || "image", g = (goals || {})[goal], req = useMemo(() => graphRequest(draft, g, IDEAS), [draft, g]), key = req ? JSON.stringify(req.body) : "", live = useLive(draft && draft.job);
  useEffect(() => { if (!req) return; let on = true; post("/api/graph", req.body).then((d) => { if (on) { setGraph(d.graph); setErr(""); } }).catch((e) => { if (on) { setGraph(null); setErr(e.message); } }); return () => { on = false; }; }, [key]);
  useEffect(() => { setResult(null); setReplay(null); setDrop(live.job || null); setWatch(null); }, [key]);
  useEffect(() => { document.body.classList.add("on-pro"); return () => document.body.classList.remove("on-pro"); }, []);
  useEffect(() => { if (!live.finished || !live.job || !following) return; let on = true; api(`/api/jobs/${live.job}`).then((s) => { const f = on && s.files && (s.files.find((x) => x.kind !== "audio")); if (f) setResult({ id: live.job, kind: f.kind, src: f.url, poster: f.url, label: [{ font: "800 52px Archivo, Inter", stretch: "expanded", color: "#27e07f", text: "THE RESULT OF THIS RUN", h: 68 }, { font: "500 36px Inter", color: "rgba(255,255,255,.7)", text: (s.seconds ? `Rendered on this machine in ${s.seconds} s` : "Rendered on this machine") + (s.seed != null ? `, seed ${s.seed}` : ""), h: 48 }] }); }).catch(() => {}); return () => { on = false; }; }, [live.finished, live.job]);
  const mine = !!(draft && draft.job && draft.job === live.job), following = !!(live.graph && (live.running || live.finished) && (mine || watch === live.job) && drop !== live.job), shown = pick ? firstGraph(picked) : following ? live.graph : graph, sample = items.find((x) => x.goal === goal && x.kind !== "audio");
  const media = useMemo(() => result || (following ? { label: [{ font: "800 52px Archivo, Inter", stretch: "expanded", color: "#f5c518", text: "LIVE PREVIEW", h: 68 }, { font: "500 36px Inter", color: "rgba(255,255,255,.72)", text: "The denoising frames ComfyUI is sending for this run", h: 48 }] } : sample ? { kind: sample.kind, src: sample.src, poster: sample.poster, label: [{ font: "800 52px Archivo, Inter", stretch: "expanded", color: "#27e07f", text: "A REAL RESULT OF THIS GOAL", h: 68 }, { font: "500 36px Inter", color: "rgba(255,255,255,.72)", text: sample.seconds ? `Rendered on the author's machine in ${sample.seconds} s, ${sample.peak_vram_gib} GB peak VRAM` : "Rendered on the author's machine", h: 48 }, { font: "400 31px Inter", color: "rgba(255,255,255,.5)", text: sample.prompt, h: 42 }] } : null), [result, following, sample && sample.id]);
  /* replay: a simulation that follows the real order of this graph. Times are a typical share of the measured total, not a recording, and the page says so */
  const total = (sample && +sample.seconds) || 20;
  const startReplay = () => { if (replay) { setReplay(null); return; } const m = buildModel(shown); setReplay({ m, plan: replayPlan(layoutGraph(shown, { plate: false }), total), t: 0, run: null }); };
  useEffect(() => { if (!replay) return; const T = replay.plan.reduce((a, e) => a + e.seconds, 0), LEN = 16, t0 = performance.now(), iv = setInterval(() => { const k = (performance.now() - t0) / 1000 / LEN; if (k > 1.32) { clearInterval(iv); setReplay(null); return; } const run = replayAt(replay.plan, Math.min(k, 1) * T + (k >= 1 ? 1 : 0)), samp = replay.plan.find((e) => e.kind === "sample"), sr = samp && run.running[samp.id]; run.noise = samp ? (run.done.includes(samp.id) ? 0 : sr ? 1 - sr[0] / sr[1] : 1) : 0; run.replay = true; setReplay((r) => r && { ...r, run }); }, 110); return () => clearInterval(iv); }, [replay && replay.plan]);
  const nameOf = (id) => (shown && shown[id] && shown[id].class_type) || id;
  const liveRun = !following ? null : live.running && live.mode === "nodes" ? { running: live.nodes.running, done: live.nodes.done, cached: live.nodes.cached, error: live.nodes.error, times: live.nodes.times, vram: live.nodes.vram, preview: live.preview > 0 } : live.finished && live.nodes ? { running: {}, done: live.nodes.done, cached: live.nodes.cached, error: live.nodes.error, times: live.nodes.times, vram: live.nodes.vram } : null, pulse = following && live.running && live.mode !== "nodes";
  const run = replay && replay.run ? replay.run : liveRun || (pulse ? { pulse: true } : null), rn = replay && replay.run ? Object.keys(replay.run.running)[0] : following && live.running && live.nodes ? Object.keys(live.nodes.running)[0] : null, rv = rn && (replay && replay.run ? replay.run.running[rn] : live.nodes.running[rn]);
  const liveLine = replay ? html`<b>Replay, simulated.</b> It follows the real order of this graph. Each node's time is a typical share of ${total} s, not a recording.` : following && live.running && live.mode === "nodes" ? html`<b>Live.</b> ComfyUI is running ${rn ? html`<b>${nameOf(rn)}</b>${rv && rv[1] ? `, step ${rv[0]} of ${rv[1]}` : ""}` : "this graph"}.<small>This is the exact graph in ComfyUI's queue. ${live.nodes.done.length + live.nodes.cached.length} of ${Object.keys(shown || {}).length} nodes finished.</small>` : pulse ? html`<b>ComfyUI is running this graph.</b><small>The node by node feed is not available for this job, so every node pulses.</small>` : following && live.finished && live.nodes ? html`<b>Finished.</b> Times on the nodes are what ComfyUI just reported.` : live.running && !following ? html`ComfyUI is running another job. <button class="btn small" onClick=${() => { setDrop(null); setWatch(live.job); }}>Watch it inside</button>` : null;
  const copy = async () => { const t = JSON.stringify(shown, null, 1); let ok = false; try { await navigator.clipboard.writeText(t); ok = true; } catch { const a = document.createElement("textarea"); a.value = t; document.body.appendChild(a); a.select(); try { ok = document.execCommand("copy"); } catch {} a.remove(); } if (window.studioToast) window.studioToast(ok ? "ok" : "warn", ok ? (req && req.fills.length ? "Graph copied. Swap the placeholder file names for your own." : "Graph copied. Paste it into ComfyUI to keep going.") : "Copy was blocked by the browser."); };
  const seg = html`<span class="g3d-seg" role="group" aria-label="view"><button class=${view === "3d" && !noGL ? "on" : ""} onClick=${() => { setNoGL(""); setView("3d"); }} aria-pressed=${view === "3d" && !noGL}>3D</button><button class=${view === "flat" || noGL ? "on" : ""} onClick=${() => setView("flat")} aria-pressed=${view === "flat" || !!noGL}>Flat</button></span>`;
  const picker = html`<${ProPicker} rows=${every.rows} counts=${every.counts} pick=${pick} onPick=${setPick}/>`;
  const tools = html`${picker}${seg}<${OpenComfy} health=${health}/><button class="btn small" disabled=${!shown} onClick=${copy}>Copy graph</button>`;
  if (pick && picked && !hasGraph(pick)) return html`<div class="lk"><div class="g3d-flatbar">${picker}</div><section class="apinotgraph" aria-label=${pick.label}><h2 style="margin:0 0 6px">${pick.label}</h2><p><b>${pick.runs_as}.</b> So there is no graph to draw. ${pick.sub}</p><pre class="apicode"><code>${pick.call.method} ${pick.call.path}\n${JSON.stringify(pick.call.body, null, 1)}\n\nthen GET ${pick.call.poll}</code></pre><div class="row"><a class="btn small" href=${"#" + pick.open}>Open it</a><button class="btn small" onClick=${() => { try { sessionStorage.setItem("api_pick", pick.key); } catch {} location.hash = "api"; }}>Use it from code</button></div></section></div>`;
  if (pick && picked && !shown) return html`<div class="lk"><div class="g3d-flatbar">${picker}</div><p class="small">${picked.format === "ui" ? "Start the main ComfyUI to turn this workflow into a graph here." : "This one writes its plan first, so its graphs are built when it runs."}</p></div>`;
  const chips = html`<div class="g3d-chips" role="listbox" aria-label="which graph">${Object.values(goals || {}).sort((a, b) => (FLAGSHIPS.indexOf(b.id) >= 0) - (FLAGSHIPS.indexOf(a.id) >= 0)).map((x) => html`<button role="option" aria-selected=${!pick && x.id === goal} class=${"chip" + (!pick && x.id === goal ? " on" : "")} onClick=${() => { setPick(null); dispatchEvent(new CustomEvent("prime-action", { detail: { type: "set_goal", goal: x.id } })); }}>${x.label}</button>`)}</div>`;
  const quote = req && req.body.prompt ? String(req.body.prompt) : "", note = following ? null : html`<p class="g3d-note">${req && req.sampled ? html`<b>Sample prompt.</b> Write your own in Create: ` : ""}${quote && !(g && g.prompt_optional && !String(draft.prompt || "").trim()) ? `"${quote}"` : ""}${req && req.fills.length ? html` <b>Add your ${req.fills.map((f) => f.replace("_", " ")).join(" and ")} in Create;</b> the file names here are placeholders.` : ""}${req && req.previewSeed ? " Seed 11 is a preview; Generate draws a new one unless you set it." : ""}</p>`;
  if (view === "flat" || noGL) return html`<div><div class="g3d-flatbar">${seg}<${OpenComfy} health=${health}/><button class="btn small" disabled=${!shown} onClick=${copy}>Copy graph</button></div>${noGL && html`<p class="small warn" style="margin:0 0 10px">${noGL}</p>`}<p class="small" style="max-width:760px;margin:0 0 10px">This is the real ComfyUI graph for your current settings. The same graph runs when you press Generate.</p>${err && html`<p class="small" style="color:var(--err)">${err}</p>`}<${GraphView} graph=${shown}/></div>`;
  return html`<${Graph3D} graph=${shown} title=${pick ? pick.label : following && !mine ? "This run" : g ? g.label : goal} family=${pick ? pick.sub : following && !mine ? "" : g && g.family} note=${pick ? html`<p class="g3d-note">${pick.runs_as}.${pickErr ? " " + pickErr : ""}</p>` : note} chips=${chips} tools=${tools} run=${pick ? null : run} media=${pick || (g && g.kind === "audio") ? null : media} previewUrl=${!replay && following && live.running && live.preview ? `/api/live/preview?seq=${live.preview}` : ""} liveLine=${liveLine} error=${!shown && err ? err : ""} noPlate=${!!pick || !!(g && g.kind === "audio")} replaying=${!!replay} onReplay=${startReplay} onFail=${(m) => setNoGL(m)}/>`;
}

/* ---------- shell ---------- */
const TABS = [["create", "Create"], ["shots", "Shot Board"], ["library", "Library"], ["families", "Families"], ["atlas", "Atlas"], ["recipes", "Recipes"], ["pipelines", "Pipelines"], ["future", "Future"], ["apps", "Apps"], ["processes", "Processes"], ["design", "Design"], ["auto", "Auto"], ["edit", "Edit"], ["university", "Learn"], ["models", "Models"], ["crew", "Crew"], ["site", "Sites"], ["viewer", "3D"], ["worldkit", "World Kit"], ["train", "Train"], ["virtualset", "Virtual Set"], ["sampling", "Sampling"], ["res4lyf", "RES4LYF"], ["api", "API"], ["pro", "Pro"]];
const TITLES = { pipelines: ["Pipelines", "Many models. One result.", "Every stage below ran on one shared graphics card. Its real output, model, seed, time, peak memory and licence are all here, and so is what failed."], future: ["The future", "Of generative AI, as we see it."], res4lyf: ["RES4LYF", "A thank-you to ClownsharkBatwing's sampling node pack."], sampling: ["Sampling Lab", "Noise in. A picture out. The code between."], train: ["Train", "Your pictures in. A LoRA out."], virtualset: ["Virtual Set", "A 3D scene in. A directed video out."], worldkit: ["World Kit", "Real-scale 3D, built on this machine."], shots: ["Shot Board", "One clip in. A whole shoot out."], api: ["API", "Every graph, callable from anything."], processes: ["Processes", "Every way we make things.", "Every process from the earlier studio: what opens here today, what is coming soon, and a guide for each."], recipes: ["Recipes", "One idea in. A finished piece out.", "Models chained together: music videos, short films, product ads and more."], create: ["Create", "Pick what you want to make, describe it, and generate."], library: ["Library", "Everything you have made."], families: ["Model families", "Every model. Its real state.", "Every model on this machine, with its own ComfyUI, its real state and what it has made."], atlas: ["Atlas", "Every model, in order.", "Generative AI from 2013 to today: what each model was, its licence, and whether this studio runs it."], apps: ["ComfyUI Apps", "Every graph, one click away.", "Any ComfyUI app, as a simple form."], auto: ["Auto", "Set it. Forget it.", "Scheduled creations."], design: ["Designers", "A few choices in. A whole sheet out.", "Products, vehicles, settings, fashion and more, as whole sheets."], edit: ["Edit", "AI edits, then a timeline.", "AI video edits, and a timeline to cut it all together."], university: ["ComfyUniversity", "Learn ComfyUI by doing it."], models: ["Models", "What runs here, and what to fetch.", "What runs on this machine, and where to find more."], crew: ["The Crew", "Specialists who show their sources.", "Specialists who know every model, and show their sources."], site: ["Site builder", "Facts in. A clean website out."], viewer: ["3D viewer", "Orbit your 3D results."], pro: ["Pro mode", "The exact graph behind every result."] };
/* the pages on the shared look (looks.css). The other pages bring their own title block, and Recipes and Learn are being worked on elsewhere. */
const LOOK = new Set(["pipelines", "future", "create", "library", "families", "atlas", "apps", "processes", "design", "auto", "edit", "models", "crew", "site", "viewer", "api", "pro"]);
function App() {
  const [tab, setTab] = useState((location.hash || "#create").slice(1)); const [health, setHealth] = useState(null); const [draft, setDraft] = useState(null); const [pinned, setPinned] = useState(null);
  const [phone, setPhone] = useState(false); const [pal, setPal] = useState(false), [help, setHelp] = useState(false), [tour, setTour] = useState(false), [toasts, setToasts] = useState(createToasts()), [goalsList, setGoalsList] = useState({});
  useEffect(() => { window.studioToast = (kind, text) => setToasts((s) => pushToast(s, { kind, text, now: Date.now() })); const t = setInterval(() => setToasts((s) => expire(s, Date.now())), 500); return () => clearInterval(t); }, []);
  useEffect(() => { api("/api/goals").then(setGoalsList).catch(() => {}); }, []);
  const [fx, setFx] = useState([]), [fxReady, setFxReady] = useState(false);
  useEffect(() => { loadFeaturePages().then((p) => { setFx(p); setFxReady(true); }); }, []);
  const opening = !fxReady && !TITLES[tab.split("/")[0]] && tab.split("/")[0];      // a direct link to a page still loading: wait for it, not Create
  const tabs = [...TABS, ...fx.map((p) => [p.tab, p.label])], titles = { ...TITLES, ...Object.fromEntries(fx.map((p) => [p.tab, p.title])), ...(opening ? { [opening]: ["\u00a0", "Opening"] } : {}) }, page = fx.find((p) => p.tab === tab.split("/")[0]);
  useEffect(() => {
    const k = (e) => { const typing = /^(INPUT|TEXTAREA|SELECT)$/.test((e.target || {}).tagName || "") || (e.target || {}).isContentEditable;
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setPal((v) => !v); } else if (!typing && e.key === "?") setHelp((v) => !v); };
    addEventListener("keydown", k); return () => removeEventListener("keydown", k);
  }, []);
  useEffect(() => { let st = null; try { st = localStorage.getItem("tour"); } catch {} if (shouldAutoStart(st) && !matchMedia("(max-width: 700px)").matches) { const t = setTimeout(() => setTour(true), 1800); return () => clearTimeout(t); } }, []);
  useEffect(() => { const f = () => setTab((location.hash || "#create").slice(1)); addEventListener("hashchange", f); return () => removeEventListener("hashchange", f); }, []);
  useEffect(() => { const f = () => api("/api/health").then(setHealth).catch(() => setHealth({ comfy: false })); f(); const t = setInterval(f, 15000); return () => clearInterval(t); }, []);
  const go = (t) => { const set = async () => { location.hash = t; await new Promise((r) => setTimeout(r, 70)); }; if (document.startViewTransition && !matchMedia("(prefers-reduced-motion: reduce)").matches) document.startViewTransition(set); else location.hash = t; };
  const tb = tab.split("/")[0], t = titles[tb] ? tb : "create";
  useEffect(() => { document.body.classList.toggle("on-create", t === "create"); document.body.classList.toggle("on-look", LOOK.has(t)); document.body.classList.toggle("on-fx", !!page); if (matchMedia("(max-width: 900px)").matches) { const n = document.querySelector(".rail .nav.on"); if (n) n.scrollIntoView({ inline: "center", block: "nearest" }); } }, [t, !!page]);
  // A graph opened from elsewhere stays pinned while Pro is open: Create keeps publishing its own draft in the background. Picking a graph in Pro goes back to Create's.
  useEffect(() => { const f = (e) => { setPinned(e.detail); location.hash = "pro"; }, un = (e) => { if ((e.detail || {}).type === "set_goal") setPinned(null); }; addEventListener("studio-graph", f); addEventListener("prime-action", un); return () => { removeEventListener("studio-graph", f); removeEventListener("prime-action", un); }; }, []);
  useEffect(() => { if (t !== "pro") setPinned(null); }, [t]);
  return html`<div style="display:contents"><nav class="rail" aria-label="main"><div class="logo">P</div>${tabs.map(([k, l]) => html`<button class=${"nav" + (t === k ? " on" : "")} onClick=${() => go(k)} aria-label=${l}><${Icon} n=${k === "university" ? "uni" : k}/>${l}</button>`)}<div class="spacer"></div><button class="nav" onClick=${() => setPhone(true)} aria-label="Use on your phone"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="7" y="2.5" width="10" height="19" rx="2.2"/><path d="M11 18.5h2"/></svg>Phone</button></nav>
    <main><div class="top"><div><h1 style=${{ "--tn": Math.max(...titles[t][0].split(" ").map((w) => w.length)) }}>${titles[t][0]}</h1><div class="sub small">${titles[t][1]}</div>${titles[t][2] && html`<p class="lede">${titles[t][2]}</p>`}</div><span class="grow"></span>
      <span class="pill"><span class=${"dot " + (health ? (health.comfy ? "ok" : "bad") : "")}></span>${comfyPill(health)}</span>${health && health.gpu && html`<span class="pill">GPU ${health.gpu.vram_free_gb} of ${health.gpu.vram_total_gb} GB free</span>`}${!isDemo(health) && html`<span class="pill">${(health && health.edition) || "open"} edition, runs locally</span>`}</div>
      <div style=${{ display: t === "create" ? "block" : "none" }}><${Create} health=${health} onDraft=${setDraft} goTab=${go}/></div>
${page && html`<${page.Page} route=${tab} health=${health} goTab=${go}/>`}${t === "pipelines" && html`<${Pipelines} route=${tab} health=${health}/>`}${t === "future" && html`<${Future} goTab=${go}/>`}${t === "res4lyf" && html`<${Res4lyf}/>`}${t === "sampling" && html`<${SamplingLab} route=${tab}/>`}      ${t === "train" && html`<${Train} route=${tab}/>`}${t === "shots" && html`<${ShotBoard}/>`}${t === "library" && html`<${Library}/>`}${t === "recipes" && html`<${Recipes} route=${tab}/>`}${t === "api" && html`<${ApiPage} goTab=${go}/>`}${t === "families" && html`<${Families} route=${tab} goTab=${go}/>`}${t === "atlas" && html`<${Atlas}/>`}${t === "processes" && html`<${Processes} goTab=${go}/>`}${t === "university" && html`<${University} route=${tab}/>`}${t === "models" && html`<${Models}/>`}${t === "apps" && html`<${Apps}/>`}${t === "design" && html`<${Designers} route=${tab} health=${health}/>`}${t === "edit" && html`<${EditHub}/>`}${t === "auto" && html`<${Schedules}/>`}${t === "crew" && html`<${Crew}/>`}${t === "site" && html`<${Site}/>`}${t === "viewer" && html`<${Studio3D}/>`}${t === "worldkit" && html`<${WorldKit} route=${tab}/>`}${t === "virtualset" && html`<${VirtualSet} route=${tab}/>`}${t === "pro" && html`<${Pro} draft=${pinned || draft} health=${health} goals=${goalsList}/>`}
    </main>
    <${PrimeDock} goal=${draft && draft.goal}/>
    <${Toasts} state=${toasts} onDismiss=${(id) => setToasts((s) => ({ ...s, items: s.items.filter((x) => x.id !== id) }))}/>
    ${phone && html`<${PhonePanel} onClose=${() => setPhone(false)}/>`}
    ${pal && html`<${Palette} items=${[...tabs.map(([k, l]) => ({ id: "tab:" + k, label: "Go to " + l, hint: "tab", keywords: k })), ...Object.entries(goalsList).map(([k, g]) => ({ id: "goal:" + k, label: "Make: " + g.label, hint: g.family, keywords: g.tagline })), { id: "act:tour", label: "Show me around", hint: "guided tour", keywords: "help walkthrough tutorial" }, { id: "act:help", label: "Keyboard shortcuts", hint: "?", keywords: "keys hotkeys" }]} onPick=${(it) => { const [kind, v] = it.id.split(":"); if (kind === "tab") go(v); else if (kind === "goal") { go("create"); setTimeout(() => dispatchEvent(new CustomEvent("prime-action", { detail: { type: "set_goal", goal: v } })), 80); } else if (v === "tour") setTour(true); else setHelp(true); }} onClose=${() => setPal(false)}/>`}
    ${help && html`<${ShortcutHelp} registry=${{ list: () => [{ combo: "ctrl+k", label: "Open the command palette" }, { combo: "?", label: "Show this help" }, { combo: "ctrl+enter", label: "Generate (in the prompt box)" }] }} onClose=${() => setHelp(false)}/>`}
    ${tour && html`<${Tour} steps=${TOUR} onClose=${() => { setTour(false); try { localStorage.setItem("tour", "done"); } catch {} }} speak=${(t) => { if (window.primeSpeak) return window.primeSpeak(t); try { if (localStorage.getItem("prime_voice") !== "off" && "speechSynthesis" in window) { speechSynthesis.cancel(); const u = new SpeechSynthesisUtterance(t); u.pitch = 1.05; speechSynthesis.speak(u); } } catch {} }}/>`}
  </div>`;
}
const isDemo = (health) => !!health && health.edition === "demo";
const comfyPill = (health) => (!health ? "checking" : isDemo(health) ? "Read-only demo" : health.comfy ? "ComfyUI ready" : "ComfyUI offline");
const OpenComfy = ({ health }) => (health && /^https?:/.test(health.comfy_url || "") ? html`<a class="btn small" href=${health.comfy_url} target="_blank" rel="noopener noreferrer">Open ComfyUI</a>` : null);
const TOUR = [
  { id: "hi", target: null, title: "Welcome to Parametric Studio", text: "Hi, I'm Comfy Prime. I'll show you around in a minute. Everything here runs on your own machine, and you can always see the exact ComfyUI graph behind any result." },
  { id: "nav", target: ".rail", title: "Your studios", text: "Create makes images, video and music. Design builds products, vehicles and more. Edit holds AI video editing. Learn is the University. Pro shows the real node graph." },
  { id: "goals", target: ".gdeck", title: "Pick what to make", text: "Each tile is a model family. The badge shows its licence. Tiles for models you have not downloaded yet will offer a download button.", tab: "create" },
  { id: "composer", target: ".cpanel", title: "Describe it", text: "Write what you want, choose a shape and speed, and press Generate. Control plus Enter works too." },
  { id: "shots", target: '.rail [aria-label="Shot Board"]', title: "Shot Board", text: "Give me one clip and pick the jobs: a new camera move, a full orbit, a new lead, or VFX. They run one at a time, and you can export them all as one video." },
  { id: "pal", target: null, title: "Command palette", text: "Press Control K anywhere to jump to a studio or start a creation. Press the question mark for shortcuts." },
  { id: "prime", target: ".orb", title: "Talk to me", text: "Click my orb any time. Tell me your name, ask how a model works, or say what you want to make, and I'll set it up. I never start a render without you.", },
  { id: "learn", target: null, title: "Learn as you go", text: "Open Learn for lessons from first steps to attention and latent space, each with a lab that runs on your computer.", tab: "university" },
];
render(html`<${App}/>`, document.getElementById("app"));
installTilt();
