// What Shot Board looks like: one clip as the hero, each job a take on a contact sheet. The queue itself lives in shotboard.js; this file only reads it and calls back.
import { useState, useEffect, useRef } from "preact/hooks";
import { html, api, post } from "./common.js";
import { clock, elapsed, totalSeconds, isStopped, stateWord, readLive, perforations, nodeName, scrubTime, miniGraph, boardEstimate } from "./shotboard_film.js";

const calm = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
const seekable = (url) => url + "#t=0.1";
// Real renders that ship with the studio, two example shoots. Every take in a shoot was made from that shoot's source clip.
const EXAMPLES = [
  { id: "vfx", tab: "LTX-2.5 VFX", source: "vfx_same_src", about: "Example source clip: a woman in a red coat walks down a sunny street", takes: [
    { id: "vfx_same_water", label: "VFX: water", note: "From this clip" },
    { id: "vfx_same_night", label: "VFX: day to night", note: "From this clip" },
    { id: "vfx_same_plate", label: "VFX: clean plate", note: "From this clip" },
    { id: "vfx_same_cutout", label: "VFX: matte, as a cutout", note: "From this clip" },
    { id: "vfx_same_transition", label: "Transition: into the night take", note: "From this clip and its night take" },
  ] },
  { id: "h3", tab: "MiniMax H3", source: "v_h3_chef", about: "Example source clip: a chef flambes a pan", takes: [
    { id: "reshoot_orbit_take", label: "Reshoot: orbit right", note: "From this clip" },
    { id: "recast_chef", label: "Recast", note: "From this clip" },
  ] },
];

const useTick = (on, ms = 1000) => { const [, set] = useState(0); useEffect(() => { if (!on) return; const t = setInterval(() => set((n) => n + 1), ms); return () => clearInterval(t); }, [on, ms]); };

// What ComfyUI says about the running job. Read-only, and separate from the queue's own polling.
function useLive(job) {
  const [live, setLive] = useState(null), graph = useRef(null);
  useEffect(() => {
    setLive(null); graph.current = null;
    if (!job) return;
    let off = false;
    const tick = async () => {
      try {
        const r = await api("/api/live" + (graph.current ? "?have=" + encodeURIComponent(job) : ""));
        if (off) return;
        if (r.graph && r.job === job) graph.current = r.graph;
        setLive(readLive(r, job, graph.current ? Object.keys(graph.current).length : 0));
      } catch {}
    };
    tick(); const t = setInterval(tick, 2000);
    return () => { off = true; clearInterval(t); };
  }, [job]);
  return [live, graph.current];
}

// One still of the source, for frames that have nothing of their own to show yet.
function useStill(url) {
  const [still, setStill] = useState("");
  useEffect(() => {
    setStill("");
    if (!url) return;
    const v = document.createElement("video"); v.muted = true; v.preload = "auto"; v.src = url;
    v.onloadeddata = () => { v.currentTime = Math.min(0.5, (v.duration || 1) / 2); };
    v.onseeked = () => { try { const c = document.createElement("canvas"); c.width = 480; c.height = Math.round(480 * (v.videoHeight / v.videoWidth)) || 270; c.getContext("2d").drawImage(v, 0, 0, c.width, c.height); setStill(c.toDataURL("image/jpeg", 0.72)); } catch {} };
    return () => { v.onloadeddata = v.onseeked = null; v.removeAttribute("src"); v.load(); };
  }, [url]);
  return still;
}

const Perfs = ({ live }) => {
  const holes = perforations(live);
  return holes.length ? html`<div class="perfs nodes" aria-hidden="true">${holes.map((h) => html`<i class=${h}></i>`)}</div>` : html`<div class="perfs" aria-hidden="true"></div>`;
};
const Grease = () => html`<svg class="grease" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true"><path d="M7 8C30 3 70 3 95 6c3 24 3 62-1 88-25 3-65 3-89-1C2 70 2 32 6 6c20-4 40-4 58-2"/></svg>`;

