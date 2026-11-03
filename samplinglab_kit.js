/* Sampling Lab instruments used on more than one view: the equation setter, the wipe, the sigma chart and the shared proof pills. */
import { useEffect, useMemo, useRef, useState } from "preact/hooks";
import { html } from "./common.js";
import { LABELS, whereWord, whereOf, mathParts, mathTokens, diffPixels, curvePoints, toPath, curveStats } from "./samplinglab_logic.js";

export const proofPill = (l) => html`<span class=${"slp" + (l === "measured here" ? " proof" : l === "inference" ? " infer" : l === "from pack README claim" ? " claim" : "")}>${LABELS[l] || l}</span>`;
export const place = (e) => html`<span class=${"slp " + whereOf(e)}>${whereWord(e)}</span>`;
export const unproven = (e) => e.in_core || e.rendered ? null : html`<span class="slp warn">Unproven here</span>`;

export function useWidth(fallback = 720) {
  const ref = useRef(null); const [w, setW] = useState(fallback);
  useEffect(() => { const el = ref.current; if (!el) return undefined; const read = () => { const x = el.clientWidth; if (x) setW(x); }; read(); if (!window.ResizeObserver) { addEventListener("resize", read); return () => removeEventListener("resize", read); } const o = new ResizeObserver(read); o.observe(el); return () => o.disconnect(); }, []);
  return [ref, w];
}

/* ---------- equations ---------- */
function Tok({ t }) {
  if (t.t === "v") return html`<i>${t.s}</i>`;
  if (t.t === "num") return html`<span class="n">${t.s}</span>`;
  if (t.t === "op") return html`<span class="o">${t.s}</span>`;
  if (t.t === "code") return html`<code>${t.s}</code>`;
  if (t.t === "sub") return html`<sub>${t.kids.map((k, i) => html`<${Tok} key=${i} t=${k}/>`)}</sub>`;
  if (t.t === "sup") return html`<sup>${t.kids.map((k, i) => html`<${Tok} key=${i} t=${k}/>`)}</sup>`;
  return t.s;
}
export const MathLine = ({ s }) => mathTokens(s).map((t, i) => html`<${Tok} key=${i} t=${t}/>`);
export function Equation({ text, label }) {
  const { symbols, lines } = useMemo(() => mathParts(text), [text]);
  return html`<div class="sleq film">
    <div class="sleq-head"><span class="slkick">The working, as the code does it</span>${label}</div>
    <div class="sleq-body" aria-label="Equation text">${lines.map((l, i) => html`<p key=${i} class=${l.eq ? "eq" : "pr"}><${MathLine} s=${l.s}/></p>`)}</div>
    ${symbols.length ? html`<dl class="sleq-sym">${symbols.map(([k, v]) => html`<div><dt><${MathLine} s=${k}/></dt><dd>${v ? html`<${MathLine} s=${v}/>` : ""}</dd></div>`)}</dl>` : null}
  </div>`;
}

