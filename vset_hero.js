// The Virtual Set hero (3D scene in, directed video out) and the wipe that compares a pass with its result. Pass names and clips arrive as props, so a real shot uses the same wipe.
import { useEffect, useRef, useState } from "preact/hooks";
import { html } from "./common.js";
import { EXAMPLES } from "./vset_example.js";
import { routeStatus, needsSync } from "./vset_helpers.js";

const quiet = () => typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;

// Two clips, one over the other. The range input is the keyboard's handle; the second range scrubs both.
export function Wipe({ over, overLabel, under, underLabel, overPoster, underPoster, autoplay = false }) {
  const [pos, setPos] = useState(45), [playing, setPlaying] = useState(false), [time, setTime] = useState(0), [dur, setDur] = useState(0);
  const a = useRef(null), b = useRef(null);
  useEffect(() => { if (autoplay && !quiet()) setPlaying(true); }, []);
  useEffect(() => {
    for (const v of [a.current, b.current]) { if (!v) continue; if (playing) { const p = v.play(); if (p && p.catch) p.catch(() => setPlaying(false)); } else v.pause(); }
  }, [playing, over, under]);
  const tick = () => { const m = b.current, o = a.current; if (!m) return; setTime(m.currentTime); if (o && needsSync(o.currentTime, m.currentTime) && !m.seeking) o.currentTime = m.currentTime; };
  const seek = (t) => { setPlaying(false); for (const v of [a.current, b.current]) if (v) v.currentTime = t; setTime(t); };
  return html`<div class="vs-wipewrap">
    <div class="vs-wipe" style=${{ "--pos": pos + "%" }}>
      <figure class="vs-wunder"><video ref=${b} src=${under} poster=${underPoster} muted loop playsinline preload="metadata" onLoadedMetadata=${(e) => { setDur(e.target.duration || 0); if (!e.target.currentTime) e.target.currentTime = 0.04; }} onTimeUpdate=${tick}></video><figcaption>${underLabel}</figcaption></figure>
      <figure class="vs-wover"><video ref=${a} key=${over} src=${over} poster=${overPoster} muted loop playsinline preload="metadata" onLoadedMetadata=${(e) => { const m = b.current; e.target.currentTime = m ? m.currentTime || 0.04 : 0.04; }}></video><figcaption>${overLabel}</figcaption></figure>
      <div class="vs-handle" aria-hidden="true"></div>
      <input class="vs-wiper" type="range" min="0" max="100" value=${pos} aria-label=${`Compare: ${overLabel} on the left, ${underLabel} on the right`} onInput=${(e) => setPos(Number(e.target.value))}/>
    </div>
    <div class="vs-deck"><button type="button" class="vs-play" aria-label=${playing ? "Pause both clips" : "Play both clips"} onClick=${() => setPlaying(!playing)}><svg viewBox="0 0 24 24" aria-hidden="true"><path d=${playing ? "M6 4h4v16H6z M14 4h4v16h-4z" : "M6 4l14 8-14 8z"}/></svg></button>
      <input class="vs-scrub" type="range" min="0" max=${dur || 1} step="0.04" value=${time} aria-label="Move both clips to a moment" onInput=${(e) => seek(Number(e.target.value))}/><span class="vs-time">${time.toFixed(1)} s</span></div>
  </div>`;
}

export function Hero({ caps }) {
  const [which, setWhich] = useState(0), [at, setAt] = useState(0), EXAMPLE = EXAMPLES[which], p = EXAMPLE.passes[Math.min(at, EXAMPLE.passes.length - 1)];
  const st = routeStatus(caps && caps.routes && caps.routes[EXAMPLE.mode]);
  return html`<section class="vs-hero film" aria-label="What Virtual Set does">
    <div class="vs-hgrid">
      <div class="vs-scene">
        <p class="vs-kicker">In</p><h2>A 3D scene</h2>
        <p class="vs-lead">Build the set, place the camera. Blender renders the same frames several ways. Pick one to compare.</p>
        <div class="vs-stack" role="group" aria-label="The passes for this shot">${EXAMPLE.passes.map((x, i) => html`<button type="button" class=${"vs-plate p" + i} style=${{ "--i": i }} aria-pressed=${x === p} onClick=${() => setAt(i)}><img src=${x.still} alt="" width="854" height="488"/><span><b>${x.label}</b><small>${x.what}</small></span></button>`)}</div>
      </div>
      <div class="vs-arrow" aria-hidden="true"><svg viewBox="0 0 64 24"><path d="M2 12h56 M46 3l14 9-14 9"/></svg></div>
      <div class="vs-out">
        <div class="vs-outhead"><div><p class="vs-kicker">Out</p><h2>A directed video</h2></div>
          <div class="vs-engines" role="group" aria-label="Which engine rendered this scene">${EXAMPLES.map((x, i) => html`<button type="button" aria-pressed=${i === which} onClick=${() => setWhich(i)}>${x.engine}</button>`)}</div></div>
        <${Wipe} key=${EXAMPLE.id} over=${p.clip} overLabel=${p.label + " pass"} overPoster=${p.still} under=${EXAMPLE.result.clip} underLabel=${EXAMPLE.engine} underPoster=${EXAMPLE.result.still} autoplay=${true}/>
      </div>
    </div>
    <div class="vs-truth">
      <div class="vs-truthlead"><p class="vs-kicker">Our test, not a promise</p><b>${EXAMPLE.name}, mode ${EXAMPLE.mode}.</b> <span>${EXAMPLE.how} ${EXAMPLE.size}, ${EXAMPLE.fps} fps, ${EXAMPLE.frames} frames, seed ${EXAMPLE.seed}.</span></div>
      <div class="vs-held"><h3>What held</h3><p>${EXAMPLE.held}</p></div>
      <div class="vs-lost"><h3>What did not</h3><p>${EXAMPLE.lost}</p></div>
      <div class="vs-nums"><h3>Automatic checks</h3><p>Flicker ${EXAMPLE.flicker}, layout ${EXAMPLE.layout}. Numbers for review. They do not judge the picture.</p><p class=${"vs-livenote " + st.cls}>Mode ${EXAMPLE.mode} on this machine now: ${st.label}.</p></div>
    </div>
  </section>`;
}
