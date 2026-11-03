// The Music page: every music model in one place, on one original brief. The audio and every number are real and were recorded by scripts/build_music_page.py. Nobody has listened to any of it.
import { useEffect, useMemo, useRef, useState } from "preact/hooks";
import { html, api, post } from "./common.js";
import { copyText, saveFile, said, FxSkeleton } from "./fx.js";
import { searchStyles, cardTags } from "./music_styles_logic.js";
import { clock, STATE_WORD, STATE_NOTE, sortModels, counts, rendered, lyricWord, bars, featureAt, trackPath, BANDS, versus, FORMS, seconds as suggest, sungLines, sameLineTags, runBody, curlFor, COMMERCIAL } from "./music_logic.js";

const calm = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
let playing = null;      // one thing plays at a time, anywhere on the page

/* An audio element and its clock. */
function useTrack(src) {
  const ref = useRef(null); const [t, setT] = useState(0), [on, setOn] = useState(false), [dur, setDur] = useState(0);
  useEffect(() => {
    const a = new Audio(); a.preload = "none"; a.src = src || ""; ref.current = a; setT(0); setOn(false); setDur(0);
    const tick = () => setT(a.currentTime), meta = () => setDur(a.duration || 0), go = () => setOn(true), stop = () => setOn(false);
    a.addEventListener("timeupdate", tick); a.addEventListener("loadedmetadata", meta); a.addEventListener("play", go); a.addEventListener("pause", stop); a.addEventListener("ended", stop);
    return () => { a.pause(); if (playing === a) playing = null; a.removeEventListener("timeupdate", tick); a.removeEventListener("loadedmetadata", meta); a.removeEventListener("play", go); a.removeEventListener("pause", stop); a.removeEventListener("ended", stop); a.src = ""; };
  }, [src]);
  const toggle = () => { const a = ref.current; if (!a) return; if (a.paused) { if (playing && playing !== a) playing.pause(); playing = a; const p = a.play(); if (p && p.catch) p.catch(() => {}); } else a.pause(); };
  const seek = (s) => { const a = ref.current; if (a && isFinite(s)) { a.currentTime = Math.max(0, s); setT(a.currentTime); } };
  return { ref, t, on, dur, toggle, seek };
}

/* The waveform of a real render. A slider: click or drag it, or use the arrow keys. */
function Wave({ peaks, seconds, track, label, n = 200, tall }) {
  const shown = useMemo(() => bars(peaks, n), [peaks, n]); const len = track.dur || seconds || 0; const pos = len ? Math.min(1, track.t / len) : 0; const box = useRef(null);
  const at = (e) => { const r = box.current.getBoundingClientRect(); const x = (e.clientX - r.left) / r.width; track.seek(Math.max(0, Math.min(1, x)) * len); };
  const key = (e) => { const d = { ArrowRight: 5, ArrowLeft: -5, PageUp: 15, PageDown: -15 }[e.key]; if (d) { e.preventDefault(); track.seek(track.t + d); } else if (e.key === "Home") { e.preventDefault(); track.seek(0); } else if (e.key === " " || e.key === "Enter") { e.preventDefault(); track.toggle(); } };
  return html`<div ref=${box} class=${"mu-wave" + (tall ? " tall" : "")} role="slider" tabindex="0" aria-label=${`Position in ${label}`} aria-valuemin="0" aria-valuemax=${Math.round(len)} aria-valuenow=${Math.round(track.t)} aria-valuetext=${`${clock(track.t)} of ${clock(len)}`} onPointerDown=${(e) => { box.current.setPointerCapture && box.current.setPointerCapture(e.pointerId); at(e); }} onPointerMove=${(e) => { if (e.buttons) at(e); }} onKeyDown=${key}>
    <svg viewBox=${`0 0 ${n} 100`} preserveAspectRatio="none" aria-hidden="true">${shown.map((v, i) => { const h = Math.max(1.5, v * 100); return html`<rect key=${i} x=${i + 0.12} y=${50 - h / 2} width="0.76" height=${h} class=${i / n <= pos ? "on" : ""}/>`; })}</svg>
  </div>`;
}

/* A play button, a waveform and the time. */
function Player({ audio, peaks, seconds, label, tall, big }) {
  const track = useTrack(audio);
  return html`<div class=${"mu-player" + (big ? " big" : "")}><button class="mu-play" onClick=${track.toggle} aria-pressed=${track.on} aria-label=${(track.on ? "Pause " : "Play ") + label}>${track.on ? html`<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 4h4v16H6zM14 4h4v16h-4z"/></svg>` : html`<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 4l13 8-13 8z"/></svg>`}</button><${Wave} peaks=${peaks} seconds=${seconds} track=${track} label=${label} tall=${tall}/><span class="mu-time">${clock(track.t)} / ${clock(track.dur || seconds)}</span></div>`;
}

