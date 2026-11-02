/* Captions & Sound: speech captions for any clip, set in a real font by ffmpeg. Every proof on this page was measured by a program; nobody has listened to the audio. */
import { useEffect, useState } from "preact/hooks";
import { html, api, post } from "./common.js";
import { said } from "./fx.js";
import { Head, Stats } from "./look.js";
import { clock, licenceWord, STYLE_WORDS, SIZE_WORDS, PLACE_WORDS, clipKey, clipRef, viewUrl, captionBody, canCaption, secs } from "./clipsound_logic.js";

const Tag = ({ w }) => html`<span class=${"fx-tag " + w[1]}>${w[0]}</span>`;
const Ext = ({ href, children }) => html`<a href=${href} target="_blank" rel="noopener noreferrer">${children}<//>`;
const Pills = ({ label, words, value, onPick }) => html`<div class="cs-pills" role="group" aria-label=${label}>${Object.entries(words).map(([k, w]) => html`<button type="button" key=${k} aria-pressed=${k === value} onClick=${() => onPick(k)}>${w}<//>`)}</div>`;

function Hero({ p }) {
  const c = p && p.captions;
  return html`<section class="cs-hero film" aria-labelledby="cs-title">
    <div class="cs-heropic">${c ? html`<video src=${c.src} poster=${c.poster} controls playsinline preload="metadata" aria-label=${c.alt}><//>` : html`<p class="small">No captioned sample yet.</p>`}</div>
    <div class="cs-herotext">
      <p class="cs-eyebrow">Captions & Sound</p>
      <h2 id="cs-title">Its words, on screen.</h2>
      <p>Whisper writes down what is said in your clip. ffmpeg sets those words in a real font, so every letter is spelled the way Whisper heard it, never as a picture model's guess. You get an SRT and a WebVTT file, and a copy with the captions drawn on if you want one.</p>
      ${c && html`<${Stats} items=${[[c.word_match_pct != null ? `${c.word_match_pct}%` : "-", "of the script's words heard"], [`${c.ocr_match_pct}%`, "read back off the frames"], [secs(c.whisper_s), `Whisper on the CPU, ${secs(c.clip_seconds)} clip`]]}/>
      <p class="cs-honest"><b>Measured, not listened to.</b> ${c.measured}</p>`}
    </div>
  </section>`;
}

function Proof({ p }) {
  const rows = p ? [p.captions, ...(p.captions_more || [])].filter(Boolean) : []; if (!rows.length) return null;
  return html`<section aria-labelledby="cs-proof">
    <${Head} id="cs-proof" sub=${p.note}>What ran here<//>
    <ol class="cs-proofs">${rows.map((r) => html`<li key=${r.src} class="fx-card">
      <video src=${r.src} poster=${r.poster} controls playsinline preload="none" aria-label=${r.alt}><//>
      <div><h3>${r.title}</h3>
        <dl class="cs-facts">
          <div><dt>Sound</dt><dd>${r.voice}</dd></div><div><dt>Picture</dt><dd>${r.picture}</dd></div>
          <div><dt>Whisper wrote</dt><dd>“${r.heard}”</dd></div>
          ${r.script && html`<div><dt>The script</dt><dd>“${r.script}”, ${r.word_match_pct}% of its words heard</dd></div>`}
          <div><dt>Read back off the frames</dt><dd>${r.ocr_match_pct}% of caption words (Tesseract)</dd></div>
          <div><dt>Time</dt><dd>Whisper ${secs(r.whisper_s)}, whole job ${secs(r.job_s)}, on the CPU, 0 GB of VRAM</dd></div>
          <div><dt>Sound track</dt><dd>${r.audio_same ? "Left exactly as it was" : "Re-encoded"}</dd></div>
        </dl>
        ${r.fault && html`<p class="small"><b>What is wrong:</b> ${r.fault}</p>`}
      </div></li>`)}</ol>
  </section>`;
}

function Picker({ clips, value, onPick }) {
  const [err, setErr] = useState(""), [up, setUp] = useState("");
  const send = async (e) => {
    const f = e.target.files && e.target.files[0]; if (!f) return; setErr("");
    const b = new FormData(); b.append("file", f);
    try { const r = await api("/api/upload", { method: "POST", body: b }); const k = clipKey({ type: "input", filename: r.name }); setUp(k); onPick(k); } catch (x) { setErr(said(x)); }
  };
  return html`<fieldset class="cs-pick"><legend>Clip</legend>
    <label class="fx-lab">One of your renders<select class="fx-in" value=${value} onChange=${(e) => onPick(e.target.value)}>
      <option value="">Pick a clip</option>
      ${up && html`<option value=${up}>Your upload: ${clipRef(up).filename}</option>`}
      ${clips.map((c) => html`<option key=${clipKey(c)} value=${clipKey(c)}>${c.subfolder ? c.subfolder + "/" : ""}${c.filename}</option>`)}
    </select></label>
    <label class="fx-lab">Or upload one<input class="fx-in" type="file" accept="video/mp4,video/webm,video/quicktime,video/x-matroska" onChange=${send}/></label>
    ${err && html`<p class="fx-err" role="alert">${err}</p>`}
  </fieldset>`;
}

function Result({ job, clip }) {
  const f = job.files || {};
  const src = f.video ? f.video.url : clip ? viewUrl(clipRef(clip)) : "";
  return html`<div class="cs-result">
    ${src && html`<video src=${src} controls playsinline preload="metadata" crossorigin="anonymous" aria-label="The clip with its captions">${!f.video && f.vtt && html`<track kind="captions" srclang=${job.language || "en"} label="Whisper" src=${f.vtt.url} default/>`}<//>`}
    <div>
      <p class="small" role="status">${job.note || `${(job.cues || []).length} caption cards from ${secs(job.speech_seconds)} of speech. Whisper took ${secs(job.whisper_s)}, the whole job ${secs(job.seconds)}.`}</p>
      <div class="fx-row">${f.srt && html`<a class="btn" href=${f.srt.url} download=${f.srt.filename}>SRT file<//>`}${f.vtt && html`<a class="btn" href=${f.vtt.url} download=${f.vtt.filename}>WebVTT file<//>`}${f.video && html`<a class="btn" href=${f.video.url} download=${f.video.filename}>Captioned clip<//>`}</div>
      ${(job.cues || []).length > 0 && html`<ol class="cs-cues">${job.cues.map((c, i) => html`<li key=${i}><span class="cs-at">${clock(c.start)} to ${clock(c.end)}</span><span>${c.lines.join(" / ")}</span></li>`)}</ol>`}
      ${(job.dropped || []).length > 0 && html`<details class="cs-dropped"><summary>Left out: ${job.dropped.length} line${job.dropped.length > 1 ? "s" : ""} Whisper probably made up</summary><ul>${job.dropped.map((d, i) => html`<li key=${i}>“${d.text}” at ${clock(d.start)}: ${d.why}</li>`)}</ul><//>`}
    </div>
  </div>`;
}

function Captions({ d, clips }) {
  const ms = d.listeners || []; const [id, setId] = useState(""); const m = ms.find((x) => x.id === id) || ms.find((x) => x.ready) || ms[0];
  const [clip, setClip] = useState(""), [f, setF] = useState({ language: "", burn: true, style: "outline", size: "medium", place: "bottom" }), [job, setJob] = useState(null), [err, setErr] = useState("");
  const up = (k, v) => setF((x) => ({ ...x, [k]: v }));
  useEffect(() => { if (!job || job.status !== "running") return undefined; const t = setInterval(() => api("/api/clipsound/jobs/" + job.job).then(setJob).catch(() => {}), 1500); return () => clearInterval(t); }, [job]);
  const go = async (e) => { e.preventDefault(); setErr(""); setJob(null); try { setJob(await post("/api/clipsound/captions", captionBody(clip, m, f))); } catch (x) { setErr(said(x)); } };
  const busy = job && job.status === "running";
  if (!m) return html`<p class="small">No Whisper model is listed in the Voices catalogue.</p>`;
  return html`<section aria-labelledby="cs-cap">
    <${Head} id="cs-cap" sub="Any clip with speech in it. Whisper runs on your machine in its own process, not in ComfyUI.">Caption a clip<//>
    <form class="fx-card cs-form" onSubmit=${go}>
      <${Picker} clips=${clips} value=${clip} onPick=${setClip}/>
      <fieldset><legend>Listener</legend>
        <label class="fx-lab">Whisper model<select class="fx-in" value=${m.id} onChange=${(e) => setId(e.target.value)}>${ms.map((x) => html`<option key=${x.id} value=${x.id} disabled=${!x.ready}>${x.label}${x.english_only ? " (English only)" : ""}${x.ready ? "" : " (not on this machine)"}</option>`)}</select></label>
        <p class="small cs-lic"><${Tag} w=${licenceWord(m.licence)}/> ${m.licence ? m.licence.name : "Licence unread"} · ${m.maker}${m.card && html` · <${Ext} href=${m.card}>Model card<//>`}</p>
        ${!m.english_only && html`<label class="fx-lab">Language (blank lets Whisper decide)<input class="fx-in" value=${f.language} maxlength="3" placeholder="en" onInput=${(e) => up("language", e.target.value)}/></label>`}
      </fieldset>
      <fieldset><legend>On screen</legend>
        <label class="cs-check"><input type="checkbox" checked=${f.burn} onChange=${(e) => up("burn", e.target.checked)}/> Also make a copy with the captions drawn on</label>
        ${f.burn && html`<${Pills} label="Caption look" words=${STYLE_WORDS} value=${f.style} onPick=${(k) => up("style", k)}/><${Pills} label="Caption size" words=${SIZE_WORDS} value=${f.size} onPick=${(k) => up("size", k)}/><${Pills} label="Caption place" words=${PLACE_WORDS} value=${f.place} onPick=${(k) => up("place", k)}/>`}
      </fieldset>
      <div class="fx-row"><button class="fx-go" type="submit" disabled=${busy || !canCaption(clip, m)}>${busy ? job.step || "Working" : "Make captions"}</button></div>
      <div aria-live="polite">${err && html`<p class="fx-err" role="alert">${err}</p>`}${job && job.status === "error" && html`<p class="fx-err" role="alert">${job.error}</p>`}</div>
      ${job && job.status === "done" && html`<${Result} job=${job} clip=${clip}/>`}
    </form>
  </section>`;
}

export function ClipSound() {
  const [d, setD] = useState(null), [clips, setClips] = useState([]), [err, setErr] = useState("");
  const load = () => { setErr(""); api("/api/clipsound/models").then(setD).catch((e) => setErr(said(e))); api("/api/clipsound/clips").then((r) => setClips(r.clips || [])).catch(() => {}); };
  useEffect(load, []);
  if (err) return html`<div class="fx"><p class="fx-err" role="alert">${err}</p><button class="btn" onClick=${load}>Try again</button></div>`;
  if (!d) return html`<div class="fx"><p class="small" role="status">Loading...</p></div>`;
  return html`<div class="fx cs"><${Hero} p=${d.proof}/><${Captions} d=${d} clips=${clips}/><${Proof} p=${d.proof}/></div>`;
}
