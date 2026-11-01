// RES4LYF page: a thank-you to ClownsharkBatwing's node pack. Facts come from reading its repo and running it on a private ComfyUI. The studio doesn't run or bundle the pack.
import { useEffect, useMemo, useState } from "preact/hooks";
import { html } from "./common.js";
import { DATA } from "./res4lyf_data.js";
import { NODES as NODE_NOTES } from "./res4lyf_nodes.js";
import { GALLERY } from "./res4lyf_gallery.js";
import { REPO, exampleUrl, flatten, filterSamplers, filterNodes, stateCounts, STATE_LABEL, sourceUrl, modelCalls, betaSchedule, countBelow, curvePath } from "./res4lyf_logic.js";
import { Plates, StepLines, ToyLab, BongWalk, NodeMap } from "./res4lyf_feature.js";

const SAMPLERS = flatten(DATA.families);
const NODES = [...DATA.nodes.core, ...DATA.nodes.beta, ...DATA.nodes.legacy];
const GROUPS = [...new Set(NODE_NOTES.map((n) => n.g))].sort();
const FAMILIES = [...new Set(GALLERY.map((r) => r.family))];
const COUNTS = stateCounts(NODE_NOTES);
const RENDER_NOTE = { control: "Not the pack", style_ref: "Input for style", redux: "ComfyUI node, pack sampler", unsample: "Second try: the first attempt, with a guide on the resample, mostly returned the source" };

const HOW = [
  { t: "Bongmath", p: ["A sampler with several stages estimates its way through each step. As the newer estimates arrive, Bongmath goes back and re-solves where the step started and where its earlier stages sat, up to 100 rounds, so they all agree with the latest numbers. It holds the model's predictions fixed and makes no extra model calls, so it costs no model time.", "It needs stages to work on. Multistep samplers skip it once they settle in: res_2m runs its first two steps as res_2s, where Bongmath can act, then goes multistep and it stops, apart from fallback steps. It also stops below sigma 0.03."], src: ["beta/rk_method_beta.py", 655] },
  { t: "Samplers that remember", p: ["The sampler stores its working state inside the latent it hands on: the raw latent, recent predictions, where it stopped in the schedule, even the random number state. That's what lets a Chainsampler pick up mid-schedule with a different method, and why the pack has state-aware versions of crop, trim and upscale."], src: ["beta/rk_sampler_beta.py", 2253] },
  { t: "Unsample and resample", p: ["Unsampling flips the noise schedule and runs it upward, turning an image back toward noise along the path the model would take. Resampling then runs it back down, and a new prompt can steer the return. Both modes pad the schedule with zeros, which stops ComfyUI adding noise of its own."], src: ["beta/samplers.py", 413] },
  { t: "Guides", p: ["A guide pulls sampling toward a reference latent, and the mode decides how. Epsilon blends the step direction toward it. Data shifts the latent after each substep. Lure shifts it and then calls the model again. Flow runs the model on the guide and image paths and uses the difference. Sync also runs a noised guide path and combines the results. Inversion works like epsilon, but while unsampling it aims at noise."], src: ["beta/rk_guide_func_beta.py", 1962] },
  { t: "Regional prompting", p: ["The regional nodes don't build their attention masks straight away. They output blank conditioning that holds a callback, and the sampler runs it once the model is known, so it can pick the right mask class for WAN, HiDream, SDXL or SD1.5, or a default for anything else."], src: ["beta/samplers.py", 632] },
  { t: "Patching the model", p: ["The Re*Patcher nodes change how a loaded model behaves by swapping the class of its blocks, so no weights are copied or reloaded. That's where regional attention and style features plug in. Style guides then pull the model's internal features toward the reference's statistics, with methods such as AdaIN and WCT."], src: ["models.py", 590] },
];
const LICENCE = `The use of this software or any derivative work for the purpose of providing a commercial service, such as (but not limited to) an AI image generation service, is strictly prohibited without obtaining permission and/or a separate commercial license from the copyright holder. This includes any service that charges users directly or indirectly for access to this software's functionality, whether standalone or integrated into a larger product.`;
const INSTALL = `cd ComfyUI/custom_nodes
git clone https://github.com/ClownsharkBatwing/RES4LYF/
cd RES4LYF
pip install -r requirements.txt`;