const Ext = ({ href, children }) => html`<a href=${href} target="_blank" rel="noopener noreferrer">${children}</a>`;
const Tag = ({ state }) => html`<span class=${"mu-state " + state}>${STATE_WORD[state] || state}</span>`;
const longest = (t) => Math.max(...String(t).split(/\s+/).map((w) => w.length));
const Head = ({ n, id, title, sub }) => html`<header class="mu-head"><span class="mu-num" aria-hidden="true">${n}</span><h2 id=${id} tabindex="-1" style=${{ "--tn": longest(title) }}>${title}</h2>${sub && html`<p>${sub}</p>`}</header>`;
const Bands = ({ b }) => b ? html`<div class="mu-bands" role="img" aria-label=${BANDS.map(([k, l]) => `${l} ${b[k]} percent`).join(", ")}>${BANDS.map(([k, l]) => html`<span class=${"b-" + k} style=${{ width: `${b[k]}%` }} title=${`${l}: ${b[k]}%`}></span>`)}</div>` : null;

/* The lines Whisper heard, one chip per unique lyric line. */
function Lines({ lyrics }) {
  if (!lyrics || !lyrics.per) return null;
  return html`<ul class="mu-lines">${lyrics.per.map((l) => html`<li class=${l.score >= 0.6 ? "heard" : "lost"}><span>${l.line}</span><b>${Math.round(l.score * 100)}%</b></li>`)}</ul>`;
}

const facts = (r) => [
  ["Length", r.seconds != null ? `${r.seconds} s` : "-"], ["Loudness", r.lufs != null ? `${r.lufs} LUFS` : "-"], ["True peak", r.true_peak_db != null ? `${r.true_peak_db} dB` : "-"], ["Brightness", r.centroid_hz != null ? `${r.centroid_hz} Hz` : "-"], ["Tempo found", r.bpm != null ? `${r.bpm} BPM` : "-"], ["Lyrics heard", r.lyrics ? lyricWord(r.lyrics) : "No lyrics"], ["Render", r.secs != null ? `${r.secs} s` : "-"], ["VRAM peak", r.peak_gib != null ? `${r.peak_gib} GiB` : "-"],
];

/* ---- the opening ---- */
function Hero({ models, brief, go }) {
  const list = rendered(models); const [pick, setPick] = useState(null); const cur = list.find((m) => m.id === pick) || list[0]; const n = counts(models);
  return html`<section class="mu-hero film" aria-labelledby="mu-title">
    <div class="mu-herotext"><p class="mu-eyebrow">The same original song. ${list.length || "No"} ${list.length === 1 ? "render" : "renders"} so far.</p><h2 id="mu-title">${brief.title || "Paper Boats"}</h2></div>
    ${cur ? html`<div class="mu-herowave"><p class="mu-nowplaying"><b>${cur.label}</b><span>${cur.job}</span></p><${Player} big audio=${cur.render.audio} peaks=${cur.render.peaks} seconds=${cur.render.seconds} label=${cur.label} tall/></div>
      <div class="mu-pills" role="group" aria-label="Pick a model to hear">${list.map((m) => html`<button key=${m.id} aria-pressed=${m.id === cur.id} onClick=${() => setPick(m.id)}>${m.label}</button>`)}</div>` : html`<p class="mu-none">Nothing has been rendered for this page on this install.</p>`}
    <dl class="mu-herostats"><div><dd>${models.length}</dd><dt>music models known here</dt></div><div><dd>${n.proven}</dd><dt>rendered on this brief</dt></div><div><dd>${n.unproven}</dd><dt>on disk, not rendered</dt></div><div><dd>${n.missing + n.unknown}</dd><dt>weights not here</dt></div></dl>
    <p class="mu-honest"><b>Nobody has listened to these.</b> A program measured them, and local Whisper transcribed them to catch nonsense. Trust your ears over this page.</p>
  </section>`;
}

