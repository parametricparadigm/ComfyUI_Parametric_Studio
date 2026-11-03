// The Commercials page: a library of TV-spot genres as templates, a brief-to-script writer, and the generator. Every rendered spot shown here is a real run that a person looked at shot by shot; its flaws are labelled, and nobody has listened to the audio.
import { useEffect, useRef, useState } from "preact/hooks";
import { html, api, post, smooth } from "./common.js";
import { said } from "./fx.js";
import { GROUPS, pick, segments, runBody, statusWord, heardWord, totals, clock, secs, classWord } from "./commercials_logic.js";

const media = (f) => `commercials/${f}`;
const Tag = ({ w }) => html`<span class=${"fx-tag " + w[1]}>${w[0]}</span>`;
const CAM = { locked: "Locked off", dolly_in: "Dolly in", dolly_out: "Dolly out", orbit_left: "Orbit left", orbit_right: "Orbit right", crane_up: "Crane up", crane_down: "Crane down", pan_left: "Pan left", pan_right: "Pan right", tilt_up: "Tilt up", tracking: "Tracking", handheld: "Handheld" };
const REF = { cast: "From the cast frame", product: "From the product frame", none: "Drawn fresh" };

function Bar({ script }) {
  const seg = segments(script);
  return html`<div class="cm-bar" role="img" aria-label=${`Timing of the ${script.length} second spot: ${seg.length} parts`}>
    ${seg.map((x) => html`<span key=${x.id} class=${"is-" + x.kind} style=${{ flexGrow: x.share }} title=${`${x.id}: ${secs(x.seconds)}`}><b>${x.n || (x.kind === "end" ? "End" : "Card")}</b><small>${secs(x.seconds)}</small></span>`)}
  </div>`;
}

function Hero({ genres, proof, cur, setCur }) {
  const t = totals(genres, proof); const spots = (proof.spots || []).filter((s) => s.video); const sp = spots.find((s) => s.id === cur) || spots[0];
  return html`<section class="cm-hero film" aria-labelledby="cm-title">
    <p class="cm-eyebrow">TV spots. Every brand, product and person invented.</p>
    <h2 id="cm-title">On air</h2>
    ${sp ? html`<figure class="cm-screen">
        <video key=${sp.video} controls playsinline preload="metadata" poster=${media(sp.poster)} src=${media(sp.video)} aria-label=${`${sp.title}, a ${sp.length} second ${sp.genre_title}`}></video>
        <figcaption><b>${sp.title}</b> <span>${sp.genre_title}, ${sp.length} s</span> <${Tag} w=${statusWord(sp.status)}/></figcaption>
      </figure>
      <div class="cm-pills" role="group" aria-label="Pick a rendered spot">${spots.map((s) => html`<button key=${s.id} type="button" aria-pressed=${s.id === sp.id} onClick=${() => setCur(s.id)}>${s.genre_title}</button>`)}</div>`
    : html`<p class="cm-empty">No spot has been rendered and reviewed on this machine yet, so there is nothing to play. The library and the generator below work now.</p>`}
    <dl class="cm-stats"><div><dd>${t.genres}</dd><dt>genres, each a full template</dt></div><div><dd>${t.rendered}</dd><dt>spots rendered and reviewed here</dt></div><div><dd>${t.shots}</dd><dt>shots looked at, frame by frame</dt></div><div><dd>0</dd><dt>words painted by an image model</dt></div></dl>
    <p class="cm-honest"><b>Nobody has listened yet.</b> Every spot's sound was measured: loudness by ffmpeg, the words by Whisper. A person looked at every shot and wrote down what's wrong with it, below. All the text on screen, the "AI-generated" label and the parody cards are set by ffmpeg from a font.</p>
  </section>`;
}

