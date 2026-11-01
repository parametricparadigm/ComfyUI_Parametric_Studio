/* The Atlas: a dated map of generative AI models, 2013 to today. Each card: what it was, why it mattered, licence, whether this studio can run it, how well it has been tested here, and a Use-this button.
   Plain list view on purpose (semantic <ol>/<article>, buttons with aria-pressed, no canvas), so it works with a keyboard and a screen reader. Facts come from /api/atlas; unverified fields say so. */
import { useState, useEffect, useMemo, useRef } from "preact/hooks";
import { html, api } from "./common.js";
import { Stage, Stats, Strip } from "./look.js";

const KINDS = [["all", "All"], ["image", "Image"], ["video", "Video"], ["audio", "Audio"], ["3d", "3D"], ["llm", "LLM"]];
const KIND_LABEL = { image: "Image", video: "Video", audio: "Audio", "3d": "3D", llm: "LLM" };
const LIC = { open: "Open licence", community: "Community terms", noncommercial: "Non-commercial", research: "Research use", proprietary: "Closed", paper: "Paper", unverified: "Licence unverified" };
const STATUS = { goal: ["Core goal here", "atl-s-goal"], instance: ["Family instance here", "atl-s-inst"], missing: ["Missing", "atl-s-miss"] };
const MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
export const fmtDate = (d, prec) => { if (!d) return "Date not verified"; const [y, m, dd] = d.split("-"); return prec === "day" && dd ? `${+dd} ${MON[+m - 1]} ${y}` : prec === "month" || !dd ? `${MON[+m - 1] || ""} ${y}`.trim() : `${+dd} ${MON[+m - 1]} ${y}`; };
const reduce = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
const goHash = (h, then) => { location.hash = h; if (then) setTimeout(then, 80); };
const useGoal = (g) => goHash("create", () => dispatchEvent(new CustomEvent("prime-action", { detail: { type: "set_goal", goal: g } })));
const copy = (t) => { try { navigator.clipboard.writeText(t); window.studioToast && window.studioToast("ok", "Copied: " + t); } catch {} };
export const matches = (m, f) => (f.kind === "all" || m.kinds.includes(f.kind)) && (!f.tested || m.tested) && (!f.runs || m.can_run) && (!f.q || [m.name, m.org, m.what, m.why, m.licence, m.family].join(" ").toLowerCase().includes(f.q));

function Media({ m }) {
  const r = m.renders && m.renders.media; const ref = useRef(null);
  useEffect(() => { const v = ref.current; if (!v || !r || r.kind !== "video") return; const io = new IntersectionObserver((es) => { es[0].isIntersecting && !reduce() ? v.play().catch(() => {}) : v.pause(); }, { threshold: 0.3 }); io.observe(v); return () => io.disconnect(); }, [r && r.src]);
  if (!r || !r.poster) return html`<div class="atl-plate" aria-hidden="true"><b>${(m.date || "").slice(0, 4) || "?"}</b></div>`;
  return r.kind === "video" ? html`<video ref=${ref} class="atl-media" src=${r.src} poster=${r.poster} muted loop playsinline preload="none" aria-label=${"A render from " + m.name}></video>` : html`<img class="atl-media" src=${r.poster} alt=${"A render from " + m.name} loading="lazy"/>`;
}

