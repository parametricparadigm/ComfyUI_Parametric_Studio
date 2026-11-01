/* ComfyUniversity: tracks from a first wire to reading the sampler's source. Every count on this page is worked out from the catalogue. Progress stays in this browser. */
import { useEffect, useMemo, useRef, useState } from "preact/hooks";
import { html, api } from "./common.js";
import { loadProgress, saveProgress, markLesson, lessonParts, trackProgress, nextLesson, neighbours, parseRoute, filterCourses, parseLesson, readingMinutes } from "./university_logic.js";
import { Quiz, LabRunner, GraphView, Wipe, Blocks, GraphTag } from "./university_parts.js";
import { PLAYS } from "./university_plays.js";

function useProgress() { const [p, setP] = useState(() => loadProgress()); const update = (code, patch) => setP((cur) => { const n = markLesson(cur, code, patch); saveProgress(n); return n; }); const reset = () => { setP({}); saveProgress({}); }; return [p, update, reset]; }
const go = (h) => { location.hash = h; };
const LEVEL = { "100": "First steps", "200": "Working knowledge", "300": "Under the hood", "400": "Expert" };
const levelWord = (l) => `${l} · ${LEVEL[l] || ""}`;

/* ---------- home ---------- */
function Stat({ n, label }) { return html`<li><b>${n}</b><span>${label}</span></li>`; }
function Home({ cat, p, reset }) {
  const byCode = useMemo(() => Object.fromEntries(cat.courses.map((c) => [c.code, c])), [cat]); const next = nextLesson(cat.tracks, byCode, p); const started = Object.keys(p).length > 0; const done = cat.courses.filter((c) => lessonParts(c, p[c.code]).done).length; const nextC = next && byCode[next.code];
  const hero = cat.art || [];
  return html`<div class="cu-view">
    <section class="cu-hero cu-film" aria-labelledby="cu-hero-h">
      <div class="cu-hero-art" aria-hidden="true">${hero.map((a) => html`<img src=${a} alt="" loading="lazy"/>`)}</div>
      <div class="cu-hero-body">
        <p class="cu-kick">Learn ComfyUI by doing it</p>
        <h2 id="cu-hero-h" class="cu-hero-h">From your first wire to reading the sampler's source.</h2>
        <p class="cu-hero-sub">Real graphs you can open. Labs that run in this browser, on your CPU, with no model and no GPU. Claims we checked against ComfyUI's own code, and a label on anything we could not.</p>
        <div class="cu-cta">${nextC ? html`<a class="cu-btn primary" href=${"#university/" + nextC.code}>${started ? "Continue" : "Start here"}: ${nextC.title}</a>` : html`<span class="cu-btn primary">You finished every lesson</span>`}<a class="cu-btn" href="#university/all">Every lesson</a></div>
        <ul class="cu-stats" aria-label="What is in the university">
          <${Stat} n=${cat.counts.lessons} label="lessons"/><${Stat} n=${cat.counts.second_read} label="read by a second reader"/><${Stat} n=${cat.tracks.length} label="tracks"/><${Stat} n=${cat.counts.plays} label="labs in this browser"/><${Stat} n=${cat.counts.graphs} label="graphs you can open"/><${Stat} n=${cat.counts.graphs_ran} label="graphs we ran on a CPU"/>
        </ul>
        ${started && html`<p class="cu-prog-line"><b>${done}</b> of ${cat.courses.length} lessons finished on this device. <button class="cu-linkbtn" onClick=${() => { if (confirm("Forget your progress on this device?")) reset(); }}>Reset</button></p>`}
      </div>
    </section>
    <section aria-labelledby="cu-tr-h"><div class="cu-band"><h2 id="cu-tr-h">The tracks</h2><p>Take them in order, or jump to the one you need. Each lesson says what it expects you to know.</p></div>
      <ol class="cu-tracks">${cat.tracks.map((t, i) => { const pr = trackProgress(t.codes, byCode, p); return html`<li key=${t.slug}><a class="cu-track" href=${"#university/track/" + t.slug}>
        ${t.art && html`<img class="cu-track-art" src=${t.art} alt="" loading="lazy"/>`}
        <span class="cu-track-n">${String(i + 1).padStart(2, "0")}</span><span class="cu-track-t">${t.title}</span><span class="cu-track-b">${t.blurb}</span>
        <span class="cu-track-f"><span>${t.codes.length} lessons</span>${pr.done > 0 && html`<span>${pr.done} done</span>`}</span><span class="cu-bar" aria-hidden="true"><i style=${{ width: pr.pct + "%" }}></i></span></a></li>`; })}</ol></section>
    <${HowWeKnow} cat=${cat}/>
  </div>`;
}
function HowWeKnow({ cat }) {
  const c = cat.counts;
  return html`<section class="cu-know" aria-labelledby="cu-know-h"><h2 id="cu-know-h">How we know this is right</h2>
    <ul>
      <li><b>${c.second_read}</b><p>lessons read by a second reader, who tried to prove them wrong against ComfyUI's source and real runs. That found and fixed ${c.errors_fixed} errors. It samples the riskiest claims in each lesson, so it is not a proof.</p></li>
      <li><b>${c.second_read_pending}</b><p>lessons checked by their author, with the second read pending. Expect a few mistakes in these: second reads have been finding them.</p></li>
      ${c.draft > 0 && html`<li><b>${c.draft}</b><p>lessons still labelled Draft. A local model wrote them. Their labs ran, but nobody has checked their prose line by line.</p></li>`}
      <li><b>${c.code_refs}</b><p>named ComfyUI functions and classes, each looked up in the source by a test.</p></li>
      <li><b>${c.graphs}</b><p>graphs, every one passed through ComfyUI's own <code>validate_prompt</code>. The ${c.graphs_ran} that need no model were really executed.</p></li>
    </ul></section>`;
}

