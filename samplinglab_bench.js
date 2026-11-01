/* Sampling Lab views: sigma curves, solver bench, renders. All numbers come from measures.json and renders.json, computed by core's own code or recorded by the proof sweep. */
import { useEffect, useMemo, useState } from "preact/hooks";
import { html } from "./common.js";
import { assignSlots, togglePick, MAX_SERIES, benchRows, sortBench, groupRenders, baselineFor, convergence, curveStats } from "./samplinglab_logic.js";
import { SigmaChart, StepRug, Wipe, ABTable, SPACE_WORD, sigmaWord, useWidth } from "./samplinglab_kit.js";

const fmt = (v) => v == null ? "n/a" : String(v);
const COMPARE_SETUPS = [
  { t: "karras on a flow model", space: "sd3_flow_shift3", steps: "20", picked: ["simple", "beta", "kl_optimal", "karras"], log: false },
  { t: "linear_quadratic's last step", space: "sd_eps", steps: "20", picked: ["karras", "normal", "linear_quadratic"], log: true },
  { t: "ddim_uniform's lower start", space: "sd_eps", steps: "20", picked: ["normal", "ddim_uniform"], log: true },
  { t: "The classic five", space: "sd_eps", steps: "20", picked: ["normal", "karras", "exponential", "beta", "simple"], log: true },
];

