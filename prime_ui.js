/* The dock: Comfy Prime and the crew, with faces and voices. Remembers your name, answers aloud in the character's own voice, listens through a push-to-talk mic, can drive the studio through a short list of safe actions, and never starts a render by itself.
   Voices come from a local speech server through /api/voice (nothing leaves this machine). The face moves on real audio events; the moving face is a loop, not lip sync. */
import { useState, useEffect, useRef } from "preact/hooks";
import { html, api } from "./common.js";
export const PRIME = { id: "master", name: "Comfy Prime", tier: "master", family: "master", portrait: "crew/master.webp" };
const FAMILY = { master: "knows every family", "text-encoders": "Text encoders", vae: "VAEs", vision: "Vision encoders", lora: "LoRAs", controlnet: "ControlNets", upscaler: "Upscalers", "wan-version-not-stated": "Wan, version not stated" };
export const familyLabel = (m) => FAMILY[m.id] || String(m.family || "").replace(/-/g, " ");
export const faceOf = (m) => m.portrait || `crew/${m.id}.webp`;
const hashOf = (s) => [...String(s)].reduce((h, c) => (h * 31 + c.charCodeAt(0)) >>> 0, 7);
const noMotion = () => { try { return matchMedia("(prefers-reduced-motion: reduce)").matches; } catch { return false; } };

