/* Live Director: speak or type, and the Shot Board's plan fills in live. Speech uses the browser's own recognition where it exists; text always works. This page has no way to start a render. */
import { useEffect, useRef, useState } from "preact/hooks";
import { html, api, post } from "./common.js";
import { applyOps, fromSaved, KEY, toSaved } from "./director_logic.js";
import { FxHero, FxMosaic } from "./fx.js";

/* The Shot Board's own example shoot, the same four takes it shows on a first visit. Our renders, labelled as ours. */
const TAKES = [["v_h3_chef", "The source clip"], ["reshoot_orbit_take", "Reshoot: orbit right"], ["recast_chef", "Recast"], ["vfx_flood", "VFX: water"]];

const read = () => { try { return JSON.parse(localStorage.getItem(KEY)) || {}; } catch { return {}; } };
const write = (board) => { try { localStorage.setItem(KEY, JSON.stringify(toSaved(read(), board))); return true; } catch { return false; } };
const Speech = () => window.SpeechRecognition || window.webkitSpeechRecognition || null;

export function LiveDirector() {
  const [st, setSt] = useState(null), [board, setBoard] = useState(() => fromSaved(read())), [log, setLog] = useState([]), [text, setText] = useState(""), [busy, setBusy] = useState(false), [err, setErr] = useState(""), [listening, setListening] = useState(false), [heard, setHeard] = useState(""), [micErr, setMicErr] = useState("");
  const rec = useRef(null), logRef = useRef([]), boardRef = useRef(board); logRef.current = log; boardRef.current = board; const has = !!Speech();
  useEffect(() => { api("/api/director/status").then(setSt).catch((e) => setErr(e.message)); return () => { if (rec.current) rec.current.abort(); }; }, []);
  const say = async (words) => {
    const t = String(words || "").trim(); if (!t) return; setBusy(true); setErr("");
    try {
      const r = await post("/api/director/turn", { text: t, history: logRef.current.slice(-6) });
      const next = applyOps(boardRef.current, r.ops); boardRef.current = next; setBoard(next); write(next); setLog((l) => [...l, { role: "user", text: t }, { role: "assistant", text: r.say, by: r.by }]);
      if (st) setSt({ ...st, model: r.by === "model", why: r.by === "model" ? "" : r.offline_why });
    } catch (e) { setErr(e.message); }
    setBusy(false);
  };
  const toggleMic = () => {
    if (listening) { rec.current && rec.current.stop(); return; }
    const S = Speech(); if (!S) return; setMicErr(""); const r = new S(); r.continuous = true; r.interimResults = true; r.lang = navigator.language || "en-US";
    r.onresult = (e) => { let live = ""; for (let i = e.resultIndex; i < e.results.length; i++) { const x = e.results[i]; if (x.isFinal) say(x[0].transcript); else live += x[0].transcript; } setHeard(live); };
    r.onerror = (e) => { setMicErr(e.error === "not-allowed" || e.error === "service-not-allowed" ? "The browser was not allowed to use your microphone. You can type instead." : e.error === "no-speech" ? "" : `Speech recognition stopped (${e.error}). You can type instead.`); };
    r.onend = () => { setListening(false); setHeard(""); };
    rec.current = r; try { r.start(); setListening(true); } catch { setMicErr("Speech recognition would not start. You can type instead."); }
  };
  const remove = (job) => { const n = applyOps(board, [{ op: "remove", job }]); setBoard(n); write(n); };
  const names = st ? st.transforms : {}; const chosen = Object.keys(board.picked).filter((k) => board.picked[k] && names[k]);
  return html`<div class="fx">
    <${FxHero} kicker="What it plans" line="Say a job. It lands on the board." lede="Every job and camera move Comfy Prime can put on your Shot Board, from what this studio knows today. The pictures are the Shot Board's own example shoot."
      stats=${st ? [[Object.keys(st.transforms || {}).length, "jobs it can plan"], [(st.cameras || []).length, "camera moves for a reshoot"]] : null}
      art=${html`<${FxMosaic} items=${TAKES.map(([id, label]) => ({ src: `showcase/${id}.webp`, label }))}/>`} note="Our renders from the Shot Board example, not yours.">
      ${st && html`<ul class="ld-know" aria-label="Jobs it knows">${Object.values(st.transforms || {}).map((n) => html`<li key=${n}>${n}</li>`)}</ul>`}<//>
    ${st && !st.model && html`<div class="fx-note warn" role="status"><b>Rules are listening, not the language model</b><p>${st.why}</p></div>`}
    ${err && html`<div class="fx-note bad" role="alert"><p>${err}</p></div>`}
    <div class="fx-two">
      <section class="fx-card" aria-label="Talk to Comfy Prime"><span class="fx-kick">You and Comfy Prime</span>
        <div class="ld-log" role="log" aria-live="polite" tabindex="0">${log.length === 0 && !heard && html`<p class="small">Try: "Orbit it, then make it night, and a dolly in for the reshoot."</p>`}${log.map((m, i) => html`<p key=${i} class=${"ld-msg " + m.role}><b>${m.role === "user" ? "You" : "Comfy Prime"}</b> ${m.text}${m.by === "rules" ? html` <span class="fx-tag">keyword rules</span>` : ""}</p>`)}${heard && html`<p class="ld-msg user ld-live"><b>Hearing</b> ${heard}</p>`}</div>
        <form class="ld-say" onSubmit=${(e) => { e.preventDefault(); say(text); setText(""); }}><label class="fx-lab" for="ld-in">Type it</label><input id="ld-in" class="fx-in" value=${text} maxlength="800" onInput=${(e) => setText(e.target.value)} autocomplete="off"/><button class="fx-go" type="submit" disabled=${busy || !text.trim()}>${busy ? "Listening" : "Send"}</button></form>
        ${has ? html`<button class=${"btn ld-mic" + (listening ? " on" : "")} type="button" aria-pressed=${listening} onClick=${toggleMic}>${listening ? "Stop listening" : "Talk instead"}</button>` : html`<p class="small" role="status">This browser has no speech recognition, so typing is the way in.</p>`}
        ${micErr && html`<p class="fx-warn" role="alert">${micErr}</p>`}
        ${has && html`<p class="small">Talking uses your browser's own speech recognition, and some browsers send your voice to their maker's servers to do it. Typing stays on this machine.</p>`}</section>
      <section class="fx-card ld-board" aria-label="The Shot Board plan" aria-live="polite"><span class="fx-kick">The Shot Board</span>
        <h2>${chosen.length} ${chosen.length === 1 ? "job" : "jobs"} planned</h2>
        ${chosen.length > 0 ? html`<ol class="ld-jobs">${chosen.map((k, i) => html`<li key=${k}><i>${i + 1}</i><b>${names[k]}</b>${k === "reshoot" && html`<small>${board.camera.replace(/_/g, " ")}</small>`}<button class="btn small" type="button" aria-label=${"Take off " + names[k]} onClick=${() => remove(k)}>Take off</button></li>`)}</ol>` : html`<p class="small">Nothing yet. Say a job and it lands here.</p>`}
        <dl class="ld-facts"><dt>Scene</dt><dd>${board.scene || "not said yet"}</dd></dl>
        <div class="fx-note"><b>Nothing has rendered</b><p>This only plans the board. To render, add your clip on the Shot Board and press its start button. That click is the only thing that spends your GPU.</p></div>
        <a class="fx-go" href="#shots">Open the Shot Board</a></section></div>
  </div>`;
}
