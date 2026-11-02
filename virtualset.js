// Virtual Set page: block a shot in an approved World Kit place (props, marks, up to two characters), preview the camera on a plan, render the Blender passes on the CPU, then send them to a video model. Routes: /api/vset/* (studio/vset/api.py). Look: virtualset.css.
import { useEffect, useRef, useState } from "preact/hooks";
import { html, api, post } from "./common.js";
import { Viewer3D } from "./viewer3d.js";
import { Hero, Wipe } from "./vset_hero.js";
import { PRESET_LABELS, MODE_NAMES, MOVE_GLYPHS, fileUrl, glbUrl, blankForm, buildShot, formFromShot, blockers, formatProblem, poseProblem, stateChip, canRetry, qcText, moveItem, planView, frustum, modeParts, modeStatus, routeName } from "./vset_helpers.js";

const errText = (e) => String((e && e.message) || e);
const Chip = ({ c }) => html`<span class=${"vs-chip " + c.cls}>${c.label}</span>`;

const paramLabel = (k) => k.replace(/_m$/, ", m").replace(/_deg$/, ", deg").replace(/_/g, " ");

function Needs({ problems }) {
  if (!problems.length) return null;
  return html`<div class="vs-needs" role="status"><b>Not ready on this machine</b>${problems.map((p) => html`<p>${p}</p>`)}</div>`;
}

function PlanView({ preview, onFrame }) {
  const [frame, setFrame] = useState(0), [playing, setPlaying] = useState(false);
  const view = planView(preview);
  const count = preview && preview.keys ? preview.keys.length : 0;
  useEffect(() => { if (onFrame) onFrame(preview && preview.keys ? preview.keys[Math.min(frame, count - 1)] : null, preview); }, [frame, preview]);
  useEffect(() => {
    if (!playing || !count) return undefined;
    const t = setInterval(() => setFrame((f) => { if (f >= count - 1) { setPlaying(false); return f; } return Math.min(count - 1, f + Math.max(1, Math.round(count / 72))); }), 1000 / 24);
    return () => clearInterval(t);
  }, [playing, count]);
  if (!view) return html`<p class="vs-hint">Press Preview camera to see the move on a plan of the set.</p>`;
  const k = preview.keys[Math.min(frame, count - 1)], at = view.at(k.pos[0], k.pos[1]), look = view.at(k.look[0], k.look[1]), [e1, e2] = frustum(at, look, k.lens_mm, preview.sensor_mm);
  const start = view.at(preview.keys[0].pos[0], preview.keys[0].pos[1]);
  return html`<div class="vs-plan"><svg viewBox="0 0 420 280" role="img" aria-label="Plan of the camera move">
      <defs><pattern id="vs-grid" width="20" height="20" patternUnits="userSpaceOnUse"><path d="M20 0H0V20" fill="none" stroke="#f5c518" stroke-opacity=".1"/></pattern></defs>
      <rect width="420" height="280" fill="url(#vs-grid)"/>
      ${view.box && html`<rect x=${view.box.x} y=${view.box.y} width=${view.box.w} height=${view.box.h} fill="rgba(245,197,24,.05)" stroke="#f5c518" stroke-opacity=".5" stroke-dasharray="2 4"/>`}
      ${preview.subject && preview.subject.length > 0 && html`<polyline points=${view.subject} fill="none" stroke="#fff" stroke-opacity=".6" stroke-dasharray="4 3"/>`}
      <polygon points=${`${at[0]},${at[1]} ${e1[0]},${e1[1]} ${e2[0]},${e2[1]}`} fill="rgba(245,197,24,.2)" stroke="#f5c518" stroke-opacity=".6"/>
      <polyline points=${view.camera} fill="none" stroke="#f5c518" stroke-width="2.5" stroke-linecap="round"/>
      <circle cx=${start[0]} cy=${start[1]} r="3.5" fill="#101311" stroke="#f5c518" stroke-width="1.5"/>
      <circle cx=${look[0]} cy=${look[1]} r="3" fill="#fff"/><circle cx=${at[0]} cy=${at[1]} r="6.5" fill="#f5c518" stroke="#141006" stroke-width="2"/></svg>
    <div class="vs-planbar"><button type="button" class="vs-play" aria-label=${playing ? "Pause the camera move" : "Play the camera move"} onClick=${() => { if (!playing && frame >= count - 1) setFrame(0); setPlaying(!playing); }}><svg viewBox="0 0 24 24" aria-hidden="true"><path d=${playing ? "M6 4h4v16H6z M14 4h4v16h-4z" : "M6 4l14 8-14 8z"}/></svg></button>
      <input class="vs-scrub" type="range" min="0" max=${count - 1} value=${frame} aria-label="Frame of the camera move" onInput=${(e) => { setPlaying(false); setFrame(Number(e.target.value)); }}/></div>
    <p class="vs-planfacts">Frame ${frame + 1} of ${preview.frames}, ${preview.fps} fps, ${preview.size[0]} x ${preview.size[1]}, lens ${k.lens_mm} mm. Yellow: camera. White dashes: what it follows.</p></div>`;
}

