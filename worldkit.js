// World Kit page, a prop shop: make a place, a prop, a look or a character (described in words, then checked); the shelf with search and filters; the 3D viewer; approve for sets; archive (never a hard delete);
// retry a failed step; export approved assets as a game pack. Routes: /api/worldkit/* (studio/worldkit/api.py). Look: worldkit.css.
import { useEffect, useRef, useState } from "preact/hooks";
import { html, api, post } from "./common.js";
import { Viewer3D } from "./viewer3d.js";
import { SAMPLES } from "./wk_example.js";
import { TYPES, TYPE_LABELS, PROP_SOURCES, fileUrl, exportUrl, statusChip, summaryOf, filterAssets, canApprove, canRetry, canMakeProp, createPayload, meshChoices, stepRows, addClip, blockers, makerBoard, stepLabel, stepDone, scaleCompare, shopCounts, firstAsset, nextStep, START_CLIPS, MAX_CLIPS, CHARACTER_IDEAS, clipSlug, clipProblem, sheetState, sheetUrl, CHARACTER_ROUGH } from "./worldkit_helpers.js";

const errText = (e) => String((e && e.message) || e);
const BLANK = { name: "", tags: "", characterId: "", prompt: "", image: "", mesh: "", meshModel: "", via: "mesh", size: "", brief: "", preset: "", time: "", weather: "", textures: "" };
const Chip = ({ c }) => html`<span class=${"wk-chip " + c.cls}>${c.label}</span>`;
const quiet = () => typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;
const STEP_MARK = { done: "M4 12l5 5 11-11", skipped: "M5 12h14", failed: "M6 6l12 12 M18 6L6 18", running: "M12 4a8 8 0 1 0 8 8" };

function Needs({ problems }) {
  if (!problems.length) return null;
  return html`<div class="wk-needs" role="status"><b>Not ready on this machine</b>${problems.map((p) => html`<p>${p}</p>`)}</div>`;
}

const MAX_DESCRIPTION = 400;
const HEIGHTS = { lo: 1.5, hi: 2.0 };

// The sheet's stage: an empty frame, the work in progress, the reason it did not pass, or the picture itself.
function SheetStage({ ch, onAgain, onReword, onDelete, busy }) {
  const state = sheetState(ch);
  if (!ch) return html`<div class="wk-sheet film is-empty"><svg viewBox="0 0 80 190" aria-hidden="true"><circle cx="40" cy="24" r="17"/><path d="M14 58c0-9 8-14 26-14s26 5 26 14v52H52v76H28v-76H14z"/></svg><p>The full-body sheet appears here. It is the picture the 3D character is built from.</p></div>`;
  const working = ch.running || ch.status === "building";
  return html`<div class=${"wk-sheet film" + (ch.sheet ? "" : " is-empty")}>
    ${ch.sheet ? html`<img src=${sheetUrl(ch.id, ch.take)} alt=${"Full-body sheet of " + ch.name} width="832" height="1216"/>` : working ? html`<div class="wk-sheetwork" role="status"><i aria-hidden="true"></i><b>Making ${ch.name}</b><p>A picture from your words, then the picture check. Usually about a minute.</p></div>`
      : html`<div class="wk-sheetwhy"><b>${state.label === "did not pass" ? "This sheet did not pass" : state.label === "interrupted" ? "The studio restarted while this was being made" : "The sheet could not be made"}</b>${ch.error && html`<p>${ch.error}</p>`}${state.label === "did not pass" && html`<p>The picture was thrown away. Often a clearer face or plainer clothes in the words fixes it.</p>`}</div>`}
    <div class="wk-sheetbar"><span class="wk-sheetname"><b>${ch.name}</b><${Chip} c=${state}/></span>
      <span class="wk-sheetbtns"><button type="button" class="btn small" disabled=${working || busy} onClick=${onAgain}>${ch.sheet ? "Another take" : "Try again"}</button><button type="button" class="btn small" disabled=${working || busy} onClick=${onReword}>Reword</button><button type="button" class="btn small" disabled=${working || busy} onClick=${onDelete}>Delete</button></span></div>
  </div>`;
}

const Rough = () => html`<section class="wk-rough" aria-label="Still rough"><b>Still rough</b><ul>${CHARACTER_ROUGH.map((t) => html`<li>${t}</li>`)}</ul></section>`;