const FEATURES = [
  { t: "Style transfer", plate: "style", q: "Include some mention of the style you wish to use in the prompt.", d: "A guide image steers the look while the prompt sets the subject. The README lists HiDream, Flux, Chroma, AuraFlow, SD1.5, SDXL, SD3.5, Stable Cascade, LTXV and WAN.", ex: ["hidream style transfer v2", "sdxl style transfer"] },
  { t: "Anti-blur", q: "Consecutive seeds, no cherrypicking.", d: "The README's section on removing Flux and HiDream blur, with style guides doing the work.", ex: ["flux style antiblur", "hidream style antiblur"] },
  { t: "Regional conditioning", plate: "regional", q: "Unlimited zones! Over 10 zones have been used in one image before.", d: "Masks can be drawn freely or kept rigid. The README lists HiDream, Flux, Chroma, SD3.5, SD1.5, SDXL, AuraFlow and WAN.", ex: ["hidream regional 3 zones", "flux regional redux (3 zone, overlapping)"] },
  { t: "Temporal conditioning", q: "Ability to change the prompt for each frame.", d: "Regional thinking applied to time, supported on WAN according to the README.", ex: ["intro to clownsampling"] },
  { t: "Unsampling", plate: "unsample", q: "", d: "New forms of rectified noise inversion for img2img, with dedicated unsample and resample modes on the sampler.", ex: ["hidream unsampling", "sd35 medium unsampling"] },
  { t: "Video to video", q: "Viable with any video model, demo with WAN.", d: "The README shows the same sampling ideas carried across to video editing.", ex: ["wan vid2vid"] },
];

const CHAPTERS = [["r4-idea", "Story"], ["r4-renders", "Plates"], ["r4-how", "The math"], ["r4-samplers", "Samplers"], ["r4-can", "What it does"], ["r4-nodes", "Node map"], ["r4-more", "Credits"], ["r4-licence", "Licence"]];
const calm = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
function jump(e, id) {
  e.preventDefault();
  const el = document.getElementById(id);
  if (!el) return;
  el.scrollIntoView({ behavior: calm() ? "auto" : "smooth" });
  el.focus({ preventScroll: true });
}
const COVER = GALLERY.find((r) => r.key === "sdxl_style_ref") || GALLERY[0];
const SHOWCASE = GALLERY.filter((r) => r.family === (COVER && COVER.family));
const plateOf = (name) => SHOWCASE.find((r) => r.name === name);