function ModeCard({ k, on, label, meta, caps, onPick }) {
  const parts = modeParts(k, label), rows = modeStatus(caps, k);
  return html`<label class=${"vs-mode" + (on ? " on" : "")}><input type="radio" name="vs-mode" checked=${on} onChange=${onPick}/>
    <i aria-hidden="true">${k}</i><span class="vs-modetext"><b>${parts.name}</b><small>${parts.what}</small>
      ${meta && html`<small class="vs-modespec">${meta.seconds.join(", ")} s, ${meta.aspects.join(", ")}</small>`}</span>
    <ul class="vs-proofs">${rows.map((r) => html`<li class=${r.cls}><span>${rows.length > 1 ? r.name : ""}</span><em>${r.label}</em>${r.proofShot && html`<a href=${"#virtualset/" + r.proofShot}>See it</a>`}</li>`)}</ul>
    ${k === "B" && html`<small class="vs-modenote">Keeps layout and camera, not exact props.</small>`}</label>`;
}

function ShotEditor({ meta, caps, assets, initial, onSaved, reloadCaps }) {
  const [form, setForm] = useState(initial || blankForm()), [preview, setPreview] = useState(null), [err, setErr] = useState(""), [busy, setBusy] = useState(false), [lens, setLens] = useState(true), [key, setKey] = useState(null);
  const of = (t) => assets.filter((a) => a.type === t);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const setRow = (key_, i, k) => (e) => setForm({ ...form, [key_]: form[key_].map((p, j) => (j === i ? { ...p, [k]: e.target.value } : p)) });
  const shot = buildShot(form);
  const defaults = (meta && meta.defaults && meta.defaults[form.preset]) || {};
  const problems = blockers(caps, form), hint = formatProblem(meta, form) || poseProblem(form);
  const place = assets.find((a) => a.id === form.place);
  const doPreview = async () => { try { setPreview(await post("/api/vset/camera", { shot })); setErr(""); } catch (e) { setErr(errText(e)); } };
  const save = async (render) => {
    setBusy(true);
    try { const r = await post("/api/vset/shots", { shot, ...(render ? { render } : {}) }); setErr(""); setForm({ ...form, id: r.shot.id }); onSaved(r.shot); } catch (e) { setErr(errText(e)); reloadCaps(); } finally { setBusy(false); }
  };
  // The plan keeps up with the form. The camera route only does sums: nothing renders. Errors wait for the button, because half-typed numbers are normal.
  const camKey = JSON.stringify([shot.camera, shot.marks, shot.cast, shot.format, form.place, form.seed]);
  useEffect(() => { if (form.preset === "custom" && !(form.startPos && form.endPos)) return undefined; const t = setTimeout(() => { post("/api/vset/camera", { shot }).then(setPreview).catch(() => {}); }, 350); return () => clearTimeout(t); }, [camKey]);
  const route = routeName(form);
  return html`<form class="vs-editor" onSubmit=${(e) => { e.preventDefault(); save(true); }} onKeyDown=${(e) => { if (e.key === "Enter" && e.target.tagName === "INPUT") e.preventDefault(); }} aria-label="Shot">
    <div class="vs-deskgrid">
      <section class="vs-slate film" aria-label="The slate">
        <div class="vs-clapper" aria-hidden="true"></div>
        <div class="vs-slategrid">
          <label class="vs-s wide"><span>Shot</span><input type="text" class="big" placeholder="Name this shot" value=${form.name} onInput=${set("name")} aria-label="Shot name"/></label>
          <label class="vs-s wide"><span>Set</span><select aria-label="Place" value=${form.place} onChange=${set("place")}><option value="">${of("place").length ? "Pick an approved place" : "No approved place yet: make one in World Kit"}</option>${of("place").map((a) => html`<option value=${a.id}>${a.name}</option>`)}</select></label>
          <label class="vs-s"><span>Lens, mm</span><input type="text" inputmode="decimal" placeholder=${meta ? String(meta.lens_mm) : ""} value=${form.lens} onInput=${set("lens")} aria-label="Lens"/></label>
          <label class="vs-s"><span>Seed</span><input type="text" inputmode="numeric" value=${form.seed} onInput=${set("seed")} aria-label="Seed"/></label>
          <label class="vs-s"><span>Aspect</span><select aria-label="Aspect" value=${form.aspect} onChange=${set("aspect")}>${((meta && meta.aspects) || []).map((x) => html`<option value=${x}>${x}</option>`)}</select></label>
          <label class="vs-s"><span>Length</span><select aria-label="Seconds" value=${form.seconds} onChange=${set("seconds")}>${[5, 8, 10].map((x) => html`<option value=${x}>${x} s</option>`)}</select></label>
          <label class="vs-s"><span>Look</span><select aria-label="Look" value=${form.look} onChange=${set("look")}>${((meta && meta.looks) || []).map((l) => html`<option value=${l.id}>${l.label}</option>`)}</select></label>
          <label class="vs-s"><span>Look asset</span><select aria-label="Look asset" value=${form.lookAsset} onChange=${set("lookAsset")}><option value="">None</option>${of("look").map((a) => html`<option value=${a.id}>${a.name}</option>`)}</select></label>
          <label class="vs-s wide"><span>Action</span><textarea rows="2" placeholder="What happens in this shot" value=${form.prompt} onInput=${set("prompt")} aria-label="Action"></textarea></label>
        </div>
        ${place && html`<p class="vs-slatefoot"><a href=${"#worldkit/" + place.id}>Open ${place.name} in World Kit</a></p>`}
      </section>
      <section class="vs-cam film" aria-label="Camera">
        <h3>Camera move</h3>
        <div class="vs-moves" role="radiogroup" aria-label="Camera move">${((meta && meta.presets) || []).map((k) => html`<label class=${"vs-move" + (form.preset === k ? " on" : "")}><input type="radio" name="vs-move" checked=${form.preset === k} onChange=${() => setForm({ ...form, preset: k, params: {} })}/><svg viewBox="0 0 48 32" aria-hidden="true">${MOVE_GLYPHS[k] && html`<path d=${MOVE_GLYPHS[k]}/>`}<circle cx=${k === "orbit" ? 24 : k === "pov" ? 24 : 42} cy=${k === "orbit" ? 24 : k === "pov" ? 8 : k === "walk_along" ? 10 : 16} r="3"/>${k === "static" && html`<rect x="6" y="11" width="10" height="10" rx="2"/>`}</svg><span>${PRESET_LABELS[k] || k}</span></label>`)}</div>
        ${form.preset === "custom" ? html`<div class="vs-params"><label class="vs-f"><span>Start, x,y,z</span><input class="vs-in" type="text" value=${form.startPos} onInput=${set("startPos")} aria-label="Start position"/></label><label class="vs-f"><span>Looks at, x,y,z</span><input class="vs-in" type="text" value=${form.startLook} onInput=${set("startLook")} aria-label="Start looks at"/></label>
            <label class="vs-f"><span>End, x,y,z</span><input class="vs-in" type="text" value=${form.endPos} onInput=${set("endPos")} aria-label="End position"/></label><label class="vs-f"><span>Looks at, x,y,z</span><input class="vs-in" type="text" value=${form.endLook} onInput=${set("endLook")} aria-label="End looks at"/></label>
            <label class="vs-f"><span>Easing</span><select class="vs-in" aria-label="Easing" value=${form.easing} onChange=${set("easing")}>${((meta && meta.easings) || []).map((x) => html`<option value=${x}>${x}</option>`)}</select></label></div>`
          : html`<div class="vs-params">${Object.entries(defaults).filter(([k]) => k !== "easing").map(([k, v]) => html`<label class="vs-f"><span>${paramLabel(k)}</span><input class="vs-in" type="text" inputmode="decimal" placeholder=${String(v)} value=${form.params[k] ?? ""} onInput=${(e) => setForm({ ...form, params: { ...form.params, [k]: e.target.value } })}/></label>`)}</div>`}
        <${PlanView} preview=${preview} onFrame=${(k, p) => setKey(k ? { ...k, sensor_mm: p && p.sensor_mm } : null)}/>
      </section>
    </div>
    ${place && html`<section class="vs-setview film" aria-label="The set"><div class="vs-sechead"><h3>The set in 3D</h3><div class="vs-seg" role="group" aria-label="How to look at the set"><button type="button" aria-pressed=${!(lens && key)} onClick=${() => setLens(false)}>Free look</button><button type="button" aria-pressed=${lens && !!key} disabled=${!key} onClick=${() => setLens(true)}>Through the lens</button></div></div>
      <${Viewer3D} key=${place.id} url=${glbUrl(place.id)} height="clamp(240px,38vh,420px)" background=${0x0b0d0b} label=${"3D view of " + place.name} lens=${lens && key ? key : null}/>
      ${lens && key && html`<p class="vs-hint">Moves with the plan's frame. The empty set only: props and the look are not drawn here, and the framing is close, not the rendered frame.</p>`}</section>`}
    <section class="vs-block" aria-label="Blocking"><div class="vs-sechead"><h3>Blocking</h3></div>
      <div class="vs-blockgrid">
        <div><h4>Props</h4>${form.props.map((p, i) => html`<div class="vs-proprow"><label class="vs-f"><span>Prop ${i + 1}</span><select class="vs-in" aria-label="Prop" value=${p.asset} onChange=${setRow("props", i, "asset")}><option value="">No prop</option>${of("prop").map((a) => html`<option value=${a.id}>${a.name}</option>`)}</select></label>
            ${[["x", "x m"], ["y", "y m"], ["yaw", "turn"]].map(([k, l]) => html`<label class="vs-f"><span>${l}</span><input class="vs-in" type="text" inputmode="decimal" value=${p[k]} onInput=${setRow("props", i, k)}/></label>`)}</div>`)}
          <button type="button" class="btn small" disabled=${!of("prop").length} onClick=${() => setForm({ ...form, props: [...form.props, { asset: "", x: "0", y: "0", yaw: "0", scale: "1" }] })}>Add a prop</button></div>
        <div><h4>What the camera follows</h4><label class="vs-f"><span>Marks in metres: x,y; x,y</span><input class="vs-in" type="text" value=${form.marks} onInput=${set("marks")} aria-label="Marks"/></label></div>
        <div class="vs-cast"><h4>Cast</h4>${!caps || caps.characters_on ? html`${form.cast.map((c, i) => { const a = assets.find((x) => x.id === c.asset); return html`<div class="vs-castcard">
            ${a && a.files.includes("thumb.jpg") ? html`<img src=${"/api/worldkit/assets/" + encodeURIComponent(a.id) + "/file/thumb.jpg"} alt="" loading="lazy" width="384" height="384"/>` : html`<span class="vs-castblank" aria-hidden="true">${i + 1}</span>`}
            <div class="vs-castfields"><label class="vs-f"><span>Character</span><select class="vs-in" value=${c.asset} onChange=${(e) => { const pick = assets.find((x) => x.id === e.target.value); setForm({ ...form, cast: form.cast.map((p, j) => (j === i ? { ...p, asset: e.target.value, clip: pick && pick.clips.length ? (pick.clips.includes(p.clip) ? p.clip : pick.clips[0]) : "" } : p)) }); }}><option value="">Pick a character</option>${of("character").map((x) => html`<option value=${x.id} disabled=${!x.rig_bones}>${x.name}${x.rig_bones ? "" : " (no rig)"}</option>`)}</select></label>
              <label class="vs-f"><span>Motion</span><select class="vs-in" value=${c.clip} onChange=${setRow("cast", i, "clip")}><option value="">${a ? "Pick a motion" : "Pick a character first"}</option>${((a && a.clips) || []).map((n) => html`<option value=${n}>${n}</option>`)}</select></label>
              <label class="vs-f"><span>Walks through, metres: x,y; x,y</span><input class="vs-in" type="text" placeholder="0,0; 0,-3" value=${c.marks} onInput=${setRow("cast", i, "marks")}/></label>
              <button type="button" class="vs-link" aria-label=${"Remove cast member " + (i + 1)} onClick=${() => setForm({ ...form, cast: form.cast.filter((_, j) => j !== i) })}>Remove</button></div></div>`; })}
          ${!of("character").length ? html`<p class="vs-hint">No approved character yet. <a href="#worldkit/character">Describe one in World Kit</a>, approve it, and it joins the cast here. A shot also works with a place and props alone.</p>`
            : form.cast.length < 2 ? html`<button type="button" class="btn small" onClick=${() => { const one = of("character").find((x) => x.rig_bones && !form.cast.some((c) => c.asset === x.id)); setForm({ ...form, cast: [...form.cast, { asset: one ? one.id : "", clip: one && one.clips[0] ? one.clips[0] : "", marks: "0,0" }] }); }}>Add a character</button>` : ""}
          ${form.cast.length > 0 && html`<p class="vs-hint">Up to two. The camera follows the first one's marks. <a href="#worldkit/character">Make another</a>.</p>`}`
        : html`<p class="vs-hint">Characters are off on this machine (STUDIO_WORLDKIT_CHARACTERS=0). A shot works with a place and props alone.</p>`}</div>
      </div></section>
    <section class="vs-modes" aria-label="How the video is made"><div class="vs-sechead"><h3>How the video is made</h3><span>Status read live from this machine</span></div>
      <div class="vs-modegrid" role="radiogroup" aria-label="Mode">${Object.keys(MODE_NAMES).map((k) => html`<${ModeCard} k=${k} on=${form.mode === k} label=${meta && meta.modes[k] && meta.modes[k].label} meta=${meta && meta.modes[k]} caps=${caps} onPick=${() => setForm({ ...form, mode: k })}/>`)}</div>
      <p class="vs-hint">"Rendered here" means a shot on this machine produced a video and its automatic checks (flicker, and face when one ran) found nothing. The checks do not judge the picture, so watch the result.</p>
      <div class="vs-modeset">
        ${form.mode === "A" && html`<label class="vs-f"><span>Engine</span><select class="vs-in" aria-label="Engine" value=${form.engine} onChange=${set("engine")}><option value="h3">MiniMax H3 Fun Union</option><option value="wan">Wan 2.2 Fun Control</option><option value="ltx">LTX-2.5 Layout to Render (clay pass)</option></select></label>
          ${form.engine !== "ltx" && html`<label class="vs-f"><span>Pass</span><select class="vs-in" aria-label="Pass" value=${form.control} onChange=${set("control")}><option value="depth">Depth pass</option><option value="pose">Pose pass</option></select></label>`}`}
        ${(form.mode === "C" || (form.mode === "A" && form.engine === "ltx")) && html`<label class="vs-f"><span>Keyframes</span><select class="vs-in" aria-label="Keyframes" value=${form.keyframes} onChange=${set("keyframes")}><option value="qwen">Qwen-Image 2.1 makes the stills photoreal</option><option value="raw">Use the Blender stills as they are</option></select></label>`}
      </div></section>
    <div class="vs-rollbar" data-route=${route}>
      <${Needs} problems=${problems}/>
      ${hint && html`<p class="vs-err" role="alert">${hint}</p>`}
      ${err && html`<p class="vs-err" role="alert">${err}</p>`}
      <div class="vs-rollbtns"><button type="button" class="btn small" onClick=${doPreview}>Preview camera</button>
        <button type="button" class="btn small" disabled=${busy} onClick=${() => save(false)}>Save</button>
        <button type="button" class="btn small" disabled=${busy || !!(caps && caps.blender)} onClick=${() => save("passes")}>Render passes (CPU, no model)</button>
        <button type="submit" class="btn primary vs-go" disabled=${busy || problems.length > 0 || !!hint}>Render video</button></div></div>
  </form>`;
}

