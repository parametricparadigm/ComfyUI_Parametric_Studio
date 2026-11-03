/* Dub & Voice: a clip's words in another language, a voice you may clone, and a voiceover mastered to a loudness target. Every number here was measured by a program; nobody has listened. */
import { useEffect, useState } from "preact/hooks";
import { html, api, post } from "./common.js";
import { said, FxSkeleton } from "./fx.js";
import { Head, Stats } from "./look.js";
import { clipKey, clipRef, secs } from "./clipsound_logic.js";
import { MODE_WORDS, MODE_NOTES, CONSENT_WORDS, werWord, db, masterChecks, dubBody, dubBlocked, lengthNote } from "./dub_logic.js";

const Pills = ({ label, words, value, onPick, off = {} }) => html`<div class="db-pills" role="group" aria-label=${label}>${Object.entries(words).map(([k, w]) => html`<button type="button" key=${k} aria-pressed=${k === value} disabled=${!!off[k]} title=${off[k] || ""} onClick=${() => onPick(k)}>${w}<//>`)}</div>`;
const Mark = () => html`<span class="db-ai">AI-generated</span>`;
const Err = ({ e }) => (e ? html`<p class="fx-err" role="alert">${e}</p>` : null);

function useJob() {
  const [job, setJob] = useState(null);
  useEffect(() => { if (!job || job.status !== "running") return undefined; const t = setInterval(() => api("/api/dub/jobs/" + job.job).then(setJob).catch(() => {}), 1500); return () => clearInterval(t); }, [job]);
  return [job, setJob, job && job.status === "running"];
}

async function upload(file) { const b = new FormData(); b.append("file", file); return api("/api/upload", { method: "POST", body: b }); }