export function Curves({ measures }) {
  const sch = measures.schedules || {}; const spaces = Object.keys(sch);
  const [space, setSpace] = useState(spaces[0]); const [steps, setSteps] = useState("20"); const [log, setLog] = useState(true); const [picked, setPicked] = useState(["normal", "karras", "exponential", "beta", "simple"]); const [slots, setSlots] = useState({}); const [step, setStep] = useState(3); const [hot, setHot] = useState(null);
  useEffect(() => setSlots((s) => assignSlots(s, picked)), [picked]);
  useEffect(() => { if (space === undefined && spaces[0]) setSpace(spaces[0]); }, [spaces.length]);
  useEffect(() => setStep((s) => Math.min(s ?? 0, +steps)), [steps]);
  if (!spaces.length) return html`<p class="slnote">The curve data isn't built yet.</p>`;
  const sp = sch[space] || sch[spaces[0]]; const row = sp.by_steps[steps] || {}; const extra = (sp.extras_by_steps && sp.extras_by_steps[steps]) || {};
  const all = { ...row, ...extra }; const names = Object.keys(all).filter((k) => Array.isArray(all[k])); const live = picked.filter((k) => Array.isArray(all[k]));
  const color = (k) => `var(--s${(slots[k] ?? 0) + 1})`;
  const series = live.map((k) => ({ k, vals: all[k], color: color(k) }));
  const core = Object.keys(row).filter((k) => Array.isArray(row[k])), more = names.filter((k) => !core.includes(k));
  const legend = (k) => html`<button key=${k} aria-pressed=${picked.includes(k)} onClick=${() => setPicked((p) => togglePick(p, k))} onPointerEnter=${() => setHot(picked.includes(k) ? k : null)} onPointerLeave=${() => setHot(null)} onFocus=${() => setHot(picked.includes(k) ? k : null)} onBlur=${() => setHot(null)}><i style=${picked.includes(k) && slots[k] !== undefined ? { background: color(k), borderColor: "transparent" } : null}></i>${k}</button>`;
  return html`<div class="slview">
    <section class="slscope film">
      <header class="slscope-top">
        <div class="slscope-title"><h2>Sigma curves</h2><p>How much noise is left at each step, from ComfyUI's own scheduler code on the CPU with the model's real sigma range. <span class="slp proof">Measured here</span></p></div>
        <div class="slscope-ctl">
          <label class="slctl"><span>Model type</span><select value=${space} onChange=${(ev) => setSpace(ev.target.value)}>${spaces.map((s) => html`<option value=${s}>${SPACE_WORD[s] || s}</option>`)}</select></label>
          <div class="slctl"><span id="sl-steps">Steps</span><div class="slseg dark" role="group" aria-labelledby="sl-steps">${Object.keys(sp.by_steps).map((n) => html`<button aria-pressed=${steps === n} onClick=${() => setSteps(n)}>${n}</button>`)}</div></div>
          <div class="slctl"><span id="sl-scale">Scale</span><div class="slseg dark" role="group" aria-labelledby="sl-scale"><button aria-pressed=${log} onClick=${() => setLog(true)}>Log</button><button aria-pressed=${!log} onClick=${() => setLog(false)}>Linear</button></div></div>
        </div>
      </header>
      <div class="slscope-main">
        <div class="slscope-plot">
          <${SigmaChart} series=${series} log=${log} step=${step} setStep=${setStep} height=${440} hot=${hot} ariaName="Sigma against step"/>
          ${series.length ? html`<${StepRug} series=${series} log=${log}/>` : html`<p class="slnote pad">Pick a schedule below to draw it.</p>`}
        </div>
        <aside class="slread" aria-label="Readout">
          <div class="slread-step"><button aria-label="Previous step" onClick=${() => setStep((s) => Math.max(0, (s ?? 0) - 1))}>‹</button><div><b>${step ?? 0}</b><span>of ${steps} steps</span></div><button aria-label="Next step" onClick=${() => setStep((s) => Math.min(+steps, (s ?? 0) + 1))}>›</button></div>
          <table class="slread-t"><thead><tr><th>Schedule</th><th class="n">Sigma here</th><th class="n">Last before 0</th></tr></thead><tbody>${series.map((s) => { const st = curveStats(s.vals); return html`<tr class=${hot === s.k ? "hot" : ""}><td><i style=${{ background: s.color }}></i>${s.k}</td><td class="n">${sigmaWord(s.vals[step])}</td><td class="n">${sigmaWord(st && st.last)}</td></tr>`; })}</tbody></table>
          <div class="slsetups"><span class="slkick">Set up a comparison</span><div class="slbtnrow col">${COMPARE_SETUPS.map((c) => html`<button class="slghost" onClick=${() => { setSpace(c.space); setSteps(c.steps); setPicked(c.picked); setLog(c.log); }}>${c.t}</button>`)}<button class="slghost" onClick=${() => setPicked([])} disabled=${!picked.length}>Clear the chart</button></div></div>
        </aside>
      </div>
      <div class="slscope-pick">
        <div class="slpickrow"><span class="slkick">Core schedulers</span><div class="sllegend" role="group" aria-label=${`Pick schedulers, at most ${MAX_SERIES}`}>${core.map(legend)}</div></div>
        ${more.length ? html`<div class="slpickrow"><span class="slkick">Tables and formulas</span><div class="sllegend" role="group" aria-label="More schedules">${more.map(legend)}</div></div>` : null}
      </div>
    </section>
    <div class="slreadme"><p>Sigma is how much noise is left. Schedulers differ in where they spend their steps: a line that drops fast early saves its steps for fine detail near the end.</p><p>${log ? "On the log scale the final sigma of 0 can't be drawn, so each line stops one point early. " : ""}${picked.length >= MAX_SERIES ? "Eight is the most the chart can tell apart. Drop one to add another." : ""} A curve is arithmetic, not a verdict: it shows the schedule, not how a picture will look.</p></div>
    <details class="sldet"><summary>The numbers as a table</summary><div class="sltablewrap"><table class="sltable"><thead><tr><th>Scheduler</th><th>Sigmas, first to last</th></tr></thead><tbody>${series.map((s) => html`<tr><td>${s.k}</td><td class="wrap mono">${s.vals.join(", ")}</td></tr>`)}</tbody></table></div></details>
    <${Ancestral} measures=${measures}/>
  </div>`;
}
function Ancestral({ measures }) {
  const a = measures.ancestral_sd_eps_20 || {}; const names = Object.keys(a); const [n, setN] = useState("karras"); const [ref, W] = useWidth(720); if (!names.length || !a[n]) return null;
  const rows = a[n]; const hi = Math.max(...rows.map((r) => r[0]), 1e-6); const H = 210, L = 44, T = 10, B = 22, bw = (W - L) / rows.length; const y = (v) => (H - B) - v / hi * (H - B - T);
  return html`<section class="slpanel"><div class="slpanel-head"><div><h3>How an ancestral sampler splits each step</h3><p class="slnote">From <code>get_ancestral_step</code> at eta 1, SD and SDXL, 20 steps: the sampler overshoots to sigma down, then adds noise of size sigma up, landing on the scheduled sigma. <span class="slp proof">Measured here</span></p></div><label class="slctl"><span>Scheduler</span><select value=${n} onChange=${(e) => setN(e.target.value)}>${names.map((k) => html`<option>${k}</option>`)}</select></label></div>
    <div ref=${ref}><svg class="slbars" width=${W} height=${H} viewBox=${`0 0 ${W} ${H}`} role="img" aria-label=${`Sigma down and fresh noise sigma up per step, ${n}`}><line class="slgrid" x1=${L} x2=${W} y1=${H - B} y2=${H - B}/><text class="slaxis" x=${L - 6} y=${y(hi) + 8} text-anchor="end">${+hi.toPrecision(3)}</text><text class="slaxis" x=${L - 6} y=${H - B} text-anchor="end">0</text><text class="slaxis" x=${L} y=${H - 6}>step 1</text><text class="slaxis" x=${W} y=${H - 6} text-anchor="end">step ${rows.length}</text>
      ${rows.map((r, i) => { const x = L + i * bw; const w2 = Math.max(2, bw / 2 - 2); const yd = y(r[2]), yu = y(r[3]); return html`<g><rect x=${x + 1} y=${yd} width=${w2} height=${Math.max(0, H - B - yd)} rx="1.5" class="b1"><title>Step ${i + 1}: down to ${r[2]}</title></rect><rect x=${x + 3 + w2} y=${yu} width=${w2} height=${Math.max(0, H - B - yu)} rx="1.5" class="b2"><title>Step ${i + 1}: fresh noise ${r[3]}</title></rect></g>`; })}</svg></div>
    <div class="slkey"><span><i class="b1"></i>Sigma it steps down to</span><span><i class="b2"></i>Fresh noise added back</span></div></section>`;
}

