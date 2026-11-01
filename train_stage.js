// The Train page's big pieces: the wipe between base and LoRA, the loss chart, the training stage and the example from our own run. Every number comes from a job the server sent, or from EXAMPLE, which is copied from one real job.
import { useEffect, useMemo, useRef, useState } from "preact/hooks";
import { html } from "./common.js";
import { averageLine, averageWindow, curveNote, fmtClock, fmtDuration, fmtGib, fmtLoss, fmtSpeed, isLive, lossChart, lossTrend, nearestPoint, statusLine } from "./train_logic.js";
import { EXAMPLE } from "./train_example.js";

/** Base on the left of the handle, LoRA on the right. The range input is the control, so it works with keys and touch. */
export function Wipe({ base, lora, baseLabel = "Base only", loraLabel, baseAlt, loraAlt, sized }) {
  const [pos, setPos] = useState(50); const [mode, setMode] = useState("wipe");
  const seg = (m, t) => html`<button type="button" aria-pressed=${mode === m} onClick=${() => setMode(m)}>${t}</button>`;
  return html`<div class=${"tr-wipewrap film mode-" + mode}>
    <div class="tr-wipe teach" style=${{ "--pos": `${pos}%` }}>
      <figure class="tr-wl"><img src=${lora} alt=${loraAlt} width=${sized} height=${sized}/><figcaption class="tr-tag on">${loraLabel}</figcaption></figure>
      <figure class="tr-wb"><img src=${base} alt=${baseAlt} width=${sized} height=${sized}/><figcaption class="tr-tag">${baseLabel}</figcaption></figure>
      ${mode === "wipe" && html`<div class="tr-handle" aria-hidden="true"><svg viewBox="0 0 34 34"><path d="M14 11l-6 6 6 6M20 11l6 6-6 6"/></svg></div><input class="tr-wiper" type="range" min="0" max="100" value=${pos} aria-label="Wipe between the base and the LoRA" onInput=${(e) => setPos(+e.target.value)}/>`}
    </div>
    <div class="tr-wipedeck"><span class="tr-seg" role="group" aria-label="How to compare">${seg("wipe", "Wipe")}${seg("side", "Side by side")}</span>${mode === "wipe" && html`<span class="tr-hint">Drag across the picture, or use the arrow keys.</span>`}</div>
  </div>`;
}

