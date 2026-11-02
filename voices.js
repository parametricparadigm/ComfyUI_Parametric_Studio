// The Voices page: every speech model side by side on one original line. The audio and every number are real and were recorded by scripts/build_voices_page.py. Nobody has listened to any of it.
import { useEffect, useMemo, useRef, useState } from "preact/hooks";
import { html, api, post } from "./common.js";
import { said } from "./fx.js";
import { KINDS, READS_A_LINE, clock, licenceWord, proofWord, SORTS, FILTERS, speakers, board, counts, bars, runBody, canRun, byLanguage } from "./voices_logic.js";

let playing = null;      // one voice at a time, anywhere on the page
const LANG = { en: "English", es: "Spanish", fr: "French", hi: "Hindi", it: "Italian", ja: "Japanese", pt: "Portuguese", zh: "Chinese" };
const Tag = ({ w }) => html`<span class=${"fx-tag " + w[1]}>${w[0]}</span>`;
const Ext = ({ href, children }) => html`<a href=${href} target="_blank" rel="noopener noreferrer">${children}</a>`;

function useTrack(src) {
  const ref = useRef(null); const [t, setT] = useState(0), [on, setOn] = useState(false), [dur, setDur] = useState(0);
  useEffect(() => {
    const a = new Audio(); a.preload = "none"; a.src = src || ""; ref.current = a; setT(0); setOn(false); setDur(0);
    const tick = () => setT(a.currentTime), meta = () => setDur(a.duration || 0), go = () => setOn(true), stop = () => setOn(false);
    a.addEventListener("timeupdate", tick); a.addEventListener("loadedmetadata", meta); a.addEventListener("play", go); a.addEventListener("pause", stop); a.addEventListener("ended", stop);
    return () => { a.pause(); if (playing === a) playing = null; a.removeEventListener("timeupdate", tick); a.removeEventListener("loadedmetadata", meta); a.removeEventListener("play", go); a.removeEventListener("pause", stop); a.removeEventListener("ended", stop); };
  }, [src]);
  const toggle = () => { const a = ref.current; if (!a) return; if (a.paused) { if (playing && playing !== a) playing.pause(); playing = a; const p = a.play(); if (p && p.catch) p.catch(() => {}); } else a.pause(); };
  const seek = (s) => { const a = ref.current; if (a && isFinite(s)) { a.currentTime = Math.max(0, s); setT(a.currentTime); } };
  return { t, on, dur, toggle, seek };
}

const PlayIcon = ({ on }) => html`<svg viewBox="0 0 24 24" aria-hidden="true"><path d=${on ? "M6 4h4v16H6z M14 4h4v16h-4z" : "M6 3l15 9-15 9z"}/></svg>`;

function Player({ src, peaks, seconds, label, big }) {
  const track = useTrack(src); const shown = useMemo(() => bars(peaks, big ? 160 : 72), [peaks, big]); const len = track.dur || seconds || 0; const pos = len ? Math.min(1, track.t / len) : 0; const box = useRef(null);
  const at = (e) => { const r = box.current.getBoundingClientRect(); track.seek(Math.max(0, Math.min(1, (e.clientX - r.left) / r.width)) * len); };
  const key = (e) => { const d = { ArrowRight: 1, ArrowLeft: -1, PageUp: 5, PageDown: -5 }[e.key]; if (d) { e.preventDefault(); track.seek(track.t + d); } else if (e.key === "Home") { e.preventDefault(); track.seek(0); } else if (e.key === "End") { e.preventDefault(); track.seek(len); } };
  return html`<div class=${"vo-player" + (big ? " big" : "")}>
    <button class="vo-play" onClick=${track.toggle} aria-pressed=${track.on} aria-label=${(track.on ? "Pause " : "Play ") + label}><${PlayIcon} on=${track.on}/></button>
    <div ref=${box} class="vo-wave" role="slider" tabindex="0" aria-label=${"Position in " + label} aria-valuemin="0" aria-valuemax=${Math.round(len)} aria-valuenow=${Math.round(track.t)} aria-valuetext=${clock(track.t)} onClick=${at} onKeyDown=${key}>
      <svg viewBox=${`0 0 ${shown.length || 1} 100`} preserveAspectRatio="none" aria-hidden="true">${shown.map((v, i) => { const h = Math.max(3, v * 100); return html`<rect key=${i} x=${i + 0.15} y=${50 - h / 2} width="0.7" height=${h} class=${i / shown.length <= pos ? "on" : ""}/>`; })}</svg>
    </div>
    <span class="vo-time">${clock(track.t)} / ${clock(len)}</span>
  </div>`;
}