function PassFrame({ url, name }) {
  return html`<figure class="vs-pass"><figcaption>${name}</figcaption><video src=${url + "#t=0.1"} controls loop muted playsinline preload="metadata" aria-label=${name + " pass"}></video></figure>`;
}

function ShotResult({ id, sum, reload }) {
  const [err, setErr] = useState(""), [cmp, setCmp] = useState("");
  if (!sum) return null;
  const act = async (verb) => { try { await post(`/api/vset/shots/${encodeURIComponent(id)}/${verb}`, {}); setErr(""); } catch (e) { setErr(errText(e)); } reload(); };
  const p = sum.passes || {};
  const names = ["shaded", "depth", "pose", "edges"].filter((k) => p[k]), pick = cmp && p[cmp] ? cmp : names[0];
  return html`<section class="vs-result film" aria-label="Result">
    <div class="vs-reshead"><div><p class="vs-kicker">Dailies</p><h2>${sum.name || sum.id}</h2></div><${Chip} c=${stateChip(sum)}/>
      <span class="vs-qc">${qcText(sum.qc)}${sum.rerolls ? `, rerolled ${sum.rerolls}x` : ""}${sum.engine ? `, passes by ${sum.engine}` : ""}</span><span class="vs-grow"></span>
      ${sum.running && html`<button type="button" class="btn small" onClick=${() => act("cancel")}>Cancel</button>`}
      ${canRetry(sum) && html`<button type="button" class="btn small" onClick=${() => act("retry")}>Retry</button>`}</div>
    ${err && html`<p class="vs-err" role="alert">${err}</p>`}
    ${sum.error && html`<p class="vs-err">${sum.error}</p>`}
    ${sum.video_url && pick && html`<div class="vs-seg caps" role="group" aria-label="Pass to compare with the video">${names.map((k) => html`<button type="button" aria-pressed=${k === pick} onClick=${() => setCmp(k)}>${k}</button>`)}</div>
      <${Wipe} over=${p[pick]} overLabel=${pick + " pass"} under=${sum.video_url} underLabel="Result"/>`}
    ${sum.video_url && !pick && html`<video class="vs-resvideo" src=${sum.video_url} controls playsinline></video>`}
    ${sum.video_url && html`<p class="vs-reslinks"><a href=${sum.video_url} download>Download the video</a></p>`}
    ${sum.video_url && sum.mode === "B" && html`<p class="vs-hint">Mode B keeps layout and camera, not exact props. Check your props against the shaded pass.</p>`}
    ${sum.qc && !sum.qc.face_checked && sum.video_url && html`<p class="vs-hint">No face check ran: it needs a saved character in the shot and a face classifier, and this studio has none.</p>`}
    ${!sum.video_url && !sum.running && sum.state === "new" && html`<p class="vs-hint">Not rendered yet.</p>`}
    ${Object.keys(p).length > 0 && html`<div class="vs-passes">${names.map((k) => html`<${PassFrame} url=${p[k]} name=${k}/>`)}</div>
      <p class="vs-reslinks">Stills: ${["first", "last"].filter((k) => p[k]).map((k) => html`<a href=${p[k]} target="_blank" rel="noopener">${k}</a> `)}${Object.entries(sum.keyframes || {}).map(([k, u]) => html`<a href=${u} target="_blank" rel="noopener">${k}</a> `)}</p>`}
  </section>`;
}