export function LossChart({ job, tall, plain }) {
  const box = useRef(); const [w, setW] = useState(720); const [hover, setHover] = useState(null);
  useEffect(() => { if (!box.current || typeof ResizeObserver === "undefined") return; const o = new ResizeObserver((es) => setW(Math.max(260, Math.round(es[0].contentRect.width)))); o.observe(box.current); return () => o.disconnect(); }, []);
  const compact = w < 480;
  const h = tall ? (compact ? 250 : Math.min(460, Math.max(300, Math.round(w * 0.46)))) : compact ? 130 : 170;
  const c = useMemo(() => lossChart(job.curve, job.total, w, h, compact || !tall ? { l: 44, r: 10, t: 12, b: 26 } : { l: 60, r: 18, t: 18, b: 34 }), [job.curve, job.total, w, h]);
  const win = averageWindow(job.total);
  const avg = useMemo(() => averageLine(c, win), [c, win]);
  const head = !c.empty && c.points[c.points.length - 1];
  const move = (e) => { const r = e.currentTarget.getBoundingClientRect(); setHover(nearestPoint(c, e.clientX - r.left)); };
  const unfinished = head && head.step < c.xMax;
  return html`<figure class=${"tr-chart" + (tall ? " tall" : "") + (isLive(job) ? " live" : "")} ref=${box}>
    ${!plain && html`<figcaption><b>Training loss by step</b><span class="tr-legend"><span class="tr-k raw">Each value ComfyUI reported</span><span class="tr-k avg">Average of the last ${win} steps, worked out on this page</span></span></figcaption>`}
    ${c.empty ? html`<div class="tr-chart-empty" style=${{ height: `${h}px` }}><span>No loss value yet. The curve appears when the first step is logged.</span></div>` : html`<svg width=${w} height=${c.h} viewBox="0 0 ${w} ${c.h}" role="img" aria-label=${`Training loss by step. Latest ${fmtLoss(job.last_loss)} at step ${job.step} of ${job.total}.`} onPointerMove=${move} onPointerLeave=${() => setHover(null)}>
      <defs><pattern id=${"trhatch" + (tall ? "t" : "s")} width="9" height="9" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="9" class="tr-hatch"/></pattern></defs>
      ${c.yTicks.map((t) => html`<g><line class="tr-gl" x1=${c.pad.l} x2=${w - c.pad.r} y1=${t.y} y2=${t.y}/><text class="tr-axis" x=${c.pad.l - 8} y=${t.y + 4} text-anchor="end">${t.v.toFixed(3)}</text></g>`)}
      ${c.xTicks.map((t) => html`<g><line class="tr-gl v" x1=${t.x} x2=${t.x} y1=${c.pad.t} y2=${c.h - c.pad.b}/><text class="tr-axis" x=${t.x} y=${c.h - 8} text-anchor=${t.s === 0 ? "start" : t.s === c.xMax ? "end" : "middle"}>${t.s}</text></g>`)}
      ${unfinished && html`<g><rect x=${head.x} y=${c.pad.t} width=${w - c.pad.r - head.x} height=${c.h - c.pad.t - c.pad.b} fill=${`url(#trhatch${tall ? "t" : "s"})`}/>${w - c.pad.r - head.x > 110 && html`<text class="tr-togo" x=${(head.x + w - c.pad.r) / 2} y=${(c.pad.t + c.h - c.pad.b) / 2} text-anchor="middle">${isLive(job) ? "Still to run" : "Not run"}</text>`}</g>`}
      <path class="tr-line" d=${c.path}/>
      ${avg.path && html`<path class="tr-avg" d=${avg.path}/>`}
      ${unfinished && html`<g><line class="tr-headline" x1=${head.x} x2=${head.x} y1=${c.pad.t} y2=${c.h - c.pad.b}/><circle class="tr-headdot" cx=${head.x} cy=${head.y} r="5"/></g>`}
      ${hover && html`<g><line class="tr-cross" x1=${hover.x} x2=${hover.x} y1=${c.pad.t} y2=${c.h - c.pad.b}/><circle class="tr-dot" cx=${hover.x} cy=${hover.y} r="4"/></g>`}
    </svg>`}
    ${hover && html`<div class="tr-tip" style=${{ left: `${Math.min(hover.x + 10, w - 120)}px` }}>step <b>${hover.step}</b><br/>loss <b>${hover.loss.toFixed(4)}</b></div>`}
  </figure>`;
}

/** What a noisy curve does and does not mean, with the numbers from our own run. */
function HowToRead() {
  const t = lossTrend(EXAMPLE.loss.map((v, i) => [i + 1, v]));
  return html`<aside class="tr-read" aria-label="How to read this curve"><h3>How to read this</h3>
    <p class="tr-readbig">It is meant to look messy.</p>
    <p>Each step tests the model at a random noise level. Some levels are harder than others, so the number jumps.</p>
    <p><b>A flat line does not mean it failed.</b> It does not prove it worked either. In our own ${EXAMPLE.steps}-step run the average went from ${t.first.toFixed(4)} in the first tenth to ${t.last.toFixed(4)} in the last, and the pictures still changed.</p>
    <p>The A/B at the end is the real test. This training graph makes no sample pictures on the way, so that is your first look.</p>
    <p>One reading does mean trouble: the loss going to not-a-number. This page says so if it happens.</p></aside>`;
}

export function Run({ job, onCancel, cancelling, baseLabel, first }) {
  const live = isLive(job), bad = job.state === "error" || job.state === "lost", s = job.settings || {};
  const frac = job.total ? Math.min(1, job.step / job.total) : 0, cells = 60, lit = Math.floor(frac * cells);
  const clock = live ? fmtClock(job.eta_s) : fmtClock(job.elapsed_s);
  return html`<section class=${"tr-stage film" + (live ? " is-live" : "") + (bad ? " is-bad" : "")} id="tr-run" aria-labelledby="tr-runh">
    <div class="tr-ticks" role="progressbar" aria-label="Training steps" aria-valuemin="0" aria-valuemax=${job.total} aria-valuenow=${job.step}>${Array.from({ length: cells }, (_, i) => html`<i class=${i < lit ? "on" : i === lit && live && job.step ? "now" : ""}></i>`)}</div>
    <header class="tr-stagehead">
      <div class="tr-stagetitle"><p class="tr-kicker">${live ? "Training now" : first ? "This run" : "The last run"}</p><h2 id="tr-runh">${job.name}</h2>
        <p class=${"tr-status " + (bad ? "tr-err" : "")} role="status">${statusLine(job)}</p>
        <p class="tr-specs">${job.pictures} pictures, ${baseLabel || job.base}, ${s.size} px, rank ${s.rank}, batch ${s.batch}, learning rate ${s.learning_rate}, seed ${s.seed}${job.prior_steps ? `, on top of ${job.prior_steps} earlier steps` : ""}</p></div>
      <div class="tr-bigs">
        <div class="tr-big"><b>${job.step}</b><span>of ${job.total} steps</span></div>
        <div class="tr-big time">${clock ? html`<b>${clock}</b>` : html`<b class="word">Not measured yet</b>`}<span>${live ? "left, from the measured speed" : "taken, loading included"}</span></div>
      </div>
    </header>
    ${job.loss_nan && html`<p class="tr-alarm" role="alert">The loss went to not-a-number. This LoRA is likely broken, so cancel it or do not trust the result.</p>`}
    <div class="tr-plot"><div class="tr-plotmain"><${LossChart} job=${job} tall=${true}/>
        <p class="small tr-note">${curveNote(job)}</p>
        ${job.curve && job.curve.length > 0 && html`<details class="small tr-numbers"><summary>Show the numbers</summary><div class="tr-nums">${job.curve.map(([st, v]) => html`<span>${st}: ${v == null ? "not a number" : v.toFixed(4)}</span>`)}</div></details>`}</div>
      <${HowToRead}/></div>
    <dl class="tr-stats"><div><dt>Latest loss</dt><dd>${fmtLoss(job.last_loss)}</dd></div><div><dt>Speed</dt><dd>${fmtSpeed(job.s_per_step)}</dd></div><div><dt>${live ? "Running for" : "Time taken"}</dt><dd>${fmtDuration(job.elapsed_s)}</dd></div><div><dt>Peak VRAM, whole card</dt><dd>${fmtGib(job.peak_vram_gib)}</dd></div></dl>
    ${live && html`<div class="tr-stagefoot"><button class="btn" disabled=${job.state === "cancelling" || cancelling} onClick=${onCancel}>Cancel training</button><p class="small">Cancel loses the steps of this run. The training node has no save point before the end. This job holds the GPU until it ends, and other ComfyUI jobs wait behind it.</p></div>`}
  </section>`;
}

/** The empty state: our real run, labelled as ours. */
export function Example() {
  const e = EXAMPLE, t = lossTrend(e.loss.map((v, i) => [i + 1, v]));
  const job = { curve: e.loss.map((v, i) => [i + 1, v]), total: e.steps, step: e.steps, last_loss: e.loss[e.loss.length - 1], state: "done" };
  return html`<div class="tr-example film" aria-label="An example from our own run">
    <div class="perfs" aria-hidden="true"></div>
    <div class="tr-exhero">
      <${Wipe} base=${e.same.base} lora=${e.same.lora} loraLabel=${`With the LoRA, strength ${e.same.strength}`} baseAlt="Lighthouse rendered on the SDXL base alone" loraAlt="The same prompt and seed with the brass lighthouse LoRA" sized="960"/>
      <div class="tr-exfacts">
        <p class="tr-kicker">Our own run, not yours</p>
        <h2>${e.name}</h2>
        <dl class="tr-exnums"><div><dd>${e.pictures}</dd><dt>pictures</dt></div><div><dd>${e.steps}</dd><dt>steps</dt></div><div><dd>~3 min</dd><dt>on our ${e.card_gb} GB card</dt></div><div><dd>SDXL</dd><dt>${e.size} px, rank ${e.rank}</dt></div></dl>
        <p class="tr-exprompt">Same seed (${e.same.seed}) and same sampler, once on the base and once with the LoRA. Prompt: <q>${e.same.prompt}</q></p>
      </div>
    </div>
    <div class="tr-exlow">
      <div class="tr-excurve"><h3>The loss from that run</h3><${LossChart} job=${job} plain=${true}/><p>All ${e.steps} real values. Noisy and flat: the average went from ${t.first.toFixed(4)} in the first tenth to ${t.last.toFixed(4)} in the last. The pictures changed anyway, so a flat curve is not a failed run.</p></div>
      <div class="tr-exover"><h3>And it overfits</h3><div class="tr-expair"><figure><img src=${e.other.base} alt="A harbour town in the rain on the SDXL base alone" loading="lazy" width="640" height="640"/><figcaption>Base only</figcaption></figure><figure><img src=${e.other.lora} alt="The same prompt and seed with the LoRA: brass towers appear in the harbour town" loading="lazy" width="640" height="640"/><figcaption>With the LoRA</figcaption></figure></div><p>We asked for a harbour town, not a lighthouse, and brass towers turned up. ${e.pictures} pictures of one subject teach one idea. Prompt: <q>${e.other.prompt}</q> Seed ${e.other.seed}, strength ${e.other.strength}.</p></div>
    </div>
    <p class="tr-exnote">These are our renders from one run on 1 November 2026. Yours depend on your pictures, your settings and your card.</p>
  </div>`;
}