function Spot({ sp }) {
  const [open, setOpen] = useState(false); const a = sp.audio || {};
  return html`<li class=${"cm-spot is-" + sp.status} id=${"spot-" + sp.id}>
    <figure class="cm-spotpic">${sp.video ? html`<video controls playsinline preload="none" poster=${media(sp.poster)} src=${media(sp.video)} aria-label=${sp.title}></video>` : html`<div class="cm-nomedia">No video: the run failed.</div>`}</figure>
    <div class="cm-spottext">
      <header><span class="fx-kick">${sp.genre_title} · ${sp.length} s · ${sp.tone}</span><h3>${sp.title}</h3></header>
      <div class="fx-row"><${Tag} w=${statusWord(sp.status)}/><${Tag} w=${heardWord(a)}/><span class="fx-tag warn">Not listened to by a person</span></div>
      <p>${sp.verdict}</p>
      ${(sp.flaws || []).length > 0 && html`<ul class="cm-flaws" aria-label="Flaws">${sp.flaws.map((f) => html`<li key=${f}>${f}</li>`)}</ul>`}
      <dl class="cm-facts">
        <div><dt>Loudness</dt><dd>${a.lufs != null ? `${a.lufs} LUFS` : "-"}</dd></div>
        <div><dt>True peak</dt><dd>${a.true_peak_db != null ? `${a.true_peak_db} dB` : "-"}</dd></div>
        <div><dt>Work</dt><dd>${sp.seconds_of_work ? `${Math.round(sp.seconds_of_work / 60)} min` : "-"}</dd></div>
        <div><dt>Peak VRAM</dt><dd>${sp.my_peak_gib ? `${sp.my_peak_gib} GiB` : "-"}</dd></div>
      </dl>
      <p class="small">Voice: ${sp.voice_model}${sp.voice ? ` (${sp.voice})` : ""}. Script: ${sp.writer}. Seeds and graphs are kept with the run.</p>
      <button type="button" class="cm-more" aria-expanded=${open} onClick=${() => setOpen(!open)}>${open ? "Hide" : "Show"} every shot and what Whisper heard</button>
    </div>
    ${open && html`<div class="cm-shots">
      <ol>${(sp.shots || []).map((s, i) => html`<li key=${s.id + i} class=${"is-" + (s.status || "ok")}>${s.frame ? html`<img src=${media(s.frame)} alt=${`Frames from shot ${i + 1}: ${s.id}`} loading="lazy"/>` : html`<div class="cm-nomedia">Not published</div>`}<div><b>${i + 1}. ${s.id}</b>${s.status === "flawed" && html` <span class="fx-tag warn">Flawed</span>`}<p class="small">${s.note}</p></div></li>`)}</ol>
      ${a.heard && html`<blockquote class="cm-heard"><b>Whisper heard:</b> ${a.heard}</blockquote>`}
      ${sp.sheet && html`<a class="btn small" href=${media(sp.sheet)} target="_blank" rel="noopener">The contact sheet, full size</a>`}
    </div>`}
  </li>`;
}

function Spots({ proof }) {
  const spots = proof.spots || []; if (!spots.length) return null;
  return html`<section aria-labelledby="cm-spots"><div class="cm-head"><h2 id="cm-spots">Rendered here</h2><p class="small">${proof.note || "Each spot is one real run on this machine, through the shared GPU gate, reviewed shot by shot."}</p></div>
    <ol class="cm-spotlist">${spots.map((s) => html`<${Spot} key=${s.id} sp=${s}/>`)}</ol></section>`;
}

function Template({ g }) {
  return html`<div class="cm-template">
    <div class="cm-tablewrap" tabindex="0" role="region" aria-label=${`Shot list for ${g.title}`}><table class="fx-table cm-beats"><thead><tr><th scope="col">Beat</th><th scope="col">In</th><th scope="col">Shot</th><th scope="col">Voice-over</th><th scope="col">On screen</th></tr></thead>
      <tbody>${g.beats.map((b) => html`<tr key=${b.id}><th scope="row">${b.id}</th><td>${b.in.join(", ")} s</td><td>${b.shot}<small>${CAM[b.camera] || b.camera} · ${b.frame.replace("_", " ")} · ${REF[b.ref]}</small><small>Sound: ${b.sfx}</small></td><td>${b.vo || html`<i>(no words)</i>`}${b.rate && b.rate !== 1 ? html`<small>Read ${b.rate}x fast</small>` : ""}</td><td>${b.super || ""}${b.legal ? html`<small>Legal: ${b.legal}</small>` : ""}</td></tr>`)}</tbody></table></div>
    <dl class="cm-meta"><div><dt>End card</dt><dd>${g.end_card.lines.join(" / ")}</dd></div><div><dt>Legal line</dt><dd>${g.legal}</dd></div><div><dt>Voice-over</dt><dd>${g.vo.style}</dd></div><div><dt>Music</dt><dd>${g.music.style}. ${g.music.mood} ${g.music.bpm} BPM.</dd></div><div><dt>Look</dt><dd>${g.look}</dd></div></dl>
  </div>`;
}

