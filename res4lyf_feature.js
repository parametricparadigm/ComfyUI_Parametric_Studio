// RES4LYF page, the feature pieces: the wipe, the plates, the step diagrams, the toy solver, the Bongmath walk-through and the node map. Pictures come from our own gallery file; the math is drawn or computed here, with no code from the pack.
import { useMemo, useState } from "preact/hooks";
import { html } from "./common.js";
import { GALLERY } from "./res4lyf_gallery.js";
import { findRender, storiesFor, nodeMap, toyPath, toyExact, TOY_METHODS } from "./res4lyf_logic.js";

const pretty = (name) => name.replace("_", " ");

export function Wipe({ a, b, start = 50, note }) {
  const [pos, setPos] = useState(start), [mode, setMode] = useState("wipe");
  const seg = (m, t) => html`<button type="button" aria-pressed=${mode === m} onClick=${() => setMode(m)}>${t}</button>`;
  return html`<div class=${"r4-wipewrap mode-" + mode}>
    <div class="r4-wipe teach" style=${{ "--r4pos": `${pos}%` }}>
      <figure class="r4-wr"><img src=${b.src} alt=${b.what} width="768" height="768"/><figcaption class="r4-wtag on">${pretty(b.name)}</figcaption></figure>
      <figure class="r4-wl"><img src=${a.src} alt=${a.what} width="768" height="768"/><figcaption class="r4-wtag">${pretty(a.name)}</figcaption></figure>
      ${mode === "wipe" && html`<div class="r4-handle" aria-hidden="true"><svg viewBox="0 0 34 34"><path d="M14 11l-6 6 6 6M20 11l6 6-6 6"/></svg></div><input class="r4-wiper" type="range" min="0" max="100" value=${pos} aria-label=${`Wipe between ${pretty(a.name)} and ${pretty(b.name)}`} aria-valuetext=${`${pos}% ${pretty(a.name)}`} onInput=${(e) => setPos(+e.target.value)}/>`}
    </div>
    <div class="r4-wipedeck"><span class="r4-seg" role="group" aria-label="How to compare">${seg("wipe", "Wipe")}${seg("side", "Side by side")}</span>${mode === "wipe" && html`<span class="r4-hint">Drag across the picture, or use the arrow keys.</span>`}${note && html`<span class="r4-hint">${note}</span>`}</div>
  </div>`;
}

const STORIES = [
  { id: "control", tab: "Plain vs the pack", a: "control", b: "res_3s", h: "Same prompt, two samplers", p: () => "On the left, ComfyUI's plain KSampler: Euler on the normal schedule. On the right, ClownsharKSampler running res_3s on beta57, with eta 0.5 and Bongmath on. Same prompt, same seed number. Several things change at once, so read it as the nodes at work, not as a ranking." },
  { id: "cost", tab: "One call or two", a: "res_2m", b: "res_2s", h: "One model call a step, or two", p: (f) => `res_2m recycles earlier steps and calls the model once a step. res_2s stops halfway through each step to ask again. At ${f.steps} steps that's close to ${f.steps} calls against ${f.steps * 2}. The picture is free to change; whether it's better is for your eye.` },
  { id: "unsample", tab: "Backwards, then forwards", a: "res_2m", b: "unsample", h: "Run it backwards, then forwards", p: () => "The left picture is our res_2m render. The graph unsampled it back toward noise, then sampled it down again under a new prompt asking for deep winter. Same lighthouse prompt otherwise, with snow on the rocks." },
  { id: "style", tab: "A picture as a guide", a: "style_ref", b: "style", h: "A picture as a guide", p: () => "The left picture is the reference, itself made with the pack. The right one keeps the lighthouse prompt, while ClownGuide Style, set to WCT, pulls sampling toward the reference's look." },
  { id: "regional", tab: "Two prompts, one frame", a: "control", b: "regional", start: 14, h: "Two prompts, one frame", p: () => "The right picture has a lighthouse prompt on its left half and a snowy pine forest prompt on its right half, split by a plain mask. The left picture is the one-prompt control, there for contrast. Drag across to see the split." },
  { id: "chain", tab: "Change hands midway", a: "res_2m", b: "chain", h: "Change samplers midway", p: () => "Both start the same way, on res_2m. Part-way down the schedule, the right one hands over to a Chainsampler and finishes with res_3s, picking up from the state the first sampler left in the latent." },
  { id: "redux", tab: "Redux", a: "style_ref", b: "redux", h: "Reference as extra tokens", p: () => "ComfyUI's own StyleModelApply, with the pack's sampler. The style reference joins the prompt as extra image tokens, so this one is a ComfyUI node doing the styling." },
];
const PLATE_NOTES = { flux_unsample: "Our FLUX.1 schnell try came out flat and blocky. That's this graph and these settings, not a verdict on the method." };
const FAMILIES = [...new Set(GALLERY.map((r) => r.family))];
const DEFAULT_FAMILY = FAMILIES.find((f) => f.startsWith("SDXL")) || FAMILIES[0];