/* ---------- every lesson ---------- */
function AllLessons({ cat, p }) {
  const [q, setQ] = useState(""); const [lv, setLv] = useState("all"); const rows = filterCourses(cat.courses, q, lv); const lvls = Object.keys(cat.levels);
  return html`<div class="cu-view"><nav class="cu-crumb" aria-label="breadcrumb"><a href="#university">All tracks</a></nav><div class="cu-band big"><h2>Every lesson</h2></div>
    <div class="cu-filter"><label class="cu-search"><span class="cu-vh">Search lessons</span><input type="search" placeholder="Search: seed, ControlNet, OOM" value=${q} onInput=${(e) => setQ(e.target.value)}/></label>
      <div class="cu-seg" role="group" aria-label="Level"><button aria-pressed=${lv === "all"} onClick=${() => setLv("all")}>All</button>${lvls.map((k) => html`<button aria-pressed=${lv === k} onClick=${() => setLv(k)}>${k}</button>`)}</div><span class="cu-n" role="status">${rows.length} lessons</span></div>
    <${LessonList} codes=${rows.map((c) => c.code)} byCode=${Object.fromEntries(cat.courses.map((c) => [c.code, c]))} p=${p}/></div>`;
}
const ReadMark = ({ c, short }) => c.second_read ? html`<span class="cu-pill ink">Second reader checked${!short && c.second_read.errors_fixed ? `, ${c.second_read.errors_fixed} ${c.second_read.errors_fixed > 1 ? "errors" : "error"} fixed` : ""}</span>` : html`<span class="cu-pill plain">${short ? "Second read pending" : "Author-checked, second read pending"}</span>`;
function LessonList({ codes, byCode, p, numbered }) {
  return html`<ol class=${"cu-list" + (numbered ? " num" : "")}>${codes.map((code, i) => { const c = byCode[code]; if (!c) return null; const st = lessonParts(c, p[code]); const some = st.parts.some(([, v]) => v); return html`<li key=${code}><a class=${"cu-row" + (st.done ? " done" : "")} href=${"#university/" + code}>
    ${numbered && html`<span class="cu-row-n">${i + 1}</span>`}<span class="cu-row-main"><b>${c.title}</b><span>${c.hook}</span></span>
    <span class="cu-row-meta"><span class="cu-pill">${c.level}</span>${c.status === "draft" ? html`<span class="cu-pill warn">Draft</span>` : html`<${ReadMark} c=${c} short=${1}/>`}${(c.plays || []).length > 0 && html`<span class="cu-pill ink">Browser lab</span>`}<span class="cu-pill plain">${c.minutes} min</span>${st.done ? html`<span class="cu-tick" aria-label="finished">✓</span>` : some ? html`<span class="cu-pill plain">Started</span>` : null}</span></a></li>`; })}</ol>`;
}
function TrackView({ cat, slug, p }) {
  const t = cat.tracks.find((x) => x.slug === slug); const byCode = Object.fromEntries(cat.courses.map((c) => [c.code, c]));
  if (!t) return html`<div class="cu-view"><p>No such track. <a class="cu-a" href="#university">All tracks</a></p></div>`;
  const pr = trackProgress(t.codes, byCode, p); const i = cat.tracks.indexOf(t), nx = cat.tracks[i + 1]; const mins = t.codes.reduce((a, c) => a + ((byCode[c] || {}).minutes || 0), 0);
  return html`<div class="cu-view"><nav class="cu-crumb" aria-label="breadcrumb"><a href="#university">All tracks</a></nav>
    <header class="cu-track-head cu-film">${t.art && html`<img src=${t.art} alt="" class="cu-track-head-art"/>`}<div><p class="cu-kick">Track ${String(i + 1).padStart(2, "0")}</p><h2>${t.title}</h2><p class="cu-track-lead">${t.blurb}</p><p class="cu-track-sum">${t.codes.length} lessons, about ${mins} minutes of reading. ${pr.done} finished on this device.</p><span class="cu-bar big" aria-hidden="true"><i style=${{ width: pr.pct + "%" }}></i></span></div></header>
    <${LessonList} numbered=${1} codes=${t.codes} byCode=${byCode} p=${p}/>
    ${nx && html`<a class="cu-next" href=${"#university/track/" + nx.slug}><span>Next track</span><b>${nx.title}</b></a>`}</div>`;
}