/* ---------- wipe ---------- */
const DIFF_SIZE = 512, GAIN = 4;
function load(url) { return new Promise((ok, no) => { const i = new Image(); i.onload = () => ok(i); i.onerror = no; i.src = url; }); }
/* The real difference between the two files on screen, worked out here in the browser. Same-origin JPEGs, no upload. */
export function useDiff(aUrl, bUrl, canvasRef, on = true, again = 0) {
  const [mean, setMean] = useState(null);
  useEffect(() => {
    if (!on) return undefined; let live = true;
    Promise.all([load(aUrl), load(bUrl)]).then(([a, b]) => {
      if (!live) return; const c = document.createElement("canvas"); c.width = c.height = DIFF_SIZE; const g = c.getContext("2d", { willReadFrequently: true });
      g.drawImage(a, 0, 0, DIFF_SIZE, DIFF_SIZE); const A = g.getImageData(0, 0, DIFF_SIZE, DIFF_SIZE).data; g.drawImage(b, 0, 0, DIFF_SIZE, DIFF_SIZE); const B = g.getImageData(0, 0, DIFF_SIZE, DIFF_SIZE).data;
      const out = new ImageData(DIFF_SIZE, DIFF_SIZE); setMean(diffPixels(A, B, GAIN, out.data));
      if (canvasRef && canvasRef.current) { const t = canvasRef.current; t.width = t.height = DIFF_SIZE; t.getContext("2d").putImageData(out, 0, 0); }
    }).catch(() => { if (live) setMean(null); });
    return () => { live = false; };
  }, [aUrl, bUrl, on, again]);
  return mean;
}
export function Wipe({ a, b, aTag, bTag, mode: fixedMode, onMean, sized = 1024, teach }) {
  const [pos, setPos] = useState(50); const [mode, setMode] = useState("wipe"); const cv = useRef(null); const m = fixedMode || mode; const [moved, setMoved] = useState(false);
  const mean = useDiff(a.url, b.url, cv, true, m);
  useEffect(() => { if (onMean) onMean(mean); }, [mean]);
  const seg = (k, t) => html`<button type="button" aria-pressed=${m === k} onClick=${() => setMode(k)}>${t}</button>`;
  const same = a.id === b.id;
  return html`<div class=${"slw film mode-" + m}>
    <div class=${"slw-stage" + (teach && !moved ? " teach" : "")} style=${{ "--pos": `${pos}%` }}>
      ${m === "diff" ? html`<figure class="slw-diff"><canvas ref=${cv} role="img" aria-label=${`Difference between ${a.label} and ${b.label}, brightened ${GAIN} times`}></canvas><figcaption class="slw-tag d">${mean === 0 ? "No difference: every pixel matches" : `Difference, brightened ${GAIN}x`}</figcaption></figure>` : html`
      <figure class="slw-b"><img src=${b.url} alt=${"B: " + b.label} width=${sized} height=${sized}/><figcaption class="slw-tag r"><b>B</b> ${bTag || b.label}</figcaption></figure>
      <figure class="slw-a"><img src=${a.url} alt=${"A: " + a.label} width=${sized} height=${sized}/><figcaption class="slw-tag l"><b>A</b> ${aTag || a.label}</figcaption></figure>
      <canvas ref=${cv} hidden></canvas>`}
      ${m === "wipe" && html`<div class="slw-handle" aria-hidden="true"><svg viewBox="0 0 34 34"><path d="M14 11l-6 6 6 6M20 11l6 6-6 6"/></svg></div><input class="slw-in" type="range" min="0" max="100" value=${pos} aria-label=${`Wipe between A, ${a.label}, and B, ${b.label}`} onInput=${(e) => { setMoved(true); setPos(+e.target.value); }}/>`}
    </div>
    ${!fixedMode && html`<div class="slw-deck"><span class="slseg dark" role="group" aria-label="How to compare">${seg("wipe", "Wipe")}${seg("side", "Side by side")}${seg("diff", "Difference")}</span><span class="slw-hint">${same ? "A and B are the same render." : m === "wipe" ? "Drag across the picture, or use the arrow keys." : m === "diff" ? "Black means the pixels match." : ""}</span></div>`}
  </div>`;
}
const delta = (x, y) => { const d = y - x; return (d > 0 ? "+" : "") + d.toFixed(1); };
/* The figures the proof sweep recorded for each render, side by side. */
export const ABTable = ({ a, b, seconds }) => html`<table class="slab-t"><thead><tr><th></th><th>A</th><th>B</th><th>B minus A</th></tr></thead><tbody>${[["Brightness", "brightness"], ["Contrast", "contrast"], ["Edge", "edge"]].map(([l, k]) => html`<tr><th>${l}</th><td>${a[k]}</td><td>${b[k]}</td><td>${delta(a[k], b[k])}</td></tr>`)}${seconds ? html`<tr><th>Seconds</th><td>${a.seconds}</td><td>${b.seconds}</td><td></td></tr>` : null}</tbody></table>`;
/* A static half-and-half of two renders, for the highlight cards. */
export const Split = ({ a, b, aTag, bTag }) => html`<div class="slsplit"><img src=${b.url} alt=${"B: " + b.label} loading="lazy" width="512" height="512"/><img class="a" src=${a.url} alt=${"A: " + a.label} loading="lazy" width="512" height="512"/><i aria-hidden="true"></i><span class="slw-tag l"><b>A</b> ${aTag || a.label}</span><span class="slw-tag r"><b>B</b> ${bTag || b.label}</span></div>`;

