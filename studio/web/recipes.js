/* Recipes: multi-model chains that really run. Media cards like Create's goal deck; each recipe shows its steps as a chain, its models and licences, measured time and VRAM, tested or untested, a Run button with live progress, and each finished step's exact graph one click away. Only recipes rendered on this box say Tested. */
import { useEffect, useMemo, useRef, useState } from "preact/hooks";
import { html, api, post } from "./common.js";

const CSS = `
.rx{display:flex;flex-direction:column;gap:22px}.rxhero{position:relative;display:grid;grid-template-columns:minmax(0,1.5fr) minmax(280px,1fr);gap:0;border-radius:18px;overflow:hidden;background:var(--panel);border:1px solid var(--line)}.rxhero video,.rxhero img{width:100%;height:100%;min-height:260px;max-height:430px;object-fit:cover;display:block;background:#050605}.rxherot{padding:clamp(16px,2vw,28px);display:flex;flex-direction:column;gap:12px;justify-content:center}.rxherot h2{margin:0;font-size:clamp(24px,2.6vw,40px);color:var(--a1)}.rxherot p{margin:0;color:var(--mut);line-height:1.45}
.rxgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,250px),1fr));gap:12px}.rxgrid .gcard{width:100%;height:auto;aspect-ratio:4/5}.rxstat{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:12px;color:rgba(255,255,255,.78)}.rxstat b{color:#fff;font-weight:600}.gflag.rxun{background:rgba(0,0,0,.6);color:#fff;font-weight:600;backdrop-filter:blur(8px)}
.rxdetail{display:flex;flex-direction:column;gap:16px;background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:clamp(14px,1.8vw,24px)}.rxhead{display:flex;flex-wrap:wrap;gap:10px;align-items:flex-start;justify-content:space-between}.rxhead h3{margin:0;font:800 clamp(20px,2vw,28px)/1.05 var(--display);font-stretch:116%;text-transform:uppercase;letter-spacing:-.02em;color:var(--text)}.rxhead p{margin:6px 0 0;color:var(--mut);max-width:70ch;line-height:1.45}
.rxchain{display:flex;flex-wrap:wrap;align-items:stretch;gap:8px;list-style:none;margin:0;padding:0}.rxstep{position:relative;display:flex;flex-direction:column;gap:4px;min-width:0;flex:1 1 150px;max-width:230px;padding:10px 11px;border-radius:12px;background:var(--panel2);border:1px solid var(--line)}.rxstep b{font-size:13px;font-weight:600;color:var(--text);line-height:1.25}.rxstep small{font-size:11.5px;color:var(--mut);line-height:1.3}.rxstep .n{font-size:11px;font-weight:700;color:var(--a1)}.rxstep .m{color:var(--a2);font-weight:600}.rxstep.running{border-color:var(--a1);box-shadow:0 0 0 1px var(--a1)}.rxstep.done{border-color:color-mix(in srgb,var(--a2) 55%,transparent)}.rxstep.error{border-color:#e5484d}.rxstep.skipped{opacity:.7}
.rxstep video,.rxstep img{width:100%;aspect-ratio:16/9;object-fit:cover;border-radius:8px;background:#050605;display:block}.rxarrow{align-self:center;color:var(--mut);font-size:16px}.rxstep .btn{align-self:flex-start;margin-top:2px}
.rxgridtwo{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:16px}.rxbox{min-width:0}.rxbox h4{margin:0 0 8px;font-size:12.5px;font-weight:600;color:var(--mut)}.rxlic{display:flex;flex-direction:column;gap:7px;margin:0;padding:0;list-style:none;font-size:13px}.rxlic b{font-weight:600}.rxlic small{display:block;color:var(--mut);line-height:1.35}.rxtips{margin:0;padding-left:18px;color:var(--mut);font-size:13px;line-height:1.45}
.rxfield{display:block;font-size:12px;font-weight:600;color:var(--mut);margin-bottom:10px}.rxfield textarea,.rxfield input{display:block;width:100%;box-sizing:border-box;margin-top:5px;font:inherit;font-weight:400;font-size:14px;color:var(--text);background:var(--panel2);border:1px solid var(--line);border-radius:11px;padding:9px 11px}.rxfield textarea{min-height:64px;resize:vertical}
.rxrun{display:flex;flex-wrap:wrap;gap:10px;align-items:center}.rxgo{height:48px;padding:0 24px;font:800 16px/1 var(--display);font-stretch:112%;text-transform:uppercase;letter-spacing:-.01em;border-radius:12px;background:var(--a1);color:var(--on-accent);border:0;box-shadow:var(--bevel);cursor:pointer}.rxgo:disabled{background:var(--panel2);color:var(--mut);box-shadow:none;cursor:not-allowed}.rxgo:focus-visible,.rxstep .btn:focus-visible{outline:2px solid var(--a1);outline-offset:2px}.rxcost{display:flex;flex-wrap:wrap;gap:4px 12px;font-size:12px;color:var(--mut)}.rxcost b{color:var(--a2);font-weight:600}
.rxresult video{width:100%;max-height:68vh;border-radius:14px;background:#050605;display:block}.rxerr{color:#e5484d;font-size:13px;margin:0}.rxstatus{font-size:13px;color:var(--text)}
.rxshot{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:6px;margin-bottom:8px}.rxshot textarea{min-height:44px}.rxshot select{background:var(--panel2);color:var(--text);border:1px solid var(--line);border-radius:10px;padding:6px;font-size:12px}
.rxmodal{position:fixed;inset:0;z-index:60;background:rgba(0,0,0,.72);display:grid;place-items:center;padding:16px}.rxmbox{width:min(1100px,100%);max-height:88vh;overflow:auto;background:var(--panel);border:1px solid var(--line2);border-radius:16px;padding:16px}.rxnodes{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,240px),1fr));gap:8px;margin-top:10px}.rxnode{background:var(--panel2);border:1px solid var(--line);border-radius:10px;padding:8px 10px;font-size:12px;min-width:0;overflow-wrap:anywhere}.rxnode b{display:block;font-weight:600;font-size:12.5px;color:var(--text)}.rxnode small{display:block;color:var(--mut)}
@media (max-width:900px){.rxhero,.rxgridtwo{grid-template-columns:minmax(0,1fr)}.rxstep{max-width:none;flex-basis:100%}.rxarrow{display:none}}
`;
const fmtT = (s) => { s = Math.round(+s || 0); return s >= 90 ? `${Math.round(s / 60)} min` : `${s} s`; };
const OPEN = "recipe_open";
/* for the Library and anything else: go to the Recipes page with this recipe and run open */
export function openRecipeRun(id, run) { try { sessionStorage.setItem(OPEN, JSON.stringify({ id, run })); } catch {} location.hash = "recipes"; }
function licenceWord(r) { const c = (r.models || []).map((m) => m.licence_class); return c.length && c.every((x) => x === "open") ? "All open" : "Open and community"; }