function ShotLists({ baseShot }) {
  const [lists, setLists] = useState([]), [sel, setSel] = useState(""), [detail, setDetail] = useState(null), [form, setForm] = useState({ name: "", script: "" }), [err, setErr] = useState("");
  const reload = () => api("/api/vset/lists").then((r) => setLists(r.lists || [])).catch((e) => setErr(errText(e)));
  const load = (id) => api(`/api/vset/lists/${encodeURIComponent(id)}`).then(setDetail).catch((e) => setErr(errText(e)));
  useEffect(() => { reload(); }, []);
  useEffect(() => { if (!sel) return undefined; load(sel); const t = setInterval(() => load(sel), 5000); return () => clearInterval(t); }, [sel]);
  const create = async () => {
    if (!baseShot) { setErr("Save a shot first: the list uses its set, look, mode and format."); return; }
    const { id, prompt, camera, name, schema, created, updated, ...base } = baseShot;
    try { const r = await post("/api/vset/lists", { name: form.name, script: form.script, base }); setErr(""); reload(); setSel(r.list.id); } catch (e) { setErr(errText(e)); }
  };
  const order = async (i, j) => { try { await post(`/api/vset/lists/${encodeURIComponent(sel)}/order`, { ids: moveItem(detail.list.shots, i, j) }); load(sel); } catch (e) { setErr(errText(e)); } };
  const render = async () => { try { await post(`/api/vset/lists/${encodeURIComponent(sel)}/render`, {}); load(sel); } catch (e) { setErr(errText(e)); } };
  const cons = detail && detail.list.state && detail.list.state.consistency;
  return html`<section class="vs-lists" aria-label="Shot lists"><div class="vs-listform"><p class="vs-kicker">The day's schedule</p><h2>Shot lists</h2>
      <p class="vs-hint">One shot per line, all in the last saved shot's set, look, mode and format. Camera words (orbit, tracking, point of view, static) pick the move.</p>
      <label class="vs-f"><span>List name</span><input class="vs-in" type="text" value=${form.name} onInput=${(e) => setForm({ ...form, name: e.target.value })} aria-label="List name"/></label>
      <label class="vs-f"><span>Script</span><textarea class="vs-in" rows="5" placeholder=${"1. the door opens\n2. orbit the counter\n3. the lights go out"} value=${form.script} onInput=${(e) => setForm({ ...form, script: e.target.value })} aria-label="Script"></textarea></label>
      <button type="button" class="btn primary" onClick=${create}>Make the list</button>
      ${err && html`<p class="vs-err" role="alert">${err}</p>`}</div>
    <div class="vs-listside"><div class="vs-seg wrap" role="group" aria-label="Saved lists">${lists.map((l) => html`<button type="button" aria-pressed=${l.id === sel} onClick=${() => setSel(l.id)}>${l.name} (${l.shots})</button>`)}</div>
      ${!lists.length && html`<p class="vs-hint">No lists yet.</p>`}
      ${detail && html`<div class="vs-listdetail"><div class="vs-sechead"><h3>${detail.list.name}</h3><span class="vs-grow"></span>
          ${cons && cons.min !== null && cons.min !== undefined && html`<${Chip} c=${{ cls: cons.ok ? "ok" : "warn", label: `set consistency ${Number(cons.min).toFixed(2)}` }}/>`}
          <button type="button" class="btn small" disabled=${detail.running} onClick=${render}>${detail.running ? "Rendering" : "Render all"}</button></div>
        <ol class="vs-listshots">${detail.shots.map((x, i) => html`<li><i>${i + 1}</i><div><${Chip} c=${stateChip(x)}/> <span>${x.prompt}</span> <small>${PRESET_LABELS[x.camera] || x.camera}${qcText(x.qc) ? ", " + qcText(x.qc) : ""}</small>${x.video_url && html` <a href=${x.video_url} target="_blank" rel="noopener">video</a>`}</div>
          <span class="vs-updown"><button type="button" class="btn small" disabled=${i === 0} onClick=${() => order(i, i - 1)} aria-label="Move up">Up</button><button type="button" class="btn small" disabled=${i === detail.shots.length - 1} onClick=${() => order(i, i + 1)} aria-label="Move down">Down</button></span></li>`)}</ol></div>`}</div>
  </section>`;
}