function Facts({ j, took }) {
  return html`<dl class="sb-facts">
    ${j.seed != null && html`<div><dt>Seed</dt><dd>${j.seed}</dd></div>`}
    ${j.graphHash && html`<div title="The first 12 characters of the SHA-256 of the graph sent to ComfyUI"><dt>Graph</dt><dd>${j.graphHash}</dd></div>`}
    ${took && j.seconds != null && html`<div><dt>Took</dt><dd>${clock(j.seconds)}</dd></div>`}
  </dl>`;
}

// ---------- the contact sheet: the source first, then one frame per take
function Frame({ j, n, count, video, still, picked, live, onPick, onGraph, onRetry, index }) {
  useTick(j.status === "running");
  const was = useRef(j.status), [just, setJust] = useState(false), vid = useRef(null), media = useRef(null);
  useEffect(() => { if (was.current === "running" && j.status === "done") setJust(true); was.current = j.status; }, [j.status]);
  const scrub = (e) => { const v = vid.current; if (!v || e.pointerType === "touch" || !v.duration) return; const r = e.currentTarget.getBoundingClientRect(); media.current.style.setProperty("--x", ((e.clientX - r.left) / r.width * 100).toFixed(1) + "%"); if (!v.seeking) v.currentTime = scrubTime(e.clientX, r.left, r.width, v.duration); };
  const running = j.status === "running", stopped = isStopped(j.status);
  const face = html`
    ${video ? html`<video ref=${vid} src=${seekable(video.url)} muted playsinline preload="metadata" tabindex="-1"></video>` : still ? html`<img class="sbf-still" src=${still} alt=""/>` : html`<span class="sbf-blank"></span>`}
    ${running && live && live.preview > 0 && html`<img class="sbf-preview" src=${"/api/live/preview?s=" + live.preview} alt=""/>`}
    ${!video && html`<span class="sbf-word">${running ? clock(elapsed(j, Date.now())) : j.status === "queued" ? `${n} of ${count}` : stateWord(j.status)}</span>`}
    ${video && html`<span class="sbf-head"></span>`}`;
  return html`<article class=${`sbf is-${j.status}${picked ? " is-picked" : ""}${just ? " just" : ""}`} style=${`--i:${index}`} key=${j.id}>
    <div class="sbf-film"><${Perfs} live=${running ? live : null}/>
      ${video || running ? html`<button class="sbf-media" ref=${media} aria-pressed=${picked} aria-label=${`Take ${n}, ${j.label}: show it on the big screen`} onClick=${onPick} onPointerMove=${scrub}>${face}${picked && html`<${Grease}/>`}</button>` : html`<div class="sbf-media">${face}</div>`}
      <${Perfs} live=${running ? live : null}/></div>
    <div class="sbf-cap">
      <div class="sbf-title"><span class="sbf-n">Take ${n}</span><b>${j.label}</b><em class=${"sbf-state " + j.status}>${stateWord(j.status)}${j.status === "done" && j.seconds != null ? `, ${clock(j.seconds)}` : ""}</em></div>
      <${Facts} j=${j}/>
      ${stopped && j.error && j.status !== "cancelled" && html`<p class="sbf-err">${j.error}</p>`}
      <div class="sbf-acts"><button class="btn small" onClick=${onGraph}>See the graph</button>${video && html`<a class="btn small" href=${video.url} download=${video.filename}>Download</a>`}${stopped && html`<button class="btn small" onClick=${onRetry}>Try again</button>`}</div>
    </div>
  </article>`;
}

// ---------- the big screen
// The graph and values this take was sent with, asked for again from the studio (the same body and seed give the same graph).
function useSent(j) {
  const [sent, setSent] = useState(null);
  useEffect(() => { let off = false; setSent(null); if (j.body) post("/api/graph", { ...j.body, seed: j.seed }).then((r) => { if (!off && r && r.graph) setSent({ map: miniGraph(r.graph), prompt: (r.values && r.values.prompt) || "" }); }).catch(() => {}); return () => { off = true; }; }, [j.id, j.seed]);
  return sent;
}