function Status({ m }) {
  const r = m.renders, p = m.proof || {}, notes = (p.tested || 0) + (p.mixed || 0) + (p.untested || 0) + (p.unknown || 0);
  return html`<dl class="atl-stat">
    <div><dt>In this studio</dt><dd><span>${m.can_run === "goal" ? html`<span class="atl-dot g"></span>Core goal: ${m.goals_live.map((g) => g.label).join(", ")}` : m.can_run === "instance" ? html`<span class="atl-dot i"></span>Family instance: ${m.instance.family}${m.instance.up ? ` (running on port ${m.instance.port})` : ""}` : html`<span class="atl-dot n"></span>${m.licence_class === "paper" ? "A paper: its ideas run inside the models below" : m.licence_class === "proprietary" ? "Closed: not runnable here" : "Not installed here"}`}</span></dd></div>
    ${(r || m.instance_check || notes > 0) && html`<div><dt>Tested here</dt><dd>
      ${r && html`<span>Rendered in this studio: ${r.count} render${r.count > 1 ? "s" : ""}${r.median_seconds ? `, median ${r.median_seconds} s` : ""}${r.peak_vram_gib ? `, peak ${r.peak_vram_gib} GB VRAM` : ""}.</span>`}
      ${m.instance_check && html`<span>Instance check: ${m.instance_check} (no render).</span>`}
      ${notes > 0 && html`<span>Earlier notes: ${p.tested} tested, ${p.mixed} mixed, ${p.untested} untested, ${p.unknown} unknown.</span>`}</dd></div>`}
  </dl>`;
}

function Use({ m }) {
  const [open, setOpen] = useState(false); const g = m.goals_live || [];
  if (g.length) return html`<div class="atl-act"><button class="btn small primary" onClick=${() => useGoal(g[0].id)}>Use this: ${g[0].label}</button>${g.slice(1).map((x) => html`<button class="btn small" onClick=${() => useGoal(x.id)}>${x.label}</button>`)}</div>`;
  if (m.instance) return html`<div class="atl-act">${m.instance.up ? html`<a class="btn small primary" href=${"http://127.0.0.1:" + m.instance.port} target="_blank" rel="noopener noreferrer">Use this: open its ComfyUI</a>` : html`<button class="btn small primary" aria-expanded=${open} onClick=${() => setOpen(!open)}>Use this: start its instance</button>`}
    ${open && !m.instance.up && html`<div class="atl-cmd"><code>python -m psn.instances start ${m.instance.family}</code><button class="btn small" onClick=${() => copy("python -m psn.instances start " + m.instance.family)}>Copy</button><small>Checks free VRAM first. Run it in the repository folder, then open the port it prints.</small></div>`}</div>`;
  return null;
}

function Card({ m }) {
  return html`<li class=${"atl-card" + (m.featured ? "" : " compact") + (m.can_run ? " runs" : "")} id=${"atlas-" + m.id}><article aria-labelledby=${"atlas-h-" + m.id}>
    ${m.featured && html`<${Media} m=${m}/>`}
    <div class="atl-body">
      <p class="atl-meta"><time datetime=${m.date || ""}>${fmtDate(m.date, m.date_precision)}</time>${!m.date_verified && m.date && html`<span class="atl-flag">date basis: ${m.date_basis}</span>`}${m.org && html`<span>${m.org}</span>`}</p>
      <h3 id=${"atlas-h-" + m.id}>${m.name}</h3>
      <p class="atl-pills">${m.kinds.map((k) => html`<span class="atl-pill">${KIND_LABEL[k]}</span>`)}<span class=${"atl-pill lic " + m.licence_class} title=${m.licence}>${LIC[m.licence_class]}</span>${!m.licence_verified && html`<span class="atl-flag">unverified</span>`}</p>
      <p class="atl-what">${m.what}</p>
      ${m.why && html`<p class="atl-why"><b>Why it mattered.</b> ${m.why}</p>`}
      <p class="atl-lic"><b>Licence.</b> ${m.licence}${m.licence_note ? ". " + m.licence_note : ""}</p>
      <${Status} m=${m}/>
      <div class="atl-foot"><${Use} m=${m}/>${m.source && m.source.url ? html`<a class="atl-src" href=${m.source.url} target="_blank" rel="noopener noreferrer">Source: ${m.source.title}<span class="sr-only"> (opens in a new tab)</span></a>` : html`<span class="atl-src">No source verified</span>`}</div>
    </div></article></li>`;
}