function Hero({ p }) {
  const v = p && (p.dubit || p.voice_dub), m = p && p.media || {}, src = m.dubit || m.voice_dub;
  return html`<section class="db-hero film" aria-labelledby="db-title">
    <div class="db-heropic">${src ? html`<video src=${src} poster=${String(src).replace(/\.mp4(\?.*)?$/, ".webp")} controls playsinline preload="none" aria-label="An invented woman, dubbed into Spanish"><//>` : html`<p class="small">No dub has been rendered here yet.</p>`}</div>
    <div class="db-herotext">
      <p class="db-eyebrow">Dub & Voice</p>
      <h2 id="db-title">Same face. Another language.</h2>
      <p>Whisper writes down what your clip says. You, or the local language model, put it in another language. Then LTX's DubIt redraws the mouth and speaks the line in the speaker's own voice, or Qwen3-TTS reads it for you. Whisper listens to the result and says how many words came through.</p>
      ${v && html`<${Stats} items=${[[v.wer != null ? `${Math.round((1 - v.wer) * 100)}%` : "-", `of the Spanish words heard back (WER ${v.wer != null ? v.wer.toFixed(2) : "-"})`], [secs(v.seconds), "to make it"], [v.peak_vram_gib != null ? `${v.peak_vram_gib} GB` : "-", "peak GPU memory"]]}/>
      <p class="db-honest"><b>Measured, not listened to.</b> ${p.note}</p>`}
    </div>
  </section>`;
}

function ClipPick({ clips, value, onPick }) {
  const [err, setErr] = useState(""), [up, setUp] = useState("");
  const send = async (e) => { const f = e.target.files && e.target.files[0]; if (!f) return; setErr(""); try { const r = await upload(f); const k = clipKey({ type: "input", filename: r.name }); setUp(k); onPick(k); } catch (x) { setErr(said(x)); } };
  return html`<fieldset><legend>1. The clip</legend>
    <label class="fx-lab">One of your renders<select class="fx-in" value=${value} onChange=${(e) => onPick(e.target.value)}>
      <option value="">Pick a clip with one person speaking</option>
      ${up && html`<option value=${up}>Your upload: ${clipRef(up).filename}</option>`}
      ${clips.map((c) => html`<option key=${clipKey(c)} value=${clipKey(c)}>${c.subfolder ? c.subfolder + "/" : ""}${c.filename}</option>`)}
    </select></label>
    <label class="fx-lab">Or upload one<input class="fx-in" type="file" accept="video/mp4,video/webm,video/quicktime" onChange=${send}/></label>
    <${Err} e=${err}/>
  </fieldset>`;
}

function DubForm({ d, clips }) {
  const [clip, setClip] = useState(""), [heard, setHeard] = useState(null), [listenJob, setListen, listening] = useJob(), [job, setJob, busy] = useJob(), [err, setErr] = useState(""), [tr, setTr] = useState(false);
  const [f, setF] = useState({ mode: d.dubit.ready ? "dubit" : "voice", language: "es", text: "", scene: "", voice: d.speakers[0], consent: "", seed: 7, permission: false });
  const up = (k, v) => setF((x) => ({ ...x, [k]: v }));
  useEffect(() => { if (listenJob && listenJob.status === "done") { setHeard(listenJob); up("source_text", listenJob.transcript); } }, [listenJob]);
  const listen = async () => { setErr(""); setHeard(null); try { setListen(await post("/api/dub/transcribe", { clip: clipRef(clip), english: f.language === "en" })); } catch (x) { setErr(said(x)); } };
  const translate = async () => { setErr(""); setTr(true); try { const r = await post("/api/dub/translate", { text: heard.transcript, to: f.language, from: heard.language }); up("text", r.text); } catch (x) { setErr(said(x)); } setTr(false); };
  const go = async (e) => { e.preventDefault(); setErr(""); setJob(null); try { setJob(await post("/api/dub/run", dubBody(clipRef(clip), f))); } catch (x) { setErr(said(x)); } };
  const why = dubBlocked(clip, f, d), langs = Object.entries(d.languages);
  return html`<section aria-labelledby="db-dub">
    <${Head} id="db-dub" sub="One person speaking, up to 5 seconds for DubIt. Speech models run on your machine in their own process.">Dub a clip<//>
    <form class="fx-card db-form" onSubmit=${go}>
      <${ClipPick} clips=${clips} value=${clip} onPick=${(k) => { setClip(k); setHeard(null); }}/>
      <fieldset><legend>2. What is said</legend>
        <div class="fx-row"><button type="button" class="btn" disabled=${!clip || listening} onClick=${listen}>${listening ? listenJob.step || "Listening" : "Listen with Whisper"}</button></div>
        ${listenJob && listenJob.status === "error" && html`<${Err} e=${listenJob.error}/>`}
        ${heard && html`<blockquote class="db-heard"><p>“${heard.transcript || "(no speech heard)"}”</p><footer class="small">Whisper large-v3 heard ${d.languages[heard.language] || heard.language}.${heard.english ? ` Its own English: “${heard.english}”` : ""}</footer></blockquote>`}
      </fieldset>
      <fieldset><legend>3. The new line</legend>
        <label class="fx-lab">Language<select class="fx-in" value=${f.language} onChange=${(e) => up("language", e.target.value)}>${langs.map(([k, n]) => html`<option key=${k} value=${k}>${n}</option>`)}</select></label>
        <div class="fx-row"><button type="button" class="btn" disabled=${!heard || !heard.transcript || !d.llm || tr} onClick=${translate} title=${d.llm ? "" : "No local language model is running"}>${tr ? "Translating" : d.llm ? `Translate with ${d.llm}` : "No local LLM running"}</button>
          ${heard && heard.english && f.language === "en" && html`<button type="button" class="btn" onClick=${() => up("text", heard.english)}>Use Whisper's English</button>`}</div>
        <label class="fx-lab">The line, in its own script (you can always type or fix it)<textarea class="fx-in" rows="3" maxlength="600" value=${f.text} onInput=${(e) => up("text", e.target.value)}></textarea></label>
        ${heard && f.text && html`<p class="small" role="status">${lengthNote(heard.transcript, f.text)}</p>`}
      </fieldset>
      <fieldset><legend>4. How it is said</legend>
        <${Pills} label="Dub method" words=${MODE_WORDS} value=${f.mode} onPick=${(k) => up("mode", k)} off=${{ dubit: d.dubit.ready ? "" : d.dubit.why_not, voice: d.tts.ready ? "" : d.tts.why_not, relip: d.tts.ready ? "" : d.tts.why_not }}/>
        <p class="small">${MODE_NOTES[f.mode]}</p>
        ${f.mode === "dubit" ? html`<label class="fx-lab">What the clip shows (helps DubIt keep it the same)<input class="fx-in" maxlength="300" value=${f.scene} placeholder="A woman in a dark coat talks to the camera" onInput=${(e) => up("scene", e.target.value)}/></label>`
          : html`<label class="fx-lab">Voice<select class="fx-in" value=${f.voice} onChange=${(e) => up("voice", e.target.value)}>${d.speakers.map((s) => html`<option key=${s} value=${s}>${s} (Qwen3-TTS)</option>`)}<option value="clone">Clone the voice in the clip</option></select></label>
            ${f.voice === "clone" && html`<fieldset class="db-consent"><legend>Whose voice is it?</legend>${Object.entries(CONSENT_WORDS).map(([k, w]) => html`<label key=${k} class="db-check"><input type="radio" name="dubconsent" checked=${f.consent === k} onChange=${() => up("consent", k)}/> ${w}</label>`)}</fieldset>`}`}
        <label class="db-check"><input type="checkbox" checked=${f.permission} onChange=${(e) => up("permission", e.target.checked)}/> The person in the clip is invented, or gave permission to be dubbed.</label>
      </fieldset>
      <div class="fx-row"><button class="fx-go" type="submit" disabled=${busy || !!why}>${busy ? job.step || "Working" : "Dub it"}</button>${why && html`<span class="small">${why}</span>`}</div>
      <div aria-live="polite"><${Err} e=${err}/>${job && job.status === "error" && html`<${Err} e=${job.error}/>`}</div>
      ${job && job.status === "done" && html`<div class="db-result"><video src=${job.file.url} controls playsinline preload="metadata" aria-label="The dubbed clip"><//>
        <dl class="db-facts"><div><dt>Made with</dt><dd>${job.model} <${Mark}/></dd></div><div><dt>Whisper heard</dt><dd>“${job.heard}”</dd></div><div><dt>Words</dt><dd>${werWord(job.wer)}</dd></div><div><dt>Time</dt><dd>${secs(job.seconds)}</dd></div><div><dt>Licence</dt><dd>${job.licence}</dd></div></dl>
        <a class="btn" href=${job.file.url} download=${job.file.filename}>Download<//></div>`}
    </form>
  </section>`;
}

function Clone({ d }) {
  const [f, setF] = useState({ way: "design", design: "A warm, low-voiced adult, unhurried, speaking close to the microphone.", text: "", language: "en", reference: "", reference_text: "", consent: "" }), [job, setJob, busy] = useJob(), [err, setErr] = useState("");
  const up = (k, v) => setF((x) => ({ ...x, [k]: v }));
  const send = async (e) => { const file = e.target.files && e.target.files[0]; if (!file) return; try { up("reference", (await upload(file)).name); } catch (x) { setErr(said(x)); } };
  const go = async (e) => { e.preventDefault(); setErr(""); setJob(null); const b = { text: f.text, language: f.language, ...(f.way === "design" ? { design: f.design } : { reference: f.reference, reference_text: f.reference_text, consent: f.consent }) }; try { setJob(await post("/api/dub/clone", b)); } catch (x) { setErr(said(x)); } };
  const ok = f.text.trim() && d.tts.ready && (f.way === "design" ? f.design.trim() : f.reference && (f.consent === "own" || f.consent === "permission"));
  const fl = job && job.files || {};
  return html`<section aria-labelledby="db-clone">
    <${Head} id="db-clone" sub="Only your own voice, a voice whose owner said yes, or a voice designed from words. Your answer is saved in a file beside the result.">Clone a voice<//>
    <form class="fx-card db-form" onSubmit=${go}>
      <${Pills} label="Where the voice comes from" words=${{ design: "Design one from words", own: "My own recording" }} value=${f.way} onPick=${(k) => up("way", k)}/>
      ${f.way === "design" ? html`<label class="fx-lab">Describe the voice<textarea class="fx-in" rows="2" maxlength="300" value=${f.design} onInput=${(e) => up("design", e.target.value)}></textarea></label>`
        : html`<label class="fx-lab">Your recording (10 to 20 seconds of clear speech)<input class="fx-in" type="file" accept="audio/*" onChange=${send}/></label>
          <label class="fx-lab">What you say in it (helps the clone)<input class="fx-in" maxlength="600" value=${f.reference_text} onInput=${(e) => up("reference_text", e.target.value)}/></label>
          <fieldset class="db-consent"><legend>Whose voice is it?</legend>${["own", "permission"].map((k) => html`<label key=${k} class="db-check"><input type="radio" name="cloneconsent" checked=${f.consent === k} onChange=${() => up("consent", k)}/> ${CONSENT_WORDS[k]}</label>`)}</fieldset>`}
      <label class="fx-lab">Language<select class="fx-in" value=${f.language} onChange=${(e) => up("language", e.target.value)}>${Object.entries(d.languages).map(([k, n]) => html`<option key=${k} value=${k}>${n}</option>`)}</select></label>
      <label class="fx-lab">A line for the cloned voice<textarea class="fx-in" rows="2" maxlength="600" value=${f.text} onInput=${(e) => up("text", e.target.value)}></textarea></label>
      <div class="fx-row"><button class="fx-go" type="submit" disabled=${busy || !ok}>${busy ? job.step || "Working" : "Clone it"}</button></div>
      <div aria-live="polite"><${Err} e=${err}/>${job && job.status === "error" && html`<${Err} e=${job.error}/>`}</div>
      ${job && job.status === "done" && html`<div class="db-audio">
        ${fl.reference && html`<figure><figcaption>The designed voice <${Mark}/></figcaption><audio controls src=${fl.reference.url}></audio></figure>`}
        <figure><figcaption>The clone reading your line <${Mark}/></figcaption><audio controls src=${fl.voice.url}></audio></figure>
        <p class="small">Voice likeness: ${job.similarity && job.similarity.cosine != null ? `${job.similarity.cosine.toFixed(2)} (cosine of Chatterbox voice-encoder embeddings; 1 is the same voice)` : "not measured"}. Consent saved: ${job.consent}. <a href=${fl.consent.url} download=${fl.consent.filename}>Consent file<//></p></div>`}
    </form>
  </section>`;
}

function Voiceover({ d }) {
  const [audio, setAudio] = useState([]), [f, setF] = useState({ text: "", speaker: d.speakers[0], language: "en", music: "", lufs: d.master.lufs, tp: d.master.tp, depth: d.master.depth }), [job, setJob, busy] = useJob(), [err, setErr] = useState("");
  const up = (k, v) => setF((x) => ({ ...x, [k]: v }));
  useEffect(() => { api("/api/dub/audio").then((r) => setAudio(r.audio || [])).catch(() => {}); }, []);
  const send = async (e) => { const file = e.target.files && e.target.files[0]; if (!file) return; try { const r = await upload(file); up("music", clipKey({ type: "input", filename: r.name })); } catch (x) { setErr(said(x)); } };
  const go = async (e) => { e.preventDefault(); setErr(""); setJob(null); try { setJob(await post("/api/dub/voiceover", { text: f.text, speaker: f.speaker, language: f.language, music: clipRef(f.music), lufs: Number(f.lufs), tp: Number(f.tp), depth: Number(f.depth) })); } catch (x) { setErr(said(x)); } };
  const checks = job && job.status === "done" ? masterChecks(job.report) : [];
  return html`<section aria-labelledby="db-vo">
    <${Head} id="db-vo" sub="The music drops while the voice speaks and comes back between lines. Then the mix is set to a loudness target and its true peak kept under a ceiling, both measured by ffmpeg's EBU R128 meter.">Voiceover on music<//>
    <form class="fx-card db-form" onSubmit=${go}>
      <label class="fx-lab">Script<textarea class="fx-in" rows="3" maxlength="1500" value=${f.text} onInput=${(e) => up("text", e.target.value)}></textarea></label>
      <div class="db-two"><label class="fx-lab">Voice<select class="fx-in" value=${f.speaker} onChange=${(e) => up("speaker", e.target.value)}>${d.speakers.map((s) => html`<option key=${s} value=${s}>${s}</option>`)}</select></label>
        <label class="fx-lab">Language<select class="fx-in" value=${f.language} onChange=${(e) => up("language", e.target.value)}>${Object.entries(d.languages).map(([k, n]) => html`<option key=${k} value=${k}>${n}</option>`)}</select></label></div>
      <label class="fx-lab">Music<select class="fx-in" value=${f.music} onChange=${(e) => up("music", e.target.value)}><option value="">Pick a music render</option>${f.music.startsWith("input:") && html`<option value=${f.music}>Your upload</option>`}${audio.map((a) => html`<option key=${clipKey(a)} value=${clipKey(a)}>${a.subfolder ? a.subfolder + "/" : ""}${a.filename}</option>`)}</select></label>
      <label class="fx-lab">Or upload music<input class="fx-in" type="file" accept="audio/*" onChange=${send}/></label>
      <div class="db-three"><label class="fx-lab">Loudness (LUFS)<input class="fx-in" type="number" step="0.5" min="-24" max="-9" value=${f.lufs} onInput=${(e) => up("lufs", e.target.value)}/></label>
        <label class="fx-lab">True peak ceiling (dBTP)<input class="fx-in" type="number" step="0.1" min="-3" max="-0.5" value=${f.tp} onInput=${(e) => up("tp", e.target.value)}/></label>
        <label class="fx-lab">Music under voice (dB)<input class="fx-in" type="number" step="1" min="8" max="24" value=${f.depth} onInput=${(e) => up("depth", e.target.value)}/></label></div>
      <div class="fx-row"><button class="fx-go" type="submit" disabled=${busy || !f.text.trim() || !f.music || !d.tts.ready}>${busy ? job.step || "Working" : "Make the voiceover"}</button></div>
      <div aria-live="polite"><${Err} e=${err}/>${job && job.status === "error" && html`<${Err} e=${job.error}/>`}</div>
      ${job && job.status === "done" && html`<div class="db-audio"><figure><figcaption>Mastered mix <${Mark}/></figcaption><audio controls src=${job.files.m4a.url}></audio></figure>
        <table class="db-table"><thead><tr><th scope="col">Check</th><th scope="col">Measured</th><th scope="col">Wanted</th><th scope="col">Result</th></tr></thead><tbody>${checks.map((c) => html`<tr key=${c.k}><th scope="row">${c.label}</th><td>${c.value}</td><td>${c.want}</td><td class=${c.ok ? "db-ok" : "db-bad"}>${c.ok ? "Pass" : "Fail"}</td></tr>`)}</tbody></table>
        <div class="fx-row"><a class="btn" href=${job.files.wav.url} download=${job.files.wav.filename}>WAV (24-bit)<//><a class="btn" href=${job.files.m4a.url} download=${job.files.m4a.filename}>M4A<//></div></div>`}
    </form>
  </section>`;
}

function Proof({ p }) {
  if (!p || !p.media) return null; const m = p.media;
  const vo = p.master, cl = p.clone, vd = p.voice_dub, dt = p.dubit, rl = p.relip;
  return html`<section aria-labelledby="db-proof">
    <${Head} id="db-proof" sub=${p.note}>What ran here<//>
    <ol class="db-proofs">
      ${dt && html`<li class="fx-card"><video src=${m.dubit} poster=${String(m.dubit).replace(/\.mp4(\?.*)?$/, ".webp")} controls playsinline preload="none" aria-label="DubIt on LTX-2.5: the invented woman speaks Spanish"><//><div><h3>DubIt on LTX-2.5, into Spanish</h3><dl class="db-facts">
        <div><dt>Asked</dt><dd>“${dt.translation}”</dd></div><div><dt>Whisper heard</dt><dd>“${dt.heard}”</dd></div><div><dt>Words</dt><dd>${werWord(dt.wer)}</dd></div>
        <div><dt>Voice</dt><dd>likeness to her original voice ${dt.voice_similarity_to_source}</dd></div><div><dt>Run</dt><dd>${dt.model}, seed ${dt.seed}, ${dt.frames} frames at ${dt.size.join("×")}, ${secs(dt.seconds)}, peak ${dt.peak_vram_gib} GB</dd></div></dl>${dt.fault && html`<p class="small"><b>What is wrong:</b> ${dt.fault}</p>`}</div></li>`}
      ${rl && html`<li class="fx-card"><video src=${m.relip} poster=${String(m.relip).replace(/\.mp4(\?.*)?$/, ".webp")} controls playsinline preload="none" aria-label="The invented woman's clip with a Spanish voice and her mouth redrawn by LatentSync"><//><div><h3>New voice, then LatentSync, into Spanish</h3><dl class="db-facts">
        <div><dt>Asked</dt><dd>“${rl.translation}”</dd></div><div><dt>Whisper heard</dt><dd>“${rl.heard}”</dd></div><div><dt>Words</dt><dd>${werWord(rl.wer)}</dd></div>
        <div><dt>Run</dt><dd>${rl.model}, ${secs(rl.seconds)}, peak ${rl.peak_vram_gib} GB</dd></div></dl>${rl.fault && html`<p class="small"><b>What is wrong:</b> ${rl.fault}</p>`}</div></li>`}
      ${vd && html`<li class="fx-card"><video src=${m.voice_dub} poster=${String(m.voice_dub).replace(/\.mp4(\?.*)?$/, ".webp")} controls playsinline preload="none" aria-label="The invented woman's clip with a Spanish voice laid on it"><//><div><h3>New voice only, into Spanish</h3><dl class="db-facts">
        <div><dt>Source said</dt><dd>“${vd.source_heard}”</dd></div><div><dt>Asked</dt><dd>“${vd.translation}” (${vd.translated_by})</dd></div><div><dt>Whisper heard</dt><dd>“${vd.heard}”</dd></div><div><dt>Words</dt><dd>${werWord(vd.wer)}</dd></div>
        <div><dt>Voice</dt><dd>${vd.model}; likeness to the source voice ${vd.voice_similarity_to_source}</dd></div><div><dt>Run</dt><dd>${secs(vd.seconds)}, peak ${vd.peak_vram_gib} GB, stretched ×${vd.tempo}</dd></div></dl><p class="small"><b>What is wrong:</b> the mouth still moves to the English words.</p></div></li>`}
      ${cl && html`<li class="fx-card db-aud"><div><h3>A designed voice, cloned</h3><figure><figcaption>Designed from words</figcaption><audio controls preload="none" src=${m.clone_reference}></audio></figure><figure><figcaption>The clone, a new line</figcaption><audio controls preload="none" src=${m.clone}></audio></figure></div><div><dl class="db-facts">
        <div><dt>Described as</dt><dd>${cl.design}</dd></div><div><dt>Likeness</dt><dd>${cl.similarity} to the designed voice; ${cl.similarity_to_a_different_voice} to a stock voice on the same line (${cl.encoder})</dd></div><div><dt>Words</dt><dd>${werWord(cl.wer)}</dd></div><div><dt>Consent stored</dt><dd>${cl.consent && cl.consent.consent}: ${cl.consent && cl.consent.meaning}</dd></div></dl></div></li>`}
      ${vo && html`<li class="fx-card db-aud"><div><h3>Voiceover on a Music 3 score</h3><figure><figcaption>Mastered mix</figcaption><audio controls preload="none" src=${m.voiceover}></audio></figure></div><div><table class="db-table"><tbody>${masterChecks(vo.report).map((c) => html`<tr key=${c.k}><th scope="row">${c.label}</th><td>${c.value}</td><td class=${c.ok ? "db-ok" : "db-bad"}>${c.ok ? "Pass" : "Fail"}</td></tr>`)}</tbody></table>
        <p class="small">Voice: ${vo.voice.model} (${vo.voice.speaker}), ${werWord(vo.voice.wer)}. Re-measured after: ${db(vo.remeasured.lufs, "LUFS")}, ${db(vo.remeasured.true_peak, "dBTP")}.</p></div></li>`}
    </ol>
  </section>`;
}

export function Dub() {
  const [d, setD] = useState(null), [clips, setClips] = useState([]), [err, setErr] = useState("");
  const load = () => { setErr(""); api("/api/dub/models").then(setD).catch((e) => setErr(said(e))); api("/api/dub/clips").then((r) => setClips(r.clips || [])).catch(() => {}); };
  useEffect(load, []);
  if (err) return html`<div class="fx"><p class="fx-err" role="alert">${err}</p><button class="btn" onClick=${load}>Try again</button></div>`;
  if (!d) return html`<div class="fx"><${FxSkeleton} label="Reading the dubbing models and your clips."/></div>`;
  return html`<div class="fx db"><${Hero} p=${d.proof}/><${DubForm} d=${d} clips=${clips}/><${Clone} d=${d}/><${Voiceover} d=${d}/><${Proof} p=${d.proof}/></div>`;
}