/* Sentences go to the speech server one at a time, so the first words play quickly however long the answer is. */
export const chunks = (text) => {
  const clean = String(text || "").replace(/[`*_#>~]/g, "").replace(/\s+/g, " ").trim().slice(0, 900); const out = [];
  for (const s of clean.split(/(?<=[.!?])\s+/)) { if (!s) continue; if (out.length && out[out.length - 1].length < 40) out[out.length - 1] += " " + s; else out.push(s); }
  return out;
};
/* speechSynthesis may use a cloud service: some browser voices (for example Chrome's "Google" voices, localService false) send the text to their maker's servers. It runs only when no local speech server answers, and a voice on this device is chosen when there is one. */
const browserVoice = (member) => { const all = speechSynthesis.getVoices().filter((v) => /^en/i.test(v.lang)); const local = all.filter((v) => v.localService); const pool = local.length ? local : all; return pool.length ? pool[hashOf(member.id) % pool.length] : null; };

/* One speaker for the whole page: plays a member's lines, reports the real start and stop of the sound and how loud it is. */
function makeSpeaker(onSpeaking, onLevel) {
  let run = 0, el = null, meter = null, raf = 0, wake = null;
  const quiet = () => { cancelAnimationFrame(raf); raf = 0; onLevel(0); };
  const stop = () => { run++; if (el) { el.pause(); el.removeAttribute("src"); } if (wake) { wake(); wake = null; } try { if ("speechSynthesis" in window) speechSynthesis.cancel(); } catch {} quiet(); onSpeaking(null); };
  const tick = () => { if (!meter) return; const b = new Uint8Array(meter.fftSize); meter.getByteTimeDomainData(b); let e = 0; for (const v of b) e += (v - 128) * (v - 128); onLevel(Math.min(1, Math.sqrt(e / b.length) / 42)); raf = requestAnimationFrame(tick); };
  const wire = async () => {           // loudness meter: if the browser will not let audio run yet, the voice still plays, just without the meter
    if (meter !== null || noMotion()) return; meter = false;
    try { const C = window.AudioContext || window.webkitAudioContext; const c = new C(); await Promise.race([c.resume(), new Promise((r) => setTimeout(r, 300))]); if (c.state !== "running") { c.close(); return; } const a = c.createAnalyser(); a.fftSize = 512; c.createMediaElementSource(el).connect(a); a.connect(c.destination); meter = a; } catch {}
  };
  const playBlob = (blob, member, mine) => new Promise(async (res) => {
    el = el || new Audio(); await wire(); if (mine !== run) return res(false);
    const url = URL.createObjectURL(blob); const done = (ok) => { URL.revokeObjectURL(url); quiet(); wake = null; res(ok); };
    wake = () => done(false); el.onended = () => done(true); el.onerror = () => done(false);
    el.onplaying = () => { if (mine === run) { onSpeaking(member.id); if (meter && !raf) tick(); } };
    el.src = url; el.play().catch(() => done(false));
  });
  const browser = (text, member, mine) => new Promise((res) => {
    if (!("speechSynthesis" in window)) return res(false);
    try { const u = new SpeechSynthesisUtterance(text); const v = browserVoice(member); if (v) { u.voice = v; u.lang = v.lang; } const h = hashOf(member.id); u.pitch = 0.75 + (h % 60) / 100; u.rate = 0.92 + (h % 20) / 100;
      u.onstart = () => { if (mine === run) onSpeaking(member.id); }; u.onend = u.onerror = () => res(true); speechSynthesis.speak(u); } catch { res(false); }
  });
  const fetchLine = (text, member) => fetch("/api/voice/tts", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text, member: member.id }) }).then((r) => { if (!r.ok) throw new Error(String(r.status)); return r.blob(); });
  const say = async (text, member) => {
    stop(); const mine = run, parts = chunks(text); if (!parts.length) return; let useBrowser = false, next = fetchLine(parts[0], member);
    for (let i = 0; i < parts.length && mine === run; i++) {
      let blob = null; if (!useBrowser) { try { blob = await next; } catch { useBrowser = true; } }
      if (mine !== run) return;
      if (blob) { if (i + 1 < parts.length) { next = fetchLine(parts[i + 1], member); next.catch(() => {}); } if (!(await playBlob(blob, member, mine)) && mine === run) useBrowser = true; }
      if (useBrowser && mine === run) { await browser(parts.slice(i).join(" "), member, mine); break; }
    }
    if (mine === run) { quiet(); onSpeaking(null); }
  };
  return { say, stop };
}

/* A face: the portrait, with its silent idle and talking loops on top when the member has them. Quiet shows idle; speech shows the talking loop, opened by the real loudness of the audio. */
export function Face({ member, speaking, className = "" }) {
  const talk = useRef(null); const m = member.motion; const [broken, setBroken] = useState(false);
  useEffect(() => { setBroken(false); }, [member.id]);
  useEffect(() => { const t = talk.current; if (!t) return; if (speaking) { t.currentTime = 0; t.play().catch(() => {}); } else t.pause(); }, [speaking, m && m.talk]);
  const initials = member.name.split(/[\s-]+/).map((w) => w[0]).join("").slice(0, 2);
  return html`<span class=${"face " + className + (speaking ? " speaking" : "")} aria-hidden="true">
    ${broken || member.portrait === null ? html`<span class="faceblank">${initials}</span>` : html`<img src=${faceOf(member)} alt="" onError=${() => setBroken(true)} draggable="false"/>`}
    ${m && !noMotion() && html`${m.idle && html`<video class="floop" key=${m.idle} src=${m.idle} muted loop autoplay playsinline preload="auto" disablepictureinpicture></video>`}<video class="floop ftalk" ref=${talk} key=${m.talk} src=${m.talk} muted loop playsinline preload="auto" disablepictureinpicture></video>`}</span>`;
}
const Bars = () => html`<span class="vbars" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i></span>`;
const Icon = ({ d }) => html`<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d=${d}/></svg>`;
const MIC = "M12 3a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3zM5 11a7 7 0 0 0 14 0M12 18v3", SOUND = "M11 5 6 9H3v6h3l5 4zM16 9a4 4 0 0 1 0 6M19 6a8 8 0 0 1 0 12", MUTED = "M11 5 6 9H3v6h3l5 4zM22 9l-6 6M16 9l6 6";
const REST = "The GPU is busy with a render, so I'm resting to give it room. Ask me again when it finishes.";
const NO_LLM = "No language model is running on this machine yet, so I can't look that up. The Models page shows the one that fits.";
const NOTES_REST = "I'm resting while the GPU renders, so here's the closest part of my notes, word for word.";
const NOTES_NONE = "No language model is running here, so here's the closest part of my notes, word for word.";
const ERR = "That took too long. The language model may be busy or asleep while a render runs. Try me again in a moment.";
const errLine = (er) => (er && er.status >= 400 && er.status < 500 ? er.message : ERR);

/* The first short answer is taken as the name, unless it is plainly not one. */
export const nameFrom = (text, explicitOnly) => {
  const t = text.trim(); const m = t.match(/\b(?:my name is|my name's|call me|i'?m|i am)\s+([\p{L}][\p{L}'-]*(?:\s+[\p{L}][\p{L}'-]*)?)/iu);
  if (m) { const n = m[1].replace(/\s+(please|thanks|thank you|and|but|so|by the way)\b.*$/i, "").trim(); return /^(a|an|the|not|here|fine|good|okay|ok|looking|trying|going|just|so|very|sorry)\b/i.test(n) ? null : n; }
  if (explicitOnly || /[?]/.test(t)) return null;
  const n = t.replace(/[.!,]+$/, "").trim(); const w = n.split(/\s+/);
  return w.length <= 2 && n.length <= 30 && /^[\p{L}][\p{L}' -]*$/u.test(n) && !/^(hi|hello|hey|yo|hiya|howdy|sup|thanks|thank you|ok|okay|yes|yeah|no|nope|sure|help|good|morning|evening|afternoon|what|why|how|who|go|start|stop|test|testing)\b/i.test(n) ? n : null;
};
/* Small talk answered on the spot, in character: it needs no model, so it works while the LLM sleeps. Notes-only specialists could not answer these otherwise. */
const smalltalk = (text, who, name) => {
  const t = text.trim().toLowerCase().replace(/[.!?,]+$/, ""); const you = name ? `, ${name}` : "";
  if (/^(hi|hello|hey|hiya|howdy|yo|good (morning|afternoon|evening))( there)?( \w+)?$/.test(t)) return `Hello${you}! What would you like to know?`;
  if (/^(thanks|thank you|cheers|great|nice|cool|awesome)( so much| very much| a lot)?$/.test(t)) return `Any time${you}.`;
  if (/^(who are you|what('s| is) your name|what do you (do|know)|what are you)$/.test(t)) return who.id === "master" ? `I'm Comfy Prime, your guide to this studio. Ask me how any model works, or tell me what you want to make.` : `I'm ${who.name}. I know ${familyLabel(who)}, and I only answer from my notes, with the exact quote so you can check me.`;
  if (/^(what('s| is) my name|who am i|do you know my name)$/.test(t)) return name ? `You're ${name}.` : `You haven't told me yet. What should I call you?`;
  return null;
};
const timed = (path, body, ms = 120000) => { const c = new AbortController(); const t = setTimeout(() => c.abort(), ms); return api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), signal: c.signal }).finally(() => clearTimeout(t)); };

export function PrimeDock({ goal }) {
  const [open, setOpen] = useState(false), [msgs, setMsgs] = useState([]), [text, setText] = useState(""), [busy, setBusy] = useState(false), [name, setName] = useState(null), [voice, setVoice] = useState(() => { try { return localStorage.getItem("prime_voice") !== "off"; } catch { return true; } });
  const [who, setWho] = useState(PRIME), [speaking, setSpeaking] = useState(null), [mic, setMic] = useState("idle"), [info, setInfo] = useState(null), [crew, setCrew] = useState({});   // mic: idle, listening, hearing
  const end = useRef(null), hist = useRef([]), root = useRef(null), rec = useRef(null), S = useRef({}), inputEl = useRef(null);
  const level = useRef(0);
  const speaker = useRef(null);
  if (!speaker.current) speaker.current = makeSpeaker(setSpeaking, (v) => { level.current = v; const r = root.current; if (r) { r.style.setProperty("--vox", v.toFixed(3)); } });
  const withFace = (m) => ({ ...(crew[m.id] || {}), ...m });
  const member = withFace(who);
  S.current = { name, voice, who: member, msgs, busy, goal };
  const push = (role, t, extra) => setMsgs((m) => [...m, { role, text: t, ...extra }]);
  const speak = (t, m) => { if (S.current.voice) speaker.current.say(t, m || S.current.who); };
  const refresh = () => api("/api/voice").then((v) => { setInfo(v); return v; }).catch(() => { const v = { tts: null, stt: null, llm: "unknown", gone: true }; setInfo(v); return v; });
  const line = (t, m, extra) => { const f = withFace(m || S.current.who); push("bot", t, { who: f, ...extra }); speak(t, f); };

  useEffect(() => { api("/api/user").then((u) => setName(u.name || "")).catch(() => setName("")); api("/api/crew").then((d) => setCrew(Object.fromEntries(d.members.map((m) => [m.id, m])))).catch(() => {}); refresh(); window.primeSpeak = (t) => speak(t, S.current.who); return () => { delete window.primeSpeak; }; }, []);
  useEffect(() => { if (!open) return; refresh(); const t = setInterval(refresh, 20000); return () => clearInterval(t); }, [open]);
  useEffect(() => { if (open && !msgs.length && name !== null) line(name ? `Welcome back, ${name}! What shall we make today?` : "Hi, I'm Comfy Prime, your guide to this studio. What should I call you?", PRIME); }, [open, name]);
  useEffect(() => { end.current && end.current.scrollIntoView({ block: "end" }); }, [msgs, busy]);
  useEffect(() => { try { localStorage.setItem("prime_voice", voice ? "on" : "off"); } catch {} if (!voice) speaker.current.stop(); }, [voice]);
  useEffect(() => { dispatchEvent(new CustomEvent("crew-state", { detail: { id: who.id, speaking, open } })); }, [who.id, speaking, open]);
  useEffect(() => { const f = (e) => talkTo(e.detail); addEventListener("crew-talk", f); return () => removeEventListener("crew-talk", f); }, [crew]);

  const talkTo = (d) => {
    setOpen(true); if (d.ask) { setTimeout(() => ask(d.ask, { id: "auto" }), 0); return; }
    const m = withFace(d); setWho(m); const you = S.current.name ? `Hi ${S.current.name}. ` : "";
    const noNotes = m.id !== "master" && m.has_dossier !== true ? " My own notes aren't written yet, so Comfy Prime answers for me." : "";
    line(m.id === "master" ? `${S.current.name ? S.current.name + ", " : ""}I'm back. What's next?` : `${you}${m.hello || `I'm ${m.name}.`}${noNotes}`, m);
  };
  const act = async (a) => {
    if (a.type === "navigate") location.hash = a.tab;
    else if (a.type === "set_goal" || a.type === "set_prompt") { location.hash = "create"; setTimeout(() => dispatchEvent(new CustomEvent("prime-action", { detail: a })), 60); }
    else if (a.type === "open_course") { location.hash = "university"; setTimeout(() => dispatchEvent(new CustomEvent("open-course", { detail: a.code })), 120); }
    else if (a.type === "remember_name") { try { const u = await timed("/api/user", { name: a.name }, 8000); setName(u.name); } catch {} }
    else if (a.type === "ask_crew") await ask(a.question, { id: "auto" }, true);
    else if (a.type === "propose_generate") push("bot", "Ready when you are.", { who: withFace(PRIME), button: "Make it" });
  };
  /* A question for the crew: /api/crew/ask answers only from the member's notes and returns the quotes it could verify. Nothing in the notes: Comfy Prime, who holds them all, takes over. */
  const ask = async (question, m, inner) => {
    if (!inner) setBusy(true);
    try {
      const v = await refresh();
      const r = await timed("/api/crew/ask", { who: m.id, question: question.slice(0, 600) }); const res = r.result || r; const f = withFace(r.member || m);
      const empty = res.supported === false && (res.problems || []).includes("No relevant chunks found");
      if (res.from_notes_only) { if (m.id === "auto") setWho(f); line(v.llm === "asleep" ? NOTES_REST : NOTES_NONE, f, { quotes: res.quotes || [] }); return true; }   // no model to think with: the closest passages, word for word
      if (empty && v.llm !== "awake" && f.id === "master") { line(v.llm === "asleep" ? REST : NO_LLM, f); return false; }
      if (empty && f.id !== "master") { const hand = "That isn't in my notes. Comfy Prime, can you take this one?"; push("bot", hand, { who: f }); if (S.current.voice) await speaker.current.say(hand, f); return ask(question, PRIME, true); }
      if (m.id === "auto") setWho(f);
      line(res.answer || "I can't back that up from my notes.", f, { quotes: res.quotes || [], unsupported: res.supported === false && !empty ? res.problems || [] : null });
      return true;
    } catch (er) { line(errLine(er), m.id === "auto" ? PRIME : m); return false; } finally { if (!inner) setBusy(false); }
  };
  const deliver = async (raw, typed) => {
    const t = raw.trim(); if (!t || S.current.busy) return; push("me", t); speaker.current.stop(); const { who: w, name: known } = S.current; const said = nameFrom(t, known !== "");
    if (said) { setBusy(true); try { const u = await timed("/api/user", { name: said }, 8000); setName(u.name); line(known === "" ? `Lovely to meet you, ${u.name}! Ask me anything about ComfyUI or the models, or tell me what you'd like to make.` : `Lovely to meet you, ${u.name}.`, w); } catch { line("I couldn't save that, sorry.", w); } setBusy(false); return; }
    const small = smalltalk(t, w, known); const v0 = (w.id !== "master" || !small) ? null : await refresh();
    if (small && (w.id !== "master" || (v0 && v0.llm !== "awake"))) { line(small, w); return; }
    if (w.id !== "master") { if (t.length < 3) { line("Could you say a little more?", w); return; } const ok = await ask(t, w); if (ok === false && typed) setText(t); return; }
    setBusy(true); hist.current.push({ role: "user", text: t });
    try {
      const v = v0 || await refresh();
      if (v.llm !== "awake" && v.llm !== "unknown") { if (/\?$|^(how|what|why|which|when|where|can|does|do|is|are|should|will)\b/i.test(t) && t.length >= 3) { await ask(t, w, true); return; } line(v.llm === "asleep" ? REST : NO_LLM, w); if (typed) setText(t); return; }
      const r = await timed("/api/prime", { text: t, history: hist.current.slice(-8), goal: S.current.goal || "" }); line(r.say, w); hist.current.push({ role: "assistant", text: r.say }); for (const a of r.actions) await act(a);
    } catch (er) { line(errLine(er), w); if (typed) setText(t); } finally { setBusy(false); }
  };
  const send = (e) => { e && e.preventDefault(); const t = text; setText(""); deliver(t, true); };

  /* ---- push to talk: hold the mic to speak, or tap once to start and again to stop ---- */
  const hear = async (blob) => {
    setMic("hearing");
    try { const fd = new FormData(); fd.append("file", blob, "speech." + (/ogg/.test(blob.type) ? "ogg" : /mp4/.test(blob.type) ? "m4a" : "webm")); const r = await api("/api/voice/stt", { method: "POST", body: fd }); setMic("idle"); const t = (r.text || "").trim(); if (t) deliver(t); else line("I didn't catch that. Try again?", S.current.who); }
    catch (er) { setMic("idle"); refresh(); push("bot", "The speech server didn't answer, so I couldn't hear that. Try again, or type.", { who: S.current.who }); }
  };
  const startRec = async () => {
    speaker.current.stop(); const st = rec.current = { want: true, chunks: [], t0: performance.now() }; setMic("listening");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
      if (!st.want) { stream.getTracks().forEach((t) => t.stop()); setMic("idle"); rec.current = null; return; }
      const type = ["audio/webm;codecs=opus", "audio/ogg;codecs=opus", "audio/mp4"].find((x) => MediaRecorder.isTypeSupported(x));
      const r = st.r = new MediaRecorder(stream, type ? { mimeType: type } : undefined); r.ondataavailable = (e) => { if (e.data && e.data.size) st.chunks.push(e.data); };
      r.onstop = () => { stream.getTracks().forEach((t) => t.stop()); rec.current = null; const b = new Blob(st.chunks, { type: r.mimeType || "audio/webm" }); if (b.size > 800 && performance.now() - st.began > 250) hear(b); else { setMic("idle"); push("bot", "That was too short for me to hear. Hold the mic a little longer.", { who: S.current.who }); } };
      r.start(); st.began = performance.now(); st.cap = setTimeout(() => { if (r.state === "recording") r.stop(); }, 30000);
    } catch (er) { rec.current = null; setMic("idle"); push("bot", window.isSecureContext ? "I can't reach a microphone. Check that the browser may use it, or type instead." : "Browsers only allow the mic on https or localhost. Open the studio that way, or type instead.", { who: S.current.who }); }
  };
  const stopRec = () => { const st = rec.current; if (!st) return; st.want = false; clearTimeout(st.cap); if (st.r && st.r.state === "recording") st.r.stop(); };
  /* webkitSpeechRecognition may use a cloud service (Chrome sends the audio to Google's servers), so it runs only when no local speech server answers, and only after you have said yes once. */
  const browserHear = () => {
    const R = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!R) { push("bot", "No speech server is running here and this browser can't transcribe by itself, so please type.", { who: S.current.who }); return; }
    let ok = false; try { ok = localStorage.getItem("prime_browser_stt") === "yes"; } catch {}
    if (!ok) { try { localStorage.setItem("prime_browser_stt", "yes"); } catch {} push("bot", "No local speech server is running, so the mic would use your browser's recogniser, which may send your voice to a cloud service. Press the mic again if that's fine, or type instead.", { who: S.current.who }); return; }
    speaker.current.stop(); const r = new R(); r.lang = navigator.language || "en-US"; r.interimResults = false; r.maxAlternatives = 1; rec.current = { browser: r }; setMic("listening");
    r.onresult = (e) => { const t = e.results[0] && e.results[0][0] ? e.results[0][0].transcript : ""; if (t.trim()) deliver(t); }; r.onend = () => { rec.current = null; setMic("idle"); }; r.onerror = (e) => { rec.current = null; setMic("idle"); push("bot", `The browser's recogniser stopped: ${e.error}.`, { who: S.current.who }); };
    try { r.start(); } catch { rec.current = null; setMic("idle"); }
  };
  const micDown = (e) => {
    e.preventDefault(); if (mic === "hearing") return;
    if (rec.current) { if (rec.current.browser) rec.current.browser.stop(); else stopRec(); return; }   // second tap of tap-to-talk
    if (info && !info.stt && !info.gone) { browserHear(); return; }
    if (!(navigator.mediaDevices && window.MediaRecorder)) { browserHear(); return; }
    try { e.currentTarget.setPointerCapture && e.pointerId !== undefined && e.currentTarget.setPointerCapture(e.pointerId); } catch {}
    startRec();
  };
  const micUp = () => { const st = rec.current; if (!st || st.browser) return; if (st.began && performance.now() - st.t0 > 400) stopRec(); };   // a quick tap, or a release during the permission prompt, leaves it listening: tap again to stop
  const micKey = (e) => { if (e.repeat || (e.key !== " " && e.key !== "Enter")) return; e.preventDefault(); if (e.type === "keydown") micDown(e); else micUp(); };

  const isSpeaking = speaking === who.id; const anySpeaking = !!speaking;
  const status = mic === "listening" ? "Listening" : mic === "hearing" ? "Writing that down" : busy ? "Thinking" : isSpeaking ? "Speaking" : "";
  const speakingFace = speaking && crew[speaking] ? crew[speaking] : member;
  const asleep = info && info.llm === "asleep";
  return html`<div class=${"prime" + (anySpeaking ? " voxon" : "")} ref=${root}>
    ${open && html`<div class="pp" role="dialog" aria-label=${member.name}>
      <header class=${"ppface" + (anySpeaking ? " speaking" : "") + (mic === "listening" ? " listening" : "")}><${Face} member=${anySpeaking ? speakingFace : member} speaking=${anySpeaking}/><div class="ppshade"></div>
        <div class="pptop">${who.id !== "master" && html`<button class="ppchip" onClick=${() => talkTo(PRIME)}>Back to Comfy Prime</button>`}<span class="grow"></span>
          <button class="ppchip" onClick=${() => setVoice(!voice)} aria-pressed=${voice} title=${voice ? "Mute voices" : "Speak answers aloud"} aria-label=${voice ? "Mute voices" : "Turn voices on"}><${Icon} d=${voice ? SOUND : MUTED}/></button>
          <button class="ppchip" onClick=${() => { setOpen(false); speaker.current.stop(); }} aria-label="Close">×</button></div>
        <div class="pptext"><b class=${(anySpeaking ? speakingFace.name : member.name).length > 13 ? "long" : ""}>${anySpeaking ? speakingFace.name : member.name}</b><small>${who.id === "master" ? (name ? `your guide, with ${name}` : "your guide") : familyLabel(member)}</small>
          <span class="ppstate" aria-live="polite">${status ? html`${(isSpeaking || anySpeaking) && mic === "idle" && !busy ? html`<${Bars}/>` : html`<i class="ppdot"></i>`}<em>${status}</em>` : asleep ? html`<i class="ppdot rest"></i><em>Resting while the GPU renders</em>` : ""}</span></div></header>
      <div class="msgs" aria-live="polite">${msgs.map((m) => html`<div class=${"msg " + (m.role === "me" ? "me" : "bot")}>${m.role !== "me" && m.who && html`<div class="msgwho"><${Face} member=${{ ...m.who, motion: null }}/><b>${m.who.name}</b></div>`}<span>${m.text}</span>
        ${(m.quotes || []).map((x) => html`<blockquote class="vq">"${x.quote}" <cite>${String(x.file).split("/").slice(-2).join("/")}</cite></blockquote>`)}${m.unsupported && m.unsupported.length > 0 && html`<p class="vqno">Not backed by the notes: ${m.unsupported.join("; ")}</p>`}
        ${m.button && html`<div style="margin-top:8px"><button class="btn small primary" style="padding:6px 14px" onClick=${() => dispatchEvent(new CustomEvent("prime-generate"))}>${m.button}</button></div>`}</div>`)}${busy && html`<div class="msg bot small">${member.name} is thinking...</div>`}<div ref=${end}></div></div>
      <form onSubmit=${send}><button type="button" class=${"micbtn " + mic} onPointerDown=${micDown} onPointerUp=${micUp} onPointerCancel=${micUp} onKeyDown=${micKey} onKeyUp=${micKey} onContextMenu=${(e) => e.preventDefault()} aria-label=${mic === "listening" ? "Stop listening and send" : "Hold to talk"} aria-pressed=${mic === "listening"} title="Hold to talk, or tap to start and tap again to stop" disabled=${mic === "hearing"}><${Icon} d=${MIC}/></button>
        <input ref=${inputEl} type="text" value=${text} onInput=${(e) => setText(e.target.value)} placeholder=${mic === "listening" ? "Listening..." : name === "" && who.id === "master" ? "Your name" : who.id === "master" ? "Ask or tell me what to make" : `Ask ${member.name}`} aria-label=${"message to " + member.name} autofocus/><button class="btn primary sendbtn" disabled=${busy || !text.trim()}>Send</button></form></div>`}
    <button class=${"orb" + (anySpeaking ? " talk" : "")} onClick=${() => { if (open) speaker.current.stop(); setOpen(!open); }} aria-label=${"Talk to " + member.name} aria-expanded=${open} title=${"Talk to " + member.name}>${!open ? html`<${Face} member=${anySpeaking ? speakingFace : member} speaking=${anySpeaking}/>` : html`<${Face} member=${{ ...member, motion: null }}/>`}</button></div>`;
}