function Genre({ g, done, onUse }) {
  const [open, setOpen] = useState(false);
  return html`<li class=${"cm-genre" + (g.parody ? " is-parody" : "")} style=${{ "--ink": g.type.accent, "--card": g.type.card }}>
    <div class="cm-swatch" aria-hidden="true"><span>${g.group}</span></div>
    <h3>${g.title}</h3>
    <p>${g.pitch}</p>
    <div class="fx-row">${g.lengths.map((l) => html`<span key=${l} class="fx-tag">${l} s</span>`)}${g.parody && html`<span class="fx-tag warn">Parody card</span>`}${done && html`<span class="fx-tag ok">Rendered here</span>`}</div>
    <p class="small"><b>Voice:</b> ${g.vo.style}. <b>Music:</b> ${g.music.style}.</p>
    <div class="fx-row"><button type="button" class="btn small" onClick=${() => onUse(g.id)}>Use this genre</button><button type="button" class="btn small" aria-expanded=${open} onClick=${() => setOpen(!open)}>${open ? "Hide" : "Show"} the shot list</button></div>
    ${open && html`<${Template} g=${g}/>`}
  </li>`;
}

function Library({ genres, proof, onUse }) {
  const [group, setGroup] = useState("All"), [q, setQ] = useState(""); const rows = pick(genres, group, q); const done = new Set((proof.spots || []).filter((s) => s.status !== "failed").map((s) => s.genre));
  return html`<section aria-labelledby="cm-lib"><div class="cm-head"><h2 id="cm-lib">The genre library</h2><p class="small">Each genre is a template: beats with a shot, a camera move and its sound; what a 15, 30 or 60 second cut keeps; the voice-over style, the music, the end card and the legal line.</p></div>
    <div class="cm-tools"><div class="cm-chips" role="group" aria-label="Which genres">${GROUPS.map((x) => html`<button key=${x} type="button" aria-pressed=${x === group} onClick=${() => setGroup(x)}>${x}</button>`)}</div>
      <label class="fx-lab cm-search">Search<input class="fx-in" type="search" value=${q} onInput=${(e) => setQ(e.target.value)} placeholder="perfume, comedy, car..."/></label></div>
    ${rows.length ? html`<ol class="cm-genres">${rows.map((g) => html`<${Genre} key=${g.id} g=${g} done=${done.has(g.id)} onUse=${onUse}/>`)}</ol>` : html`<p class="small">No genre fits that search.</p>`}
  </section>`;
}

function Script({ s, setS }) {
  const line = (i, v) => setS({ ...s, writer: "edited on the page", beats: s.beats.map((b, j) => (i === j ? { ...b, vo: v } : b)) });
  return html`<div class="cm-script">
    <${Bar} script=${s}/>
    <p class="small">${s.length} s spot · ${s.beats.length} shots · end card ${secs(s.end_card.seconds)}${s.parody_card ? ` · parody card ${secs(s.parody_card.seconds)}` : ""} · about ${s.vo_seconds} s of voice-over for ${s.vo_room} s of picture${s.fits ? "" : " (too long: the cut will read it faster, or refuse)"} · written by ${s.writer}</p>
    <ol class="cm-lines">${s.beats.map((b, i) => html`<li key=${b.id}>
      <div class="cm-when"><b>${i + 1}</b><span>${clock(b.start)}</span><small>${secs(b.seconds)}${b.parts && b.parts.length > 1 ? ", long take in two parts" : ""}</small></div>
      <div class="cm-what"><p>${b.shot}</p><p class="small">${CAM[b.camera] || b.camera} · ${b.frame.replace("_", " ")} · ${REF[b.ref]} · Sound: ${b.sfx}</p>
        <label class="fx-lab">Voice-over${b.rate !== 1 ? ` (read ${b.rate}x fast)` : ""}<textarea class="fx-in" rows="2" maxlength="400" value=${b.vo} onInput=${(e) => line(i, e.target.value)}></textarea></label>
        ${(b.super || b.legal) && html`<p class="small">${b.super && html`<b>On screen:</b> ${b.super} `}${b.legal && html`<b>Legal:</b> ${b.legal}`}</p>`}</div>
    </li>`)}
    <li class="cm-endline"><div class="cm-when"><b>End</b><span>${clock(s.end_card.start)}</span></div><div class="cm-what"><p><b>${s.end_card.lines.join(" / ")}</b></p><p class="small">Voice-over: ${s.end_card.vo || "none"} · Legal: ${s.legal}</p></div></li>
    ${s.parody_card && html`<li class="cm-endline is-parody"><div class="cm-when"><b>Card</b><span>${clock(s.parody_card.start)}</span></div><div class="cm-what"><p><b>PARODY</b> · ${s.parody_card.lines.join(" ")}</p><p class="small">Voice-over: ${s.parody_card.vo}</p></div></li>`}</ol>
  </div>`;
}