function GraphModal({ recipe, run, step, onClose }) {
  const [g, setG] = useState(null), [err, setErr] = useState("");
  useEffect(() => { api(`/api/recipes/${recipe}/runs/${run}/graph/${step.id}`).then((d) => setG(d.graph)).catch((e) => setErr(e.message)); }, [step.id]);
  useEffect(() => { const k = (e) => { if (e.key === "Escape") onClose(); }; addEventListener("keydown", k); return () => removeEventListener("keydown", k); }, []);
  return html`<div class="rxmodal" role="dialog" aria-modal="true" aria-label=${"Graph of " + step.label} onClick=${onClose}><div class="rxmbox" onClick=${(e) => e.stopPropagation()}>
    <div class="rxhead"><div><h3>${step.label}: the graph</h3><p class="small">The exact ComfyUI graph this step ran. Copy it and drop it into ComfyUI to keep going node by node.</p></div><div class="rxrun">${g && html`<button class="btn small" onClick=${() => navigator.clipboard && navigator.clipboard.writeText(JSON.stringify(g, null, 1))}>Copy graph JSON</button>`}<button class="btn small" onClick=${onClose}>Close</button></div></div>
    ${err && html`<p class="rxerr">${err}</p>`}
    ${g && html`<div class="rxnodes">${Object.entries(g).map(([id, n]) => html`<div class="rxnode"><b>${n.class_type}</b><small>node ${id}</small>${Object.entries(n.inputs || {}).filter(([, v]) => !Array.isArray(v)).slice(0, 5).map(([k, v]) => html`<small>${k}: ${String(v).slice(0, 80)}</small>`)}</div>`)}</div>`}
  </div></div>`;
}