function Coverage({ data, kind }) {
  const [st, setSt] = useState("all"); const ofKind = data.coverage.filter((c) => kind === "all" || c.kinds.includes(kind)); const rows = ofKind.filter((c) => st === "all" || c.status === st); const n = { goal: 0, instance: 0, missing: 0 }; ofKind.forEach((c) => n[c.status]++);
  const eraOf = (d) => (d ? d.slice(0, 4) : "n/a");
  return html`<section aria-labelledby="atl-cov-h" class="atl-cov"><h2 id="atl-cov-h">Coverage: notable open models from SD 1.5 to today</h2>
    <p class="atl-lede">Each model is marked by what this studio has: a <b>core goal</b> (a button in Create), a <b>family instance</b> (its own ComfyUI, started on demand), or <b>missing</b>. Checked on 30 Oct 2026 against ${data.coverage_sources.map((s) => `${s.title} (${s.entries} entries)`).join(" and ")}, and the ${data.stats.families_installed} families installed here. Missing means no family folder and no goal; it is not a claim that the model cannot be added.</p>
    <div class="atl-chips" role="group" aria-label="coverage status">${[["all", `All ${ofKind.length}`], ["goal", `Core goal ${n.goal}`], ["instance", `Family instance ${n.instance}`], ["missing", `Missing ${n.missing}`]].map(([k, l]) => html`<button class=${"chip" + (st === k ? " on" : "")} aria-pressed=${st === k} onClick=${() => setSt(k)}>${l}</button>`)}</div>
    <ul class="atl-covlist">${rows.map((c) => html`<li class="atl-covrow"><span class="atl-covname"><b>${c.name}</b><small>${c.kinds.map((k) => KIND_LABEL[k]).join(", ")}</small></span><span class="atl-covyear">${eraOf(c.date)}${!c.date_verified ? " (unverified)" : ""}</span>
      <span class="atl-covlic">${c.licence}${!c.licence_verified ? " (unverified)" : ""}</span><span class=${"atl-badge " + STATUS[c.status][1]}>${STATUS[c.status][0]}</span>
      <span class="atl-covcomfy">${c.in_comfy_lists ? "Found in Comfy's hub or templates" : "Not found in Comfy's hub or templates"}</span>${c.note && html`<span class="atl-covnote">${c.note}</span>`}${c.source_url && html`<a class="atl-src" href=${c.source_url} target="_blank" rel="noopener noreferrer">Source<span class="sr-only"> for ${c.name} (opens in a new tab)</span></a>`}</li>`)}</ul>
    ${!rows.length && html`<p class="small">Nothing matches these filters.</p>`}</section>`;
}