function Motions({ rows, onChange }) {
  const put = (i, k, v) => onChange(rows.map((r, j) => (j === i ? { ...r, [k]: v } : r)));
  return html`<fieldset class="wk-motions"><legend>What it can do</legend>
    ${rows.map((r, i) => html`<div class="wk-motion"><label class="wk-f"><span>Motion name</span><input class="wk-in" type="text" maxlength="24" value=${r.name} onInput=${(e) => put(i, "name", clipSlug(e.target.value))}/></label>
      <label class="wk-f"><span>What happens</span><input class="wk-in" type="text" placeholder="a person sits down on a chair" value=${r.text} onInput=${(e) => put(i, "text", e.target.value)}/></label>
      <button type="button" class="btn small" aria-label=${"Remove the motion " + (r.name || i + 1)} onClick=${() => onChange(rows.filter((_, j) => j !== i))}>Remove</button></div>`)}
    ${rows.length < MAX_CLIPS && html`<button type="button" class="btn small" onClick=${() => onChange([...rows, { name: "", text: "" }])}>Add a motion</button>`}</fieldset>`;
}

// The Character tab: words -> a checked sheet -> motions -> a rigged character on the shelf. No upload exists at any point.
function CharacterBench({ caps, reloadCaps, onCreated }) {
  const [data, setData] = useState({ characters: [], enabled: true, message: "", limits: "" }), [sel, setSel] = useState(""), [form, setForm] = useState({ name: "", description: "" }), [build, setBuild] = useState({ name: "", tags: "", height: "1.7", clips: START_CLIPS }), [err, setErr] = useState(""), [busy, setBusy] = useState(false), [loaded, setLoaded] = useState(false);
  const alive = useRef(true);
  const load = () => api("/api/worldkit/characters").then((d) => { if (alive.current) { setData(d); setLoaded(true); } }).catch((e) => alive.current && setErr(errText(e)));
  useEffect(() => { alive.current = true; load(); return () => { alive.current = false; }; }, []);
  const anyRunning = data.characters.some((c) => c.running);
  useEffect(() => { if (!anyRunning) return undefined; const t = setInterval(load, 2500); return () => clearInterval(t); }, [anyRunning]);
  const ch = data.characters.find((c) => c.id === sel) || (sel ? null : data.characters.find((c) => c.ok) || data.characters[0] || null);
  const sheetBlock = blockers(caps, "character_sheet"), buildBlock = blockers(caps, "character").filter((p) => !sheetBlock.includes(p));
  const clipBad = clipProblem(build.clips), h = parseFloat(build.height), heightBad = !(h >= HEIGHTS.lo && h <= HEIGHTS.hi) ? `Height is ${HEIGHTS.lo} to ${HEIGHTS.hi} metres.` : "";
  const guard = async (fn) => { setBusy(true); setErr(""); try { await fn(); } catch (x) { setErr(errText(x)); reloadCaps(); } finally { setBusy(false); load(); } };
  const makeSheet = (e) => { e.preventDefault(); guard(async () => { const r = await post("/api/worldkit/characters", { name: form.name.trim(), description: form.description.trim() }); setSel(r.id); setForm({ name: "", description: "" }); }); };
  const again = () => guard(() => post(`/api/worldkit/characters/${encodeURIComponent(ch.id)}/again`, {}));
  const reword = () => { setForm({ name: ch.name, description: ch.description || "" }); const n = document.getElementById("wk-chardesc"); if (n) n.focus(); };
  const drop = () => { if (window.confirm(`Delete ${ch.name}'s words and sheet? Anything already built from them stays on the shelf.`)) guard(async () => { await api(`/api/worldkit/characters/${encodeURIComponent(ch.id)}`, { method: "DELETE" }); setSel(""); }); };
  const makeCharacter = (e) => { e.preventDefault(); guard(async () => { const r = await post("/api/worldkit/assets", createPayload("character", { name: build.name, tags: build.tags, characterId: ch.id, height: build.height, clips: build.clips })); onCreated(r.asset.id); }); };
  const ready = !!(ch && ch.ok);
  if (loaded && !data.enabled) return html`<div class="wk-needs" role="status"><b>Off on this machine</b><p>${data.message}</p></div>`;
  return html`<div class="wk-char">
    <ol class="wk-charsteps" aria-label="From words to a character"><li class=${!ch ? "on" : "done"}><i>1</i>Describe someone</li><li class=${ch && !ready ? "on" : ready ? "done" : ""}><i>2</i>Check the sheet</li><li class=${ready ? "on" : ""}><i>3</i>Choose motions, build</li></ol>
    <div class="wk-chargrid">
      <div class="wk-charside">
        <form class="wk-charform" onSubmit=${makeSheet} aria-label="Describe a character">
          <${Needs} problems=${sheetBlock}/>
          <label class="wk-f"><span>Name</span><input class="wk-in" type="text" maxlength="60" placeholder="An invented name" value=${form.name} onInput=${(e) => setForm({ ...form, name: e.target.value })}/></label>
          <label class="wk-f"><span>Who are they, and what are they wearing?</span><textarea id="wk-chardesc" class="wk-in" rows="4" maxlength=${MAX_DESCRIPTION} placeholder="Age, build, hair, clothes from head to boots" value=${form.description} onInput=${(e) => setForm({ ...form, description: e.target.value })}></textarea></label>
          <div class="wk-ideas" role="group" aria-label="Start from an idea"><small>Or start from</small>${CHARACTER_IDEAS.map(([label, text]) => html`<button type="button" onClick=${() => setForm({ name: form.name, description: text })}>${label}</button>`)}</div>
          <p class="wk-hint">An invented adult, fully clothed. Never a real person, and there is no photo upload. ${form.description.length > MAX_DESCRIPTION - 60 ? `${MAX_DESCRIPTION - form.description.length} letters left.` : ""}</p>
          ${err && html`<p class="wk-err" role="alert">${err}</p>`}
          <button type="submit" class="btn primary wk-go" disabled=${busy || sheetBlock.length > 0 || !form.name.trim() || !form.description.trim()}>${busy ? "Starting" : "Make the sheet"}</button>
        </form>
        ${data.characters.length > 0 && html`<div class="wk-wall"><div class="wk-sechead"><h3>Saved characters</h3><span>${data.characters.length}</span></div>
          <ul>${data.characters.map((c) => { const s = sheetState(c); return html`<li><button type="button" aria-current=${ch && c.id === ch.id ? "true" : undefined} onClick=${() => { setSel(c.id); setErr(""); }}>${c.sheet ? html`<img src=${sheetUrl(c.id, c.take)} alt="" loading="lazy" width="832" height="1216"/>` : html`<span class="wk-noimg" aria-hidden="true">${c.name[0]}</span>`}<b>${c.name}</b><small class=${"wk-sstate " + s.cls}>${s.label}</small></button></li>`; })}</ul></div>`}
      </div>
      <${SheetStage} ch=${ch} busy=${busy} onAgain=${again} onReword=${reword} onDelete=${drop}/>
      ${ready ? html`<form class="wk-charbuild" onSubmit=${makeCharacter} aria-label="Build the 3D character">
        <div class="wk-sechead"><h3>Build ${ch.name} in 3D</h3></div>
        <${Needs} problems=${buildBlock}/>
        <div class="wk-tri"><label class="wk-f"><span>Name on the shelf</span><input class="wk-in" type="text" placeholder=${ch.name} value=${build.name} onInput=${(e) => setBuild({ ...build, name: e.target.value })}/></label>
          <label class="wk-f"><span>Height, metres</span><input class="wk-in" type="text" inputmode="decimal" value=${build.height} onInput=${(e) => setBuild({ ...build, height: e.target.value })}/></label>
          <label class="wk-f"><span>Tags, comma separated</span><input class="wk-in" type="text" value=${build.tags} onInput=${(e) => setBuild({ ...build, tags: e.target.value })}/></label></div>
        <${Motions} rows=${build.clips} onChange=${(clips) => setBuild({ ...build, clips })}/>
        <p class="wk-hint">You get a rigged, moving 3D figure in the sheet's clothes, hair and colour. Every step runs on this machine, and you can watch them on the next screen.</p>
        <${Rough}/>
        ${(clipBad || heightBad) && html`<p class="wk-err">${heightBad || clipBad}</p>`}
        <button type="submit" class="btn primary wk-go" disabled=${busy || buildBlock.length > 0 || !!clipBad || !!heightBad}>${busy ? "Starting" : "Build the character"}</button></form>` : ""}
    </div>
    <details class="wk-limits"><summary>What the checks can and cannot catch</summary><p>${data.limits}</p></details>
  </div>`;
}

