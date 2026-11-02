/* The Pipelines page: productions that chain several model families, each with what a real run left behind. All of it comes from /api/pipelines; a stage with no proof says so. Runs use the recipe queue. Add one by adding a file, see docs/ADDING_A_PIPELINE.md. */
import { useEffect, useRef, useState } from "preact/hooks";
import { html, api, post } from "./common.js";
import { Media, Stats } from "./look.js";
import { clockOf, minutesOf, statusWord, classWord, stageMeta, pageTotals } from "./pipelines_logic.js";

const src = (id, f) => `pipelines/${id}/${f}`;

function StageMedia({ id, m, big }) {
  if (!m) return html`<div class="pl-nomedia">No output</div>`;
  if (m.kind === "audio") return big ? html`<div class="pl-audiobig">${m.poster && html`<img src=${src(id, m.poster)} alt="Waveform of this audio"/>`}<audio controls preload="none" src=${src(id, m.src)}></audio></div>` : html`<img class="pl-wave" src=${src(id, m.poster || "")} alt="Waveform of this audio" loading="lazy"/>`;
  if (m.kind === "video") return big ? html`<video key=${m.src} controls playsinline preload="metadata" poster=${src(id, m.poster)} src=${src(id, m.src)}></video>` : html`<img src=${src(id, m.poster)} alt="" loading="lazy"/>`;
  if (m.kind === "image") return html`<img src=${src(id, m.src)} alt="" loading="lazy"/>`;
  return html`<div class="pl-nomedia">A ${m.name || "file"} on disk</div>`;
}

function Stage({ id, s, i, open, onOpen }) {
  const lead = s.media.find((m) => m.kind !== "file") || s.media[0];
  return html`<li class=${"pl-stage is-" + s.status}>
    <button type="button" aria-expanded=${open} onClick=${onOpen}>
      <span class="pl-thumb"><${StageMedia} id=${id} m=${lead}/><i>${i + 1}</i>${s.status !== "ok" && html`<em>${s.status === "failed" ? "Failed" : "Flawed"}</em>`}</span>
      <b>${s.label}</b>
      <small class="pl-model">${s.model}</small>
      <small class="pl-num">${stageMeta(s)}</small>
    </button>
  </li>`;
}

function StageOpen({ id, s }) {
  return html`<div class="pl-open">
    <div class="pl-openpic">${s.media.filter((m) => m.kind !== "file").slice(0, 3).map((m) => html`<figure key=${m.src}><${StageMedia} id=${id} m=${m} big/></figure>`)}${!s.media.length && html`<div class="pl-nomedia">This stage left no output.</div>`}</div>
    <div class="pl-opentext">
      <h4>${s.label}</h4>
      ${s.does && html`<p>${s.does}</p>`}
      ${s.note && html`<p class=${"pl-note is-" + s.status}><b>${statusWord(s.status)}.</b> ${s.note}</p>`}
      <dl class="pl-facts">
        <div><dt>Model</dt><dd>${s.model || "None"}</dd></div>
        ${s.licence && html`<div><dt>Licence</dt><dd>${s.licence}</dd></div>`}
        <div><dt>Seed</dt><dd>${s.seed == null ? (s.peak_gib == null ? "None" : "Not recorded") : s.seed}</dd></div>
        <div><dt>Time</dt><dd>${s.seconds == null ? "Not recorded" : clockOf(s.seconds)}</dd></div>
        <div><dt>Peak VRAM</dt><dd>${s.peak_gib == null ? "CPU step" : s.peak_gib + " GiB"}</dd></div>
      </dl>
      ${s.prompt && html`<details class="pl-prompt"><summary>Its prompt</summary><p>${s.prompt}</p></details>`}
      ${s.build && html`<details class="pl-prompt"><summary>Its inner steps</summary><ul>${s.build.map((b) => html`<li key=${b.name}>${b.name}: ${b.status}${b.seconds ? ", " + clockOf(b.seconds) : ""}</li>`)}</ul></details>`}
      ${s.graph && html`<a class="btn small" href=${src(id, s.graph)} target="_blank" rel="noopener">The real graph, as JSON</a>`}
    </div>
  </div>`;
}

function Runner({ p, health }) {
  const [vals, setVals] = useState({}), [run, setRun] = useState(null), [err, setErr] = useState(""), t = useRef();
  useEffect(() => () => clearInterval(t.current), []);
  const start = async () => {
    setErr("");
    try {
      const r = await post(`/api/recipes/${p.id}/run`, { values: vals }); const f = async () => { const d = await api(`/api/recipes/${p.id}/runs/${r.run}`); setRun(d); if (["done", "error", "cancelled"].includes(d.status)) clearInterval(t.current); };
      await f(); t.current = setInterval(() => f().catch(() => {}), 3000);
    } catch (e) { setErr(String((e && e.message) || e)); }
  };
  const off = !(health && health.comfy), busy = run && !["done", "error", "cancelled"].includes(run.status);
  return html`<details class="pl-runner"><summary>Run this one yourself</summary>
    <div class="pl-fields">${(p.fields || []).map((f) => html`<label class="lk-field" key=${f.key}>${f.label}<textarea rows=${f.multiline ? 4 : 2} value=${vals[f.key] ?? f.default} onInput=${(e) => setVals({ ...vals, [f.key]: e.target.value })}></textarea></label>`)}</div>
    <button class="btn primary" type="button" disabled=${off || busy} onClick=${start}>${busy ? "Running" : "Run it on this machine"}</button>
    ${off && html`<p class="small">ComfyUI isn't reachable, so this can't run yet.</p>`}
    ${err && html`<p class="small" role="alert" style="color:var(--err)">${err}</p>`}
    ${run && html`<ol class="pl-live" aria-live="polite">${run.steps.map((s) => html`<li key=${s.id} class=${"is-" + s.status}><b>${s.label}</b> <span>${s.status}${s.seconds ? ", " + clockOf(s.seconds) : ""}</span>${s.note && html`<small>${s.note}</small>`}${s.error && html`<small style="color:#ff8c99">${s.error}</small>`}</li>`)}</ol>`}
    ${run && run.status === "done" && run.output && html`<a class="btn" href=${run.output.url} target="_blank" rel="noopener">Open the result</a>`}
    ${(p.tips || []).length > 0 && html`<ul class="pl-tips">${p.tips.map((x) => html`<li key=${x}>${x}</li>`)}</ul>`}
  </details>`;
}

