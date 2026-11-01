/* The Sampling Lab: every sampler, scheduler, guidance trick, noise and latent operation we could read the source of, what the code really does, whether it runs here, and the proof. An instrument and an encyclopedia. */
import { useEffect, useMemo, useRef, useState } from "preact/hooks";
import { html, api } from "./common.js";
import { FAMILIES, WHERE, PROOFS, LABELS, LABEL_MEANS, filterEntries, familyCounts, parseRoute, windowRange, dotKind, dotCounts, dotsOf, mapLayout, evidenceCards, licenceCounts, creditWall, tidyText, FIND_GROUPS, whereFirst, hilite, packName, licenceWord } from "./samplinglab_logic.js";
import { proofPill, place, unproven, useWidth, Wipe, Split, SigmaChart, ABTable } from "./samplinglab_kit.js";
import { Curves, Bench, Renders } from "./samplinglab_bench.js";
import { Method } from "./samplinglab_method.js";

const famWord = Object.fromEntries(FAMILIES);
const CLEAR = { q: "", family: "all", where: "all", proof: "all", sort: "match" };
const active = (f) => !!(f.q || f.family !== "all" || f.where !== "all" || f.proof !== "all");
const KIND = { rendered: "Rendered here", core: "In core, not rendered", live: "Live pack, unproven", pack: "Needs a pack, unproven" };

/* ---------- the map ---------- */
function AtlasMap({ data, renders, onFamily }) {
  const [ref, W] = useWidth(1100); const [tip, setTip] = useState(null); const box = useRef(null);
  const tiles = useMemo(() => { const byFam = {}; for (const e of data.entries) (byFam[e.family] = byFam[e.family] || []).push(e); return FAMILIES.map(([k, l]) => ({ k, l, n: (byFam[k] || []).length, dots: dotsOf(byFam[k] || []) })); }, [data]);
  const lay = useMemo(() => mapLayout(tiles, W), [tiles, W]); const c = useMemo(() => dotCounts(data.entries), [data]); const d = lay.dot;
  const over = (ev) => { const r = ev.target; if (!r.dataset || r.dataset.id === undefined) { setTip(null); return; } const b = box.current.getBoundingClientRect(), q = r.getBoundingClientRect(); setTip({ name: r.dataset.name, kind: r.dataset.kind, x: Math.min(q.left - b.left, b.width - 240), y: q.top - b.top }); };
  const dotClick = (ev, fam) => { const r = ev.target; if (r.dataset && r.dataset.id) { ev.stopPropagation(); location.hash = "sampling/" + r.dataset.id; } else onFamily(fam); };
  return html`<section class="slmap film" aria-labelledby="sl-map-h">
    <header class="slmap-top"><div class="slmap-big"><b id="sl-map-h">${data.entries.length}</b><span>methods read from source.<br/>One square each.</span></div>
      <ul class="slmap-key">
        <li><i class="d rendered"></i><b>${c.rendered}</b> rendered here, all in ComfyUI core</li><li><i class="d core"></i><b>${c.core}</b> in core, not rendered</li><li><i class="d live"></i><b>${c.live}</b> in a live pack, unproven</li><li><i class="d pack"></i><b>${c.pack}</b> need a pack, unproven</li>
      </ul></header>
    <div class="slmap-field" ref=${ref}><div class="slmap-tiles" ref=${box} style=${{ height: lay.H + "px" }} onPointerOver=${over} onPointerLeave=${() => setTip(null)}>
      ${lay.tiles.map((t) => { const core = t.dots.filter((e) => e.in_core).length, live = t.dots.filter((e) => e.live && !e.in_core).length; return html`<button class=${"slt" + (t.narrow ? " narrow" : "")} key=${t.k} style=${{ left: t.x + "px", top: t.y + "px", width: t.w + "px", height: t.h + "px" }} aria-label=${`${t.l}: ${t.n} methods, ${core} in core, ${live} in a live pack. Show them.`} onClick=${(ev) => dotClick(ev, t.k)}>
        <span class="slt-l"><b>${t.n}</b><span><em>${t.l}</em><small>${core} in core${live ? ` · ${live} live` : ""}</small></span></span>
        <svg class="slt-d" aria-hidden="true" width=${t.w - 28} height=${Math.max(1, t.h - t.dotY - 6)} style=${{ top: t.dotY + "px" }}>${t.dots.map((e, i) => html`<rect key=${e.id} class=${dotKind(e)} x=${(i % t.cols) * d + .5} y=${Math.floor(i / t.cols) * d + .5} width=${d - Math.max(1.5, d * .14)} height=${d - Math.max(1.5, d * .14)} rx=${Math.max(1, d * .1)} data-id=${e.id} data-name=${e.name} data-kind=${KIND[dotKind(e)]}/>`)}</svg></button>`; })}
      ${tip && html`<div class="slmap-tip" style=${{ left: Math.max(0, tip.x) + "px", top: tip.y + "px" }} role="status"><b>${tip.name}</b><span>${tip.kind}</span></div>`}
    </div></div>
    <${ProofStrip} data=${data} renders=${renders}/>
  </section>`;
}
function ProofStrip({ data, renders }) {
  const cov = data.coverage || {}; const sr = cov.second_reader || {}; const lab = renders.pack_lab; const done = (renders.renders || []).filter((r) => r.status === "rendered").length; const non = data.entries.filter((e) => !e.in_core).length;
  return html`<div class="slstrip">
    <div><b class="gold">${done}</b><span>core renders on this machine, one seed and one prompt per set</span></div>
    ${lab ? html`<div class="warn"><b>${lab.rendered}</b><span>of the ${non} methods outside core are proven by a render. Pack Lab tried ${lab.attempted}, and its control render failed too: <code>VAEDecode</code> hit maximum recursion depth.</span></div>` : null}
    ${cov.second_reader_total ? html`<div><b>${cov.second_reader_total}</b><span>entries checked by a second reader: ${sr.correct || 0} right, ${sr.minor || 0} imprecise, ${sr.wrong || 0} wrong, ${cov.second_reader_fixed || 0} corrected</span></div>` : null}
  </div>`;
}
function LabelKey({ data, renders }) {
  const n = (l) => data.entries.filter((e) => e.label === l).length; const rendered = data.entries.filter((e) => e.rendered).length;
  const rows = [["from code", n("from code") + " methods"], ["measured here", rendered + " methods rendered"], ["from pack README claim", n("from pack README claim") + " methods"], ["inference", n("inference") + " methods"]];
  return html`<section class="slkeyrow" aria-label="How to read a label"><h3>How to read a label</h3><ul>${rows.map(([k, c]) => html`<li>${proofPill(k)}<p>${LABEL_MEANS[k]}</p><small>${c}</small></li>`)}</ul></section>`;
}