function Maker({ d, gid, setGid }) {
  const g = d.genres.find((x) => x.id === gid) || d.genres[0];
  const [brief, setBrief] = useState({}), [length, setLength] = useState(30), [tone, setTone] = useState(""), [engine, setEngine] = useState("kokoro"), [rewrite, setRewrite] = useState(false);
  const [s, setS] = useState(null), [steps, setSteps] = useState([]), [err, setErr] = useState(""), [busy, setBusy] = useState(false), [run, setRun] = useState(null); const t = useRef();
  useEffect(() => { setBrief({}); setS(null); setErr(""); setLength(g.lengths.includes(30) ? 30 : g.lengths[0]); setTone(""); }, [g.id]);
  useEffect(() => () => clearInterval(t.current), []);
  const write = async () => { setErr(""); setBusy(true); try { const r = await post("/api/commercials/script", { genre: g.id, brief, length, tone: tone || undefined, rewrite, engine }); setS(r.script); setSteps(r.steps); } catch (e) { setErr(said(e)); setS(null); } setBusy(false); };
  const make = async () => {
    setErr(""); clearInterval(t.current);
    try {
      const r = await post("/api/commercials/run", runBody(g, brief, s, engine)); const f = async () => { const x = await api(`/api/commercials/runs/${r.run}`); setRun(x); if (["done", "error", "cancelled", "interrupted"].includes(x.status)) clearInterval(t.current); };
      await f(); t.current = setInterval(() => f().catch(() => {}), 3000);
    } catch (e) { setErr(said(e)); }
  };
  const live = run && !["done", "error", "cancelled", "interrupted"].includes(run.status); const ve = d.vo_engines[engine];
  return html`<section aria-labelledby="cm-make" id="cm-maker"><div class="cm-head"><h2 id="cm-make">Make one</h2><p class="small">Fill in what you like; an empty field takes the genre's example. Every name is checked against real brands, people, politicians, parties and medicines before anything is written.</p></div>
    <div class="cm-maker">
      <div class="fx-card cm-brief">
        <label class="fx-lab">Genre<select class="fx-in" value=${g.id} onChange=${(e) => setGid(e.target.value)}>${d.genres.map((x) => html`<option key=${x.id} value=${x.id}>${x.title}</option>`)}</select></label>
        <div class="cm-two"><fieldset class="cm-seg"><legend>Length</legend>${g.lengths.map((l) => html`<button key=${l} type="button" aria-pressed=${l === length} onClick=${() => setLength(l)}>${l} s</button>`)}</fieldset>
          <label class="fx-lab">Tone<select class="fx-in" value=${tone} onChange=${(e) => setTone(e.target.value)}><option value="">The genre's own (${d.tones[g.tone].label})</option>${Object.entries(d.tones).filter(([k]) => k !== "as_written").map(([k, v]) => html`<option key=${k} value=${k}>${v.label}</option>`)}</select></label></div>
        ${Object.keys(g.fields).map((k) => html`<label key=${g.id + k} class="fx-lab">${g.labels[k]}<input class="fx-in" value=${brief[k] || ""} maxlength="400" placeholder=${g.fields[k]} onInput=${(e) => setBrief({ ...brief, [k]: e.target.value })}/></label>`)}
        <label class="fx-lab">Voice-over model<select class="fx-in" value=${engine} onChange=${(e) => setEngine(e.target.value)}>${Object.entries(d.vo_engines).map(([k, v]) => html`<option key=${k} value=${k}>${v.label} (${v.licence})</option>`)}</select></label>
        <p class="small">${ve.note} Licence: ${ve.licence}. About ${ve.peak_gib} GiB of VRAM.</p>
        <label class="cm-check"><input type="checkbox" checked=${rewrite} disabled=${!d.llm} onChange=${(e) => setRewrite(e.target.checked)}/> Let the local language model punch up the voice-over</label>
        ${!d.llm && html`<p class="small">The model on :8002 isn't up right now, so the template's words are used. The page never starts it.</p>`}
        <div class="fx-row"><button type="button" class="fx-go" disabled=${busy} onClick=${write}>${busy ? "Writing..." : "Write the script"}</button></div>
        <div aria-live="polite">${err && html`<p class="fx-err" role="alert">${err}</p>`}</div>
      </div>
      <div class="cm-out">
        ${s ? html`<${Script} s=${s} setS=${setS}/>
          <div class="fx-card"><h3>What runs</h3><ol class="cm-steps">${steps.map((x) => html`<li key=${x.id}><b>${x.label}</b> <span class="small">${x.model}</span></li>`)}</ol>
            <div class="fx-row"><button type="button" class="fx-go" disabled=${live} onClick=${make}>${live ? "Rendering..." : "Make the commercial"}</button><span class="small">Runs on the recipe queue. Expect about a minute per shot once the models are loaded.</span></div></div>`
        : html`<div class="cm-placeholder"><p>The script, the shot list and the timing appear here.</p><${Template} g=${g}/></div>`}
        ${run && html`<div class="fx-card" aria-live="polite"><h3>${run.status === "done" ? "Done" : run.status === "error" ? "It stopped" : "Rendering"}</h3>
          <ol class="cm-live">${run.steps.map((x) => html`<li key=${x.id} class=${"is-" + x.status}><b>${x.label}</b> <span>${x.status}${x.seconds ? ", " + clock(x.seconds) : ""}</span>${x.note && html`<small>${x.note}</small>`}${x.error && html`<small class="fx-err">${x.error}</small>`}</li>`)}</ol>
          ${run.error && html`<p class="fx-err" role="alert">${run.error}</p>`}
          ${run.status === "done" && run.output && html`<video class="cm-result" controls playsinline src=${run.output.url}></video><a class="btn" href=${run.output.url} download>Download the spot</a>`}</div>`}
      </div>
    </div></section>`;
}