function NewAsset({ onCreated, caps, reloadCaps, start, onClose }) {
  const [type, setType] = useState((start && start.type) || "place");
  const [form, setForm] = useState({ ...BLANK, via: (start && start.via) || "mesh" });
  const [looks, setLooks] = useState({ looks: [], times: [], weathers: [] });
  const [meshes, setMeshes] = useState([]);
  const [models3d, setModels3d] = useState([]);
  const [err, setErr] = useState(""), [busy, setBusy] = useState(false);
  useEffect(() => {
    api("/api/worldkit/looks").then(setLooks).catch((e) => setErr(errText(e)));
    api("/api/worldkit/meshes").then((r) => setMeshes(r.items || [])).catch(() => {});
    api("/api/3d/models").then((r) => setModels3d(r.models || [])).catch(() => {});
    reloadCaps();
  }, []);
  useEffect(() => { if (start) { setType(start.type); setForm({ ...BLANK, via: start.via || "mesh" }); setErr(""); } }, [start]);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const upload = async (e) => {
    const f = e.target.files && e.target.files[0]; if (!f) return;
    const b = new FormData(); b.append("file", f);
    try { const r = await api("/api/upload", { method: "POST", body: b }); setForm({ ...form, image: r.name }); } catch (x) { setErr(errText(x)); }
  };
  const create = async (e) => {
    e.preventDefault(); setBusy(true); setErr("");
    try { const r = await post("/api/worldkit/assets", createPayload(type, form)); onCreated(r.asset.id); } catch (x) { setErr(errText(x)); reloadCaps(); } finally { setBusy(false); }
  };
  const problems = blockers(caps, type, form.via);
  const head = html`<div class="wk-newhead"><h2>${type === "character" ? "New character" : "New asset"}</h2>${onClose && html`<button type="button" class="btn small" onClick=${onClose}>Back to the shelf</button>`}</div>
    <div class="wk-types" role="group" aria-label="What to make">${TYPES.map((t) => html`<button type="button" aria-pressed=${type === t} onClick=${() => { setType(t); setForm(BLANK); setErr(""); }}>${TYPE_LABELS[t]}</button>`)}</div>`;
  if (type === "character") return html`<section class="wk-new" aria-label="New character">${head}<${CharacterBench} caps=${caps} reloadCaps=${reloadCaps} onCreated=${onCreated}/></section>`;
  return html`<form class="wk-new" onSubmit=${create} aria-label="New asset">
    ${head}
    <${Needs} problems=${problems}/>
    <div class="wk-fields">
      <label class="wk-f"><span>Name (optional)</span><input class="wk-in" type="text" value=${form.name} onInput=${set("name")} aria-label="Asset name"/></label>
      ${type === "prop" && html`<div class="wk-f wide"><span>Made from</span><div class="wk-types small" role="group" aria-label="Made from">${PROP_SOURCES.map(([k, l]) => html`<button type="button" aria-pressed=${form.via === k} onClick=${() => setForm({ ...form, via: k })}>${l}</button>`)}</div></div>
        ${form.via === "mesh" && html`<label class="wk-f wide"><span>3D result</span><select class="wk-in" aria-label="3D result" value=${form.mesh} onChange=${set("mesh")}><option value="">${meshes.length ? "Pick a 3D result" : "No .glb in the outputs folder yet"}</option>${meshes.map((m) => html`<option value=${m}>${m}</option>`)}</select></label>`}
        ${form.via === "image" && html`<label class="wk-f wide"><span>Picture</span><input class="wk-in" type="file" accept="image/png,image/jpeg,image/webp" onChange=${upload}/></label>${form.image && html`<p class="wk-hint wide">Picture: ${form.image}</p>`}`}
        ${form.via === "text" && html`<label class="wk-f wide"><span>Describe the object</span><textarea class="wk-in" rows="2" value=${form.prompt} onInput=${set("prompt")}></textarea></label>`}
        ${form.via !== "mesh" && html`<label class="wk-f wide"><span>3D model</span><select class="wk-in" aria-label="3D model" value=${form.meshModel} onChange=${set("meshModel")}><option value="">The studio picks</option>${meshChoices(models3d, form.via).map((m) => html`<option value=${m.id}>${m.label}</option>`)}</select></label>`}
        <label class="wk-f wide"><span>Longest side in metres (optional, guessed from the name)</span><input class="wk-in" type="text" inputmode="decimal" value=${form.size} onInput=${set("size")} aria-label="Size in metres"/></label>`}
      ${type === "place" && html`<label class="wk-f wide"><span>The brief</span><textarea class="wk-in" rows="2" placeholder="Rainy downtown block at night, beach boardwalk, cafe interior" value=${form.brief} onInput=${set("brief")}></textarea></label>
        <label class="wk-f wide"><span>Textures</span><select class="wk-in" aria-label="Textures" value=${form.textures} onChange=${set("textures")}>
          <option value="">${caps && caps.textures_generated ? "Generated (FLUX.2 Klein on ComfyUI)" : "Procedural (no model on ComfyUI right now)"}</option>
          <option value="procedural">Procedural, CPU only</option><option value="generated">Always ask ComfyUI</option></select></label>`}
      ${(type === "place" || type === "look") && html`<div class="wk-tri wide">
        <label class="wk-f"><span>Look</span><select class="wk-in" aria-label="Look" value=${form.preset} onChange=${set("preset")}><option value="">${type === "place" ? "From the brief" : "Daylight"}</option>${looks.looks.map((l) => html`<option value=${l.id}>${l.label}</option>`)}</select></label>
        <label class="wk-f"><span>Time of day</span><select class="wk-in" aria-label="Time of day" value=${form.time} onChange=${set("time")}><option value="">The look's</option>${looks.times.map((t) => html`<option value=${t}>${t}</option>`)}</select></label>
        <label class="wk-f"><span>Weather</span><select class="wk-in" aria-label="Weather" value=${form.weather} onChange=${set("weather")}><option value="">The look's</option>${looks.weathers.map((w) => html`<option value=${w}>${w}</option>`)}</select></label></div>`}
      <label class="wk-f wide"><span>Tags, comma separated</span><input class="wk-in" type="text" value=${form.tags} onInput=${set("tags")} aria-label="Tags"/></label>
    </div>
    ${err && html`<p class="wk-err" role="alert">${err}</p>`}
    <button type="submit" class="btn primary wk-go" disabled=${busy || problems.length > 0}>${busy ? "Starting" : "Make it"}</button>
    ${type === "place" && !problems.length && html`<p class="wk-hint">A place needs only Blender. It starts as a draft for you to check.</p>`}
  </form>`;
}

// The hang tag on the screen: the real size, with a 1.8 m person drawn at the same scale.
function ScaleTag({ scale }) {
  const c = scaleCompare(scale);
  if (!c) return null;
  return html`<div class="wk-tag" aria-label=${`Real scale: longest side ${c.text}`}><small>Real scale</small><b>${c.text}</b>
    <div class="wk-ruler" aria-hidden="true"><i style=${{ width: `${Math.max(c.asset * 100, 3)}%` }}></i><svg viewBox="0 0 10 24" style=${{ height: `${Math.max(c.person * 34, 5)}px` }}><circle cx="5" cy="3" r="3"/><path d="M1.5 8h7v8h-2v8h-3v-8h-2z"/></svg></div>
    <small>longest side. Person: 1.8 m</small></div>`;
}

function Steps({ meta }) {
  const rows = stepRows(meta);
  if (!rows.length) return null;
  return html`<section class="wk-steps" aria-label="Making steps"><div class="wk-sechead"><h3>Making steps</h3><span>${stepDone(rows)} of ${rows.length} finished</span></div>
    <ol>${rows.map((r, i) => html`<li class=${"is-" + r.status}><i aria-hidden="true">${STEP_MARK[r.status] ? html`<svg viewBox="0 0 24 24"><path d=${STEP_MARK[r.status]}/></svg>` : i + 1}</i><span><b>${stepLabel(r.name)}</b><small>${r.status}${r.note ? ": " + r.note : ""}</small>${r.error && html`<em>${r.error}</em>`}</span></li>`)}</ol></section>`;
}

function AssetDetail({ id, onChanged, onExport }) {
  const [meta, setMeta] = useState(null), [err, setErr] = useState(""), [clip, setClip] = useState({ name: "", text: "" }), [view, setView] = useState(""), [playing, setPlaying] = useState("");
  const alive = useRef(true);
  const load = () => api(`/api/worldkit/assets/${encodeURIComponent(id)}`).then((m) => { if (alive.current) setMeta(m); }).catch((e) => alive.current && setErr(errText(e)));
  useEffect(() => { alive.current = true; load(); return () => { alive.current = false; }; }, [id]);
  useEffect(() => { if (!meta || !meta.running) return undefined; const t = setInterval(load, 3000); return () => clearInterval(t); }, [meta && meta.running]);
  const act = async (verb, body) => {
    try { const r = await post(`/api/worldkit/assets/${encodeURIComponent(id)}/${verb}`, body || {}); setErr(""); onChanged(r.asset ? r.asset.id : ""); } catch (e) { setErr(errText(e)); }
    if (verb !== "archive") load();
  };
  if (!meta) return html`<div class="wk-stage film wk-loading"><p>${err || "Loading..."}</p></div>`;
  const sum = summaryOf(meta), files = meta.files || {}, glb = files["asset.glb"], turn = files["preview.mp4"];
  const shown = view && files[view === "3d" ? "asset.glb" : "preview.mp4"] ? view : glb ? "3d" : turn ? "turn" : "";
  const clipNames = (meta.clips || []).map((c) => c.name), sheetId = meta.type === "character" && meta.source && meta.source.character_id;
  return html`<section class="wk-stage film" aria-label=${meta.name}>
    <div class="wk-screen">
      ${glb && shown === "3d" && html`<${Viewer3D} key=${meta.id} url=${fileUrl(meta.id, "asset.glb")} height="clamp(300px,58vh,660px)" background=${0x0b0d0b} spin=${!playing} grid=${meta.type !== "look"} clip=${playing} label=${"3D view of " + meta.name}/>`}
      ${turn && shown === "turn" && html`<video class="wk-turn" src=${fileUrl(meta.id, "preview.mp4")} controls loop muted playsinline autoplay=${!quiet()} aria-label=${"Turntable of " + meta.name}></video>`}
      ${!shown && (sheetId ? html`<div class="wk-noview has-sheet"><img src=${sheetUrl(sheetId)} alt="" width="832" height="1216" onError=${(e) => { e.target.style.display = "none"; }}/><p>${meta.running ? "Being built from this sheet. The turntable and the 3D file appear here when the steps finish." : "Nothing to look at yet."}</p></div>` : html`<div class="wk-noview">${meta.running ? "Being built. The turntable and the 3D file appear here when the steps finish." : "Nothing to look at yet."}</div>`)}
      ${glb && shown === "3d" && clipNames.length > 0 && html`<div class="wk-clipbar" role="group" aria-label="Play a motion"><button type="button" aria-pressed=${!playing} onClick=${() => setPlaying("")}>Still</button>${clipNames.map((n) => html`<button type="button" aria-pressed=${playing === n} onClick=${() => setPlaying(n)}>${n}</button>`)}</div>`}
      <${ScaleTag} scale=${meta.scale_m}/>
      ${glb && turn && html`<div class="wk-viewswitch" role="group" aria-label="How to look at it"><button type="button" aria-pressed=${shown === "3d"} onClick=${() => setView("3d")}>3D</button><button type="button" aria-pressed=${shown === "turn"} onClick=${() => setView("turn")}>Turntable</button></div>`}
    </div>
    <div class="wk-plate">
      <div class="wk-platehead"><p class="wk-kicker">${TYPE_LABELS[meta.type]}${meta.colliders ? `, ${meta.colliders} ${meta.colliders === 1 ? "collider" : "colliders"}` : ""}</p><h2 tabindex="-1" id="wk-name">${meta.name}</h2><${Chip} c=${statusChip(sum)}/></div>
      <div class="wk-actions">
        ${canApprove(sum) && html`<button type="button" class="btn primary wk-go" onClick=${() => act("approve")}>Approve for sets</button>`}
        ${meta.status === "approved" && html`<a class="btn wk-go ghost" href="#virtualset">Use in Virtual Set</a>`}
        ${meta.status === "approved" && html`<button type="button" class="btn small" onClick=${onExport}>Go to export</button><button type="button" class="btn small" onClick=${() => act("unapprove")}>Unapprove</button>`}
        ${canRetry(sum) && html`<button type="button" class="btn primary wk-go" onClick=${() => act("retry")}>Retry</button>`}
        ${meta.running && html`<button type="button" class="btn small" onClick=${() => act("cancel")}>Cancel</button>`}
        ${canMakeProp(meta) && html`<button type="button" class="btn small" onClick=${() => act("as-prop")}>Use as a static prop</button>`}
        <button type="button" class="btn small" disabled=${meta.running} onClick=${() => { if (window.confirm("Move this asset to the archive? Nothing is deleted.")) act("archive"); }}>Archive</button>
      </div>
      <p class="wk-next">${nextStep(sum)}${meta.type === "prop" && meta.scale_m ? " A prop made without a size has its scale guessed from its name, so check the tag." : ""}</p>
    </div>
    ${err && html`<p class="wk-err" role="alert">${err}</p>`}
    ${meta.build.error && html`<p class="wk-err">${meta.build.error}</p>`}
    <${Steps} meta=${meta}/>
    ${meta.type === "character" && html`<section class="wk-clips" aria-label="Motion clips"><div class="wk-sechead"><h3>Motion clips</h3><span>${clipNames.join(", ") || "none yet"}</span></div>
      ${(sum.lost_motions || []).map((n) => html`<p class="wk-lost" role="status"><span><b>${n}</b> did not make it into this character. The build went on without it.</span> <button type="button" class="btn small" disabled=${meta.running} onClick=${() => act("retry-motion", { name: n })}>Retry ${n}</button></p>`)}
      <div class="wk-tri"><label class="wk-f"><span>Clip name (lowercase)</span><input class="wk-in" type="text" value=${clip.name} onInput=${(e) => setClip({ ...clip, name: e.target.value })}/></label>
        <label class="wk-f"><span>What happens</span><input class="wk-in" type="text" placeholder="a person sits down on a chair" value=${clip.text} onInput=${(e) => setClip({ ...clip, text: e.target.value })}/></label>
        <button type="button" class="btn small" disabled=${meta.running || !clip.name || !clip.text} onClick=${() => act("clips", { clips: addClip(meta.recipe.clips, clip.name, clip.text) })}>Add clip</button></div></section>`}
    ${meta.type === "character" && html`<${Rough}/>`}
    <p class="wk-lic"><b>Licences (for your information):</b> ${meta.licence_note}</p>
  </section>`;
}

function ExportPack({ approved }) {
  const [name, setName] = useState("my-game"), [res, setRes] = useState(null), [err, setErr] = useState(""), [busy, setBusy] = useState(false);
  const run = async () => { setBusy(true); setErr(""); setRes(null); try { setRes(await post("/api/worldkit/export", { name })); } catch (e) { setErr(errText(e)); } finally { setBusy(false); } };
  return html`<section class="wk-export" id="wk-export" aria-label="Export for a game"><p class="wk-kicker">Crate it up</p><h3>Export for a game</h3><p>Approved assets as .glb files, a manifest and a Godot 4 scene, in one zip.</p>
    <p class="wk-crate"><b>${approved}</b><span>${approved === 1 ? "asset" : "assets"} approved and ready to pack</span></p>
    <div class="wk-inline"><label class="wk-f"><span>Pack name</span><input class="wk-in" type="text" value=${name} onInput=${(e) => setName(e.target.value)} aria-label="Pack name"/></label><button type="button" class="btn primary" disabled=${busy} onClick=${run}>${busy ? "Packing" : "Export approved"}</button></div>
    ${err && html`<p class="wk-err" role="alert">${err}</p>`}
    ${res && html`<p class="wk-done"><a href=${exportUrl(res.zip)} download>${res.zip}</a> (${res.assets} assets)</p>`}</section>`;
}

function Workshop({ caps, onPick }) {
  return html`<section class="wk-bench" aria-label="What can be made on this machine"><div class="wk-sechead"><h3>The workshop, on this machine</h3><span>${caps ? "Read from this machine" : "Checking"}</span></div>
    <ul>${makerBoard(caps).map((m) => html`<li class=${"is-" + m.cls}><i aria-hidden="true"></i><div><b>${m.label}</b><strong>${m.state}</strong>${m.why && html`<p>${m.why}</p>`}${m.more.length > 0 && html`<details><summary>What is missing</summary>${m.more.map((x) => html`<p>${x}</p>`)}</details>`}</div>
      <button type="button" class="btn small" aria-label=${(m.cls === "ok" ? "Make: " : "See: ") + m.label} onClick=${() => onPick(m)}>${m.cls === "ok" ? "Make" : "See"}</button></li>`)}</ul></section>`;
}

function Flow({ counts, filters, showNew, onMake, onFilter, onExport }) {
  const steps = [["Make", `${counts.total} on the shelf${counts.building ? `, ${counts.building} building` : ""}`, showNew, onMake], ["Check", `${counts.review} waiting for you`, filters.status === "draft", () => onFilter("draft")], ["Approve", `${counts.approved} approved`, filters.status === "approved", () => onFilter("approved")], ["Export", "A game pack", false, onExport]];
  return html`<nav class="wk-flow" aria-label="From making to export"><ol>${steps.map(([b, s, on, go], i) => html`<li><button type="button" aria-pressed=${on} onClick=${go}><i>${i + 1}</i><span><b>${b}</b><small>${s}</small></span></button></li>`)}</ol></nav>`;
}

// Nothing on the shelf yet: what the makers have built for us, plainly marked as ours.
function EmptyShop({ caps, reloadCaps, onCreated, start }) {
  const [at, setAt] = useState(0), s = SAMPLES[at], formAt = useRef(null);
  useEffect(() => { if (start && formAt.current) formAt.current.scrollIntoView({ block: "start", behavior: quiet() ? "auto" : "smooth" }); }, [start]);
  return html`<div class="wk-empty">
    <section class="wk-show film" aria-label="Our test builds">
      <figure class="wk-showmain">${s.clip && !quiet() ? html`<video key=${s.key} src=${s.clip} poster=${s.still} autoplay loop muted playsinline aria-label=${s.alt}></video>` : html`<img key=${s.key} src=${s.still} alt=${s.alt} width="448" height="448"/>`}
        <figcaption><small>Ours, not in your library</small><b>${s.name}</b><span>${s.kind}${s.size ? `, ${s.size}` : ""}</span></figcaption></figure>
      <ul class="wk-showlist">${SAMPLES.map((x, i) => html`<li><button type="button" aria-pressed=${i === at} onClick=${() => setAt(i)}><img src=${x.still} alt="" loading="lazy" width="96" height="96"/><span><b>${x.name}</b><small>${x.kind}${x.size ? `, ${x.size}` : ""}</small></span></button></li>`)}</ul>
      <p class="wk-showlead"><b>Your shelf is empty.</b> These are our own test builds from the same makers, on our machine. Yours will differ. A place needs only Blender: describe one and press Make it. To make someone, pick Character and describe them.</p>
    </section>
    <div ref=${formAt}><${NewAsset} caps=${caps} reloadCaps=${reloadCaps} start=${start} onCreated=${onCreated}/></div></div>`;
}

// #worldkit/<id> opens one asset, so another page can link straight to it.
// #worldkit/character opens the Character tab, for the Cast section of Virtual Set.
export function WorldKit({ route = "" }) {
  const hashPart = String(route).split("/")[1] || "", askedChar = hashPart === "character";
  const [list, setList] = useState(null), [filters, setFilters] = useState({ type: "", q: "", status: "" }), [sel, setSel] = useState(askedChar ? "" : hashPart), [showNew, setShowNew] = useState(askedChar), [start, setStart] = useState(askedChar ? { type: "character" } : null), [err, setErr] = useState(""), [caps, setCaps] = useState(null);
  const stage = useRef(null);
  const reload = () => api("/api/worldkit/assets").then((r) => { setList(r.assets || []); setErr(""); }).catch((e) => { setErr(errText(e)); setList((l) => l || []); });
  const reloadCaps = () => api("/api/worldkit/capabilities").then(setCaps).catch(() => {});
  useEffect(() => { document.body.classList.add("on-worldkit"); reload(); reloadCaps(); const t = setInterval(reload, 6000); return () => { clearInterval(t); document.body.classList.remove("on-worldkit", "worldkit-busy"); }; }, []);
  const items = list || [], shown = filterAssets(items, filters), first = firstAsset(items), active = sel || (first ? first.id : "");
  useEffect(() => { document.body.classList.toggle("worldkit-busy", items.length > 0); }, [items.length > 0]);
  const setF = (k) => (e) => setFilters({ ...filters, [k]: e.target.value });
  const counts = shopCounts(items);
  const toStage = () => { const n = stage.current; if (n) { n.scrollIntoView({ block: "start", behavior: quiet() ? "auto" : "smooth" }); } };
  const openNew = (m) => { setStart(m ? { type: m.type, via: m.via } : null); setShowNew(true); setTimeout(toStage, 0); };
  const toExport = () => { const n = document.getElementById("wk-export"); if (n) { n.scrollIntoView({ block: "center", behavior: quiet() ? "auto" : "smooth" }); const b = n.querySelector("input"); if (b) b.focus({ preventScroll: true }); } };
  const created = (id) => { setShowNew(false); reload(); setSel(id); };
  if (list === null) return html`<div class="wk" aria-label="World Kit"><p class="wk-hint">Opening the shop...</p></div>`;
  return html`<div class="wk" aria-label="World Kit">
    ${err && html`<p class="wk-err" role="alert">${err}</p>`}
    ${!items.length && !err ? html`<${EmptyShop} caps=${caps} reloadCaps=${reloadCaps} start=${start} onCreated=${created}/>` : html`
    <${Flow} counts=${counts} filters=${filters} showNew=${showNew} onMake=${() => openNew()} onFilter=${(st) => setFilters({ ...filters, status: filters.status === st ? "" : st })} onExport=${toExport}/>
    <div class="wk-floor">
      <div class="wk-main" ref=${stage}>${showNew ? html`<${NewAsset} caps=${caps} reloadCaps=${reloadCaps} start=${start} onClose=${() => setShowNew(false)} onCreated=${created}/>` : active ? html`<${AssetDetail} key=${active} id=${active} onExport=${toExport} onChanged=${(id) => { reload(); setSel(id || ""); }}/>` : html`<p class="wk-hint">Pick an asset or make a new one.</p>`}</div>
      <aside class="wk-shelf" aria-label="Library">
        <div class="wk-sechead"><h3>The shelf</h3><button type="button" class="btn small" onClick=${() => (showNew ? setShowNew(false) : openNew())}>${showNew ? "Cancel" : "New asset"}</button></div>
        <input class="wk-in" type="search" placeholder="Search name or tag" value=${filters.q} onInput=${setF("q")} aria-label="Search assets"/>
        <div class="wk-inline"><select class="wk-in" aria-label="Type" value=${filters.type} onChange=${setF("type")}><option value="">All types</option>${TYPES.map((t) => html`<option value=${t}>${TYPE_LABELS[t]}</option>`)}</select>
          <select class="wk-in" aria-label="Status" value=${filters.status} onChange=${setF("status")}><option value="">Any status</option><option value="approved">Approved</option><option value="draft">Draft</option></select></div>
        <ul class="wk-items">${shown.map((a) => { const sc = scaleCompare(a.scale_m), c = statusChip(a); return html`<li><button type="button" class="wk-item" aria-current=${a.id === active && !showNew ? "true" : undefined} onClick=${() => { setSel(a.id); setShowNew(false); setTimeout(toStage, 0); }}>
            ${a.files.includes("thumb.jpg") ? html`<img src=${fileUrl(a.id, "thumb.jpg")} alt="" loading="lazy" width="512" height="512"/>` : html`<span class="wk-noimg" aria-hidden="true">${TYPE_LABELS[a.type][0]}</span>`}
            ${sc && html`<em>${sc.text}</em>`}<span class="wk-itemtext"><b>${a.name}</b><${Chip} c=${c}/></span></button></li>`; })}</ul>
        ${!shown.length && html`<p class="wk-hint">Nothing here matches. Clear the search or the filters.</p>`}
      </aside>
    </div>`}
    <div class="wk-yard"><${Workshop} caps=${caps} onPick=${openNew}/><${ExportPack} approved=${counts.approved}/></div>
  </div>`;
}