export function Plates({ notes }) {
  const [fam, setFam] = useState(DEFAULT_FAMILY), [storyId, setStoryId] = useState("control"), [pick, setPick] = useState(null);
  const stories = storiesFor(STORIES, GALLERY, fam);
  const story = stories.find((s) => s.id === storyId) || stories[0];
  const rows = GALLERY.filter((r) => r.family === fam);
  const a = (pick && findRender(GALLERY, fam, pick.a)) || (story && findRender(GALLERY, fam, story.a)) || rows[0];
  const b = (pick && findRender(GALLERY, fam, pick.b)) || (story && findRender(GALLERY, fam, story.b)) || rows[1] || rows[0];
  if (!a || !b) return null;
  const choose = (s) => { setStoryId(s.id); setPick(null); };
  const custom = !!pick, extra = [PLATE_NOTES[a.key], PLATE_NOTES[b.key], notes[a.name] && `${pretty(a.name)}: ${notes[a.name]}.`, a.name !== b.name && notes[b.name] && `${pretty(b.name)}: ${notes[b.name]}.`].filter(Boolean);
  const select = (side, value) => html`<label class="r4-field">${side === "a" ? "Left picture" : "Right picture"}<select value=${value} onChange=${(e) => setPick({ a: a.name, b: b.name, [side]: e.target.value })}>${rows.map((r) => html`<option value=${r.name}>${pretty(r.name)}</option>`)}</select></label>`;
  return html`<div class="r4-plates film">
    <div class="r4-platepic"><${Wipe} key=${a.key + b.key} a=${a} b=${b} start=${custom ? 50 : story.start || 50}/></div>
    <div class="r4-plateside">
      <div class="r4-seg r4-seg-wide" role="group" aria-label="Model">${FAMILIES.map((f) => html`<button type="button" aria-pressed=${fam === f} onClick=${() => { setFam(f); setPick(null); }}>${f.split(" (")[0]}</button>`)}</div>
      <p class="r4-kicker">${custom ? "Your comparison" : "Plate"}</p>
      <h3 class="r4-platetitle">${custom ? `${pretty(a.name)} and ${pretty(b.name)}` : story.h}</h3>
      ${custom ? html`<p class="r4-platetext">Two renders of your choosing, from the same set. The notes below say what each one is.</p>` : html`<p class="r4-platetext">${story.p(a)}</p>`}
      <ul class="r4-storylist">${stories.map((s) => html`<li><button type="button" aria-pressed=${!custom && story.id === s.id} onClick=${() => choose(s)}>${s.tab}</button></li>`)}</ul>
      <div class="r4-platepick">${select("a", a.name)}${select("b", b.name)}</div>
      <dl class="r4-platefacts">
        <div><dt>Left</dt><dd>${a.what} <a href=${a.graph} download>Graph</a></dd></div>
        <div><dt>Right</dt><dd>${b.what} <a href=${b.graph} download>Graph</a></dd></div>
        <div><dt>Set</dt><dd>${a.family}, ${a.size}px, ${a.steps} steps, CFG ${a.cfg}. Our renders with the pack.</dd></div>
      </dl>
      ${extra.map((x) => html`<p class="r4-platenote">${x}</p>`)}
    </div>
  </div>`;
}

// Euler, res_2s and res_2m as one step along the sigma line. A filled dot is a model call; a ring is an earlier result used again.
function StepLine({ title, calls, dots, sub }) {
  return html`<figure class="r4-stepline">
    <figcaption><b>${title}</b><span>${calls}</span></figcaption>
    <svg viewBox="0 0 320 74" role="img" aria-label=${`${title}: ${sub}`}>
      <line class="r4-sl-track" x1="10" y1="40" x2="310" y2="40"/>
      <line class="r4-sl-step" x1="110" y1="40" x2="290" y2="40"/>
      <text x="110" y="68" text-anchor="middle">this step</text><text x="290" y="68" text-anchor="middle">next</text>
      ${dots.map((d) => html`<circle class=${d.call ? "r4-sl-call" : "r4-sl-ring"} cx=${d.x} cy="40" r="8"/>`)}
      ${dots.filter((d) => d.t).map((d) => html`<text class="r4-sl-lab" x=${d.x} y="22" text-anchor="middle">${d.t}</text>`)}
      <circle class="r4-sl-end" cx="290" cy="40" r="4"/>
    </svg>
    <p>${sub}</p>
  </figure>`;
}