/* ---------- highlights ---------- */
function FindCard({ c }) {
  return html`<article class=${"slfind" + (c.minor ? " minor" : "")}>
    <a class="slfind-pic" href=${`#sampling/renders/${c.set}/${c.a}/${c.b}`} aria-label=${"Compare in the render bench: " + c.title}><${Split} a=${c.ra} b=${c.rb}/></a>
    <div class="slfind-body"><h3>${c.title}</h3><div class="slfig"><b>${c.stat}</b><span>${c.unit}</span></div><p>${c.seen}${c.more ? " " + c.more : ""}</p>
      <div class="slfind-foot"><span class="slp proof">Measured here</span><span class="slp">One seed</span><span class="grow"></span><a class="sllink" href=${"#sampling/" + c.method}>The method</a></div></div>
  </article>`;
}
function Highlights({ renders, measures }) {
  const cards = useMemo(() => evidenceCards(renders, measures), [renders, measures]); if (!cards.length) return null;
  return html`<section class="slhigh film" aria-labelledby="sl-h-h"><div class="slband-head"><h2 id="sl-h-h">What we found by running them</h2><a class="sllink" href="#sampling/finds">All the surprises, with the code that causes them ›</a></div>
    <div class="slfinds">${cards.filter((c) => !c.minor).map((c) => html`<${FindCard} key=${c.key} c=${c}/>`)}</div></section>`;
}

/* ---------- the encyclopedia ---------- */
const Row = ({ e, q, i, n, onKey }) => html`<li class="slr-li" style=${{ top: `calc(${i} * var(--row))` }} aria-posinset=${i + 1} aria-setsize=${n}><a class=${"slr " + dotKind(e)} href=${"#sampling/" + e.id} data-i=${i} onKeyDown=${onKey}>
  <span class="slr-pic" aria-hidden="true">${(e.rendered_ids || [])[0] ? html`<img src=${`sampling_lab/${e.rendered_ids[e.rendered_ids.length - 1]}.jpg`} alt="" loading="lazy" width="64" height="64"/>` : html`<i class=${"d " + dotKind(e)}></i>`}</span>
  <span class="slr-main"><span class="slr-fam">${famWord[e.family] || e.family}${e.subfamily ? " · " + e.subfamily : ""}</span><b>${hilite(e.name, q).map(([s, h]) => h ? html`<mark>${s}</mark>` : s)}</b><span class="slr-plain">${e.plain}</span></span>
  <span class="slr-by"><small>by</small> ${e.by && e.by[0] ? e.by[0] : "author not recorded"}${e.providers_n > 1 ? html`<small> and ${e.providers_n - 1} more pack${e.providers_n > 2 ? "s" : ""}</small>` : null}</span>
  <span class="slr-tags">${place(e)}${proofPill(e.label)}${e.rendered ? html`<span class="slp proof">Rendered here</span>` : unproven(e)}</span>
</a></li>`;
function VirtualList({ rows, q }) {
  const box = useRef(null); const [range, setRange] = useState([0, 24]); const pending = useRef(0);
  useEffect(() => {
    const read = () => { pending.current = 0; const el = box.current; if (!el) return; const rh = parseFloat(getComputedStyle(el).getPropertyValue("--row")) || 96; const top = -el.getBoundingClientRect().top; let next = windowRange(top, innerHeight, rh, rows.length); if (next[1] < 16) next = [0, Math.min(16, rows.length)]; /* still below the view: keep the first rows there for screen readers and for anyone tabbing down */ setRange((r) => r[0] === next[0] && r[1] === next[1] ? r : next); };
    const on = () => { if (!pending.current) pending.current = requestAnimationFrame(read); };
    read(); addEventListener("scroll", on, { passive: true }); addEventListener("resize", on);
    return () => { removeEventListener("scroll", on); removeEventListener("resize", on); if (pending.current) cancelAnimationFrame(pending.current); };
  }, [rows]);
  const onKey = (ev) => { const d = { ArrowDown: 1, ArrowUp: -1 }[ev.key]; if (!d) return; const i = +ev.currentTarget.dataset.i + d; const t = box.current.querySelector(`a[data-i="${i}"]`); if (t) { ev.preventDefault(); t.focus(); } };
  const [a, b] = range;
  return html`<ul class="slv" ref=${box} style=${{ height: `calc(${rows.length} * var(--row))` }} aria-label="Methods">${rows.slice(a, b).map((e, k) => html`<${Row} key=${e.id} e=${e} q=${q} i=${a + k} n=${rows.length} onKey=${onKey}/>`)}</ul>`;
}
function SearchBar({ f, set, count, total }) {
  return html`<div class="slsearch"><label class="slsr" for="sl-q"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/></svg><span class="vh">Search the methods</span>
    <input id="sl-q" type="search" autocomplete="off" spellcheck="false" placeholder=${`Search ${total} methods: dpmpp, rescale, pink noise, slerp, teacache`} value=${f.q} onInput=${(ev) => set({ ...f, q: ev.target.value })} onKeyDown=${(ev) => { if (ev.key === "Escape" && f.q) { ev.preventDefault(); set({ ...f, q: "" }); } }}/><kbd aria-hidden="true">/</kbd></label>
    ${active(f) ? html`<span class="slsr-n" aria-live="polite"><b>${count}</b> ${count === 1 ? "method" : "methods"}</span>` : null}</div>`;
}
function Filters({ f, set, counts, count, total }) {
  const [open, setOpen] = useState(false); const on = [f.family, f.where, f.proof].filter((x) => x !== "all").length;
  const chip = (key, k, l, n) => html`<button key=${k} class="slchip" aria-pressed=${f[key] === k} onClick=${() => set({ ...f, [key]: k })}>${l}${n != null ? html`<small>${n}</small>` : null}</button>`;
  return html`<div class=${"slfilters" + (open ? " open" : "")}>
    <button class="slfilt-t" aria-expanded=${open} aria-controls="sl-filters" onClick=${() => setOpen(!open)}><span>Filters${on ? ` (${on} on)` : ""}</span><span class="slnote">${count} of ${total}</span></button>
    <div class="slfilters-b" id="sl-filters"><div class="slf" role="group" aria-label="Kind of method"><span>Kind</span>${chip("family", "all", "All", total)}${FAMILIES.map(([k, l]) => counts[k] ? chip("family", k, l, counts[k]) : null)}</div>
    <div class="slf" role="group" aria-label="Where it runs"><span>Runs</span>${WHERE.map(([k, l]) => chip("where", k, l))}</div>
    <div class="slf" role="group" aria-label="Kind of proof"><span>Proof</span>${PROOFS.map(([k, l]) => chip("proof", k, l))}</div>
    <div class="slf end"><label class="slctl row"><span>Order</span><select value=${f.sort} onChange=${(ev) => set({ ...f, sort: ev.target.value })}><option value="match">What runs here first</option><option value="name">A to Z</option><option value="packs">Most packs</option></select></label>${active(f) ? html`<button class="slghost" onClick=${() => set({ ...CLEAR, sort: f.sort })}>Clear</button>` : null}<span class="slnote" aria-live="polite">${count} of ${total}</span></div></div>
  </div>`;
}
function AtlasView({ data, measures, renders, f, set, rows }) {
  const counts = useMemo(() => familyCounts(data.entries), [data]); const on = active(f); const top = useRef(null);
  const family = (k) => { set({ ...f, family: k }); requestAnimationFrame(() => { if (top.current) top.current.scrollIntoView({ block: "start" }); }); };
  return html`<div class="slview">
    <div ref=${top} class="slanchor"></div>
    <${SearchBar} f=${f} set=${set} count=${rows.length} total=${data.entries.length}/>
    ${!on && html`<${AtlasMap} data=${data} renders=${renders} onFamily=${family}/><${LabelKey} data=${data} renders=${renders}/><${Highlights} renders=${renders} measures=${measures}/>`}
    <section class="slency" aria-labelledby="sl-e-h"><div class="slband-head"><h2 id="sl-e-h" class=${on ? "vh" : ""}>${on ? "Results" : "The encyclopedia"}</h2>${!on ? html`<p class="slnote">Plain English, the working, the proof and the author, for every one. Arrow keys move through the list.</p>` : null}</div>
      <${Filters} f=${f} set=${set} counts=${counts} count=${rows.length} total=${data.entries.length}/>
      ${rows.length ? html`<${VirtualList} rows=${rows} q=${f.q}/>` : html`<div class="slnone"><b>Nothing matches.</b><p>Try fewer words, or clear the filters.</p><button class="btn" onClick=${() => set(CLEAR)}>Clear everything</button></div>`}
    </section>
  </div>`;
}

/* ---------- what surprised us ---------- */
function Unread({ c }) {
  if (!c || !c.packs_in_sections) return null; const h = c.helpers_read || {}; const sr = c.second_reader || {};
  const cells = [[c.packs_in_sections, "packs in the sampling sections"], [c.packs_with_source, "had source on this box; every Python file parsed, not run"], [c.packs_no_source_on_box, "had no source here, so they aren't described"], [(h.read || 0) + (h["read-part"] || 0), "rows opened in full or in part"], [c.evidence_lines_checked_ok, "evidence lines found on disk, " + c.evidence_lines_rejected + " dropped"], [c.second_reader_total || 0, `entries re-read: ${sr.correct || 0} right, ${sr.minor || 0} imprecise, ${sr.wrong || 0} wrong`]];
  return html`<section class="slpanel"><div class="slpanel-head"><div><h3>What we read, and what we didn't</h3></div></div><div class="slfunnel">${cells.map(([n, t]) => html`<div><b>${n}</b><span>${t}</span></div>`)}</div>
    <p class="slnote">Function by function, readers set aside ${h["not-a-method"] || 0} rows as not being a method (mostly by name), went by name alone on ${h["skim-name-only"] || 0}, and skipped ${h.skipped || 0}. A script finding the evidence only proves the code exists there, so the second reader checked ${c.second_reader_total || 0} entries against the code and ${c.second_reader_fixed || 0} were corrected. Entries without that pill had one reader.${c.qwen_tail ? ` Our local model also drafted notes on ${c.qwen_tail} functions nobody opened. Those are unverified, so they aren't shown here.` : ""}</p></section>`;
}
function EvidenceBand({ c, measures, flip }) {
  const sp = c.curve && measures.schedules && measures.schedules[c.curve.space]; const row = sp && sp.by_steps["20"]; const palette = ["#6ea8ff", "#f5c518"]; const series = c.curve && row ? c.curve.names.map((k, i) => ({ k, vals: row[k], color: palette[i] })).filter((s) => s.vals) : null;
  return html`<article class=${"slband film" + (flip ? " flip" : "")} id=${"find-" + c.key}><div class="slband-pic"><${Wipe} a=${c.ra} b=${c.rb}/></div><div class="slband-text">
    <span class="slkick">Rendered on this machine</span><h3>${c.title}</h3><div class="slfig big"><b>${c.stat}</b><span>${c.unit}</span></div>
    <p class="seen">${c.seen}${c.more ? " " + c.more : ""}</p>
    ${series && series.length ? html`<div class="slband-chart"><${SigmaChart} series=${series} log=${c.key !== "karras"} compact height=${170} ariaName=${c.title}/><div class="slkey">${series.map((s) => html`<span><i style=${{ background: s.color }}></i>${s.k}</span>`)}</div></div>` : null}
    ${!series || !series.length ? html`<${ABTable} a=${c.ra} b=${c.rb}/>` : null}
    ${c.code ? html`<p class="slcode"><code>${c.code}</code></p>` : null}
    <div class="slfind-foot"><span class="slp proof">Measured here</span><span class="slp">One seed, one prompt</span><span class="grow"></span><a class="sllink" href=${"#sampling/" + c.method}>The method</a></div></div></article>`;
}
function Finds({ data, renders, measures }) {
  const cards = useMemo(() => evidenceCards(renders, measures), [renders, measures]); const rows = (data.surprises || []).filter((s) => s.source !== "renders"); const [g, setG] = useState("all"); const groups = useMemo(() => { const c = {}; for (const s of rows) c[s.source] = (c[s.source] || 0) + 1; return c; }, [data]);
  const shown = g === "all" ? rows : rows.filter((s) => s.source === g);
  if (!rows.length && !cards.length) return html`<p class="slnote">Nothing written up yet.</p>`;
  return html`<div class="slview">
    <header class="slband-head big"><h2>What surprised us</h2><p class="slnote">${cards.length} seen in real renders, ${rows.length} read in the code. One seed shows a difference; it doesn't prove a rule.</p></header>
    ${cards.map((c, i) => html`<${EvidenceBand} key=${c.key} c=${c} measures=${measures} flip=${i % 2 === 1}/>`)}
    <section class="slread-finds" aria-labelledby="sl-f-h"><div class="slband-head"><h2 id="sl-f-h">Read in the code</h2><p class="slnote">Found by readers of the source. <span class="slp">From code</span> Not run here unless it says so.</p></div>
      <div class="slf wrap" role="group" aria-label="Filter the surprises"><button class="slchip" aria-pressed=${g === "all"} onClick=${() => setG("all")}>All<small>${rows.length}</small></button>${Object.entries(groups).map(([k, n]) => html`<button class="slchip" key=${k} aria-pressed=${g === k} onClick=${() => setG(k)}>${FIND_GROUPS[k] || k}<small>${n}</small></button>`)}</div>
      <div class="slcols">${shown.map((s, i) => { const w = whereFirst(s.where); return html`<article class="slnote-card" key=${i}><span class="slkick ink">${FIND_GROUPS[s.source] || s.source}</span><p>${tidyText(s.text)}</p>${s.id ? html`<a class="sllink" href=${"#sampling/" + s.id}>${s.name || "See the method"}</a>` : null}${w.first ? html`<code>${w.first}${w.more ? ` and ${w.more} more` : ""}</code>` : null}</article>`; })}</div></section>
    <${Unread} c=${data.coverage}/>
  </div>`;
}

/* ---------- credits ---------- */
function Credits({ data }) {
  const [q, setQ] = useState(""); const list = data.credits || []; const rows = useMemo(() => list.filter((c) => !q || (c.pack + " " + c.author).toLowerCase().includes(q.toLowerCase())), [data, q]); const wall = useMemo(() => creditWall(list), [data]); const lic = useMemo(() => licenceCounts(list), [data]); const top = lic.length ? lic[0][1] : 1;
  const tier = (m) => m >= 15 ? "t1" : m >= 6 ? "t2" : m >= 2 ? "t3" : "t4";
  return html`<div class="slview">
    <section class="slroll film" aria-labelledby="sl-c-h"><div class="slroll-top"><h2 id="sl-c-h">Thanks</h2><p>Every method here came from someone's work. These are the people whose code we read, largest share first.</p><div class="slfigs"><div><b class="gold">${list.length}</b><span>packs credited</span></div><div><b>${wall.authors.length}</b><span>named authors</span></div></div></div>
      <p class="slwall">${wall.authors.map((a) => html`<span class=${tier(a.methods)} title=${`${a.methods} method${a.methods === 1 ? "" : "s"}, ${a.packs} pack${a.packs === 1 ? "" : "s"}`}>${a.name}</span> `)}</p>
      ${wall.unknown.length ? html`<div class="slunknown"><h3>${wall.unknown.length} packs whose author we couldn't record</h3><p class="slnote">Their folders on this box carry no owner or repository address, so we credit them by name rather than guess.</p><p class="slwall small">${wall.unknown.map((c) => html`<span class="t4">${packName(c.pack)}</span> `)}</p></div>` : null}
    </section>
    <section class="slpanel"><div class="slpanel-head"><div><h3>Licences as found</h3><p class="slnote">As found in each repository; check them yourself before you ship anything. Each licence is its author's choice and the studio doesn't bundle pack code. RES4LYF's licence bars commercial services without the author's permission, so it gets its own page: <a class="sllink" href="#res4lyf">the RES4LYF tribute</a>.</p></div></div>
      <ul class="sllic">${lic.map(([k, n]) => html`<li><span>${k}</span><i><em style=${{ width: n / top * 100 + "%" }}></em></i><b>${n}</b></li>`)}</ul></section>
    <section class="slency"><div class="slband-head"><h2>Every pack</h2><p class="slnote">"Qwen read it" is our local model's reading of the source, plus a keyword scan. It's a reading, not a safety guarantee.</p></div>
      <label class="slsr small"><span class="vh">Find an author or pack</span><input type="search" placeholder="Find an author or pack" value=${q} onInput=${(e) => setQ(e.target.value)}/></label><p class="slnote" aria-live="polite">${rows.length} of ${list.length}</p>
      <div class="sltablewrap sticky1"><table class="sltable"><thead><tr><th>Pack</th><th>Author</th><th>Licence</th><th class="n">Methods</th><th>Qwen read it</th><th>Risk flags</th></tr></thead><tbody>${rows.map((c) => html`<tr><td>${packName(c.pack)}</td><td>${c.author || "not recorded"}</td><td>${licenceWord(c.licence)}</td><td class="n">${c.methods}</td><td>${c.verdict || "not reviewed"}</td><td class="wrap">${(c.risks || []).join(", ")}</td></tr>`)}</tbody></table></div></section>
  </div>`;
}

/* ---------- the page ---------- */
const VIEWS = (d, m, r) => [["methods", "Atlas", `${d.entries.length} methods`, ""], ["curves", "Curves", `${m.schedules ? Object.keys(m.schedules).length : 0} model types`, "/curves"], ["bench", "Bench", `${m.solvers ? Object.keys(m.solvers).length : 0} solvers`, "/bench"], ["renders", "Renders", `${(r.renders || []).filter((x) => x.status === "rendered").length} real, wipe them`, "/renders"], ["finds", "Surprises", `${(d.surprises || []).length} found`, "/finds"], ["credits", "Credits", `${(d.credits || []).length} packs`, "/credits"]];
export function SamplingLab({ route }) {
  const { view, id, rest } = parseRoute(route);
  const [data, setData] = useState(null); const [measures, setM] = useState({}); const [renders, setR] = useState({ renders: [], models: {} }); const [err, setErr] = useState(""); const [f, setF] = useState(CLEAR); const place0 = useRef(0); const saved = useRef(0); const idRef = useRef(id);
  useEffect(() => { api("/api/sampling/atlas").then(setData).catch(() => setErr("The atlas didn't load. Is the studio server running?")); api("/api/sampling/measures").then(setM).catch(() => {}); api("/api/sampling/renders").then(setR).catch(() => {}); }, []);
  useEffect(() => { document.body.classList.add("on-sampling"); return () => document.body.classList.remove("on-sampling", "sl-deep"); }, []);
  useEffect(() => { document.body.classList.toggle("sl-deep", !!id || view !== "methods"); }, [id, view]);
  /* Back from a method lands where the reader was in the list. */
  if (id && !idRef.current) saved.current = place0.current; idRef.current = id;
  useEffect(() => { const on = () => { if (!idRef.current && view === "methods") place0.current = scrollY; }; addEventListener("scroll", on, { passive: true }); return () => removeEventListener("scroll", on); }, [view]);
  const wasId = useRef(null);
  useEffect(() => { if (id) scrollTo(0, 0); else if (wasId.current && view === "methods") requestAnimationFrame(() => requestAnimationFrame(() => scrollTo(0, saved.current))); else scrollTo(0, 0); wasId.current = id; }, [id, view]);
  const rows = useMemo(() => data ? filterEntries(data.entries, f) : [], [data, f]);
  /* "/" jumps to search from anywhere on the page, unless someone is typing. */
  useEffect(() => { const k = (ev) => { const t = ev.target; if (ev.key !== "/" || ev.ctrlKey || ev.metaKey || ev.altKey || (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT" || t.isContentEditable))) return; ev.preventDefault(); if (id || view !== "methods") location.hash = "sampling"; setTimeout(() => { const i = document.getElementById("sl-q"); if (i) { i.focus(); i.select(); } }, 60); }; addEventListener("keydown", k); return () => removeEventListener("keydown", k); }, [id, view]);
  if (err) return html`<div class="sl"><p class="slerr" role="alert">${err}</p></div>`;
  if (!data) return html`<div class="sl"><div class="slloading"><b>Loading the atlas</b></div></div>`;
  const at = id ? "" : view;
  return html`<div class="sl">
    <nav class="slrack" aria-label="Sampling Lab"><ol>${VIEWS(data, measures, renders).map(([k, l, sub, h], i) => html`<li key=${k}><a class=${at === k ? "on" : ""} aria-current=${at === k ? "page" : null} href=${"#sampling" + h}><i>${i + 1}</i><span><b>${l}</b><small>${sub}</small></span></a></li>`)}</ol></nav>
    ${id ? html`<${Method} key=${id} id=${id} measures=${measures} renders=${renders} data=${data} rows=${rows}/>` : html`
      ${view === "methods" && html`<${AtlasView} data=${data} measures=${measures} renders=${renders} f=${f} set=${setF} rows=${rows}/>`}${view === "curves" && html`<${Curves} measures=${measures}/>`}${view === "bench" && html`<${Bench} measures=${measures}/>`}${view === "renders" && html`<${Renders} renders=${renders} rest=${rest}/>`}${view === "finds" && html`<${Finds} data=${data} renders=${renders} measures=${measures}/>`}${view === "credits" && html`<${Credits} data=${data}/>`}`}
  </div>`;
}