/* ---------- a lesson ---------- */
const Section = ({ id, title, children, kick }) => html`<section class="cu-sec" id=${"cu-" + id} aria-labelledby=${"cuh-" + id}>${kick && html`<p class="cu-kick">${kick}</p>`}<h2 id=${"cuh-" + id} tabindex="-1">${title}</h2>${children}</section>`;
function Lesson({ cat, code, p, update }) {
  const [c, setC] = useState(null); const [err, setErr] = useState("");
  useEffect(() => { let on = true; setC(null); setErr(""); api("/api/university/" + code).then((d) => { if (on) { setC(d); window.scrollTo(0, 0); } }).catch((e) => { if (on) setErr(e.message); }); return () => { on = false; }; }, [code]);
  const doc = useMemo(() => c ? parseLesson(c.lesson) : null, [c]);
  const end = useRef(null);
  useEffect(() => { const el = end.current; if (!el || !c || (p[code] || {}).read) return; if (!("IntersectionObserver" in window)) return; const io = new IntersectionObserver((es) => { if (es.some((e) => e.isIntersecting)) { update(code, { read: true }); io.disconnect(); } }); io.observe(el); return () => io.disconnect(); }, [c, code]);
  if (err) return html`<div class="cu-view"><nav class="cu-crumb"><a href="#university">All tracks</a></nav><p class="cu-err">${err}</p></div>`;
  if (!c) return html`<div class="cu-loading" role="status"><b>Opening the lesson</b></div>`;
  const track = cat.tracks.find((t) => t.slug === c.track); const nb = neighbours(code, track); const byCode = Object.fromEntries(cat.courses.map((x) => [x.code, x])); const st = lessonParts(c, p[code]); const teacher = (cat.characters[c.char] || {}).name;
  const passPlay = (name) => update(code, { plays: { [name]: true } }); const entry = p[code] || {};
  const used = new Set(doc.sections.flatMap((s) => s.blocks.filter((b) => b.t === "graph").map((b) => b.id))); const extra = (c.graphs || []).filter((g) => !used.has(g.id));
  const hasWrong = doc.sections.some((s) => s.id === "what-goes-wrong");
  const rack = [...doc.sections.filter((s) => s.id !== "sources").map((s) => [s.id, s.title]), ...(extra.length ? [["graph", "The graph"]] : []), ["run", "Run the lab"], ["check", "Check yourself"]];
  const before = (s) => s.id === "sources";
  const tail = html`${extra.length > 0 && html`<${Section} id="graph" title=${extra.length > 1 ? "The graphs" : "The graph"} kick="Open it">${extra.map((g) => html`<${GraphView} key=${g.id} g=${g}/>`)}</${Section}>`}
    <${Section} id="run" title="Run the lab" kick="On your CPU"><${LabRunner} c=${c}/></${Section}>
    <${Section} id="check" title="Check yourself" kick="Did it land?"><${Quiz} items=${c.quiz} passed=${entry.quiz} onPass=${() => update(code, { quiz: true })}/></${Section}>`;
  const sources = doc.sections.find(before); const main = doc.sections.filter((s) => !before(s));
  return html`<article class="cu-view cu-lesson">
    <nav class="cu-crumb" aria-label="breadcrumb"><a href="#university">All tracks</a>${track && html`<span aria-hidden="true">/</span><a href=${"#university/track/" + track.slug}>${track.title}</a>`}${nb.at > 0 && html`<span class="cu-crumb-at">${nb.at} of ${nb.of}</span>`}</nav>
    <header class="cu-lesson-head"><p class="cu-kick">${c.code} · ${levelWord(c.level)}${teacher ? ` · ${teacher}` : ""}</p><h2 class=${"cu-lesson-title" + (doc.title.length > 34 ? " long" : "")}>${doc.title}</h2>${doc.objective && html`<p class="cu-objective">${doc.objective.replace(/\s*Taught by .*$/, "")}</p>`}
      <div class="cu-meta">${c.status !== "draft" && html`<${ReadMark} c=${c}/>`}<span class="cu-pill plain">${c.minutes} min read</span>${(c.plays || []).length > 0 && html`<span class="cu-pill ink">${c.plays.length} browser ${c.plays.length > 1 ? "labs" : "lab"}</span>`}${(c.graphs || []).length > 0 && html`<span class="cu-pill plain">${c.graphs.length} ${c.graphs.length > 1 ? "graphs" : "graph"}</span>`}<span class="cu-pill plain">CPU lab</span>${(c.prereq || []).length > 0 && html`<span class="cu-pre">Needs ${c.prereq.map((x, i) => html`${i ? ", " : ""}<a class="cu-a" href=${"#university/" + x}>${(byCode[x] || {}).title || x}</a>`)}</span>`}</div>
      ${doc.draft && html`<p class="cu-draft" role="note"><b>Draft.</b> ${doc.draft.replace(/^Draft\.\s*/, "")}</p>`}</header>
    ${doc.intro.length > 0 && html`<div class="cu-prose"><${Blocks} blocks=${doc.intro} c=${c} passPlay=${passPlay} entry=${entry}/></div>`}
    <nav class="cu-rack" aria-label="In this lesson"><ol>${rack.map(([id, t]) => html`<li key=${id}><a href=${"#university/" + code} onClick=${(e) => { e.preventDefault(); const el = document.getElementById("cu-" + id); if (el) { el.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" }); const h = document.getElementById("cuh-" + id); if (h) h.focus({ preventScroll: true }); } }}>${t}</a></li>`)}</ol></nav>
    ${main.map((s) => html`<${Section} key=${s.id} id=${s.id} title=${s.title}><div class="cu-prose"><${Blocks} blocks=${s.blocks} c=${c} passPlay=${passPlay} entry=${entry}/></div></${Section}>`)}
    ${tail}
    <div ref=${end} aria-hidden="true"></div>
    ${(c.verified || c.unchecked) && html`<${Section} id="know" title="How we know" kick="What was checked"><div class="cu-checks">${(c.verified || []).map((v) => html`<div class="cu-check ok"><span class="cu-pill ink">${v.how}</span><p>${v.claim}${v.ref ? html` <code>${v.ref}</code>` : ""}</p></div>`)}${(c.unchecked || []).map((v) => html`<div class="cu-check no"><span class="cu-pill warn">Not checked</span><p>${v}</p></div>`)}</div></${Section}>`}
    ${sources && html`<${Section} id="sources" title="Sources"><div class="cu-prose small"><${Blocks} blocks=${sources.blocks} c=${c} passPlay=${passPlay} entry=${entry}/></div></${Section}>`}
    <footer class="cu-lesson-foot"><div class="cu-done" role="status">${st.parts.map(([k, v]) => html`<span class=${"cu-pill " + (v ? "ink" : "plain")}>${v ? "✓ " : ""}${k === "read" ? "Read" : k === "quiz" ? "Quiz" : "Browser lab"}</span>`)}</div>
      ${nb.next ? html`<a class="cu-next" href=${"#university/" + nb.next}><span>Next in ${track.title}</span><b>${(byCode[nb.next] || {}).title}</b></a>` : track ? html`<a class="cu-next" href="#university"><span>End of ${track.title}</span><b>All tracks</b></a>` : null}</footer>
  </article>`;
}

/* ---------- page ---------- */
export function University({ route }) {
  const [cat, setCat] = useState(null); const [err, setErr] = useState(""); const [p, update, reset] = useProgress(); const r = parseRoute(route);
  useEffect(() => { api("/api/university").then(setCat).catch((e) => setErr(e.message)); }, []);
  useEffect(() => { document.body.classList.add("on-learn"); return () => document.body.classList.remove("on-learn", "cu-deep"); }, []);
  useEffect(() => { document.body.classList.toggle("cu-deep", r.view !== "home"); if (r.view !== "lesson") window.scrollTo(0, 0); }, [r.view, r.slug]);
  useEffect(() => { const f = (e) => { if (e.detail) location.hash = "university/" + e.detail; }; addEventListener("open-course", f); return () => removeEventListener("open-course", f); }, []);
  if (err) return html`<div class="cu"><p class="cu-err">${err}</p></div>`;
  if (!cat) return html`<div class="cu"><div class="cu-loading" role="status"><b>Opening the university</b></div></div>`;
  return html`<div class="cu">${r.view === "home" && html`<${Home} cat=${cat} p=${p} reset=${reset}/>`}${r.view === "all" && html`<${AllLessons} cat=${cat} p=${p}/>`}${r.view === "track" && html`<${TrackView} cat=${cat} slug=${r.slug} p=${p}/>`}${r.view === "lesson" && html`<${Lesson} key=${r.code} cat=${cat} code=${r.code} p=${p} update=${update}/>`}</div>`;
}
export { readingMinutes, PLAYS, GraphTag, Wipe, go };