/* ---- side by side ---- */
function Compare({ models }) {
  const list = rendered(models); const [a, setA] = useState(list[0] && list[0].id), [b, setB] = useState((list[1] || list[0] || {}).id), [side, setSide] = useState("a"); const A = list.find((m) => m.id === a), B = list.find((m) => m.id === b);
  const ta = useTrack(A && A.render.audio), tb = useTrack(B && B.render.audio); const live = side === "a" ? ta : tb, other = side === "a" ? tb : ta;
  const flip = (next) => { if (next === side) return; const from = side === "a" ? ta : tb, to = next === "a" ? ta : tb, was = from.on; const at = from.t; from.ref.current && from.ref.current.pause(); to.seek(at); setSide(next); if (was) to.toggle(); };
  const key = (e) => { if (e.key === "a" || e.key === "A") flip("a"); if (e.key === "b" || e.key === "B") flip("b"); };
  if (list.length < 2) return html`<p class="mu-none">Two rendered models are needed for this.</p>`;
  const R = [A.render, B.render];
  const rows = [["Lyrics heard", (r) => r.lyrics ? `${r.lyrics.pct}%` : "n/a"], ["Loudness", (r) => `${r.lufs} LUFS`], ["True peak", (r) => `${r.true_peak_db} dB`], ["Brightness", (r) => `${r.centroid_hz} Hz`], ["Tempo found", (r) => `${r.bpm} BPM`], ["Length", (r) => `${r.seconds} s`], ["Render time", (r) => `${r.secs} s`], ["VRAM peak", (r) => `${r.peak_gib} GiB`]];
  const col = (m, s, set) => html`<div class=${"mu-side" + (side === s ? " live" : "")}><label class="mu-picklab">${s.toUpperCase()}<select class="fx-in" value=${m.id} onChange=${(e) => { live.ref.current && live.ref.current.pause(); set(e.target.value); }} aria-label=${`Model ${s.toUpperCase()}`}>${list.map((x) => html`<option key=${x.id} value=${x.id}>${x.label}</option>`)}</select></label><${Wave} peaks=${m.render.peaks} seconds=${m.render.seconds} track=${s === "a" ? ta : tb} label=${`${s.toUpperCase()}: ${m.label}`} n=${160}/><${Bands} b=${m.render.bands}/></div>`;
  return html`<div class="mu-ab" onKeyDown=${key}>
    <div class="mu-abbar"><button class="mu-go" onClick=${live.toggle} aria-pressed=${live.on}>${live.on ? "Pause" : "Play"}</button><div class="mu-abflip" role="group" aria-label="Which one you hear"><button aria-pressed=${side === "a"} onClick=${() => flip("a")}>Hear A</button><button aria-pressed=${side === "b"} onClick=${() => flip("b")}>Hear B</button></div><span class="mu-time">${clock(live.t)}</span><span class="mu-hint">Switching keeps your place in the song. Keys: A, B.</span></div>
    <div class="mu-sides">${col(A, "a", setA)}${col(B, "b", setB)}</div>
    <div class="mu-tablewrap" tabindex="0" role="region" aria-label="Measured side by side"><table class="mu-table"><thead><tr><th scope="col">Measured</th><th scope="col">${A.label}</th><th scope="col">${B.label}</th></tr></thead><tbody>${rows.map(([l, f]) => html`<tr key=${l}><th scope="row">${l}</th><td>${f(R[0])}</td><td>${f(R[1])}</td></tr>`)}</tbody></table></div>
    <div class="mu-legend" aria-hidden="true">${BANDS.map(([k, l, r]) => html`<span><i class=${"b-" + k}></i>${l} <small>${r}</small></span>`)}</div>
  </div>`;
}

/* ---- every model ---- */
function Wall({ models }) {
  return html`<ol class="mu-wall">${sortModels(models).map((m, i) => html`<li key=${m.id}><a class=${"mu-card " + m.state} href=${"#music/" + m.id}><span class="mu-cardn">${String(i + 1).padStart(2, "0")}</span><h3>${m.label}</h3><p>${m.job}</p>
    ${m.render && m.render.peaks ? html`<svg class="mu-mini" viewBox="0 0 80 24" preserveAspectRatio="none" aria-hidden="true">${bars(m.render.peaks, 80).map((v, j) => html`<rect x=${j + 0.1} y=${12 - Math.max(0.5, v * 12)} width="0.8" height=${Math.max(1, v * 24)}/>`)}</svg>` : html`<span class="mu-mini none" aria-hidden="true"></span>`}
    <span class="mu-cardfoot"><${Tag} state=${m.state}/><span class="mu-lic">${m.licence.short}</span></span></a></li>`)}</ol>`;
}

function GraphBox({ name }) {
  const [g, setG] = useState(null), [err, setErr] = useState("");
  useEffect(() => { let live = true; setG(null); setErr(""); if (name) api("/api/workflow-graphs/" + encodeURIComponent(name)).then((d) => { if (live) setG(d); }).catch((e) => { if (live) setErr(said(e)); }); return () => { live = false; }; }, [name]);
  if (!name) return html`<p class="small">No ComfyUI graph: this one runs as its own program or through its own pack.</p>`;
  if (err) return html`<p class="fx-err" role="alert">${err}</p>`;
  if (!g) return html`<${FxSkeleton} label="Reading the graph." rows=${2}/>`;
  const nodes = Object.entries(g.graph).map(([id, n]) => [id, n.class_type]);
  return html`<div class="mu-graph"><ol class="mu-nodes">${nodes.map(([id, c]) => html`<li key=${id}><code>${c}</code></li>`)}</ol><p class="small">${nodes.length} nodes. It fills in: ${(g.fills || []).join(", ") || "nothing"}.</p><div class="fx-row"><button class="btn small" onClick=${() => saveFile(name, JSON.stringify(g.graph, null, 1))}>Save the graph</button><a class="btn small" href="#api">See it on the API page</a></div></div>`;
}