function MiniMap({ g, onGraph }) {
  if (!g || !g.nodes.length) return null;
  const px = (x) => 6 + (g.width > 1 ? x / (g.width - 1) : 0.5) * 208, py = (y) => 5 + (g.height > 1 ? y / (g.height - 1) : 0.5) * 50, bend = 104 / Math.max(1, g.width - 1);
  return html`<button class="sb-map" onClick=${onGraph} aria-label=${`This take's graph, ${g.nodes.length} nodes. Open it.`} title="Open this take's graph">
    <svg viewBox="0 0 220 60" aria-hidden="true">${g.links.map(([a, b, c, d]) => html`<path d=${`M${px(a)} ${py(b)}C${px(a) + bend} ${py(b)} ${px(c) - bend} ${py(d)} ${px(c)} ${py(d)}`}/>`)}${g.nodes.map((n) => html`<circle cx=${px(n.x)} cy=${py(n.y)} r="2.4"><title>${n.cls}</title></circle>`)}</svg>
    <span>${g.nodes.length} nodes</span>
  </button>`;
}

function Screen({ j, n, count, video, source, onGraph, onCutout, onReel, busy }) {
  const sent = useSent(j);
  const take = useRef(null), src = useRef(null), [mode, setMode] = useState("wipe"), [pos, setPos] = useState(50), [t, setT] = useState(0), [dur, setDur] = useState(0), [playing, setPlaying] = useState(false), [sound, setSound] = useState(false);
  const toSource = (time) => { const s = src.current; if (s && s.duration && Math.abs(s.currentTime - time) > 0.14) s.currentTime = Math.min(time, s.duration - 0.05); };
  useEffect(() => { setT(0); setPlaying(false); const v = take.current; if (v && !calm()) v.play().catch(() => {}); }, [video.url]);
  const toggle = () => { const v = take.current; if (v) v.paused ? v.play().catch(() => {}) : v.pause(); };
  const seek = (time) => { const v = take.current; if (!v) return; v.currentTime = time; setT(time); toSource(time); };
  return html`<section class=${"sb-screen film mode-" + mode} aria-label=${`Take ${n} against the source`}>
    <div class="perfs" aria-hidden="true"></div>
    <div class="sb-wipe" style=${`--pos:${pos}%`}>
      <figure class="sb-take"><video ref=${take} src=${video.url} loop muted=${!sound} playsinline preload="auto" onLoadedMetadata=${(e) => setDur(e.target.duration || 0)} onTimeUpdate=${(e) => { setT(e.target.currentTime); toSource(e.target.currentTime); }} onPlay=${() => { setPlaying(true); if (src.current) src.current.play().catch(() => {}); }} onPause=${() => { setPlaying(false); if (src.current) src.current.pause(); }}></video><figcaption>Take ${n}</figcaption></figure>
      <figure class="sb-src"><video ref=${src} src=${source.url} muted loop playsinline preload="auto"></video><figcaption>Source</figcaption></figure>
      ${mode === "wipe" && html`<span class="sb-handle" aria-hidden="true"></span><input class="sb-wiper" type="range" min="0" max="100" value=${pos} aria-label="Wipe between the source and the take" onInput=${(e) => setPos(+e.target.value)}/>`}
    </div>
    <div class="sb-deck">
      <button class="sb-play" aria-label=${playing ? "Pause" : "Play"} onClick=${toggle}>${playing ? html`<svg viewBox="0 0 16 16" aria-hidden="true"><rect x="3" y="2" width="3.6" height="12"/><rect x="9.4" y="2" width="3.6" height="12"/></svg>` : html`<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 2l10 6-10 6z"/></svg>`}</button>
      <input class="sb-scrub" type="range" min="0" max=${dur || 1} step="0.01" value=${t} aria-label="Scrub through the take" onInput=${(e) => seek(+e.target.value)}/>
      <span class="sb-time">${clock(t)} of ${clock(dur)}</span>
      <div class="sb-seg" role="group" aria-label="How to compare"><button aria-pressed=${mode === "wipe"} onClick=${() => setMode("wipe")}>Wipe</button><button aria-pressed=${mode === "side"} onClick=${() => setMode("side")}>Side by side</button></div>
      <button class="btn small" aria-pressed=${sound} onClick=${() => setSound(!sound)}>${sound ? "Sound on" : "Sound off"}</button>
    </div>
    <div class="sb-slate">
      <div class="sb-slate-t"><span class="sbf-n">Take ${n} of ${count}</span><h3>${j.label}</h3><${Facts} j=${j} took/></div>
      <${MiniMap} g=${sent && sent.map} onGraph=${onGraph}/>
      ${sent && sent.prompt.trim() && html`<details class="sb-prompt"><summary>Prompt sent</summary><p>${sent.prompt}</p></details>`}
      <div class="sbf-acts"><button class="btn small" onClick=${onGraph}>See the graph</button><a class="btn small" href=${video.url} download=${video.filename}>Download</a>
        ${j.id === "matte" && !j.cutout && onCutout && html`<button class="btn small" disabled=${!!busy} onClick=${onCutout} title="Your clip with this matte as its alpha channel, as ProRes 4444">${busy === "cutout" ? "Making the cutout..." : "Make the cutout"}</button>`}
        ${!j.reel && onReel && html`<button class="btn small" disabled=${!!busy} onClick=${onReel} title="Before and after as 9:16, 1:1 and 16:9 videos, each with an AI-generated label and an end card">${busy === "reel" ? "Making the reel..." : "Make a shareable reel"}</button>`}
        ${j.reel && html`<a class="btn small" href=${j.reel["9x16"].url} download=${j.reel["9x16"].filename}>Reel 9:16</a><a class="btn small" href=${j.reel["1x1"].url} download=${j.reel["1x1"].filename}>Reel 1:1</a><a class="btn small" href=${j.reel["16x9"].url} download=${j.reel["16x9"].filename}>Reel 16:9</a>`}
        ${j.cutout && html`<a class="btn small" href=${j.cutout.mov.url} download=${j.cutout.mov.filename}>Cutout, ProRes 4444 with alpha</a><a class="btn small" href=${j.cutout.preview.url} target="_blank" rel="noopener">Cutout over a checkerboard</a>`}</div>
    </div>
  </section>`;
}

function LiveScreen({ j, n, count, source, still, live, graph }) {
  useTick(true);
  const seconds = elapsed(j, Date.now()), sending = j.status !== "running", detail = live && live.total > 0, name = detail ? nodeName(graph, live.node) : "";
  return html`<section class="sb-screen film sb-live" aria-label=${`Take ${n} of ${count} is rendering`}>
    <${Perfs} live=${live}/>
    <div class="sb-livepic">
      ${live && live.preview > 0 ? html`<img class="is-preview" src=${"/api/live/preview?s=" + live.preview} alt="ComfyUI's latest preview of this take"/>` : still ? html`<img src=${still} alt=""/>` : html`<span class="sbf-blank"></span>`}
      <div class="sb-liveinfo">
        <p class="sb-livetake" role="status"><span class="sbf-n">Take ${n} of ${count}</span><b>${j.label}</b></p>
        <p class="sb-timer" aria-label=${`${seconds} seconds elapsed`}>${clock(seconds)}</p>
        ${sending ? html`<p class="sb-liveline">Sending this take to ComfyUI.</p>` : live && live.waiting ? html`<p class="sb-liveline">ComfyUI is finishing another job first${live.pending ? `, with ${live.pending} waiting` : ""}. This take is in its line.</p>` : detail ? html`
          <p class="sb-liveline"><b>${live.done + live.cached} of ${live.total}</b> graph nodes finished${live.cached ? `, ${live.cached} reused from the last run` : ""}.${name ? html` Now on <b>${name}</b>.` : ""}</p>
          ${live.max > 0 && html`<div class="sb-step" role="progressbar" aria-valuemin="0" aria-valuemax=${live.max} aria-valuenow=${live.value} aria-label="Steps on the current node"><i style=${`--step:${Math.min(100, live.value / live.max * 100)}%`}></i><span>Step ${live.value} of ${live.max}</span></div>`}`
        : html`<p class="sb-liveline">ComfyUI has not sent node progress for this take, so this is elapsed time only.</p>`}
      </div>
      ${live && live.preview > 0 && html`<span class="sb-tag">ComfyUI preview</span>`}
      ${!(live && live.preview > 0) && still && html`<span class="sb-tag">Your source clip</span>`}
    </div>
    <${Perfs} live=${live}/>
  </section>`;
}

// ---------- first visit: a real example, labelled as one
function Example() {
  const [times, setTimes] = useState({}), [which, setWhich] = useState(EXAMPLES[0].id), hero = useRef(null), ex = EXAMPLES.find((x) => x.id === which) || EXAMPLES[0];
  useEffect(() => { let off = false; fetch("showcase/showcase.json").then((r) => r.json()).then((list) => { if (!off) setTimes(Object.fromEntries(list.map((x) => [x.id, x.seconds]))); }).catch(() => {}); return () => { off = true; }; }, []);
  useEffect(() => { if (hero.current && !calm()) hero.current.play().catch(() => {}); }, [which]);
  const scrub = (e) => { const v = e.currentTarget.querySelector("video"); if (!v || !v.duration || e.pointerType === "touch") return; const r = e.currentTarget.getBoundingClientRect(); if (!v.seeking) v.currentTime = scrubTime(e.clientX, r.left, r.width, v.duration); };
  return html`<section class="sb-screen film sb-example" aria-label="An example shoot">
    <div class="perfs" aria-hidden="true"></div>
    <figure class="sb-exhero">
      <video key=${ex.source} ref=${hero} src=${`showcase/${ex.source}.mp4`} poster=${`showcase/${ex.source}.webp`} muted loop playsinline preload="metadata" aria-label=${ex.about}></video>
      <figcaption><span>Example</span><b>One source clip</b></figcaption><${Grease}/>
    </figure>
    <div class="perfs" aria-hidden="true"></div>
    <div class="sb-seg sb-exwhich" role="group" aria-label="Which example shoot">${EXAMPLES.map((x) => html`<button aria-pressed=${x.id === which} onClick=${() => setWhich(x.id)}>${x.tab}</button>`)}</div>
    <ul class="sb-extakes">
      ${ex.takes.map((t) => html`<li key=${t.id} onPointerMove=${scrub}>
        <video src=${seekable(`showcase/${t.id}.mp4`)} poster=${`showcase/${t.id}.webp`} muted playsinline preload="none" aria-label=${"Example take: " + t.label}></video>
        <div><b>${t.label}</b><small>${t.note}${times[t.id] ? `, ${clock(times[t.id])} to render` : ""}</small></div>
      </li>`)}
    </ul>
    <div class="perfs" aria-hidden="true"></div>
    <p class="sb-exnote">These are our own renders, not yours. Render times are from our 96 GB card.<span class="sb-hoverhint"> Hover a take to scrub it.</span></p>
  </section>`;
}

const Drop = ({ label, hint, accept, what, file, onFile, big, children }) => {
  const [over, setOver] = useState(false);
  return html`<label class=${`sb-drop${big ? " big" : ""}${over ? " over" : ""}${file ? " has" : ""}`} onDragOver=${(e) => { e.preventDefault(); setOver(true); }} onDragLeave=${() => setOver(false)} onDrop=${(e) => { e.preventDefault(); setOver(false); onFile(e.dataTransfer.files[0]); }}>
    <input type="file" accept=${accept} aria-label=${label} data-what=${what} onChange=${(e) => onFile(e.target.files[0])}/>
    ${children}<span class="sb-dropt"><b>${file ? file.label : label}</b><small>${file ? "Choose another" : hint}</small></span>
  </label>`;
};

function Setup(p) {
  const { source, character, scene, camera, picked, lib, transforms, cameras, busy, blocked, chosen, err, vfx } = p, anyVfx = chosen.some((t) => t.goal === "vfx_ltx"), est = boardEstimate(chosen, vfx);
  return html`<div class="sb-setup">
    <${Drop} big label="Add your clip" hint="Drop a video here, or choose one" what="clip" accept="video/mp4,video/webm,video/quicktime,video/x-matroska" file=${source} onFile=${(f) => p.useFile(f, p.setSource, "clip")}/>
    ${lib.length > 0 && html`<div class="sb-lib"><span id="sb-lib-l">Or use one from your Library</span><div class="sb-libstrip" role="group" aria-labelledby="sb-lib-l">${lib.map((r) => html`<button title=${r.prompt || r.video.filename} aria-label=${"Use " + (r.prompt || r.video.filename)} onClick=${() => p.fromLibrary(r)}><video src=${seekable(r.video.url)} muted preload="metadata" tabindex="-1"></video></button>`)}</div></div>`}
    <h3 class="sb-sub">Today's takes</h3>
    <ul class="sb-jobs">
      ${transforms.map((t) => { const on = !!picked[t.id], order = on ? chosen.indexOf(t) + 1 : 0; return html`<li>
        <button class=${"sb-job" + (on ? " on" : "")} aria-pressed=${on} onClick=${() => p.setPicked({ ...picked, [t.id]: !on })}><span class="sb-tick" aria-hidden="true">${order || ""}</span><span><b>${t.label}</b><small>${t.about}</small></span></button>
        ${on && t.id === "reshoot" && html`<label class="sb-opt">Camera move <select value=${camera} onChange=${(e) => p.setCamera(e.target.value)}>${cameras.map((c) => html`<option value=${c}>${c.replace(/_/g, " ")}</option>`)}</select></label>`}
        ${on && (t.strength || t.words) && html`<div class="sb-opt sb-vfxopt">
          ${t.strength && html`<label>Strength <select value=${(vfx[t.id] || {}).intensity || "auto"} onChange=${(e) => p.setVfx({ ...vfx, [t.id]: { ...(vfx[t.id] || {}), intensity: e.target.value } })}>${p.strengths.map((x) => html`<option value=${x.value}>${x.label}</option>`)}</select></label>`}
          ${t.words && html`<label>${t.words.label} <input type="text" value=${(vfx[t.id] || {}).text || ""} placeholder=${t.words.placeholder} onInput=${(e) => p.setVfx({ ...vfx, [t.id]: { ...(vfx[t.id] || {}), text: e.target.value } })}/></label>`}
        </div>`}
        ${on && t.needsSecond && html`<div class="sb-opt"><${Drop} label="Add the second clip" hint="The shot to transition into" what="second" accept="video/mp4,video/webm,video/quicktime,video/x-matroska" file=${p.second} onFile=${(f) => p.useFile(f, p.setSecond, "second clip")}/></div>`}
        ${on && t.needsCharacter && html`<div class="sb-opt"><${Drop} label="Add a character picture" hint="PNG, JPG or WebP" what="character" accept="image/png,image/jpeg,image/webp" file=${character} onFile=${(f) => p.useFile(f, p.setCharacter, "character")}>${character && html`<img src=${character.url} alt="Your character"/>`}<//></div>`}
      </li>`; })}
    </ul>
    <label class="sb-scene">What the clip shows, for VFX<input type="text" value=${scene} onInput=${(e) => p.setScene(e.target.value)} placeholder="a wet cobblestone street at dusk"/></label>
    ${anyVfx && html`<label class="sb-scene">VFX size<select value=${vfx.quality} onChange=${(e) => p.setVfx({ ...vfx, quality: e.target.value })}>${p.qualities.map((x) => html`<option value=${x.value}>${x.label}</option>`)}</select></label>`}
    <button class="gobtn" disabled=${!!blocked || !!busy} onClick=${p.start}>Run ${chosen.length} job${chosen.length === 1 ? "" : "s"}</button>
    ${est.seconds > 0 && html`<p class="sb-est">About ${clock(est.seconds)} on our 96 GB card${est.unknown ? `, plus ${est.unknown} job${est.unknown === 1 ? "" : "s"} we have no time for yet` : ""}.</p>`}
    <p class="sb-why" role="status">${busy && busy !== "export" && busy !== "cutout" && busy !== "reel" ? `Uploading your ${busy}...` : blocked}</p>
    ${err && html`<p class="sb-errline" role="alert">${err}</p>`}
    <ul class="sb-notes">
      <li>Each job runs on your GPU, one at a time.</li>
      <li>Keep this tab open while they run. If you reload or come back to this page, the queue picks up where it left off.</li>
      <li>Recast is the slowest job. One 5-second take took about 9 minutes on our 96 GB card.</li>
      <li>Every result keeps its exact graph and seed.</li>
    </ul>
  </div>`;
}

function CallSheet(p) {
  const { jobs, active, finished, busy, err, done, onCancel } = p, now = Date.now();
  useTick(active);
  const [open, setOpen] = useState(false);
  return html`<div class="sb-callsheet">
    <div class="sb-tally"><p><b>${done}</b> of ${jobs.length} takes done</p><p class="sb-total" title="Render time of the takes so far, added up">${clock(totalSeconds(jobs, now))}</p></div>
    <ol class="sb-order">
      ${jobs.map((j, i) => html`<li class=${"is-" + j.status} aria-current=${j.status === "running" ? "step" : null}><span class="sb-ordern">${i + 1}</span><b>${j.label}</b><span class="sb-ordert">${j.status === "queued" ? stateWord("queued") : j.status === "running" || j.status === "done" ? clock(elapsed(j, now)) : stateWord(j.status)}</span></li>`)}
    </ol>
    ${active && html`<p class="sb-keep">Keep this tab open while the queue runs. If you reload, it picks up where it left off.</p>`}
    <div class="sb-wrapacts">
      ${jobs.length > 0 && !active && html`<a class="btn small" href="#project">Pack this board into one file</a>`}${finished.length > 0 && !active && html`<button class="gobtn" disabled=${!!busy} onClick=${p.doExport}>${busy === "export" ? "Exporting..." : "Export contact video"}</button>`}
      ${active && onCancel && html`<button class="btn" onClick=${onCancel}>Cancel the board</button>`}
      ${!active && html`<button class="btn" onClick=${p.reset}>Clear the board</button>`}
    </div>
    ${err && html`<p class="sb-errline" role="alert">${err}</p>`}
    <details class="sb-more" open=${open} onToggle=${(e) => setOpen(e.target.open)}><summary>Change the clip or the takes</summary>${open && html`<${Setup} ...${p}/>`}</details>
  </div>`;
}

export function Board(p) {
  const { source, jobs, chosen, exported, active, finished, resultVideo, graph, retry } = p;
  const [pin, setPin] = useState(null), run = jobs.find((j) => j.status === "running"), next = jobs.find((j) => j.status === "queued");
  const [live, liveGraph] = useLive(run && run.job), still = useStill(source && source.url);
  const number = (j) => jobs.indexOf(j) + 1;
  const hadJobs = useRef(jobs.length > 0), [deal, setDeal] = useState(false);
  useEffect(() => { if (!hadJobs.current && jobs.length) { setDeal(true); setPin(null); } hadJobs.current = jobs.length > 0; }, [jobs.length]);
  useEffect(() => { document.body.classList.add("on-shots"); return () => document.body.classList.remove("on-shots", "shots-busy"); }, []);
  useEffect(() => { document.body.classList.toggle("shots-busy", !!source); }, [!!source]);

  const pinned = pin && pin !== "source" ? finished.find((j) => j.id === pin) : null, latest = active ? finished[finished.length - 1] : finished[0];
  const showing = pin === "source" ? null : pinned || (active ? null : latest) || null, rolling = pin !== "source" && !pinned && active ? run || next : null;
  const pick = (id) => setPin((now) => (now === id ? null : id));

  const roll = source && html`<section class=${"sb-roll" + (deal ? " deal" : "")} aria-label="Contact sheet">
      <div class="sb-grid">
        <article class=${"sbf is-source" + (pin === "source" ? " is-picked" : "")} style="--i:0">
          <div class="sbf-film"><div class="perfs" aria-hidden="true"></div><button class="sbf-media" aria-pressed=${pin === "source"} aria-label="Show the source clip on the big screen" onClick=${() => pick("source")}>${still ? html`<img class="sbf-still on" src=${still} alt=""/>` : html`<span class="sbf-blank"></span>`}${pin === "source" && html`<${Grease}/>`}</button><div class="perfs" aria-hidden="true"></div></div>
          <div class="sbf-cap"><div class="sbf-title"><span class="sbf-n">Source</span><b class="sbf-srcname">${source.label}</b></div></div>
        </article>
        ${jobs.map((j, i) => html`<${Frame} key=${j.id} j=${j} n=${i + 1} count=${jobs.length} index=${i + 1} video=${j.status === "done" ? resultVideo(j.files) : null} still=${still} picked=${pin === j.id || (!pin && showing === j)} live=${j === run ? live : null} onPick=${() => (j.status === "done" ? pick(j.id) : setPin(null))} onGraph=${() => graph(j)} onRetry=${() => retry(j.id)}/>`)}
        ${!jobs.length && chosen.map((t, i) => html`<article class="sbf is-planned" key=${t.id} style=${`--i:${i + 1}`}><div class="sbf-film"><div class="perfs" aria-hidden="true"></div><div class="sbf-media">${still ? html`<img class="sbf-still" src=${still} alt=""/>` : html`<span class="sbf-blank"></span>`}<span class="sbf-word">Planned</span></div><div class="perfs" aria-hidden="true"></div></div><div class="sbf-cap"><div class="sbf-title"><span class="sbf-n">Take ${i + 1}</span><b>${t.label}</b></div></div></article>`)}
      </div>
    </section>`;

  return html`<div class=${"shotboard sb" + (source ? "" : " no-clip") + (jobs.length ? " has-jobs" : "") + (active ? " is-rolling" : "")}>
    <div class="sb-top">
      <div class="sb-left"><div class="sb-stage">
        ${!source ? html`<div class="sb-phoneadd"><${Drop} big label="Add your clip" hint="Choose a video" what="clip" accept="video/mp4,video/webm,video/quicktime,video/x-matroska" onFile=${(f) => p.useFile(f, p.setSource, "clip")}/></div><${Example}/>`
          : showing ? html`<${Screen} key=${showing.id} j=${showing} n=${number(showing)} count=${jobs.length} video=${resultVideo(showing.files)} source=${source} onGraph=${() => graph(showing)} onCutout=${() => p.makeCutout(showing.id)} onReel=${() => p.makeReel(showing.id)} busy=${p.busy}/>`
          : rolling ? html`<${LiveScreen} j=${rolling} n=${number(rolling)} count=${jobs.length} source=${source} still=${still} live=${run ? live : null} graph=${liveGraph}/>`
          : html`<section class="sb-screen film sb-sourcehero" aria-label="Your source clip"><div class="perfs" aria-hidden="true"></div><figure><video key=${source.url} src=${source.url} controls muted loop playsinline preload="metadata"></video><figcaption>Source</figcaption></figure><div class="perfs" aria-hidden="true"></div><p class="sb-sourcename">${source.label}</p></section>`}
      </div>${!jobs.length && roll}</div>
      <aside class="sb-call" aria-label="Call sheet">${jobs.length ? html`<${CallSheet} ...${p}/>` : html`<${Setup} ...${p}/>`}</aside>
    </div>
    ${exported && html`<section class="sb-export film"><h3>Contact video</h3><video src=${exported.url} controls loop playsinline></video><p><a class="btn small" href=${exported.url} download=${exported.filename}>Download ${exported.filename}</a></p></section>`}
    ${jobs.length > 0 && roll}
  </div>`;
}