function Rules({ d }) {
  return html`<section aria-labelledby="cm-rules" class="cm-rulesec"><div class="cm-head"><h2 id="cm-rules">Hard rules, in code</h2><p class="small">They run on every brief, every script and every rewrite, and tests hold them. A refused brief says which rule and why.</p></div>
    <div class="cm-rules"><ol class="cm-rulelist">${d.rules.map((r) => html`<li key=${r}>${r}</li>`)}</ol>
      <div class="fx-card"><h3>Models and licences</h3><ul class="cm-lic">${d.models.map((m) => html`<li key=${m.name}><span class=${"cm-class is-" + m.licence_class}>${classWord(m.licence_class)}</span><b>${m.name}</b><small>${m.licence}. ${m.does}${m.note ? " " + m.note : ""}</small></li>`)}</ul></div></div></section>`;
}

export function Commercials() {
  const [d, setD] = useState(null), [proof, setProof] = useState({ spots: [] }), [err, setErr] = useState(""), [cur, setCur] = useState(null), [gid, setGid] = useState("pharma");
  const load = () => { setErr(""); api("/api/commercials/genres").then(setD).catch((e) => setErr(said(e))); api("/api/commercials/proof").then(setProof).catch(() => {}); };
  useEffect(load, []);
  useEffect(() => { document.body.classList.add("on-commercials"); return () => document.body.classList.remove("on-commercials"); }, []);
  const use = (id) => { setGid(id); const el = document.getElementById("cm-maker"); if (el) el.scrollIntoView({ behavior: smooth(), block: "start" }); };
  if (err) return html`<div class="fx"><p class="fx-err" role="alert">${err}</p><button type="button" class="btn" onClick=${load}>Try again</button></div>`;
  if (!d) return html`<div class="fx"><p class="small" role="status">Loading the genres...</p></div>`;
  return html`<div class="fx cm"><${Hero} genres=${d.genres} proof=${proof} cur=${cur} setCur=${setCur}/><${Spots} proof=${proof}/><${Library} genres=${d.genres} proof=${proof} onUse=${use}/><${Maker} d=${d} gid=${gid} setGid=${setGid}/><${Rules} d=${d}/></div>`;
}