function Card({ m, n }) {
  const r = m.proof; const [hear, setHear] = useState(false);
  return html`<li class="vo-card" id=${"vo-" + m.id}>
    <header><span class="vo-n" aria-hidden="true">${String(n).padStart(2, "0")}</span><div><h3>${m.label}</h3><p class="small">${m.maker}</p></div></header>
    <${Player} src=${r.audio} peaks=${r.peaks} seconds=${r.seconds} label=${m.label}/>
    <div class="fx-row"><${Tag} w=${proofWord(r)}/><${Tag} w=${licenceWord(m.licence)}/></div>
    <dl class="vo-facts">
      <div><dt>Time</dt><dd>${r.secs != null ? `${r.secs} s` : "-"}</dd></div>
      <div><dt>Peak VRAM</dt><dd>${r.peak_gib ? `${r.peak_gib} GB` : "CPU"}</dd></div>
      <div><dt>Length</dt><dd>${r.seconds} s</dd></div>
      <div><dt>LUFS</dt><dd>${r.lufs != null ? r.lufs : "-"}</dd></div>
    </dl>
    <p class="vo-voice"><b>Voice:</b> ${r.voice_note}</p>
    <p class="small">${m.job}</p>
    <p class="small"><b>Licence:</b> ${m.licence ? m.licence.name : "unread"}${m.licence && m.licence.note ? `. ${m.licence.note}` : ""}${m.card ? html` · <${Ext} href=${m.card}>Model card<//>` : ""}</p>
    <button class="vo-more" aria-expanded=${hear} onClick=${() => setHear(!hear)}>${hear ? "Hide" : "Show"} what Whisper heard</button>
    ${hear && html`<blockquote class="vo-heard">${r.heard || "(nothing)"}</blockquote>`}
  </li>`;
}

function Hero({ models, line }) {
  const list = speakers(models); const [pick, setPick] = useState(null); const cur = list.find((m) => m.id === pick) || list[0]; const n = counts(models);
  return html`<section class="vo-hero film" aria-labelledby="vo-title">
    <p class="vo-eyebrow">Speech models on this machine</p>
    <h2 id="vo-title">Voices</h2>
    <blockquote class="vo-line">“${line}”</blockquote>
    ${cur && html`<div class="vo-now"><b>${cur.label}</b><span>${cur.proof.voice_note}</span></div><${Player} big src=${cur.proof.audio} peaks=${cur.proof.peaks} seconds=${cur.proof.seconds} label=${cur.label}/>
    <div class="vo-pills" role="group" aria-label="Pick a voice">${list.map((m) => html`<button key=${m.id} aria-pressed=${m.id === cur.id} onClick=${() => setPick(m.id)}>${m.short || m.label}</button>`)}</div>`}
    <dl class="vo-stats"><div><dd>${n.speaking}</dd><dt>models read the line</dt></div><div><dd>${n.tools}</dd><dt>listeners and tools proved</dt></div><div><dd>${n.files}</dd><dt>files they use, rendered</dt></div><div><dd>${n.blocked}</dd><dt>not proved, each says why</dt></div></dl>
    <p class="vo-honest"><b>Nobody has listened yet.</b> Whisper checked the words, a script checked level and length. A machine can't tell you whether a voice sounds good, so judge that yourself. Every sample uses a built-in or synthetic voice. No real person's voice was copied.</p>
  </section>`;
}

function Board({ models }) {
  const [filter, setFilter] = useState("all"), [sort, setSort] = useState("match"); const rows = board(models, filter, sort);
  return html`<section aria-labelledby="vo-side"><div class="vo-head"><h2 id="vo-side">Side by side</h2>
    <div class="vo-tools"><div class="vo-pills plain" role="group" aria-label="Which models">${Object.entries(FILTERS).map(([k, [w]]) => html`<button key=${k} aria-pressed=${k === filter} onClick=${() => setFilter(k)}>${w}</button>`)}</div>
    <label class="fx-lab vo-sort">Sort<select class="fx-in" value=${sort} onChange=${(e) => setSort(e.target.value)}>${Object.entries(SORTS).map(([k, [w]]) => html`<option value=${k}>${w}</option>`)}</select></label></div></div>
    ${rows.length ? html`<ol class="vo-grid">${rows.map((m, i) => html`<${Card} key=${m.id} m=${m} n=${i + 1}/>`)}</ol>` : html`<p class="small">No model fits that filter yet.</p>`}
  </section>`;
}

function Kokoro({ kokoro }) {
  const groups = byLanguage(kokoro); const total = Object.keys(kokoro || {}).length; if (!total) return null;
  return html`<section aria-labelledby="vo-kokoro"><div class="vo-head"><h2 id="vo-kokoro">All ${total} Kokoro voices</h2><p class="small">Each voice read the line in its own language. Non-English lines are our translations of it. Whisper's match is against that translation.</p></div>
    ${groups.map(([lang, list]) => html`<h3 class="vo-lang">${LANG[lang] || lang}</h3><ul class="vo-voices">${list.map((v) => html`<li key=${v.voice}><div class="vo-vname"><b>${v.voice}</b><span class=${v.match_pct >= 90 ? "good" : "low"}>${v.match_pct}%</span></div><${Player} src=${v.audio} peaks=${v.peaks} seconds=${v.seconds} label=${"Kokoro voice " + v.voice}/></li>`)}</ul>`)}
  </section>`;
}

function Tools({ models }) {
  const rows = models.filter((m) => !READS_A_LINE.has(m.kind) && m.state === "rendered"); if (!rows.length) return null;
  const ears = rows.filter((m) => m.kind === "listen"), rest = rows.filter((m) => m.kind !== "listen");
  return html`<section aria-labelledby="vo-tools"><div class="vo-head"><h2 id="vo-tools">Listeners and tools</h2><p class="small">Speech-to-text models were given the Kokoro reading and scored against the words it was given. Codecs and clean-up models were given the same reading and their output was checked by Whisper.</p></div>
    ${ears.length > 0 && html`<div class="vo-tablewrap" tabindex="0" role="region" aria-label="Speech to text results"><table class="vo-table"><thead><tr><th scope="col">Model</th><th scope="col">Words right</th><th scope="col">Time</th><th scope="col">Peak VRAM</th><th scope="col">Licence</th><th scope="col">What it wrote</th></tr></thead>
      <tbody>${ears.map((m) => html`<tr key=${m.id}><th scope="row">${m.label}</th><td>${m.proof.match_pct != null ? `${m.proof.match_pct}%` : "-"}${m.listen_lang ? ` (${LANG[m.listen_lang]})` : ""}</td><td>${m.proof.secs} s</td><td>${m.proof.peak_gib ? `${m.proof.peak_gib} GB` : "CPU"}</td><td>${m.licence ? m.licence.name : "unread"}</td><td class="vo-said">${m.proof.text}</td></tr>`)}</tbody></table></div>`}
    ${rest.length > 0 && html`<ol class="vo-grid">${rest.map((m, i) => html`<li class="vo-card" key=${m.id}><header><span class="vo-n" aria-hidden="true">${KINDS[m.kind]}</span><div><h3>${m.label}</h3><p class="small">${m.maker}</p></div></header><${Player} src=${m.proof.audio} peaks=${m.proof.peaks} seconds=${m.proof.seconds} label=${m.label}/><div class="fx-row"><${Tag} w=${proofWord(m.proof)}/><${Tag} w=${licenceWord(m.licence)}/></div><p class="small">${m.job}</p>${m.proof.sdr_out != null && html`<p class="vo-voice"><b>Against the clean reading:</b> ${m.proof.sdr_in} dB in, ${m.proof.sdr_out} dB out.</p>`}<p class="vo-voice"><b>Input:</b> ${m.proof.voice_note}</p></li>`)}</ol>`}
  </section>`;
}

function Blocked({ models }) {
  const rows = models.filter((m) => m.state !== "rendered"); if (!rows.length) return null;
  return html`<section aria-labelledby="vo-blocked"><div class="vo-head"><h2 id="vo-blocked">Not proved yet</h2><p class="small">Nothing here has been rendered on this machine. Each line says what stops it.</p></div>
    <ul class="vo-blocked">${rows.map((m) => html`<li key=${m.id}><div><b>${m.label}</b> <span class="small">${KINDS[m.kind]}</span></div><p class="small">${m.blocked || "Its files are here, and it hasn't been run yet."}</p></li>`)}</ul></section>`;
}

function Try({ models }) {
  const usable = models.filter((m) => READS_A_LINE.has(m.kind) && m.state === "rendered");
  const [id, setId] = useState(""); const m = usable.find((x) => x.id === id) || usable[0];
  const [f, setF] = useState({ text: "", voice: "", reference: "", referenceText: "", consent: "" }); const [job, setJob] = useState(null), [err, setErr] = useState(""), [busy, setBusy] = useState(false);
  const up = (k, v) => setF((x) => ({ ...x, [k]: v }));
  const send = async (e) => { const fl = e.target.files && e.target.files[0]; if (!fl) return; setErr(""); const b = new FormData(); b.append("file", fl); try { const r = await api("/api/upload", { method: "POST", body: b }); up("reference", r.name); } catch (x) { setErr(said(x)); } };
  const go = async () => { setErr(""); setJob(null); setBusy(true); try { const r = await post("/api/voices/run", runBody(m, f)); setJob(r); const tick = async () => { const s = await api("/api/voices/jobs/" + r.job); setJob(s); if (s.status === "running") setTimeout(tick, 2500); else setBusy(false); }; setTimeout(tick, 2500); } catch (x) { setErr(said(x)); setBusy(false); } };
  if (!m) return null;
  return html`<section aria-labelledby="vo-try"><div class="vo-head"><h2 id="vo-try">Try one</h2><p class="small">It runs on your machine in its own process, not in ComfyUI. Words go through the studio's safety check.</p></div>
    <div class="fx-card vo-form">
      <label class="fx-lab">Model<select class="fx-in" value=${m.id} onChange=${(e) => setId(e.target.value)}>${usable.map((x) => html`<option value=${x.id}>${x.label} (${KINDS[x.kind]})</option>`)}</select></label>
      <label class="fx-lab">Line to read<textarea class="fx-in vo-text" rows="3" maxlength="800" value=${f.text} onInput=${(e) => up("text", e.target.value)} placeholder="Write something for it to read."></textarea></label>
      ${m.kind === "design" && html`<label class="fx-lab">Describe the voice<input class="fx-in" value=${f.voice} onInput=${(e) => up("voice", e.target.value)} placeholder=${m.voice_default || ""}/></label>`}
      ${m.kind === "speech" && m.voices && html`<label class="fx-lab">Built-in voice<select class="fx-in" value=${f.voice} onChange=${(e) => up("voice", e.target.value)}><option value="">Default</option>${m.voices.map((v) => html`<option value=${v}>${v}</option>`)}</select></label>`}
      ${m.reference !== "none" && html`<fieldset class="vo-consent"><legend>Reference clip${m.reference === "required" ? "" : " (optional)"}</legend>
        <p class="small">This model copies the voice in the clip. Never use someone's voice without their permission.</p>
        <label class="fx-lab">Clip<input class="fx-in" type="file" accept="audio/*" onChange=${send}/></label>
        <label class="fx-lab">What the clip says<input class="fx-in" value=${f.referenceText} onInput=${(e) => up("referenceText", e.target.value)}/></label>
        <label class="vo-check"><input type="radio" name="vo-consent" checked=${f.consent === "own"} onChange=${() => up("consent", "own")}/> It's my own voice</label>
        <label class="vo-check"><input type="radio" name="vo-consent" checked=${f.consent === "permission"} onChange=${() => up("consent", "permission")}/> I have the speaker's permission to use it</label>
      </fieldset>`}
      <div class="fx-row"><button class="fx-go" disabled=${busy || !canRun(m, f)} onClick=${go}>${busy ? "Rendering..." : "Read it"}</button><span class="small">${m.licence ? licenceWord(m.licence)[0] : ""}${m.proof.peak_gib ? ` · about ${m.proof.peak_gib} GB of VRAM` : ""}</span></div>
      <div aria-live="polite">${err && html`<p class="fx-err" role="alert">${err}</p>`}${job && job.status === "error" && html`<p class="fx-err" role="alert">${job.error}</p>`}${job && job.status === "done" && html`<p class="small">Saved to the output folder: <code>${job.file}</code>, ${job.seconds} s.</p>`}</div>
    </div></section>`;
}

export function Voices() {
  const [d, setD] = useState(null), [err, setErr] = useState("");
  const load = () => { setErr(""); api("/api/voices/models").then(setD).catch((e) => setErr(said(e))); };
  useEffect(load, []);
  useEffect(() => { document.body.classList.add("on-voices"); return () => document.body.classList.remove("on-voices"); }, []);
  if (err) return html`<div class="fx"><p class="fx-err" role="alert">${err}</p><button class="btn" onClick=${load}>Try again</button></div>`;
  if (!d) return html`<div class="fx"><p class="small" role="status">Loading the voices...</p></div>`;
  return html`<div class="fx vo"><${Hero} models=${d.models} line=${d.line}/><${Board} models=${d.models}/><${Kokoro} kokoro=${d.kokoro}/><${Tools} models=${d.models}/><${Try} models=${d.models}/><${Blocked} models=${d.models}/></div>`;
}