export function Atlas() {
  const [data, setData] = useState(null); const [err, setErr] = useState(""); const [kind, setKind] = useState("all"); const [tested, setTested] = useState(false); const [runs, setRuns] = useState(false); const [q, setQ] = useState(""); const [view, setView] = useState("timeline"); const [era, setEra] = useState("");
  useEffect(() => { api("/api/atlas").then(setData).catch((e) => setErr(e.message)); }, []);
  const f = { kind, tested, runs, q: q.trim().toLowerCase() };
  const shown = useMemo(() => (data ? data.models.filter((m) => matches(m, f)) : []), [data, kind, tested, runs, q]);
  const byEra = useMemo(() => (data ? data.eras.map((e) => ({ ...e, items: shown.filter((m) => m.era === e.id) })).filter((e) => e.items.length) : []), [data, shown]);
  useEffect(() => { if (!byEra.length || view !== "timeline") return; const io = new IntersectionObserver((es) => { const v = es.filter((x) => x.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0]; if (v) setEra(v.target.dataset.era); }, { rootMargin: "-20% 0px -65% 0px" }); document.querySelectorAll(".atl-era").forEach((el) => io.observe(el)); return () => io.disconnect(); }, [byEra, view]);
  const jump = (id) => { const el = document.getElementById("atlas-era-" + id); if (el) { el.scrollIntoView({ behavior: reduce() ? "auto" : "smooth", block: "start" }); el.focus({ preventScroll: true }); } };
  if (err) return html`<p class="small" style="color:var(--err)">${err}</p>`;
  if (!data) return html`<p class="small">Loading the atlas...</p>`;
  const s = data.stats, renders = data.models.filter((m) => m.renders && m.renders.media && m.renders.media.poster).reverse().map((m) => ({ id: m.id, src: m.renders.media.poster, kind: "image", title: m.name, sub: fmtDate(m.date, m.date_precision) + (m.org ? `, ${m.org}` : ""), kicker: "Rendered in this studio" })).filter((x) => !/chef/.test(x.src)).slice(0, 6);
  return html`<div class="atl lk atl-page">
    <div class="lk-lead"><p class="lk-plain">From the first GANs and VAEs in 2013 to today's open video and image models. Each card says what the model was, why it mattered, its licence, whether this studio runs it, and how well it has been tested here. Dates and licences are read from the named source; anything not checked says so.</p><${Stats} items=${[[s.models, "Models and ideas"], [s.run_here, "Run here"], [s.tested, "Tested here"], [s.rendered_here, "Rendered here"]]}/></div>
    ${renders.length > 0 && html`<${Stage} items=${renders} label="Models rendered in this studio" note="Each picture is a real render from that model in this studio's showcase, not yours."/>`}
    <${Strip} label="Atlas view" value=${view} onPick=${setView} items=${[{ k: "timeline", b: "Timeline", s: "Every model, oldest first" }, { k: "coverage", b: "Coverage", s: `${data.coverage.length} notable open models` }]}/>
    <div class="atl-bar" role="region" aria-label="filters">
      <div class="atl-chips" role="group" aria-label="kind">${KINDS.map(([k, l]) => html`<button class=${"chip" + (kind === k ? " on" : "")} aria-pressed=${kind === k} onClick=${() => setKind(k)}>${l}</button>`)}</div>
      <div class="atl-chips" role="group" aria-label="status"><button class=${"chip" + (tested ? " on" : "")} aria-pressed=${tested} onClick=${() => setTested(!tested)}>Tested only</button><button class=${"chip" + (runs ? " on" : "")} aria-pressed=${runs} onClick=${() => setRuns(!runs)}>Runs here</button></div>
      <input type="search" class="atl-q" placeholder="Search models, makers, licences" value=${q} onInput=${(e) => setQ(e.target.value)} aria-label="search the atlas"/>
            <p class="atl-count" role="status" aria-live="polite">${view === "timeline" ? `${shown.length} of ${data.models.length} shown` : `${data.coverage.length} notable models`}</p></div>
    ${view === "coverage" ? html`<${Coverage} data=${data} kind=${kind}/>` : html`<nav class="atl-rail" aria-label="eras">${byEra.map((e) => html`<button class=${"atl-eralink" + (era === e.id ? " on" : "")} aria-current=${era === e.id ? "true" : null} onClick=${() => jump(e.id)}><b>${e.from === e.to ? e.from : `${e.from}-${String(e.to).slice(2)}`}</b><span>${e.name}</span></button>`)}</nav>
      ${byEra.map((e) => html`<section class="atl-era" id=${"atlas-era-" + e.id} data-era=${e.id} tabindex="-1" aria-labelledby=${"atl-eh-" + e.id}>
        <header class="atl-eh"><p class="atl-years">${e.from === e.to ? e.from : `${e.from} to ${e.to}`}</p><h2 id=${"atl-eh-" + e.id}>${e.name}</h2><p>${e.blurb}</p><a class="atl-src" href=${e.source.url} target="_blank" rel="noopener noreferrer">Era source: ${e.source.title}<span class="sr-only"> (opens in a new tab)</span></a></header>
        <ol class="atl-grid">${e.items.map((m) => html`<${Card} m=${m} key=${m.id}/>`)}</ol></section>`)}
      ${!shown.length && html`<div class="atl-none"><h2>Nothing matches</h2><p>Clear a filter or the search box to see more.</p></div>`}`}
    <p class="atl-foot2">Test status: "Rendered in this studio" counts renders in the Create showcase with their measured time and VRAM. "Instance check" means the family's own ComfyUI started and loaded its nodes (${data.instance_check_as_of}). "Earlier notes" are status counts from the author's earlier work and were not re-run here. Coverage is also written up in docs/COVERAGE.md.</p>
  </div>`;
}