function Chain({ steps, live, recipe, run, onGraph }) {
  const list = live || steps;
  return html`<ol class="rxchain" aria-label="steps of this recipe">${list.map((s, i) => { const meta = steps.find((x) => x.id === s.id) || {}; const st = live ? s.status : ""; const f = live && (s.files || []).find((x) => x.kind !== "audio"); const au = live && (s.files || []).find((x) => x.kind === "audio"); const secs = live ? s.seconds : meta.seconds; const peak = live ? s.peak_gib : meta.peak_gib;
    return html`${i > 0 && html`<li class="rxarrow" aria-hidden="true">→</li>`}<li class=${"rxstep " + st}><span class="n">${i + 1}</span><b>${s.label || meta.label}</b>
      ${f && f.kind === "video" && html`<video src=${f.url} muted loop playsinline preload="metadata" controls></video>`}${f && f.kind === "image" && html`<img src=${f.url} alt=${s.label} loading="lazy"/>`}${au && html`<audio src=${au.url} controls preload="none" style="width:100%;height:30px"></audio>`}
      <small>${s.model || meta.model || (meta.type === "cpu" ? "ffmpeg, on the CPU" : "")}</small>${!live && meta.what && html`<small>${meta.what}</small>`}
      ${(secs || peak) && html`<small class="m">${secs ? fmtT(secs) : ""}${secs && peak ? ", " : ""}${peak ? Math.round(peak) + " GiB" : ""}</small>`}
      ${s.note && html`<small>${s.note}</small>`}${s.error && html`<small style="color:#e5484d">${s.error}</small>`}
      ${live && run && s.type !== "cpu" && s.type !== "plan" && s.status === "done" && html`<button class="btn small" onClick=${() => onGraph(s)} aria-label=${"Open the graph of " + s.label}>Open the graph</button>`}
    </li>`; })}</ol>`;
}

function FilmPlan({ recipe, sentence, plan, setPlan, onErr }) {
  const [busy, setBusy] = useState(false);
  const write = async () => { setBusy(true); onErr(""); try { setPlan(await post(`/api/recipes/${recipe.id}/plan`, { sentence })); } catch (e) { onErr(e.message); } setBusy(false); };
  const setShot = (i, k, v) => setPlan({ ...plan, shots: plan.shots.map((s, j) => (j === i ? { ...s, [k]: v } : s)) });
  return html`<div class="rxbox"><div class="rxrun" style="margin-bottom:10px"><button class="btn small" disabled=${busy || !sentence.trim()} onClick=${write}>${busy ? "Writing the shot list" : plan ? "Write it again" : "Write the shot list first"}</button>${plan && html`<small class="small">Written by ${plan.writer || "you"}. Change anything before you run it.</small>`}</div>
    ${plan && html`<div><label class="rxfield">The character<textarea value=${plan.character} onInput=${(e) => setPlan({ ...plan, character: e.target.value })}></textarea></label><label class="rxfield">The world<textarea value=${plan.world} onInput=${(e) => setPlan({ ...plan, world: e.target.value })}></textarea></label>
      ${plan.shots.map((s, i) => html`<div class="rxshot"><label class="rxfield" style="margin:0">Shot ${i + 1}<textarea value=${s.action} onInput=${(e) => setShot(i, "action", e.target.value)}></textarea></label><span style="align-self:end"><select aria-label=${"camera of shot " + (i + 1)} value=${s.camera} onChange=${(e) => setShot(i, "camera", e.target.value)}>${["dolly_in", "dolly_out", "orbit_left", "orbit_right", "crane_up", "crane_down", "pan_left", "pan_right", "tilt_up", "tracking", "handheld", "locked"].map((c) => html`<option value=${c}>${c.replace("_", " ")}</option>`)}</select></span></div>`)}</div>`}</div>`;
}