export function StepLines() {
  return html`<div class="r4-steplines">
    <${StepLine} title="euler" calls="1 call a step" sub="Ask once at the start, then walk in that direction." dots=${[{ x: 110, call: true }]}/>
    <${StepLine} title="res_2s" calls="2 calls a step" sub="Ask at the start, step halfway, ask again, then finish the step from the start using both answers." dots=${[{ x: 110, call: true }, { x: 200, call: true, t: "c2 = 0.5" }]}/>
    <${StepLine} title="res_2m" calls="1 call a step" sub="Ask once. The second point is the previous step's answer, used again, so c2 comes out negative and looks backward." dots=${[{ x: 30, t: "last step" }, { x: 110, call: true }]}/>
  </div>`;
}

const fmt = (x) => (x >= 0.1 ? x.toFixed(3) : x >= 0.001 ? x.toFixed(4) : x.toExponential(1));

export function ToyLab() {
  const [calls, setCalls] = useState(8), [start, setStart] = useState(0.3);
  const FROM = 3, TO = 0.03, W = 620, H = 250, PAD = 30;
  const exact = useMemo(() => toyExact(start, FROM, TO), [start]);
  const answer = exact[exact.length - 1][1];
  const runs = useMemo(() => Object.keys(TOY_METHODS).map((k) => {
    const path = toyPath(k, start, calls, FROM, TO);
    return { k, path, gap: Math.abs(path[path.length - 1][1] - answer) };
  }), [calls, start, answer]);
  const X = (s) => (PAD + (Math.log(FROM / s) / Math.log(FROM / TO)) * (W - PAD - 10)).toFixed(1);
  const Y = (x) => (H - 26 - (Math.max(-0.05, Math.min(1.1, x)) + 0.05) / 1.15 * (H - 40)).toFixed(1);
  const line = (path) => path.map(([s, x], i) => `${i ? "L" : "M"}${X(s)} ${Y(x)}`).join(" ");
  const fine = exact.filter((_, i) => i % 60 === 0);
  const most = Math.max(...runs.map((r) => r.gap), 1e-9);
  return html`<div class="r4-toy film">
    <div class="r4-toyplot">
      <svg viewBox=${`0 0 ${W} ${H}`} role="img" aria-label=${`A one-number toy with ${calls} model calls. Distance from the exact answer: ${runs.map((r) => `${TOY_METHODS[r.k].label} ${fmt(r.gap)}`).join(", ")}.`}>
        ${[0, 0.5, 1].map((v) => html`<g><line class="r4-t-grid" x1=${PAD} x2=${W - 10} y1=${Y(v)} y2=${Y(v)}/><text class="r4-t-ax" x=${PAD - 6} y=${+Y(v) + 4} text-anchor="end">${v}</text></g>`)}
        <text class="r4-t-ax" x=${PAD} y=${H - 6}>sigma ${FROM}, noisy</text><text class="r4-t-ax" x=${W - 10} y=${H - 6} text-anchor="end">sigma ${TO}, nearly clean</text>
        <path class="r4-t-exact" d=${line(fine)}/>
        ${runs.map((r) => html`<g class=${"r4-t-" + r.k}><path d=${line(r.path)}/>${r.path.map(([s, x]) => html`<circle cx=${X(s)} cy=${Y(x)} r="3.6"/>`)}</g>`)}
      </svg>
    </div>
    <div class="r4-toyside">
      <p class="r4-kicker">Same number of model calls</p>
      <ul class="r4-gaps" role="status">${runs.map((r) => html`<li class=${"r4-g-" + r.k}><span>${TOY_METHODS[r.k].label}</span><i aria-hidden="true"><em style=${{ width: `${Math.max(1.5, (r.gap / most) * 100)}%` }}></em></i><b>${fmt(r.gap)}</b></li>`)}</ul>
      <p class="r4-toyread">Distance from the exact answer at the end, with ${calls} model calls each. Euler gets ${calls} steps; the other two get ${calls / 2}.</p>
      <label class="r4-field">Model calls: ${calls}<input type="range" min="4" max="40" step="2" value=${calls} onInput=${(e) => setCalls(+e.target.value)}/></label>
      <label class="r4-field">Start value: ${start.toFixed(2)}<input type="range" min="0.1" max="1.2" step="0.05" value=${start} onInput=${(e) => setStart(+e.target.value)}/></label>
      <p class="r4-toynote">A toy, computed here in your browser: one number instead of an image, and only two possible answers, so the ideal denoiser is one line of maths and the exact path can be worked out. It uses the published formulas, not the pack's code. The ranking moves as you change the sliders, so try a few. It says nothing about pictures.</p>
    </div>
  </div>`;
}