function Pipeline({ p, n, health }) {
  const pr = p.proof, [at, setAt] = useState(null), stages = pr ? pr.stages : [], cur = at != null && stages[at];
  return html`<article class="pl-item film" id=${"pl-" + p.id} aria-labelledby=${"plh-" + p.id}>
    <header class="pl-head"><span class="pl-no" aria-hidden="true">${String(n + 1).padStart(2, "0")}</span><div><span class="lk-kick">${p.kicker}</span><h2 id=${"plh-" + p.id}>${p.title}</h2><p>${p.pitch}</p></div></header>
    ${pr && pr.final ? html`<div class="pl-final">
      <figure class="pl-finalpic">${pr.final.kind === "video" ? html`<video controls playsinline preload="metadata" poster=${src(p.id, pr.final.poster)} src=${src(p.id, pr.final.src)} aria-label=${"The final result of " + p.title}></video>` : html`<${StageMedia} id=${p.id} m=${pr.final} big/>`}</figure>
      <div class="pl-side">
        <span class=${"pl-status is-" + pr.status}>${statusWord(pr.status)}</span>
        <${Stats} items=${[[minutesOf(pr.seconds), "Minutes of work"], [`${pr.peak_vram_gib}`, "GiB, highest peak"], [stages.length, "Stages"]]}/>
        <p class="pl-why">${pr.verdict}</p>
      </div>
    </div>` : pr ? html`<p class="pl-why"><span class=${"pl-status is-" + pr.status}>${statusWord(pr.status)}</span> ${pr.verdict}</p>` : html`<p class="pl-why"><span class="pl-status is-none">Not run yet</span> This pipeline has no real run to show, so it shows nothing.</p>`}
    ${pr && html`<ol class="pl-chain" aria-label="The stages, in order">${stages.map((s, i) => html`<${Stage} key=${s.id} id=${p.id} s=${s} i=${i} open=${at === i} onOpen=${() => setAt(at === i ? null : i)}/>`)}</ol>`}
    ${cur && html`<${StageOpen} id=${p.id} s=${cur}/>`}
    <div class="pl-foot">
      <div class="pl-col"><h3>Why these models</h3><p>${p.why}</p></div>
      <div class="pl-col"><h3>Licences</h3><ul class="pl-lic">${p.models.map((m) => html`<li key=${m.name}><span class=${"pl-class is-" + m.licence_class}>${classWord(m.licence_class)}</span><b>${m.name}</b><small>${m.licence}${m.note ? ". " + m.note : ""}</small></li>`)}</ul></div>
      ${pr && pr.rejected && pr.rejected.length > 0 && html`<div class="pl-col"><h3>What we threw out</h3><ul class="pl-rej">${pr.rejected.map((r) => html`<li key=${r.what}><b>${r.what}.</b> ${r.why}</li>`)}</ul></div>`}
    </div>
    <${Runner} p=${p} health=${health}/>
  </article>`;
}

export function Pipelines({ route, health }) {
  const [list, setList] = useState(null), [err, setErr] = useState("");
  useEffect(() => { api("/api/pipelines").then((d) => setList([...d.pipelines.filter((p) => p.proof), ...d.pipelines.filter((p) => !p.proof)])).catch((e) => setErr(String((e && e.message) || e))); }, []);
  useEffect(() => { const id = (route || "").split("/")[1]; if (list && id) { const el = document.getElementById("pl-" + id); if (el) el.scrollIntoView(); } }, [list, route]);
  if (err) return html`<p class="lk-plain" role="alert">The list didn't load: ${err}</p>`;
  if (!list) return html`<p class="lk-plain">Reading the pipelines.</p>`;
  const t = pageTotals(list);
  return html`<div class="lk pl">
    <div class="pl-sum"><${Stats} items=${[[t.ran, "Pipelines run for real"], [t.stages, "Stages rendered"], [t.families, "Models and tools"], [t.minutes, "Minutes of work"]]}/>${t.notRun > 0 && html`<p class="small">${t.notRun} more ${t.notRun === 1 ? "is" : "are"} written and not run yet.</p>`}<p class="small">${list[0] && list[0].proof ? list[0].proof.peak_note : ""}</p></div>
    <nav class="pl-index" aria-label="The pipelines"><ol>${list.map((p, i) => html`<li key=${p.id}><a href=${"#pipelines/" + p.id}><i>${i + 1}</i><span>${p.title}</span></a></li>`)}</ol></nav>
    ${list.map((p, i) => html`<${Pipeline} key=${p.id} p=${p} n=${i} health=${health}/>`)}
    <section class="pl-add"><h2>Add one in a file</h2><p class="lk-plain">A pipeline is one JSON file in <code>studio/pipelines</code>: its stages, in the recipe format, and a licence for every model. A test checks it, the studio can run it right away, and <code>scripts/record_pipeline.py</code> puts the real run on this page after you have looked at it. The steps are in <code>docs/ADDING_A_PIPELINE.md</code>.</p></section>
  </div>`;
}