/* ---------- solver bench ---------- */
const PER_STEP = (p) => p == null ? 3 : p <= 1 ? 1 : p <= 2 ? 2 : 3;
function ConvChart({ rows, hot, setHot }) {
  const [ref, W] = useWidth(760); const H = W < 560 ? 300 : 380; const L = 54, R = 16, T = 14, B = 36;
  const all = rows.flatMap((r) => r.pts); if (!all.length) return null;
  const x0 = Math.min(...all.map((p) => p[0])), x1 = Math.max(...all.map((p) => p[0])), y0 = Math.min(...all.map((p) => p[1])), y1 = Math.max(...all.map((p) => p[1]));
  const X = (v) => L + (Math.log(v) - Math.log(x0)) / (Math.log(x1) - Math.log(x0) || 1) * (W - L - R); const Y = (v) => T + (Math.log(y1) - Math.log(v)) / (Math.log(y1) - Math.log(y0) || 1) * (H - T - B);
  const decade = []; for (let p = Math.floor(Math.log10(y0)); p <= Math.ceil(Math.log10(y1)); p++) { const v = 10 ** p; if (v >= y0 * .98 && v <= y1 * 1.02) decade.push(v); }
  const xs = [5, 10, 20, 40, 80, 160].filter((v) => v >= x0 * .98 && v <= x1 * 1.02); const hr = rows.find((r) => r.name === hot);
  const near = (ev) => { const b = ev.currentTarget.getBoundingClientRect(); const px = (ev.clientX - b.left) / b.width * W, py = (ev.clientY - b.top) / b.height * H; let best = null, d = 900; for (const r of rows) for (const p of r.pts) { const q = (X(p[0]) - px) ** 2 + (Y(p[1]) - py) ** 2; if (q < d) { d = q; best = r.name; } } setHot(best); };
  return html`<div ref=${ref} class="slconv"><svg width=${W} height=${H} viewBox=${`0 0 ${W} ${H}`} role="img" aria-label=${"Error against model calls on log scales for " + rows.length + " deterministic solvers. The table below holds every number."} onPointerMove=${near} onPointerLeave=${() => setHot(null)}>
    ${decade.map((v) => html`<g><line class="slgrid" x1=${L} x2=${W - R} y1=${Y(v)} y2=${Y(v)}/><text class="slaxis" x=${L - 7} y=${Y(v) + 4} text-anchor="end">${+v.toPrecision(2)}</text></g>`)}
    ${xs.map((v) => html`<g><line class="slgrid" y1=${T} y2=${H - B} x1=${X(v)} x2=${X(v)}/><text class="slaxis" x=${X(v)} y=${H - B + 16} text-anchor="middle">${v}</text></g>`)}
    <text class="slaxis strong" x=${W - R} y=${H - 4} text-anchor="end">model calls</text><text class="slaxis strong" x=${W - R} y=${T + 10} text-anchor="end">error to exact, log scale</text>
    ${rows.map((r) => { const d = "M" + r.pts.map((p) => X(p[0]).toFixed(1) + " " + Y(p[1]).toFixed(1)).join("L"); const on = hot === r.name; return html`<g key=${r.name} class=${"slcv k" + PER_STEP(r.perStep) + (hot && !on ? " dim" : "") + (on ? " on" : "")}><path d=${d}/>${r.pts.map((p) => html`<circle cx=${X(p[0])} cy=${Y(p[1])} r=${on ? 4 : 2.4}/>`)}</g>`; })}
    ${hr && html`<text class="slcvname" x=${Math.min(W - R, X(hr.pts[hr.pts.length - 1][0]) + 0)} y=${Y(hr.pts[hr.pts.length - 1][1]) - 10} text-anchor="end">${hr.name}, slope ${hr.slope}</text>`}
  </svg></div>`;
}
function NoiseSpectra({ measures }) {
  const n = measures.noise_spectra || {}; const names = Object.keys(n); if (!names.length) return null;
  return html`<section class="slpanel"><div class="slpanel-head"><div><h3>Is core's noise really white?</h3><p class="slnote">Radial power of each noise source, low frequencies on the left, relative to flat. A bar at the line means that band holds its fair share. <span class="slp proof">Measured here</span></p></div></div>
    <div class="slspectra">${names.map((k) => { const s = n[k]; const hi = 1.2; return html`<figure><figcaption><b>${k}</b><span>mean ${s.mean}, std ${s.std}</span></figcaption><div class="slspec" role="img" aria-label=${`${k}: band powers from ${Math.min(...s.radial_power_relative)} to ${Math.max(...s.radial_power_relative)} relative to flat`}><i class="ref" style=${{ bottom: 1 / hi * 100 + "%" }}></i>${s.radial_power_relative.map((v) => html`<b style=${{ height: v / hi * 100 + "%" }} title=${String(v)}></b>`)}</div></figure>`; })}</div></section>`;
}
export function Bench({ measures }) {
  const [space, setSpace] = useState("eps"); const [sort, setSort] = useState(["calls20", 1]); const [hot, setHot] = useState(null);
  const rows = useMemo(() => sortBench(benchRows(measures.solvers, space), sort[0], sort[1]), [measures, space, sort]); const conv = useMemo(() => convergence(measures.solvers, space), [measures, space]);
  const th = (k, l, cls) => html`<th class=${cls || ""} aria-sort=${sort[0] === k ? (sort[1] > 0 ? "ascending" : "descending") : "none"}><button onClick=${() => setSort(([a, d]) => [k, a === k ? -d : 1])}>${l}${sort[0] === k ? (sort[1] > 0 ? " ↑" : " ↓") : ""}</button></th>`;
  if (!rows.length) return html`<p class="slnote">The bench data isn't built yet.</p>`;
  const maxE = Math.max(...rows.map((r) => r.rmse || 0), 1e-9);
  return html`<div class="slview">
    <section class="slscope film">
      <header class="slscope-top"><div class="slscope-title"><h2>Solver bench</h2><p>${rows.length} core samplers, run by ComfyUI's own code on a problem with a known exact answer. No picture and no neural network. <span class="slp proof">Measured here</span></p></div>
        <div class="slscope-ctl"><div class="slctl"><span id="sl-bs">Problem</span><div class="slseg dark" role="group" aria-labelledby="sl-bs"><button aria-pressed=${space === "eps"} onClick=${() => setSpace("eps")}>Noise prediction, Karras</button><button aria-pressed=${space === "flow"} onClick=${() => setSpace("flow")}>Flow, simple, shift 3</button></div></div></div></header>
      <${ConvChart} rows=${conv} hot=${hot} setHot=${setHot}/>
      <div class="slkey film-key"><span><i class="k1"></i>1 model call per step</span><span><i class="k2"></i>Up to 2 calls</span><span><i class="k3"></i>More than 2, or adaptive</span><span class="slnote">Deterministic solvers only. Further down and left means less error for fewer calls on this toy.</span></div>
    </section>
    <div class="slreadme"><p>Data drawn from a plain Gaussian, so the perfect denoiser can be written down. It measures how a solver follows the equation and what it costs in model calls.</p><p><b>It says nothing about how pictures look, and a low number here does not mean a better picture.</b> Stochastic samplers have no single exact path, so they get a variance error instead.</p></div>
    <p class="slswipe slnote">Swipe the table sideways for every column.</p>
    <div class="sltablewrap sticky1"><table class="sltable bench"><thead><tr>${th("name", "Sampler")}${th("calls20", "Model calls, 20 steps", "n")}${th("perStep", "Calls per step", "n")}${th("det", "Kind")}${th("rmse", "Error to exact, 20 steps", "n")}<th class="n">Error at 5, 10, 20, 40 steps</th>${th("slope", "Slope", "n")}${th("varErr", "Variance error, 20 steps", "n")}</tr></thead>
      <tbody>${rows.map((r) => r.error ? html`<tr><td>${r.name}</td><td colspan="7">Did not run on the toy: ${r.error}</td></tr>` : html`<tr class=${hot === r.name ? "hot" : ""} onPointerEnter=${() => setHot(r.det ? r.name : null)} onPointerLeave=${() => setHot(null)}><td>${r.name}</td><td class="n">${r.calls20}</td><td class="n">${r.perStep}</td><td><span class=${"slkind " + (r.det ? "d" : "s")}>${r.det ? "Deterministic" : "Stochastic"}</span></td><td class="n bar">${r.rmse != null ? html`<i style=${{ width: Math.max(1, r.rmse / maxE * 100) + "%" }}></i>` : null}<span>${fmt(r.rmse)}</span></td><td class="n">${r.rmseCurve ? r.rmseCurve.join(", ") : "n/a"}</td><td class="n">${r.det ? fmt(r.slope) : "n/a"}</td><td class="n">${r.varErr}</td></tr>`)}</tbody></table></div>
    <${NoiseSpectra} measures=${measures}/>
  </div>`;
}