const BONG = [
  { t: "Ask, and step", p: "From the start of the step, the sampler asks the model for its guess at the clean image, then uses it to reach the first stage." },
  { t: "Ask again", p: "At the stage it asks again. A guide or added noise may also have moved the latent since the first answer arrived, so the numbers no longer quite line up." },
  { t: "Solve back to the start", p: "Now it works backward. The model's answers stay fixed. From where the newest stage sits, it solves for where the step must have started." },
  { t: "Refresh what came before", p: "With that new start it re-solves the earlier stages and the direction each one implies, which is each stored guess minus the new start." },
  { t: "Round and round", p: "That's one round, and it repeats up to 100 times with no model calls at all. Then the next stage goes ahead from numbers that agree." },
];
const BONG_DOTS = [
  { start: 110, stage: 300, moved: 0, ghost: false, back: false },
  { start: 110, stage: 300, moved: -20, ghost: false, back: false },
  { start: 90, stage: 300, moved: -20, ghost: true, back: true },
  { start: 90, stage: 300, moved: -20, ghost: true, back: true },
  { start: 90, stage: 300, moved: -20, ghost: true, back: true },
];

export function BongWalk() {
  const [i, setI] = useState(0), s = BONG[i], d = BONG_DOTS[i], sy = 76 + d.moved, y0 = 96;
  return html`<div class="r4-bong film">
    <svg class="r4-bongart" viewBox="0 0 420 150" role="img" aria-label=${`Schematic, step ${i + 1} of ${BONG.length}: ${s.t}`}>
      <line class="r4-b-rail" x1="30" y1="130" x2="400" y2="130"/>
      <text class="r4-b-ax" x="30" y="146">noisier</text><text class="r4-b-ax" x="400" y="146" text-anchor="end">cleaner</text>
      ${d.ghost && html`<circle class="r4-b-ghost" cx="110" cy=${y0} r="9"/>`}
      <path class="r4-b-link" d=${`M${d.start} ${y0} L300 ${sy}`}/>
      ${d.back && html`<path class="r4-b-back" d=${`M284 ${sy + 2} L${d.start + 18} ${y0 - 3}`}/>`}
      <circle class="r4-b-start" cx=${d.start} cy=${y0} r="10"/><text class="r4-b-lab" x=${d.start} y=${y0 + 28} text-anchor="middle">start</text>
      ${i > 0 ? html`<circle class="r4-b-stage" cx="300" cy=${sy} r="10"/>` : html`<circle class="r4-b-next" cx="300" cy=${sy} r="10"/>`}
      <text class="r4-b-lab" x="300" y=${sy - 18} text-anchor="middle">stage</text>
      ${i === 4 && html`<text class="r4-b-count" x="210" y="22" text-anchor="middle">up to 100 rounds, 0 model calls</text>`}
    </svg>
    <div class="r4-bongtext">
      <p class="r4-kicker" aria-live="off">Step ${i + 1} of ${BONG.length}</p>
      <div role="status"><h3 class="r4-platetitle">${s.t}</h3><p class="r4-platetext">${s.p}</p></div>
      <div class="r4-bongctl">
        <button type="button" class="btn" disabled=${i === 0} onClick=${() => setI(i - 1)}>Back</button>
        <button type="button" class="btn primary" disabled=${i === BONG.length - 1} onClick=${() => setI(i + 1)}>Next</button>
      </div>
      <p class="r4-toynote">A schematic of the order of the work, drawn by us, not measured values. In symbols, with stage weights a and step h: start = stage − h Σ a·ε, then each earlier stage = start + h Σ a·ε.</p>
    </div>
  </div>`;
}

export function NodeMap({ nodes, group, onPick }) {
  const regions = useMemo(() => nodeMap(nodes), [nodes]);
  return html`<div class="r4-map">
    <p class="r4-mapkey"><span><i class="r4-dotk on"></i>Rendered in our test</span><span><i class="r4-dotk"></i>Any other result</span><span>Each dot is one node. Pick a group to filter the list below.</span></p>
    <div class="r4-regions">${regions.map((r) => html`<section class="r4-region" aria-label=${r.t}>
      <header><b>${r.count}</b><h3>${r.t}</h3><p>${r.d}</p></header>
      <ul>${r.groups.map((g) => html`<li><button type="button" aria-pressed=${group === g.name} onClick=${() => onPick(group === g.name ? "all" : g.name)}><span class="r4-gname">${g.name}<small>${g.nodes.length}</small></span><span class="r4-gdots" aria-hidden="true">${g.nodes.map((n) => html`<i class=${n.s === "rendered" ? "on" : ""}></i>`)}</span><span class="sr-only">, ${g.rendered} rendered</span></button></li>`)}</ul>
    </section>`)}</div>
  </div>`;
}
