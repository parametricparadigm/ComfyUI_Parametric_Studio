/* One method's page in the Sampling Lab: plain English, the working, the proof, who wrote it, and what runs here. */
import { useEffect, useRef, useState } from "preact/hooks";
import { html, api, post } from "./common.js";
import { FAMILIES, LABELS, LABEL_MEANS, proofFacets, runsHere, canRun, runRequest, neighbours, packName, licenceWord, authorWord, tidyText, baselineFor, curveStats } from "./samplinglab_logic.js";
import { proofPill, place, unproven, Equation, Wipe, ABTable, SigmaChart, StepRug, SPACE_WORD, sigmaWord } from "./samplinglab_kit.js";

const famWord = Object.fromEntries(FAMILIES);
const toList = (ev) => { if (ev) ev.preventDefault(); location.hash = "sampling"; };

function RunPanel({ e, renders }) {
  const models = renders.models || {}; const keys = Object.keys(models);
  const [model, setModel] = useState(keys.includes(e.prefer_model) ? e.prefer_model : keys[1] || keys[0] || "sdxl"); const [state, setState] = useState(null); const [err, setErr] = useState(""); const [g, setG] = useState(null); const t = useRef(null);
  useEffect(() => () => clearTimeout(t.current), []);
  const q = () => runRequest(e, model);
  const copy = async () => { setErr(""); try { const d = await api("/api/sampling/graph?" + new URLSearchParams(q())); setG(d); try { await navigator.clipboard.writeText(JSON.stringify(d.graph, null, 1)); window.studioToast && window.studioToast("ok", "Graph copied. Paste it into ComfyUI's API or Pro."); } catch { /* the text box below still shows it */ } } catch (x) { setErr(x.message || "Could not build the graph."); } };
  const run = async () => { setErr(""); setState({ status: "queued" }); try { const d = await post("/api/sampling/run", q()); const poll = async () => { const j = await api("/api/jobs/" + d.job); setState(j); if (!["done", "error"].includes(j.status) && !j.lost) t.current = setTimeout(poll, 1500); }; poll(); } catch (x) { setState(null); setErr(x.message || "Could not start it."); } };
  return html`<div class="slrun"><h3>Try it on this machine</h3>
    <label class="slctl"><span>Model</span><select value=${model} onChange=${(ev) => setModel(ev.target.value)}>${keys.map((k) => html`<option value=${k}>${models[k].name}</option>`)}</select></label>
    <div class="slbtnrow"><button class="btn primary" onClick=${run} disabled=${state && !["done", "error"].includes(state.status)}>Run it</button><button class="btn" onClick=${copy}>Copy the graph</button></div>
    <p class="slnote">Core nodes only, same seed and prompt as the proof renders. It uses the GPU and joins ComfyUI's queue like any other job.</p>
    ${err && html`<p class="slerr" role="alert">${err}</p>`}
    ${state && html`<p class="slnote" aria-live="polite">${state.status === "done" ? `Done in ${state.seconds ?? "?"} s.` : state.status === "error" ? "It failed: " + (state.error || "ComfyUI gave no reason.") : state.status === "queued" ? "Waiting in the queue." : "Rendering."}</p>`}
    ${state && state.files && state.files[0] && html`<img src=${state.files[0].url} alt=${"Result of " + e.name}/>`}
    ${g && html`<details class="sldet"><summary>The graph</summary><pre class="slpre">${JSON.stringify(g.graph, null, 1)}</pre></details>`}
  </div>`;
}
const kv = (o) => Object.entries(o || {}).filter(([, v]) => v !== "" && v != null && !(typeof v === "object" && !Object.keys(v).length));
const show = (v) => typeof v === "boolean" ? (v ? "yes" : "no") : typeof v === "object" ? JSON.stringify(v) : String(v);