function Contents() {
  const [now, setNow] = useState("");
  useEffect(() => {
    const seen = CHAPTERS.map(([id]) => document.getElementById(id)).filter(Boolean);
    if (!seen.length || typeof IntersectionObserver === "undefined") return undefined;
    const io = new IntersectionObserver((list) => { for (const x of list) if (x.isIntersecting) setNow(x.target.id); }, { rootMargin: "-20% 0px -70% 0px" });
    seen.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);
  return html`<nav class="r4-toc" aria-label="Chapters on this page"><ol>${CHAPTERS.map(([id, t], i) => html`<li><a href="#res4lyf" aria-current=${now === id ? "true" : undefined} onClick=${(e) => jump(e, id)}><i>${String(i + 1).padStart(2, "0")}</i>${t}</a></li>`)}</ol></nav>`;
}

const Head = ({ n, title, id, children }) => html`<header class="r4-head"><span class="r4-num" aria-hidden="true">${n}</span><h2 id=${id} tabindex="-1">${title}</h2>${children}</header>`;

const Ext = ({ href, children, cls }) => html`<a class=${cls} href=${href} target="_blank" rel="noopener noreferrer">${children}</a>`;

function StageArt() {
  const rows = [["euler", 1], ["res_2m", 1], ["res_2s", 2], ["res_3s", 3], ["res_5s", 5], ["res_8s", 8], ["res_16s", 16]];
  return html`<svg class="r4-art" viewBox="0 0 420 196" role="img" aria-label="Model calls for one step, from one for euler to sixteen for res_16s">
    ${rows.map(([n, c], y) => html`<g transform=${`translate(0 ${y * 28 + 6})`}><text x="0" y="12">${n}</text>${Array.from({ length: c }, (_, i) => html`<circle class="r4-dot" cx=${86 + i * 21} cy="8" r="7" style=${{ animationDelay: `${i * 90}ms` }}/>`)}</g>`)}
  </svg>`;
}

function CostLab() {
  const [steps, setSteps] = useState(20), [name, setName] = useState("res_3s");
  const s = SAMPLERS.find((x) => x.name === name) || SAMPLERS[0], calls = modelCalls(steps, s.stages);
  return html`<div class="card r4-lab"><h3>What a sampler costs</h3>
    <label class="r4-field">Sampler<select value=${name} onChange=${(e) => setName(e.target.value)}>${DATA.families.map((f) => html`<optgroup label=${f.label}>${f.samplers.map((n) => html`<option value=${n}>${n}</option>`)}</optgroup>`)}</select></label>
    <label class="r4-field">Steps: ${steps}<input type="range" min="1" max="60" value=${steps} onInput=${(e) => setSteps(Number(e.target.value))}/></label>
    <div class="r4-sum" role="status"><b>${calls}</b><span>model calls, against ${steps} for Euler at the same steps</span></div>
    <p class="small">Model calls set the render time. The count is steps × stages, read from the sampler's name using the README's rule, so treat it as close, not exact: multistep samplers spend a little extra on their first steps, and implicit steps cost more on top. Hybrid names give the same count, which we inferred. It says nothing about quality.</p>
  </div>`;
}

function BetaLab() {
  const [steps, setSteps] = useState(20);
  const b57 = useMemo(() => betaSchedule(steps, 0.5, 0.7), [steps]), plain = useMemo(() => betaSchedule(steps, 0.6, 0.6), [steps]);
  return html`<div class="card r4-lab"><h3>The beta57 scheduler</h3>
    <svg class="r4-curve" viewBox="0 0 320 170" preserveAspectRatio="none" role="img" aria-label=${`Timestep position at each step. beta57 puts ${countBelow(b57, 0.25)} of ${steps} steps in the lowest quarter; ComfyUI's default beta puts ${countBelow(plain, 0.25)}.`}>
      <path class="r4-grid" d="M0 127.5H320 M0 85H320 M0 42.5H320"/><path class="r4-plain" d=${curvePath(plain, 320, 170)}/><path class="r4-b57" d=${curvePath(b57, 320, 170)}/>
    </svg>
    <div class="r4-key"><span class="r4-k57">beta57 (α 0.5, β 0.7)</span><span class="r4-kplain">ComfyUI beta default (α 0.6, β 0.6)</span></div>
    <label class="r4-field">Steps: ${steps}<input type="range" min="4" max="60" value=${steps} onInput=${(e) => setSteps(Number(e.target.value))}/></label>
    <div class="r4-sum" role="status"><b>${countBelow(b57, 0.25)} vs ${countBelow(plain, 0.25)}</b><span>steps in the lowest quarter of the timesteps</span></div>
    <p class="small">The shape only, computed here from those two settings, before rounding to a model's timesteps. Left is the first step, the noisiest. Our own Anima notes record beta57 as a way to get a more realistic or painterly look.</p>
  </div>`;
}

function SamplerAtlas() {
  const [fam, setFam] = useState("all"), [q, setQ] = useState("");
  const shown = filterSamplers(SAMPLERS, fam, q);
  return html`<div class="r4-samplerbox">
    <div class="tabs r4-tabs" role="group" aria-label="Sampler family">${[{ key: "all", label: "All" }, ...DATA.families].map((f) => html`<button type="button" aria-pressed=${fam === f.key} class=${"chip" + (fam === f.key ? " on" : "")} onClick=${() => setFam(f.key)}>${f.label} ${f.key === "all" ? SAMPLERS.length : f.samplers.length}</button>`)}</div>
    <input type="search" class="r4-search" placeholder="Search samplers" aria-label="Search samplers" value=${q} onInput=${(e) => setQ(e.target.value)}/>
    <p class="small" role="status">${shown.length} shown. The number is stages per step.</p>
    <ul class="r4-grid-list" tabindex="0" aria-label="Samplers, scrollable">${shown.map((s) => html`<li><code>${s.name}</code><b title="Stages per step">${s.stages}</b></li>`)}</ul>
  </div>`;
}

function Gallery() {
  const [fam, setFam] = useState(FAMILIES[0]);
  const shown = GALLERY.filter((r) => r.family === fam), first = shown[0] || {};
  return html`<div class="r4-gallerybox">
    <div class="tabs r4-tabs" role="group" aria-label="Model">${FAMILIES.map((f) => html`<button type="button" aria-pressed=${fam === f} class=${"chip" + (fam === f ? " on" : "")} onClick=${() => setFam(f)}>${f}</button>`)}</div>
    <p class="small r4-gnote">${first.size}px, ${first.steps} steps, CFG ${first.cfg}, seed ${first.seed}. One seed for all of them, no picking.</p>
    <div class="r4-gallery film">${shown.map((r) => html`<figure class="r4-plate"><img src=${r.src} alt=${r.what} loading="lazy" width="768" height="768"/><figcaption><b>${r.name.replace("_", " ")}</b>${RENDER_NOTE[r.name] && html` <span class="r4-tag">${RENDER_NOTE[r.name]}</span>`}<span>${r.what}</span><a href=${r.graph} download>Download graph</a></figcaption></figure>`)}</div>
  </div>`;
}

function NodeCard({ n }) {
  const src = n.src.split(":");
  return html`<article class="card r4-node">
    ${n.t ? html`<img src=${n.t} alt=${"Render from a graph using " + n.n} loading="lazy" width="256" height="256"/>` : html`<div class="r4-nothumb" aria-hidden="true">${n.s === "ran" ? "text output" : "no image"}</div>`}
    <div class="r4-nodebody"><h4><code>${n.n}</code></h4><span class=${"r4-state r4-s-" + n.s}>${STATE_LABEL[n.s] || n.s}</span>
      <p>${n.d}</p>${n.u && html`<p class="r4-use">${n.u}</p>`}${n.e && html`<p class="r4-err"><code>${n.e}</code></p>`}
      <p class="r4-nodelinks"><${Ext} href=${sourceUrl(DATA.sha, src[0], src[1])}>Source<//>${n.j && html`<a href=${n.j} download>Graph</a>`}</p></div>
  </article>`;
}

function NodeList() {
  const [q, setQ] = useState(""), [group, setGroup] = useState("all"), [state, setState] = useState("all"), [limit, setLimit] = useState(36);
  const shown = filterNodes(NODE_NOTES, group, state, q);
  const reset = (f) => (e) => { f(e.target.value); setLimit(36); };
  return html`<div class="r4-nodes">
    <${NodeMap} nodes=${NODE_NOTES} group=${group} onPick=${(g) => { setGroup(g); setLimit(36); }}/>
    <div class="r4-filter">
      <input type="search" class="r4-search" placeholder="Search names and notes" aria-label="Search nodes" value=${q} onInput=${reset(setQ)}/>
      <select aria-label="Group" value=${group} onChange=${reset(setGroup)}><option value="all">All groups</option>${GROUPS.map((g) => html`<option value=${g}>${g}</option>`)}</select>
      <select aria-label="Test result" value=${state} onChange=${reset(setState)}><option value="all">All results</option>${Object.keys(COUNTS).map((s) => html`<option value=${s}>${STATE_LABEL[s] || s} (${COUNTS[s]})</option>`)}</select>
    </div>
    <p class="small r4-count" role="status">${shown.length} of ${NODE_NOTES.length} nodes</p>
    <div class="r4-nodegrid">${shown.slice(0, limit).map((n) => html`<${NodeCard} key=${n.n} n=${n}/>`)}</div>
    ${shown.length > limit && html`<button type="button" class="btn r4-more" onClick=${() => setLimit(limit + 72)}>Show more (${shown.length - limit} left)</button>`}
  </div>`;
}

export function Res4lyf() {
  useEffect(() => { document.body.classList.add("on-res4lyf"); return () => document.body.classList.remove("on-res4lyf"); }, []);
  return html`<div class="r4">
    <section class="r4-hero film">
      ${COVER && html`<figure class="r4-coverart"><img src=${COVER.src} alt=${COVER.what} width="768" height="768"/></figure>`}
      <div class="r4-herotext">
        <div class="r4-eyebrow">A thank-you</div>
        <h2>RES4LYF</h2>
        <p class="r4-by">by <b>ClownsharkBatwing</b></p>
        <p class="r4-lead">A ComfyUI node pack that treats sampling as a craft of its own: Runge-Kutta methods, noise, guides and schedules, all opened up to be worked by hand. Its README puts it this way: <em>“Superior sampling with RES4LYF: the power of Bongmath.”</em></p>
        <div class="r4-actions"><${Ext} cls="btn primary" href=${REPO}>Open the repo<//><a class="btn" href="#res4lyf" onClick=${(e) => jump(e, "r4-licence")}>Read the licence first</a></div>
      </div>
      ${COVER && html`<p class="r4-covercap">Cover: <code>${COVER.key}</code>, ${COVER.family}. A reference image we made with the pack, seed ${COVER.seed}.</p>`}
    </section>

    <div class="r4-notes">
      <div class="card r4-status" role="note"><b>This pack doesn't ship with Parametric Studio.</b> We ran it in a separate ComfyUI on our own machine to learn it and made every render on this page that way. Our code and installs don't bundle any of it.</div>
      <div class="r4-licnote" role="note"><b>The licence, plainly.</b> The pack's <code>LICENSE</code> prohibits using it for a commercial service without the copyright holder's permission. So we link to it and don't bundle it. <a href="#res4lyf" onClick=${(e) => jump(e, "r4-licence")}>The full wording is below.</a></div>
    </div>

    <dl class="r4-stats">
      <div><dt>${SAMPLERS.length}</dt><dd>samplers in its picker</dd></div>
      <div><dt>${NODE_NOTES.length}</dt><dd>nodes loaded and read</dd></div>
      <div><dt>${DATA.noiseTypes.length}</dt><dd>noise types</dd></div>
      <div><dt>${DATA.noiseModes}</dt><dd>noise modes</dd></div>
      <div><dt>${DATA.examples.length}</dt><dd>example workflows</dd></div>
    </dl>
    <p class="small r4-src">Counted by reading the source at commit <code>${DATA.commit}</code> (${DATA.commitDate}). The source registers ${NODES.length} node names, ${NODE_NOTES.length} of which loaded here. The pack's README, which covers an earlier version, gives 69 samplers.</p>

    <${Contents}/>

    <section class="r4-sect"><${Head} n="01" title="The idea" id="r4-idea"/>
      <p class="r4-story r4-dropcap">An image model starts from noise and guesses, over and over, what the clean picture might be. The sampler is the part that decides how to move from one guess to the next. RES4LYF is a ComfyUI node pack about that walk: how many times to ask the model in each step, how noise goes in along the way, which way a guide pulls, and what can change part-way through.</p>
      <div class="r4-two">
        <p>At the heart of the repo is the ClownsharKSampler, built to support both rectified flow and probability flow models. Around it sit nodes for changing sigmas, latents, noise and guides as sampling runs, so that settings can change over time and not just once per render.</p>
        <p>The name <em>Bongmath</em> runs right through the sampler code. The README's own claim is that RES samplers typically need only 20 steps where Uni-PC needs far more and still doesn't reach the same quality. That's the author's claim and comparison; we haven't tested it here.</p>
      </div>
      <blockquote class="r4-quote r4-pull">“Much of this work remains experimental and is subject to further changes.”<cite>The README, being straight about it</cite></blockquote>
    </section>

    <section class="r4-sect r4-wide"><${Head} n="02" title="Our renders with it" id="r4-renders"><p class="sectsub">Made by us with this pack, in graphs we built by following the author's examples. They show the nodes working, not a quality test, and our settings are starting points, not the author's best.</p><//>
      <${Plates} notes=${RENDER_NOTE}/>
      <h3 class="r4-subhead">The whole set</h3>
      <${Gallery}/>
    </section>

    <section class="r4-sect r4-wide"><${Head} n="03" title="How it works" id="r4-how"><p class="sectsub">Our reading of the code at that commit. These are our words, not the author's, so check the source if it matters.</p><//>
      <div class="r4-math">
        <div class="r4-mathtext">
          <h3 class="r4-subhead">Stepping on a log scale</h3>
          <p>The noise level, sigma, falls from high to nearly nothing. The pack's exponential samplers measure each step on a log scale, as the fall from one sigma to the next. Between any two sigmas, the walk to the model's guess of the clean image follows a known curve. So they don't approximate that curve. They solve it exactly, and only have to estimate how the guess itself changes along the way.</p>
          <p>The tools for that are the phi functions, which are the weights you get from solving it. If the guess stayed perfectly still, a step of any size would land on the right spot. A sampler's extra stages are there to measure how much the guess doesn't stay still.</p>
          <p class="r4-small">The pack's comments point to <code>arxiv.org/abs/2308.02157</code> for these functions, and credit Clybius for an exact analytic version.</p>
        </div>
        <div class="r4-formulas film" role="group" aria-label="The formulas, read from the source">
          <p class="r4-kicker">One res_2s step</p>
          <p class="r4-f"><i>h</i> = −ln(<i>σ</i><sub>next</sub> / <i>σ</i>)</p>
          <p class="r4-f"><i>ε</i><sub>i</sub> = <i>D</i><sub>i</sub> − <i>x</i></p>
          <p class="r4-f"><i>x</i><sub>next</sub> = <i>x</i> + <i>h</i> (<i>b</i><sub>1</sub><i>ε</i><sub>1</sub> + <i>b</i><sub>2</sub><i>ε</i><sub>2</sub>)</p>
          <p class="r4-f"><i>b</i><sub>2</sub> = <i>φ</i><sub>2</sub>(<i>h</i>) / <i>c</i><sub>2</sub>, <i>b</i><sub>1</sub> = <i>φ</i><sub>1</sub>(<i>h</i>) − <i>b</i><sub>2</sub></p>
          <p class="r4-f"><i>φ</i><sub>1</sub>(<i>h</i>) = (1 − <i>e</i><sup>−<i>h</i></sup>) / <i>h</i></p>
          <p class="r4-fnote"><i>D</i> is the model's guess at the clean image. <i>c</i><sub>2</sub> defaults to 0.5, which is where the second stage sits. Written out by us from <code>beta/rk_coefficients_beta.py</code> and <code>beta/rk_method_beta.py</code>.</p>
        </div>
      </div>
      <h3 class="r4-subhead">The letter at the end of the name</h3>
      <${StepLines}/>
      <${StageArt}/>
      <h3 class="r4-subhead">Try it on a toy</h3>
      <${ToyLab}/>
      <h3 class="r4-subhead">${HOW[0].t}</h3>
      <div class="r4-bongwrap">
        <div>${HOW[0].p.map((x) => html`<p class="r4-plain">${x}</p>`)}<${Ext} href=${sourceUrl(DATA.sha, HOW[0].src[0], HOW[0].src[1])}>${HOW[0].src[0]}<//></div>
        <${BongWalk}/>
      </div>
      <h3 class="r4-subhead">And the rest of the machine</h3>
      <div class="r4-cards r4-howlist">${HOW.slice(1).map((h, i) => html`<article><span class="r4-hown" aria-hidden="true">${i + 1}</span><h3>${h.t}</h3>${h.p.map((x) => html`<p class="r4-plain">${x}</p>`)}<${Ext} href=${sourceUrl(DATA.sha, h.src[0], h.src[1])}>${h.src[0]}<//></article>`)}</div>
    </section>

    <section class="r4-sect"><${Head} n="04" title="Samplers" id="r4-samplers"><p class="sectsub">The list the pack offers, in the pack's own families.</p><//><${SamplerAtlas}/></section>

    <section class="r4-sect"><${Head} title="Try the arithmetic"><p class="sectsub">Two small labs, computed in your browser. They don't run the pack or use the GPU.</p><//><div class="r4-labs"><${CostLab}/><${BetaLab}/></div></section>

    <section class="r4-sect"><${Head} n="05" title="What it can do" id="r4-can"><p class="sectsub">Taken from the README. Each link opens the author's example workflow on GitHub, where you'll also find the author's own images.</p><//>
      <div class="r4-features">${FEATURES.map((f) => { const pic = f.plate && plateOf(f.plate); return html`<article class=${pic ? "has-pic" : ""}>${pic && html`<figure><img src=${pic.src} alt=${pic.what} loading="lazy" width="768" height="768"/><figcaption>Our render, not the author's. ${pic.family}.</figcaption></figure>`}<div class="r4-fbody"><h3>${f.t}</h3>${f.q && html`<blockquote>“${f.q}”</blockquote>`}<p>${f.d}</p><ul>${f.ex.map((x) => html`<li><${Ext} href=${exampleUrl(x)}>${x}<//></li>`)}</ul></div></article>`; })}</div>
    </section>

    <section class="r4-sect r4-words film"><${Head} title="In the author's words"/>
      <div class="r4-two">
        <blockquote class="r4-quote r4-pull">“Imagine you're walking down the street and see what looks like an enticing music festival in the distance (your positive conditioning). You're on the fence about attending, but then, suddenly, a horde of pickleshark cannibals come storming out of a nearby bar (your negative conditioning). Together, the two team up to drive you toward the music festival. That's CFG.”</blockquote>
        <blockquote class="r4-quote r4-pull">“Try "res_5s" as your explicit sampler type, and "gauss-legendre_5s", if you wish to demonstrate your commitment to climate change (and image quality).”</blockquote>
      </div>
    </section>

    <section class="r4-sect r4-wide"><${Head} n="06" title="Every node" id="r4-nodes"><p class="sectsub">We read the source of all ${NODE_NOTES.length} nodes and wrote what each does. Then we put each one into a graph of its own, on Stable Diffusion 1.5 with its default settings, and rendered it. <b>${COUNTS.rendered || 0} rendered.</b></p><//>
      <p class="small r4-gnote">A picture means the graph ran, not that those settings suit the node, and a strange image is often just a poor default for this setup. A failure here can come from our simple test as easily as from the node: many need a particular model, video latents or a partner node. The notes come from reading the code, and some mention options that look unfinished; the author does call this work experimental.</p>
      <${NodeList}/>
    </section>

    <section class="r4-sect"><${Head} n="07" title="More from the author" id="r4-more"/><ul class="r4-links">
      <li><${Ext} href=${exampleUrl("intro to clownsampling")}>Intro to clownsampling<//>: the workflow the README recommends for learning the concepts.</li>
      <li><${Ext} href="https://github.com/ClownsharkBatwing/UltraCascade">UltraCascade<//>: linked from the README for Stable Cascade and UltraPixel style work.</li>
      <li><${Ext} href="https://huggingface.co/ClownsharkBatwing/CSBW_Style">CSBW_Style<//>: where the README's amateur cell phone LoRA for Flux lives.</li>
      <li><${Ext} href=${REPO + "/graphs/contributors"}>Everyone who contributed<//>: the author's GitHub handle is the only name the repo's README gives, and others have committed to it too.</li>
      <li>Code comments in the pack also credit work it builds on, including ComfyUI, kijai's KJNodes, cubiq's ComfyUI_essentials, pythongosssss's Custom Scripts, Nourepide's Allor, zju-pi's diff-sampler and Extraltodeus's sigmas tools.</li>
    </ul></section>

    <section class="r4-sect"><${Head} title="Install it yourself"><p class="sectsub">From the README. It needs <code>opencv-python</code>, <code>matplotlib</code>, <code>pywavelets</code> and <code>numpy>=1.26.4</code>. The README also recommends rgthree-comfy for its sampler menus. Read the licence first, and activate your ComfyUI environment before running pip.</p><//><pre class="r4-pre" tabindex="0">${INSTALL}</pre></section>

    <section class="r4-sect"><${Head} n="08" title="Licence" id="r4-licence"/>
      <div class="r4-licence">
        <p>The pack's <code>LICENSE</code> file opens with this condition, followed by the full GNU Affero General Public License v3:</p>
        <blockquote>${LICENCE}</blockquote>
        <p><b>In plain terms:</b> a paid service built on this pack, or a derivative of it, needs the copyright holder's permission first, even if it charges indirectly or only uses the pack inside a larger product.</p>
        <p>The pack's <code>pyproject.toml</code> says <code>license = "MIT"</code>, which doesn't match. The <code>LICENSE</code> file is the stricter of the two, so that's the one we show here. If it matters for your use, ask the author. This is a reading of the files, not legal advice.</p>
        <p>This page holds no code from the pack: only names, counts, short credited quotes, our own notes, and our own graphs and renders that use it. The page itself is part of Parametric Studio and is under the studio's AGPL-3.0 licence.</p>
        <p><b>A safety note:</b> the Sigmas Math nodes run their formula text as Python, so treat a shared workflow that uses them like a script from a stranger. That's sound advice for any custom node workflow.</p>
        <div class="r4-actions"><${Ext} cls="btn" href=${REPO + "/blob/main/LICENSE"}>Full licence on GitHub<//><${Ext} cls="btn" href=${REPO + "/issues"}>Contact through its issues<//></div>
      </div>
    </section>

    <section class="r4-thanks film">
      <p class="r4-eyebrow">The last word</p>
      <p class="r4-thankline"><span>Thank you,</span> <span>ClownsharkBatwing.</span></p>
      <p>The work belongs to the author and the repo's contributors. Any mistake in how this page reads it is ours.</p>
      <div class="r4-actions"><${Ext} cls="btn primary" href=${REPO}>Go to the repo<//></div>
    </section>
  </div>`;
}