function Sheet({ m, brief, goBack }) {
  const r = m.render; const lic = m.licence || {};
  useEffect(() => { const h = document.getElementById("mu-sheet"); if (h) h.focus({ preventScroll: true }); if (window.scrollTo) { const top = document.querySelector("main"); if (top) top.scrollTop = 0; } }, [m.id]);
  return html`<article class="mu-sheet"><a class="mu-back" href="#music" onClick=${goBack}>All music models</a>
    <header class="film mu-sheethead"><span class="mu-eyebrow">${m.maker}</span><h2 id="mu-sheet" tabindex="-1" style=${{ "--tn": longest(m.label) }}>${m.label}</h2><p class="mu-sheetjob">${m.job}</p>
      ${r && r.audio ? html`<${Player} big tall audio=${r.audio} peaks=${r.peaks} seconds=${r.seconds} label=${m.label}/>` : html`<p class="mu-noaudio">No audio from this model: nothing has been rendered with it on this page.</p>`}
      <p class="mu-stateline"><${Tag} state=${m.state}/><span>${STATE_NOTE[m.state]}</span></p></header>
    ${m.why_not && m.state !== "proven" && html`<div class="fx-note warn"><b>Why there's no render:</b> <span>${m.why_not}</span>${m.missing && m.missing.length > 0 && html`<span class="small">Not found on this install: ${m.missing.join(", ")}</span>`}</div>`}
    <div class="mu-sheetgrid"><section><h3>What it does</h3><p>${m.does}</p>${m.can && m.can.length > 0 && html`<ul class="mu-can">${m.can.map((c) => html`<li key=${c}>${c}</li>`)}</ul>`}<p class="mu-links">${(m.links || []).map(([t, u]) => html`<${Ext} href=${u}>${t}</${Ext}>`)}</p></section>
      <section class=${"mu-licence " + (lic.commercial || "")}><h3>Licence</h3><p class="mu-licname">${lic.name}</p><p><b>${COMMERCIAL[lic.commercial] || ""}.</b> ${lic.use}</p><p class="mu-links"><${Ext} href=${lic.url}>Read it on its source page</${Ext}></p></section></div>
    ${r && html`<section class="mu-sect"><h3>What the machine measured</h3><dl class="mu-facts">${facts(r).map(([k, v]) => html`<div key=${k}><dd>${v}</dd><dt>${k}</dt></div>`)}</dl><${Bands} b=${r.bands}/>
      <h3>What Whisper heard</h3><${Lines} lyrics=${r.lyrics}/>${r.heard && html`<blockquote class="mu-heard">${r.heard}</blockquote>`}${!r.lyrics && html`<p class="small">Whisper wasn't run on this one, because the brief had no lyrics for it to sing.</p>`}<p class="small">Seed ${r.seed}. Rendered ${r.date}.</p></section>`}
    <div class="mu-sheetgrid"><section><h3>Settings it ran with</h3>${Object.keys(m.settings || {}).length ? html`<dl class="mu-set">${Object.entries(m.settings).map(([k, v]) => html`<div key=${k}><dt>${k}</dt><dd>${v}</dd></div>`)}</dl>` : html`<p class="small">Not run here, so the page lists no settings as fact.</p>`}</section><section><h3>The graph</h3><${GraphBox} name=${m.graph}/>${(m.goal || m.family) && html`<div class="fx-row">${m.goal && html`<a class="btn small" href="#create">Open Create</a>`}${m.family && html`<a class="btn small" href=${"#families/" + m.family}>Open its family page</a>`}</div>`}</section></div>
    ${m.graph && html`<${Maker} models=${[m]} brief=${brief} fixed/>`}
  </article>`;
}

/* ---- make one ---- */
function StylePick({ onPick }) {
  const [lib, setLib] = useState(null), [q, setQ] = useState(""), [err, setErr] = useState("");
  useEffect(() => { api("/api/music-styles").then(setLib).catch((e) => setErr(said(e))); }, []);
  const hits = lib ? searchStyles(lib.families, q).slice(0, 8) : [];
  const take = (id) => api("/api/music-styles/" + encodeURIComponent(id)).then((s) => { const c = s.cards[0]; onPick({ style: cardTags(s, c).join(", "), bpm: c.bpm, key: /^[A-G][#b]? (major|minor)$/.test(c.key || "") ? c.key : "", label: s.label, lyrics: s.lyrics_set ? s.lyrics_set.lyrics : "" }); setQ(""); }).catch((e) => setErr(said(e)));
  return html`<div class="fx-lab mu-stylepick"><label for="mu-styleq">Style library${lib ? `: ${lib.counts.styles} styles from Music 3's library` : ""}</label><input id="mu-styleq" class="fx-in" type="search" placeholder="Search: ballad, bossa nova, dubstep" value=${q} onInput=${(e) => setQ(e.target.value)}/>${err && html`<span class="fx-err" role="alert">${err}</span>`}${hits.length > 0 && html`<ul>${hits.map(({ style }) => html`<li key=${style.id}><button class="btn small" onClick=${() => take(style.id)}>${style.label}${style.lyrics ? " · with lyrics" : ""}</button></li>`)}</ul>`}</div>`;
}

function Kit({ f, setF }) {
  const [kit, setKit] = useState(null), [open, setOpen] = useState(false);
  useEffect(() => { api("/api/music/kit").then(setKit).catch(() => setKit(false)); }, []);
  if (!kit) return null;
  const groups = [["genre", "Genre"], ["voice", "Voice"]]; const sl = kit.sliders.find((x) => x.id === f.slider); const proof = (kit.proof || {}).renders || {};
  const done = (id) => proof[id] && proof[id].status === "success";
  return html`<fieldset class="mu-kit"><legend>Style kit</legend>
    <label class="fx-lab">Style nudge<select class="fx-in" value=${f.slider || "none"} onChange=${(e) => setF({ ...f, slider: e.target.value })}><option value="none">None</option>${groups.map(([g, label]) => html`<optgroup key=${g} label=${label}>${kit.sliders.filter((x) => x.group === g).map((x) => html`<option key=${x.id} value=${x.id}>${x.label}${done(x.id) ? "" : " (not rendered here yet)"}</option>`)}</optgroup>`)}</select></label>
    ${sl && html`<label class="fx-lab">Nudge strength: ${Number(f.strength ?? 1).toFixed(2)}<input type="range" min=${kit.strength.min} max=${kit.strength.max} step="0.05" value=${f.strength ?? 1} onInput=${(e) => setF({ ...f, strength: Number(e.target.value) })} aria-label="nudge strength"/></label>`}
    <label class="fx-lab mu-kitturbo"><input type="checkbox" checked=${!!f.turbo} onChange=${(e) => setF({ ...f, turbo: e.target.checked })}/> Turbo: 8 sampling steps instead of 30${done("turbo") ? "" : " (not rendered here yet)"}</label>
    <p class="small">${sl ? `${sl.label}: an ntc-ai slider LoRA on the text encoder (MIT). It nudges; write the style in the caption too.` : "No nudge: the plain Music 3 graph."} ${f.turbo ? "Turbo is guillaume127's DiT LoRA (Apache-2.0); only the sampling gets faster." : ""}</p>
    <button class="btn small" aria-expanded=${open} onClick=${() => setOpen(!open)}>${open ? "Hide" : "What the kit can and can't do"}</button>
    ${open && html`<ul class="small">${kit.honest.map((h) => html`<li key=${h}>${h}</li>`)}<li>Sources: <${Ext} href=${kit.sources.sliders.url}>ntc-ai sliders, ${kit.sources.sliders.licence}</${Ext}>; <${Ext} href=${kit.sources.turbo.url}>guillaume127 turbo, ${kit.sources.turbo.licence}</${Ext}>. ${kit.sources.base}</li>${kit.left_out.map((x) => html`<li key=${x.file}>Left out: ${x.file.split("/").pop()}, ${x.why}.</li>`)}</ul>`}
  </fieldset>`;
}

function Maker({ models, brief, fixed }) {
  const ready = models.filter((m) => m.graph && (m.state === "proven" || m.state === "unproven")); const [mid, setMid] = useState((ready[0] || {}).id);
  const [f, setF] = useState({ style: "", lyrics: "", seconds: 60, seed: 7701, bpm: 90, key: "C major", slider: "none", strength: 1, turbo: false }), [job, setJob] = useState(null), [err, setErr] = useState(""), [copied, setCopied] = useState(false);
  const m = ready.find((x) => x.id === mid) || ready[0]; const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const useBrief = () => setF({ ...f, style: m && !m.lyrics ? brief.instrumental : brief.style, lyrics: brief.lyrics, seconds: brief.seconds, bpm: brief.bpm, key: brief.key });
  useEffect(() => { if (!job || !job.id || ["done", "error"].includes(job.status)) return undefined; const t = setInterval(() => api("/api/jobs/" + job.id).then((d) => setJob({ ...d, id: job.id })).catch(() => {}), 2500); return () => clearInterval(t); }, [job && job.id, job && job.status]);
  if (!m) return null;
  const body = runBody(m, f); const tagged = sameLineTags(f.lyrics); const file = job && job.files && job.files.find((x) => x.kind === "audio" || /\.(flac|mp3|m4a|wav|opus)$/i.test(x.filename || ""));
  const go = async () => { setErr(""); setJob(null); try { const r = await post("/api/music/run", body); setJob({ id: r.job, status: "queued" }); } catch (e) { setErr(said(e)); } };
  return html`<div class="mu-make">
    ${fixed ? html`<h3>Render it yourself</h3>` : html`<label class="fx-lab">Model<select class="fx-in" value=${m.id} onChange=${(e) => setMid(e.target.value)}>${ready.map((x) => html`<option key=${x.id} value=${x.id}>${x.label}</option>`)}</select></label>`}
    <${StylePick} onPick=${(s) => setF({ ...f, style: s.style, bpm: s.bpm || f.bpm, key: s.key || f.key, lyrics: s.lyrics && !f.lyrics.trim() ? s.lyrics : f.lyrics })}/>
    <label class="fx-lab">${m.takes === "caption" ? "Style, or a full three-part caption" : "Style"}<textarea class="fx-in" rows="3" value=${f.style} onInput=${set("style")}></textarea></label>
    ${m.lyrics ? html`<div class="fx-lab"><label for=${"mu-ly-" + m.id}>Lyrics</label><div class="fx-row" role="group" aria-label="Song forms">${FORMS.map((x) => html`<button key=${x.id} class="btn small" onClick=${() => setF({ ...f, lyrics: x.text })}>${x.label}</button>`)}</div><textarea id=${"mu-ly-" + m.id} class="fx-in" rows="8" value=${f.lyrics} onInput=${set("lyrics")}></textarea><span class="small">${sungLines(f.lyrics)} sung lines. About ${suggest(f.lyrics)} s fits them.</span>${tagged.length > 0 && html`<span class="fx-warn">Put each section name on its own line: words after a tag on the same line aren't sung.</span>`}</div>` : html`<p class="small">This model takes no lyrics.</p>`}
    ${m.id === "music3" && html`<${Kit} f=${f} setF=${setF}/>`}
    <div class="mu-makerow"><label class="fx-lab">Seconds<input class="fx-in" type="number" min="8" max="300" value=${f.seconds} onInput=${set("seconds")}/></label><label class="fx-lab">BPM<input class="fx-in" type="number" min="30" max="300" value=${f.bpm} onInput=${set("bpm")}/></label><label class="fx-lab">Key<input class="fx-in" value=${f.key} onInput=${set("key")}/></label><label class="fx-lab">Seed<input class="fx-in" type="number" value=${f.seed} onInput=${set("seed")}/></label></div>
    <div class="fx-row"><button class="fx-go" disabled=${!f.style.trim() || (job && !["done", "error"].includes(job.status))} onClick=${go}>Render on this machine</button>${brief && html`<button class="btn" onClick=${useBrief}>Use this page's brief</button>`}<button class="btn" onClick=${async () => { setCopied(await copyText(curlFor(body, location.origin))); }}>${copied ? "Copied" : "Copy as curl"}</button></div>
    ${err && html`<p class="fx-err" role="alert">${err}</p>`}
    ${job && html`<p role="status" class="small">${job.status === "done" ? `Done in ${job.seconds} s.` : job.status === "error" ? job.error : `Status: ${job.status}${job.position ? `, number ${job.position} in the queue` : ""}.`}</p>`}
    ${file && html`<audio controls src=${file.url}></audio>`}
    <p class="small">Your song uses the model's licence: ${m.licence.name}.</p>
  </div>`;
}

/* ---- the showpiece: his features driving a picture ---- */
function Ring({ fx, track }) {
  const cv = useRef(null); const tRef = useRef(0); tRef.current = track.t;
  useEffect(() => {
    const c = cv.current; if (!c || !fx) return undefined; const g = c.getContext("2d"); let raf = 0;
    const draw = () => {
      const a = track.ref.current; const t = a ? a.currentTime : tRef.current; const W = c.width, H = c.height, r = Math.min(W, H) / 2; g.clearRect(0, 0, W, H); g.save(); g.translate(W / 2, H / 2);
      const e = featureAt(fx.rms, fx.fps, t), o = featureAt(fx.onset, fx.fps, t), b = featureAt(fx.centroid, fx.fps, t); const spokes = 150, span = 5;
      for (let i = 0; i < spokes; i++) {   // each spoke is an instant from the last five seconds of the song, so the ring is the music's recent past
        const when = t - (i / spokes) * span, v = featureAt(fx.rms, fx.fps, when), hit = featureAt(fx.onset, fx.fps, when), ang = (i / spokes) * Math.PI * 2 - Math.PI / 2 + t * 0.12, base = r * (0.42 + e * 0.1), len = r * (0.02 + v * 0.42 + hit * 0.1);
        g.strokeStyle = `rgba(${245 + b * 10},${197 + b * 58},${24 + b * 215},${0.28 + 0.72 * (1 - i / spokes)})`; g.lineWidth = Math.max(1.5, r * 0.012); g.beginPath(); g.moveTo(Math.cos(ang) * base, Math.sin(ang) * base); g.lineTo(Math.cos(ang) * (base + len), Math.sin(ang) * (base + len)); g.stroke();
      }
      g.fillStyle = `rgba(245,197,24,${0.06 + o * 0.3})`; g.beginPath(); g.arc(0, 0, r * (0.4 + e * 0.1), 0, Math.PI * 2); g.fill(); g.restore();
    };
    if (calm()) { draw(); return undefined; }
    const loop = () => { draw(); raf = requestAnimationFrame(loop); }; loop(); return () => cancelAnimationFrame(raf);
  }, [fx, track.ref.current, calm() ? Math.floor(track.t / 2) : 0]);      // with reduced motion it redraws once every two seconds, and doesn't animate
  return html`<canvas ref=${cv} class="mu-ring" width="720" height="720" role="img" aria-label="A ring drawn from the song's energy over the last five seconds"></canvas>`;
}

const METERS = [["rms", "Energy", "RMS energy"], ["onset", "Attacks", "Onset strength"], ["centroid", "Brightness", "Spectral centroid"]];
function Reactive({ models, visual }) {
  const list = rendered(models).filter((m) => m.render.features); const [id, setId] = useState((list[0] || {}).id); const m = list.find((x) => x.id === id) || list[0]; const [fx, setFx] = useState(null), track = useTrack(m && m.render.audio);
  useEffect(() => { let live = true; setFx(null); if (m) fetch(m.render.features).then((r) => r.json()).then((d) => { if (live) setFx(d); }).catch(() => {}); return () => { live = false; }; }, [m && m.id]);
  return html`<div class="mu-react">
    ${visual && visual.video && html`<figure class="mu-vid film"><video controls preload="none" playsinline poster=${visual.poster} src=${visual.video}></video><figcaption><b>Rendered by his nodes.</b> ${visual.caption}</figcaption></figure>`}
    ${m ? html`<div class="mu-live film"><${Ring} fx=${fx} track=${track}/><div class="mu-liveside"><p class="mu-eyebrow">Live, in your browser</p><p class="mu-livehead">His numbers. Our drawing.</p><p class="small mu-onfilm">His AudioFeatureExtractor measured these three tracks from the render. The page draws them in time with the audio. No frame here is a render.</p>
      <label class="fx-lab mu-onfilm">Song<select class="fx-in" value=${m.id} onChange=${(e) => setId(e.target.value)}>${list.map((x) => html`<option key=${x.id} value=${x.id}>${x.label}</option>`)}</select></label>
      <div class="mu-player"><button class="mu-play" onClick=${track.toggle} aria-pressed=${track.on} aria-label=${(track.on ? "Pause " : "Play ") + m.label}>${track.on ? html`<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 4h4v16H6zM14 4h4v16h-4z"/></svg>` : html`<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 4l13 8-13 8z"/></svg>`}</button><${Wave} peaks=${m.render.peaks} seconds=${m.render.seconds} track=${track} label=${m.label} n=${120}/><span class="mu-time">${clock(track.t)}</span></div>
      ${fx && html`<div class="mu-tracks">${METERS.map(([k, l, node]) => html`<div key=${k}><span>${l} <small>${node}</small></span><svg viewBox="0 0 300 40" preserveAspectRatio="none" aria-hidden="true"><path d=${trackPath(fx[k], 300, 40)}/><rect x=${(track.t / (m.render.seconds || 1)) * 300} y="0" width="1.5" height="40"/></svg></div>`)}</div>`}</div></div>` : html`<p class="mu-none">No feature tracks are recorded on this install.</p>`}
  </div>`;
}

/* ---- a whole song, filmed: Wren Halloway, made before the studio and labelled so ---- */
function Film({ f }) {
  if (!f || !f.video) return null;
  return html`<figure class="mu-film film"><video controls preload="none" playsinline poster=${f.poster} src=${f.video} aria-label=${f.title + ", music video"}></video><figcaption><p class="mu-eyebrow">${f.label}, ${f.made}</p><p class="mu-filmtitle">${f.title}</p><p class="mu-onfilm">${f.pitch}</p><dl class="mu-filmcred">${(f.credits || []).map((c) => html`<div key=${c.part}><dt>${c.part}</dt><dd>${c.model}. <${Ext} href=${c.url}>${c.licence}</${Ext}></dd></div>`)}</dl></figcaption></figure>
  <ul class="mu-filmnotes">${(f.honest || []).map((x) => html`<li key=${x}>${x}</li>`)}</ul>`;
}

function ExtraRow({ x }) {
  return html`<li class="mu-extra"><div class="mu-extrahead"><h4>${x.label}</h4>${x.pack && html`<span class="mu-packtag">RyanOnTheInside's pack</span>`}</div><p class="small">${x.how}</p>${x.audio ? html`<${Player} audio=${x.audio} peaks=${x.peaks} seconds=${x.seconds} label=${x.label}/>` : html`<p class="fx-warn">${x.problem || "Did not run."}</p>`}${x.audio && html`<p class="small mu-extrafacts">${x.seconds} s, ${x.lufs} LUFS, ${x.centroid_hz} Hz bright${x.lyrics ? `, ${lyricWord(x.lyrics)} heard` : ""}${x.words_in_stem != null ? `, and Whisper made out only ${x.words_in_stem} word-like ${x.words_in_stem === 1 ? "fragment" : "fragments"} in it` : ""}. Rendered in ${x.secs} s.</p>`}</li>`;
}

const STRIP = [["mu-ab", "Side by side", "One brief, two models"], ["mu-models", "Every model", "A page each"], ["mu-reactive", "Reactive", "Sound drives picture"], ["mu-film", "A song, filmed", "Before the studio"], ["mu-make", "Make one", "Styles, forms, lyrics"], ["mu-change", "Change a song", "Cover, repaint, stems"], ["mu-ryan", "Credit", "RyanOnTheInside, install"]];
function jump(e, id) { e.preventDefault(); const el = document.getElementById(id); if (!el) return; el.scrollIntoView({ behavior: calm() ? "auto" : "smooth" }); el.focus({ preventScroll: true }); }
function Strip() {
  return html`<nav class="mu-strip" aria-label="Sections of this page"><ol>${STRIP.map(([id, t, s], i) => html`<li key=${id}><a href="#music" onClick=${(e) => jump(e, id)}><i>${i + 1}</i><span><b>${t}</b><small>${s}</small></span></a></li>`)}</ol></nav>`;
}

function Ryan({ r }) {
  if (!r || !r.pack) return null;
  return html`<section class="mu-sect"><${Head} n="7" id="mu-ryan" title="RyanOnTheInside"/>
    <div class="mu-credit film"><p class="mu-eyebrow">Built on his work</p><p class="mu-creditname">Everything reacts to everything.</p><p class="mu-creditline">That's his idea, from his node pack. The reactive demo above, and the cover, repaint and stem takes on this page, ran on his real code on a separate ComfyUI. None of his code is copied or shipped here.</p><p class="mu-links mu-onfilm"><${Ext} href=${r.pack}>His pack on GitHub</${Ext}><${Ext} href=${r.site}>ryanontheinside.com</${Ext}><${Ext} href=${r.youtube}>YouTube</${Ext}><${Ext} href=${r.civitai}>Civitai</${Ext}></p></div>
    <div class="mu-sheetgrid"><section><h3>To run these yourself</h3><p>The reactive and pack-marked graphs on this page need his pack in your ComfyUI. The Render buttons will refuse and bring you here until it's there.</p><pre class="fx-pre">${r.install}</pre><div class="fx-row"><button class="btn small" onClick=${() => copyText(r.install)}>Copy the commands</button><a class="btn small" href="#packlab">Open Pack Lab</a></div></section>
      <section class="mu-risks"><h3>Read this first</h3><p>From reading his code. No outright fault: these are the things to know before putting it in a ComfyUI you care about, which is why we ran it on a separate one.</p><ul>${r.risks.map((x) => html`<li key=${x}>${x}</li>`)}</ul></section></div>
    <h3>All his packs, as found</h3><div class="mu-tablewrap" tabindex="0" role="region" aria-label="All of his packs"><table class="mu-table"><thead><tr><th scope="col">Pack</th><th scope="col">Licence</th><th scope="col">What it is</th><th scope="col">Here</th></tr></thead><tbody>${r.packs.map((p) => html`<tr key=${p.name}><th scope="row"><${Ext} href=${p.url}>${p.name}</${Ext}></th><td>${p.licence}</td><td>${p.use}</td><td>${p.verdict}</td></tr>`)}</tbody></table></div>
  </section>`;
}

export function Music({ route }) {
  const [d, setD] = useState(null), [err, setErr] = useState("");
  const load = () => { setErr(""); api("/api/music/models").then(setD).catch((e) => setErr(said(e))); };
  useEffect(load, []);
  const sub = String(route || "").split("/")[1] || "";
  useEffect(() => { document.body.classList.toggle("on-music", true); return () => document.body.classList.remove("on-music"); }, []);
  if (err) return html`<div class="fx"><p class="fx-err" role="alert">${err}</p><button class="btn" onClick=${load}>Try again</button></div>`;
  if (!d) return html`<div class="fx"><${FxSkeleton} label="Loading the music models."/></div>`;
  const models = d.models || []; const cur = sub && models.find((m) => m.id === sub); const x = d.extras || {};
  if (sub && !cur) return html`<div class="fx mu"><p>No music model called that. <a href="#music">All music models</a></p></div>`;
  if (cur) return html`<div class="fx mu"><${Sheet} m=${cur} brief=${d.brief}/></div>`;
  const unready = sortModels(models).filter((m) => m.state !== "proven");
  return html`<div class="fx mu">
    <${Hero} models=${models} brief=${d.brief}/>
    <${Strip}/>
    <section class="mu-brief"><div><p class="mu-kick">The brief</p><p class="mu-style">${d.brief.style}</p><p class="small">Seed ${d.brief.seed}, ${d.brief.seconds} s ceiling, written for this page. Models with no lyric input got the instrumental line.</p></div><pre class="mu-lyrics" tabindex="0" aria-label="The lyrics">${d.brief.lyrics}</pre></section>
    <section class="mu-sect"><${Head} n="1" id="mu-ab" title="Side by side" sub="The same brief, two models, one clock."/><${Compare} models=${models}/></section>
    <section class="mu-sect"><${Head} n="2" id="mu-models" title="Every model" sub="Open one for its audio, settings, graph, licence and proof."/><${Wall} models=${models}/>
      ${unready.length > 0 && html`<p class="small">${unready.length} have no render on this page yet, and say why on their own page.</p>`}
      ${d.not_music && d.not_music.length > 0 && html`<details class="mu-notmusic"><summary>Looks like music, isn't</summary><ul>${d.not_music.map((n) => html`<li key=${n.name}><b>${n.name}.</b> ${n.why}</li>`)}</ul></details>`}</section>
    <section class="mu-sect"><${Head} n="3" id="mu-reactive" title="Sound drives picture" sub="RyanOnTheInside's idea, on this page's real songs."/><${Reactive} models=${models} visual=${x.visual}/></section>
    ${d.film && html`<section class="mu-sect"><${Head} n="4" id="mu-film" title="A whole song, filmed" sub="Wren Halloway is an invented singer. Made before this studio, and labelled so."/><${Film} f=${d.film}/></section>`}
    <section class="mu-sect"><${Head} n="5" id="mu-make" title="Make one" sub="Music 3's style library, song forms, your words. It runs on this machine."/><${Maker} models=${models} brief=${d.brief}/></section>
    <section class="mu-sect"><${Head} n="6" id="mu-change" title="Change a song" sub="The source is this page's Music 3 render. Each take below is real, and none has been heard."/>
      ${(x.change || []).length ? html`<ul class="mu-extras">${x.change.map((c) => html`<${ExtraRow} key=${c.id} x=${c}/>`)}</ul>` : html`<p class="mu-none">No takes are recorded yet.</p>`}</section>
    <${Ryan} r=${d.roti}/>
  </div>`;
}