/* ---------- renders ---------- */
const SETS = { sampler: "Samplers", scheduler: "Schedulers", guidance: "Guidance", flow: "Flow model" };
export function Renders({ renders, rest }) {
  const groups = useMemo(() => groupRenders(renders.renders), [renders]); const sets = Object.keys(SETS).filter((k) => groups[k]);
  const [set, setSet] = useState(rest[0] && SETS[rest[0]] ? rest[0] : null); const [aId, setA] = useState(rest[1] || null); const [bId, setB] = useState(rest[2] || null); const [turn, setTurn] = useState("b"); const [mean, setMean] = useState(null);
  useEffect(() => { if (rest[0] && SETS[rest[0]]) { setSet(rest[0]); setA(rest[1] || null); setB(rest[2] || null); setTurn("b"); } }, [rest.join("/")]);
  if (!sets.length) return html`<p class="slnote">No proof renders yet. This page only shows real ones.</p>`;
  const cur = set && groups[set] ? set : sets[0]; const rows = groups[cur]; const base = baselineFor(rows); const a = rows.find((r) => r.id === aId) || base; const b = rows.find((r) => r.id === bId) || rows.find((r) => r !== a) || a;
  const pick = (r) => { if (turn === "a") { setA(r.id); setTurn("b"); } else { setB(r.id); setTurn("a"); } };
  const m = renders.models && renders.models[a.model]; const maxD = Math.max(...rows.map((r) => r.diff_to_base || 0), 1); const same = a === b; const identical = b.identical_to && b.identical_to.includes(a.id);
  const setup = (r) => [r.sampler, r.scheduler, "CFG " + r.cfg, ...(r.patches || []).map((p) => p[0]), r.guider].filter(Boolean).join(" · ");
  const recorded = !same && (a === base ? b.diff_to_base : b === base ? a.diff_to_base : null);
  return html`<div class="slview">
    <section class="sltheatre film">
      <div class="sltheatre-pic"><${Wipe} key=${cur} a=${a} b=${b} onMean=${setMean} teach/></div>
      <div class="sltheatre-side">
        <div class="slctl full"><span id="sl-set">Render set, one model each</span><div class="slseg dark wrap" role="group" aria-labelledby="sl-set">${sets.map((k) => html`<button aria-pressed=${cur === k} onClick=${() => { setSet(k); setA(null); setB(null); setTurn("b"); }}>${SETS[k]} <small>${groups[k].length}</small></button>`)}</div></div>
        <h2>${same ? a.label : html`${a.label} <em>against</em> ${b.label}`}</h2>
        <div class="slfigs"><div><b class=${identical || mean === 0 ? "gold" : ""}>${mean == null ? "…" : mean.toFixed(mean < 10 ? 2 : 1)}</b><span>mean difference of 255, worked out in this browser from the two JPEGs at 512 px</span></div>${recorded != null ? html`<div><b>${recorded}</b><span>recorded by the sweep at full size</span></div>` : null}</div>
        ${identical ? html`<p class="slsame">These two are identical, pixel for pixel.</p>` : null}
        <${ABTable} a=${a} b=${b} seconds/>
        <dl class="slkv"><dt>A</dt><dd>${setup(a)}</dd><dt>B</dt><dd>${setup(b)}</dd></dl>
        ${[a, b].filter((r, i) => (i === 0 || !same) && (r.note || r.seen)).map((r) => html`<p class="slseen"><b>${r.label}:</b> ${r.note} ${r.seen ? "What we saw: " + r.seen : ""}</p>`)}
        <div class="slpills"><span class="slp proof">Measured here</span><span class="slp">One seed, one prompt</span></div>
      </div>
    </section>
    <section class="slsheet film" aria-label="Contact sheet">
      <div class="slsheet-head"><h3>Contact sheet</h3><div class="slctl row"><span id="sl-next">The next picture sets</span><div class="slseg dark" role="group" aria-labelledby="sl-next"><button aria-pressed=${turn === "a"} onClick=${() => setTurn("a")}>A</button><button aria-pressed=${turn === "b"} onClick=${() => setTurn("b")}>B</button></div></div><button class="slghost" onClick=${() => { setA(null); setB(null); setTurn("b"); }}>Back to the baseline</button><span class="slnote">The bar under each frame is its recorded distance from the baseline, ${base.label}.</span></div>
      <div class="slthumbs">${rows.map((r) => html`<button key=${r.id} class="slthumb" aria-label=${`Set ${turn.toUpperCase()} to ${r.label}`} data-pick=${r === a ? "a" : r === b ? "b" : null} onClick=${() => pick(r)}><span class="pic"><img src=${r.url} alt="" loading="lazy" width="200" height="200"/>${r === a ? html`<em>A</em>` : r === b ? html`<em class="b">B</em>` : null}</span><span class="nm">${r.label}</span><span class="dbar"><i style=${{ width: (r.diff_to_base || 0) / maxD * 100 + "%" }}></i></span><span class="dn">${r.baseline ? "baseline" : r.diff_to_base}</span></button>`)}</div>
    </section>
    <section class="slpanel slsame-set"><h3>Same in all of these</h3><dl class="slkv"><dt>Model</dt><dd>${m ? m.name : a.model}${m ? ", " + m.licence : ""}</dd><dt>Seed</dt><dd>${renders.seed}</dd><dt>Steps</dt><dd>${renders.steps}</dd><dt>Prompt</dt><dd>${renders.prompt}</dd>${m && m.note ? html`<dt>Note</dt><dd>${m.note}</dd>` : null}</dl>
      <p class="slnote">Real renders on this machine, measured here. One seed and one prompt show a difference. They don't prove one method is better. ${renders.timing || ""}</p>${renders.pack_lab ? html`<p class="slwarn"><b>No pack method is in these renders.</b> ${renders.pack_lab.why}</p>` : null}</section>
  </div>`;
}