/* A core scheduler's own curve, drawn against its neighbours by the same code. */
function MethodCurve({ name, measures }) {
  const sch = measures.schedules || {}; const spaces = Object.keys(sch).filter((s) => sch[s].by_steps["20"] && sch[s].by_steps["20"][name]);
  const [space, setSpace] = useState(spaces[0]); const [log, setLog] = useState(true); const [step, setStep] = useState(3); if (!spaces.length) return null;
  const row = sch[space || spaces[0]].by_steps["20"]; const others = ["karras", "normal", "simple"].filter((k) => k !== name && row[k]).slice(0, 2);
  const series = [{ k: name, vals: row[name], color: "#f5c518" }, ...others.map((k, i) => ({ k, vals: row[k], color: ["#6ea8ff", "#9aa39a"][i] }))];
  const st = curveStats(row[name]);
  return html`<section class="slinst film"><div class="slinst-head"><div><span class="slkick">Instrument</span><h3>Its sigma curve at 20 steps</h3></div><div class="slscope-ctl">
      <label class="slctl"><span>Model type</span><select value=${space} onChange=${(e) => setSpace(e.target.value)}>${spaces.map((s) => html`<option value=${s}>${SPACE_WORD[s] || s}</option>`)}</select></label>
      <div class="slctl"><span>Scale</span><div class="slseg dark" role="group" aria-label="Scale"><button aria-pressed=${log} onClick=${() => setLog(true)}>Log</button><button aria-pressed=${!log} onClick=${() => setLog(false)}>Linear</button></div></div></div></div>
    <${SigmaChart} series=${series} log=${log} step=${step} setStep=${setStep} height=${300} ariaName=${"Sigma curve of " + name}/>
    <${StepRug} series=${series} log=${log}/>
    <div class="slfigs small"><div><b class="gold">${sigmaWord(st.start)}</b><span>first sigma</span></div><div><b>${sigmaWord(st.last)}</b><span>last sigma before zero</span></div><div class="push"><span class="slp proof">Measured here</span></div></div>
  </section>`;
}
function MethodRenders({ shots, renders }) {
  const [at, setAt] = useState(0); const r = shots[at] || shots[0]; const rows = (renders.renders || []).filter((x) => x.set === r.set && x.status === "rendered"); const base = baselineFor(rows) || r; const a = base.id === r.id ? rows.find((x) => x.id !== r.id) || r : base;
  return html`<section class="slinst film"><div class="slinst-head"><div><span class="slkick">Instrument</span><h3>Rendered here, against ${a.label}</h3></div>${shots.length > 1 ? html`<div class="slseg dark" role="group" aria-label="Which render">${shots.map((s, i) => html`<button aria-pressed=${i === at} onClick=${() => setAt(i)}>${s.model === "sd35" ? "SD 3.5" : s.model === "sdxl" ? "SDXL" : "SD 1.5"}</button>`)}</div>` : null}</div>
    <div class="slinst-split"><div class="slinst-wipe"><${Wipe} key=${a.id + r.id} a=${a} b=${r}/></div><div class="slinst-side">
      <div class="slfigs">${r.diff_to_base != null && base.id !== r.id ? html`<div><b class="gold">${r.diff_to_base}</b><span>mean pixel difference from ${base.label}, of 255</span></div>` : null}<div><b>${r.seconds}</b><span>seconds, coarse</span></div></div>
      <${ABTable} a=${a} b=${r}/>
      ${r.seen ? html`<p class="slseen"><b>What we saw:</b> ${r.seen}</p>` : null}
      <div class="slpills"><span class="slp proof">Measured here</span><span class="slp">One seed, one prompt</span></div>
      <p><a class="sllink" href=${`#sampling/renders/${r.set}/${a.id}/${r.id}`}>Open it in the render bench</a></p>
    </div></div>
  </section>`;
}
function MethodBench({ bench, sampler }) {
  const e = bench.eps; const det = e.same_answer_with_other_noise_seed; const rm = e.rmse_to_exact || {}; const hi = Math.max(...[5, 10, 20, 40].map((n) => rm[n] || 0), 1e-9);
  return html`<section class="slinst"><div class="slinst-head"><div><span class="slkick ink">Instrument</span><h3>Measured on a toy problem, not a picture</h3></div><span class="slp proof">Measured here</span></div>
    <div class="slfigs small"><div><b class="ink">${e.calls && e.calls["20"]}</b><span>model calls for 20 steps</span></div><div><b>${det ? "Yes" : "No"}</b><span>${det ? "same answer with another noise seed, so deterministic" : "same answer with another noise seed: it is stochastic"}</span></div>${!det ? html`<div><b>${e.variance_error["20"]}</b><span>variance error at 20 steps</span></div>` : null}</div>
    ${det ? html`<div class="slminib" role="img" aria-label=${`${sampler} error to exact answer at 5, 10, 20 and 40 steps: ${[5, 10, 20, 40].map((n) => rm[n]).join(", ")}`}>${[5, 10, 20, 40].map((n) => html`<div><i style=${{ height: (rm[n] / hi * 100) + "%" }}></i><b>${rm[n]}</b><span>${n} steps</span></div>`)}</div>` : null}
    <p class="slnote">Error to the exact answer falls as steps rise. This says how a solver follows the equation, nothing about how a picture looks. <a class="sllink" href="#sampling/bench">See all the solvers</a></p></section>`;
}

export function Method({ id, measures, renders, data, rows }) {
  const [e, setE] = useState(null); const [err, setErr] = useState(""); const head = useRef(null);
  useEffect(() => { setE(null); setErr(""); api("/api/sampling/entry/" + encodeURIComponent(id)).then(setE).catch(() => setErr("That method isn't in the atlas.")); }, [id]);
  useEffect(() => { if (e && head.current) head.current.focus({ preventScroll: true }); }, [e && e.id]);
  const back = html`<a class="slback" href="#sampling" onClick=${toList}>‹ All ${(data.entries || []).length} methods</a>`;
  if (err) return html`<div class="slm">${back}<p class="slerr" role="alert">${err}</p></div>`;
  if (!e) return html`<div class="slm">${back}<div class="slm-skel pp-loading" aria-busy="true" role="status"><span class="slnote">Opening this method</span><i aria-hidden="true"></i></div></div>`;
  const sampler = e.core_ref && e.core_ref.sampler_name, scheduler = e.core_ref && e.core_ref.scheduler; const bench = sampler && measures.solvers && measures.solvers[sampler]; const benchOk = bench && bench.eps && !bench.eps.error;
  const hasCurve = !!(scheduler && measures.schedules && Object.values(measures.schedules).some((s) => s.by_steps["20"] && s.by_steps["20"][scheduler]));
  const shots = (renders.renders || []).filter((r) => (e.rendered_ids || []).includes(r.id)); const facets = proofFacets(e, { curve: hasCurve, bench: benchOk }); const run = runsHere(e); const n = neighbours(rows, data.entries, e); const lab = renders.pack_lab;
  return html`<article class="slm">
    <nav class="slm-nav" aria-label="Method navigation">${back}<span class="grow"></span>${n.prev && html`<a class="slghost" href=${"#sampling/" + n.prev.id} rel="prev"><span aria-hidden="true">‹</span> ${n.prev.name}</a>`}${n.next && html`<a class="slghost" href=${"#sampling/" + n.next.id} rel="next">${n.next.name} <span aria-hidden="true">›</span></a>`}</nav>
    <header class="slm-head">
      <div class="slm-title"><span class="slkick ink">${famWord[e.family] || e.family}${e.subfamily ? " · " + e.subfamily : ""}</span><h2 tabindex="-1" ref=${head}>${e.name}</h2><p class="sllead">${e.plain}</p></div>
      <aside class=${"slm-runs " + run.tone}><span class="slkick">What runs here</span><b>${run.word}</b><p>${run.text}</p>
        ${!e.in_core && renders.packs ? (e.rendered ? null : html`<p class="why">${e.live ? `Its pack is installed here. We rendered ${renders.packs.rendered} pack methods on this machine, chosen to show visible differences; this isn't one of them yet.` : "Its pack isn't installed on this machine, so nothing here has run it."}</p>`) : !e.in_core && lab ? html`<p class="why">${lab.why}</p>` : null}
        <div class="slpills">${place(e)}${e.audit && (e.audit.verdict === "correct" || e.audit.fixed) ? html`<span class="slp proof">Second reader checked</span>` : null}${e.flagged_providers ? html`<span class="slp warn">Script scan flags on ${e.flagged_providers} of ${e.providers_n} packs</span>` : null}</div>
      </aside>
    </header>
    <ol class="slladder" aria-label="What this page's claims rest on">${facets.map((f) => html`<li class=${(f.on ? "on" : "off") + (f.main ? " main" : "")}><b>${LABELS[f.key] || f.key}${f.main ? html`<small>main source</small>` : null}</b><span>${f.on ? f.note || LABEL_MEANS[f.key] : "Nothing of this kind here"}</span></li>`)}</ol>
    ${e.math ? html`<${Equation} text=${e.math} label=${proofPill(e.label)}/>` : null}
    ${shots.length ? html`<${MethodRenders} shots=${shots} renders=${renders}/>` : null}
    ${hasCurve ? html`<${MethodCurve} name=${scheduler} measures=${measures}/>` : null}
    ${benchOk ? html`<${MethodBench} bench=${bench} sampler=${sampler}/>` : null}
    ${e.surprise ? html`<aside class="slworth"><span class="slkick ink">Worth knowing</span><p>${tidyText(e.surprise)}</p></aside>` : null}
    <div class="slm-grid"><div class="slcol">
      <section class="slcredit"><h3>Who wrote it, and thanks</h3><ul>${(e.providers || []).map((p) => html`<li><div class="who"><b>${authorWord(p)}</b><span>${p.pack === "core" ? "ComfyUI core" : packName(p.pack)}</span></div><div class="slpills"><span class=${"slp" + (!p.licence || p.licence === "none-found" ? " warn" : "")}>${licenceWord(p.licence)}</span>${p.kind && p.kind !== "original" ? html`<span class="slp">${p.kind}</span>` : null}${p.verdict ? html`<span class="slp">Qwen read it: ${p.verdict}</span>` : null}</div>${(p.risks || []).length ? html`<p class="slrisk">Script scan: ${p.risks.join(", ")}</p>` : null}${p.note ? html`<p class="slnote">${p.note}</p>` : null}${p.res4lyf ? html`<p><a class="sllink" href="#res4lyf">See the RES4LYF page</a></p>` : null}${p.blepping ? html`<p><a class="sllink" href="#blepping">See the blepping page, with our renders</a></p>` : null}</li>`)}</ul></section>
      ${(e.claims || []).length ? html`<section class="slbox"><h3>What the authors say, not checked here</h3><ul class="sllist">${e.claims.map((c) => html`<li>${c.text} ${proofPill(c.label)}</li>`)}</ul></section>` : null}
      ${(e.family_fit || []).length ? html`<section class="slbox"><h3>Model families, only where there is evidence</h3><ul class="sllist">${e.family_fit.map((f) => html`<li><b>${f.family}</b>: ${f.why} ${proofPill(f.label)}</li>`)}</ul></section>` : null}
      ${e.audit ? html`<section class="slbox"><h3>Second reader</h3><p class="slnote">${e.audit.verdict === "correct" ? "A second reader checked this against the code and agreed." : e.audit.fixed ? "A second reader found a problem and this text is the corrected version. " + e.audit.note : e.audit.verdict === "couldnt_verify" ? "A second reader couldn't verify this. " + e.audit.note : "A second reader's note on this entry: " + e.audit.note}</p></section>` : null}
      <section class="slbox"><h3>Where we read it</h3><ul class="sllist code">${(e.evidence || []).map((ev) => html`<li><code>${ev.where}</code> <code class="sym">${ev.symbol}</code></li>`)}</ul></section>
    </div><div class="slcol">
      ${canRun(e) ? html`<${RunPanel} e=${e} renders=${renders}/>` : null}
      ${kv(e.props).length ? html`<section class="slbox"><h3>Properties</h3><dl class="slkv">${kv(e.props).map(([k, v]) => html`<dt>${k.replace(/_/g, " ")}</dt><dd>${show(v)}</dd>`)}</dl></section>` : null}
      ${!e.in_core && !e.live ? html`<p class="slnote">Pack code is not bundled with the studio.</p>` : null}
      ${n.siblings.length ? html`<section class="slbox"><h3>Also in ${e.subfamily || famWord[e.family]}</h3><ul class="slsibs">${n.siblings.map((s) => html`<li><a href=${"#sampling/" + s.id}>${s.name}</a>${unproven(s)}</li>`)}</ul></section>` : null}
    </div></div>
  </article>`;
}