function Detail({ recipe, onClose, initialRun }) {
  const fields = recipe.fields || []; const [vals, setVals] = useState(() => Object.fromEntries(fields.map((f) => [f.key, f.default || ""]))); const [plan, setPlan] = useState(null); const [run, setRun] = useState(null), [rid, setRid] = useState(initialRun || null), [err, setErr] = useState(""), [graph, setGraph] = useState(null), [starting, setStarting] = useState(false);
  const ref = useRef(null); const film = recipe.tags && recipe.tags.includes("hero");
  useEffect(() => { ref.current && ref.current.scrollIntoView({ behavior: "smooth", block: "nearest" }); }, [recipe.id]);
  useEffect(() => { if (!rid) return; let stop = false; const tick = async () => { try { const r = await api(`/api/recipes/${recipe.id}/runs/${rid}`); if (stop) return; setRun(r); if (["queued", "running"].includes(r.status)) setTimeout(tick, 1500); } catch (e) { if (!stop) setErr(e.message); } }; tick(); return () => { stop = true; }; }, [rid]);
  const going = run && ["queued", "running"].includes(run.status);
  const go = async () => { setErr(""); setStarting(true); setRun(null); try { const r = await post(`/api/recipes/${recipe.id}/run`, { values: vals, plan: plan || undefined }); setRid(r.run); } catch (e) { setErr(e.message); } setStarting(false); };
  const cancel = () => post(`/api/recipes/${recipe.id}/runs/${rid}/cancel`, {}).catch((e) => setErr(e.message));
  const active = run && (run.steps || []).find((s) => s.status === "running"); const done = run ? (run.steps || []).filter((s) => s.status === "done" || s.status === "skipped").length : 0;
  const statusLine = !run ? "" : run.status === "queued" ? `In line${run.position ? ", position " + run.position : ""}. One recipe runs at a time.` : run.status === "running" ? `Step ${done + 1} of ${run.steps.length}: ${active ? active.label : ""}${active && active.note ? ". " + active.note : ""}` : run.status === "done" ? `Done in ${fmtT(run.seconds)}, peak ${Math.round(run.peak_vram_gib || 0)} GiB.` : run.status === "cancelled" ? "Cancelled." : run.error || run.status;
  const t = recipe.tested; const tSteps = t && t.steps ? recipe.steps.map((s) => ({ ...s, ...(t.steps[s.id] || {}) })) : recipe.steps;
  return html`<section class="rxdetail" ref=${ref} aria-label=${recipe.title}>
    <div class="rxhead"><div><h3>${recipe.title}</h3><p>${recipe.why}</p></div><button class="btn small" onClick=${onClose}>Close</button></div>
    <div class="rxbox"><h4>The chain</h4><${Chain} steps=${tSteps} live=${run ? run.steps : null} recipe=${recipe.id} run=${rid} onGraph=${setGraph}/></div>
    ${run && run.output && html`<div class="rxresult"><video key=${run.output.url} src=${run.output.url} controls autoplay loop playsinline></video><div class="rxrun" style="margin-top:8px"><a class="btn small" href=${run.output.url} download>Download</a>${(run.steps || []).filter((s) => s.facts && s.facts.bpm).map((s) => html`<span class="small">${s.facts.bpm} BPM, cuts at ${(s.facts.cuts_at || []).join(", ")} s</span>`)}${(run.steps || []).filter((s) => s.facts && s.facts.seam_ssim_after != null).map((s) => html`<span class="small">Seam SSIM ${s.facts.seam_ssim_before} before, ${s.facts.seam_ssim_after} after</span>`)}</div></div>`}
    ${!run && t && t.media && html`<div class="rxresult"><video src=${t.media} poster=${t.poster} controls playsinline preload="metadata"></video><p class="small" style="margin:8px 0 0">Rendered on this box${t.rendered ? " on " + t.rendered : ""}: ${fmtT(t.seconds)} in total, ${Math.round(t.peak_vram_gib)} GiB peak.${t.note ? " " + t.note : ""}</p></div>`}
    <div class="rxgridtwo"><div class="rxbox">
      ${fields.map((f) => html`<label class="rxfield">${f.label}${f.multiline ? html`<textarea value=${vals[f.key]} onInput=${(e) => setVals({ ...vals, [f.key]: e.target.value })}></textarea>` : html`<input type="text" value=${vals[f.key]} onInput=${(e) => setVals({ ...vals, [f.key]: e.target.value })}/>`}</label>`)}
      ${film && html`<${FilmPlan} recipe=${recipe} sentence=${vals.sentence || ""} plan=${plan} setPlan=${setPlan} onErr=${setErr}/>`}
      <div class="rxrun"><button class="rxgo" disabled=${going || starting} onClick=${go}>${going ? "Running" : "Run this recipe"}</button>${going && html`<button class="btn small" onClick=${cancel}>Cancel</button>`}<div class="rxcost"><b>0 credits</b>${recipe.expected.seconds > 0 && html`<span>about ${fmtT((t && t.seconds) || recipe.expected.seconds)}</span>`}${recipe.expected.peak_gib > 0 && html`<span>${Math.round((t && t.peak_vram_gib) || recipe.expected.peak_gib)} GiB peak</span>`}<span>${t ? "tested here" : "not rendered here yet"}</span></div></div>
      ${statusLine && html`<p class="rxstatus" aria-live="polite" style="margin:10px 0 0">${statusLine}</p>`}${err && html`<p class="rxerr">${err}</p>`}
    </div><div class="rxbox"><h4>Models and licences</h4><ul class="rxlic">${(recipe.models || []).map((m) => html`<li><b>${m.name}</b><small>${m.licence}${m.note ? ". " + m.note : ""}</small></li>`)}</ul>
      ${recipe.tips && recipe.tips.length > 0 && html`<h4 style="margin-top:14px">Tips</h4><ul class="rxtips">${recipe.tips.map((x) => html`<li>${x}</li>`)}</ul>`}</div></div>
    ${graph && html`<${GraphModal} recipe=${recipe.id} run=${rid} step=${graph} onClose=${() => setGraph(null)}/>`}
  </section>`;
}