/* ---------- sigma chart ---------- */
export const SPACE_WORD = { sd_eps: "SD 1.5 and SDXL (noise prediction)", sd3_flow_shift3: "SD3 (flow, shift 3)", flux_shift1_15: "Flux (flow, shift 1.15)" };
const prec = (v) => v == null ? "none" : v >= 100 ? v.toFixed(0) : String(+v.toPrecision(v < 1 ? 3 : 4));
export function SigmaChart({ series, log = true, step = null, setStep, height = 400, compact = false, hot = null, ariaName = "Sigma against step" }) {
  const [ref, W] = useWidth(compact ? 320 : 760); const H = compact ? height : Math.min(height, Math.max(250, Math.round(W * .82))); const L = compact ? 34 : 52, R = compact ? 6 : 14, T = 12, B = compact ? 20 : 30;
  const longest = Math.max(1, ...series.map((s) => s.vals.length - 1)); const flat = series.flatMap((s) => s.vals); const hi = flat.length ? Math.max(...flat) : 1; const pos = flat.filter((x) => x > 0); const lo = pos.length ? Math.min(...pos) : .001;
  const X = (f) => L + f / 100 * (W - L - R), Y = (f) => T + f / 100 * (H - T - B);
  const yOf = (v) => log ? (hi === lo ? 0 : (Math.log(hi) - Math.log(v)) / (Math.log(hi) - Math.log(lo)) * 100) : (1 - v / hi) * 100;
  const ticks = log ? (() => { const o = []; for (let p = Math.floor(Math.log10(lo)); p <= Math.ceil(Math.log10(hi)); p++) { const v = 10 ** p; if (v >= lo * .99 && v <= hi * 1.01) o.push(v); } return o; })() : [0, .25, .5, .75, 1].map((f) => f * hi);
  const xTicks = compact ? [0, longest] : [0, .25, .5, .75, 1].map((f) => Math.round(f * longest));
  const move = (ev) => { if (!setStep) return; const r = ev.currentTarget.getBoundingClientRect(); const i = Math.round(((ev.clientX - r.left) / r.width * W - L) / (W - L - R) * longest); setStep(Math.max(0, Math.min(longest, i))); };
  const key = (ev) => { if (!setStep) return; const d = { ArrowLeft: -1, ArrowRight: 1, Home: -longest, End: longest }[ev.key]; if (d) { ev.preventDefault(); setStep((s) => Math.max(0, Math.min(longest, (s ?? 0) + d))); } };
  const label = series.map((s) => `${s.k} ${step != null ? prec(s.vals[step]) : ""}`).join(", ");
  const slider = setStep ? { role: "slider", tabindex: "0", "aria-valuemin": 0, "aria-valuemax": longest, "aria-valuenow": step ?? 0, "aria-valuetext": `Step ${step ?? 0} of ${longest}: ${label}`, "aria-label": `${ariaName}. Arrow keys move along the steps.`, onKeyDown: key, onPointerMove: move, onPointerDown: move } : { role: "img", "aria-label": `${ariaName}: ${series.map((s) => s.k).join(", ")}` };
  return html`<div class="slchartbox" ref=${ref}><svg class="slc" width=${W} height=${H} viewBox=${`0 0 ${W} ${H}`} ...${slider}>
    <defs>${series.map((s, i) => html`<linearGradient id=${"slg" + i} x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color=${s.color} stop-opacity=".22"/><stop offset="1" stop-color=${s.color} stop-opacity="0"/></linearGradient>`)}</defs>
    ${ticks.map((v) => html`<g><line class="slgrid" x1=${L} x2=${W - R} y1=${Y(yOf(v))} y2=${Y(yOf(v))}/><text class="slaxis" x=${L - 7} y=${Y(yOf(v)) + 4} text-anchor="end">${prec(v)}</text></g>`)}
    ${xTicks.map((n) => html`<text class="slaxis" x=${X(n / longest * 100)} y=${H - (compact ? 4 : 9)} text-anchor=${n === 0 ? "start" : n === longest ? "end" : "middle"}>${compact ? (n === 0 ? "step 0" : "step " + n) : n}</text>`)}
    ${!compact && html`<text class="slaxis strong" x=${W - R} y=${T + 12} text-anchor="end">sigma${log ? ", log scale" : ""}</text>`}
    ${series.length <= 2 && series.map((s, i) => { const pts = curvePoints(s.vals, { log, max: hi, min: lo }).map((p) => [X(p[0]), Y(p[1])]); if (pts.length < 2) return null; return html`<path d=${toPath(pts) + `L${pts[pts.length - 1][0].toFixed(1)} ${H - B}L${pts[0][0].toFixed(1)} ${H - B}Z`} fill=${`url(#slg${i})`} stroke="none"/>`; })}
    ${series.map((s) => { const raw = curvePoints(s.vals, { log, max: hi, min: lo }); const pts = raw.map((p) => [X(p[0]), Y(p[1])]); const dim = hot && hot !== s.k; const big = hot === s.k; return html`<g class=${"slseries" + (dim ? " dim" : "")} key=${s.k}><path class="slline draw" pathLength="1" d=${toPath(pts)} style=${{ stroke: s.color, strokeWidth: big ? 3.5 : 2.4 }}/>${longest <= 30 ? pts.map((p, i) => html`<circle cx=${p[0]} cy=${p[1]} r=${compact ? 1.8 : 2.8} fill=${s.color}/>`) : null}</g>`; })}
    ${step != null && setStep && html`<g class="slcursor"><line x1=${X(step / longest * 100)} x2=${X(step / longest * 100)} y1=${T} y2=${H - B}/>${series.map((s) => { const v = s.vals[step]; if (v == null || (log && !(v > 0))) return null; return html`<circle cx=${X(step / (s.vals.length - 1) * 100)} cy=${Y(yOf(v))} r="5.5" fill="#0b0e0c" stroke=${s.color} stroke-width="2.4"/>`; })}</g>`}
  </svg></div>`;
}
/* Where each schedule puts its steps: one tick per real sigma on one shared axis. */
export function StepRug({ series, log = true }) {
  const flat = series.flatMap((s) => s.vals); const hi = flat.length ? Math.max(...flat) : 1; const pos = flat.filter((x) => x > 0); const lo = pos.length ? Math.min(...pos) : .001;
  const at = (v) => log ? (hi === lo ? 0 : (Math.log(hi) - Math.log(v)) / (Math.log(hi) - Math.log(lo))) * 100 : (1 - v / hi) * 100;
  return html`<div class="slrug" role="img" aria-label=${"Where each schedule places its steps, from high sigma on the left to low sigma on the right: " + series.map((s) => s.k).join(", ")}>
    <div class="slrug-head"><span>Where the steps land</span><span class="r">sigma ${prec(hi)}</span><span class="r2">sigma ${prec(lo)}</span></div>
    ${series.map((s) => html`<div class="slrug-row" key=${s.k}><span class="n" style=${{ color: s.color }}>${s.k}</span><span class="t">${s.vals.filter((v) => !log || v > 0).map((v) => html`<i style=${{ left: at(v) + "%", background: s.color }}></i>`)}</span></div>`)}
  </div>`;
}
export { prec as sigmaWord, curveStats };