// #virtualset/<id> opens one shot, so another page can link straight to it.
export function VirtualSet({ route = "" }) {
  const [meta, setMeta] = useState(null), [caps, setCaps] = useState(null), [assets, setAssets] = useState([]), [shots, setShots] = useState([]), [tab, setTab] = useState("shot"), [current, setCurrent] = useState(""), [initial, setInitial] = useState(null), [baseShot, setBaseShot] = useState(null), [err, setErr] = useState(""), [showHero, setShowHero] = useState(false);
  const reload = () => api("/api/vset/shots").then((r) => { setShots(r.shots || []); setErr(""); }).catch((e) => setErr(errText(e)));
  const reloadCaps = () => api("/api/vset/capabilities").then(setCaps).catch(() => {});
  const open = async (id) => {
    try { const r = await api(`/api/vset/shots/${encodeURIComponent(id)}`); setInitial(formFromShot(r.shot)); setBaseShot(r.shot); setCurrent(id); setTab("shot"); setShowHero(false); } catch (e) { setErr(errText(e)); }
  };
  useEffect(() => {
    document.body.classList.add("on-virtualset");
    api("/api/vset/meta").then(setMeta).catch((e) => setErr(errText(e)));
    api("/api/worldkit/assets?status=approved").then((r) => setAssets(r.assets || [])).catch(() => setAssets([]));
    reload(); reloadCaps();
    const t = setInterval(reloadCaps, 15000);    // tests finish while the page is open, so the proof beside each mode stays current
    return () => { clearInterval(t); document.body.classList.remove("on-virtualset", "virtualset-busy"); };
  }, []);
  const hash = String(route).split("/")[1] || "";
  useEffect(() => { if (hash && hash !== current) open(hash); }, [hash]);
  useEffect(() => { if (!shots.some((x) => x.running)) return undefined; const t = setInterval(reload, 4000); return () => clearInterval(t); }, [shots.map((x) => x.running).join()]);
  const sum = shots.find((x) => x.id === current);
  const places = assets.filter((a) => a.type === "place").length;
  const heroOn = tab === "shot" && (!current || showHero);
  useEffect(() => { document.body.classList.toggle("virtualset-busy", !!current); }, [!!current]);
  return html`<div class="vs" aria-label="Virtual Set">
    ${heroOn ? html`<${Hero} caps=${caps}/>` : tab === "shot" && html`<p class="vs-heroback"><button type="button" class="vs-link" onClick=${() => setShowHero(true)}>Show our test shot</button></p>`}
    <section class="vs-reel film" aria-label="Shots">
      <div class="vs-reelhead"><h3>The reel</h3><div class="vs-seg" role="group" aria-label="Shots or shot lists"><button type="button" aria-pressed=${tab === "shot"} onClick=${() => setTab("shot")}>Shot</button><button type="button" aria-pressed=${tab === "lists"} onClick=${() => setTab("lists")}>Shot lists</button></div></div>
      <div class="vs-perfs" aria-hidden="true"></div>
      <ul class="vs-frames"><li><button type="button" class="vs-frame new" aria-current=${!current && tab === "shot" ? "true" : undefined} onClick=${() => { setInitial(null); setCurrent(""); setTab("shot"); }}><span class="vs-plus" aria-hidden="true">+</span><b>New shot</b></button></li>
        ${shots.map((x) => html`<li><button type="button" class="vs-frame" aria-current=${x.id === current ? "true" : undefined} onClick=${() => open(x.id)}>${x.passes && x.passes.first ? html`<img src=${x.passes.first} alt="" loading="lazy" width="1344" height="768"/>` : html`<span class="vs-noimg" aria-hidden="true">${x.mode || ""}</span>`}<b>${x.name || x.prompt.slice(0, 40)}</b><${Chip} c=${stateChip(x)}/></button></li>`)}</ul>
      <div class="vs-perfs" aria-hidden="true"></div>
      ${err && html`<p class="vs-err" role="alert">${err}</p>`}
      ${!shots.length && !err && html`<p class="vs-hint">No shots yet.</p>`}
      ${!places && html`<p class="vs-hint vs-needplace">A shot needs an approved place. <a href="#worldkit">Make and approve one in World Kit</a>; it needs only Blender.</p>`}
    </section>
    ${tab === "shot" ? html`<${ShotEditor} key=${current || "new"} meta=${meta} caps=${caps} assets=${assets} initial=${initial} reloadCaps=${reloadCaps} onSaved=${(s) => { setInitial(formFromShot(s)); setCurrent(s.id); setBaseShot(s); reload(); }}/><${ShotResult} id=${current} sum=${sum} reload=${reload}/>` : html`<${ShotLists} baseShot=${baseShot}/>`}
  </div>`;
}