function Card({ r, on, onPick }) {
  const t = r.tested;
  return html`<button class=${"gcard" + (on ? " on" : "")} aria-pressed=${on} onClick=${() => onPick(r.id)}>
    ${t && t.media ? html`<video class="gmedia" src=${t.media} poster=${t.poster} muted loop playsinline preload="none" onMouseEnter=${(e) => e.target.play().catch(() => {})} onMouseLeave=${(e) => e.target.pause()}></video>` : html`<div class="gmedia gblank">${"→"}</div>`}
    <span class="gshade"></span><span class=${"gflag" + (t ? "" : " rxun")}>${t ? "Tested here" : "Not rendered yet"}</span><span class="glic" title=${(r.models || []).map((m) => m.name + ": " + m.licence).join("\n")}>${licenceWord(r)}</span>
    <span class="gtext"><b>${r.title}</b><small>${r.pitch}</small><span class="rxstat">${r.steps.length} steps${t ? html`<span><b>${fmtT(t.seconds)}</b></span><span><b>${Math.round(t.peak_vram_gib)} GiB</b></span>` : r.expected.seconds ? html`<span>about ${fmtT(r.expected.seconds)}</span>` : null}</span></span></button>`;
}

export function Recipes() {
  const [d, setD] = useState(null), [err, setErr] = useState(""), [sel, setSel] = useState(null), [filter, setFilter] = useState("all"), [initialRun, setInitialRun] = useState(null);
  useEffect(() => { api("/api/recipes").then(setD).catch((e) => setErr(e.message)); try { const o = JSON.parse(sessionStorage.getItem(OPEN) || "null"); if (o) { sessionStorage.removeItem(OPEN); setSel(o.id); setInitialRun(o.run); } } catch {} }, []);
  const rows = (d && d.recipes) || []; const heroes = rows.filter((r) => r.tags && r.tags.includes("hero")).sort((a, b) => (b.id === "music_video") - (a.id === "music_video")); const tags = useMemo(() => ["all", "tested", ...new Set(rows.flatMap((r) => r.tags || []).filter((x) => x !== "hero"))], [rows]); const shown = rows.filter((r) => !heroes.includes(r) && (filter === "all" || (filter === "tested" ? r.status === "tested" : (r.tags || []).includes(filter)))); const cur = rows.find((r) => r.id === sel);
  if (!d) return html`<p class="small">${err || "Loading the recipes..."}</p>`;
  return html`<div class="rx"><style>${CSS}</style>
    ${heroes.map((hero) => html`<section class="rxhero" aria-label=${hero.title}>${hero.tested && hero.tested.media ? html`<video src=${hero.tested.media} poster=${hero.tested.poster} muted autoplay loop playsinline controls></video>` : html`<div class="gmedia gblank" style="position:static;min-height:260px;height:100%"></div>`}<div class="rxherot"><h2>${hero.title}</h2><p>${hero.pitch}</p><div class="rxcost"><b>0 credits</b>${hero.tested ? html`<span>${fmtT(hero.tested.seconds)} here</span><span>${Math.round(hero.tested.peak_vram_gib)} GiB peak</span><span>tested here</span>` : html`<span>not rendered here yet</span>`}</div><div class="rxrun"><button class="rxgo" onClick=${() => { setSel(hero.id); setInitialRun(null); }}>${hero.id === "music_video" ? "Make a music video" : "Try it"}</button></div></div></section>`)}
    <p class="small" style="margin:0;max-width:760px">Each recipe runs the same goals you can run by hand, one step at a time, passing each output to the next step. ${d.tested} of ${rows.length} rendered on this box so far; the others say so.</p>
    <div class="chips" role="group" aria-label="filter recipes">${tags.map((t) => html`<button class=${"chip" + (filter === t ? " on" : "")} onClick=${() => setFilter(t)}>${t}</button>`)}</div>
    ${cur && html`<${Detail} key=${cur.id} recipe=${cur} initialRun=${initialRun} onClose=${() => { setSel(null); setInitialRun(null); }}/>`}
    <div class="rxgrid">${shown.map((r) => html`<${Card} r=${r} on=${sel === r.id} onPick=${(id) => { setSel(id); setInitialRun(null); }}/>`)}</div>
  </div>`;
}
export default Recipes;
