// blepping page: a thank-you to blepping's sampling node packs, Sonar, Overly Complicated Sampling and bleh. Facts come from reading the repos and running them in a throwaway ComfyUI; the studio doesn't run or bundle them.
import { useEffect, useState } from "preact/hooks";
import { html } from "./common.js";
import { DATA } from "./blepping_data.js";
import { OWNER, REPOS, byId, pairFor, ofPack, counts, stage0Verdict, samePixels, secs, gib, diffWord, stepMethod } from "./blepping_logic.js";

const R = DATA.renders, C = counts(R), S0 = stage0Verdict(DATA.stage0);
const calm = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
function jump(e, id) {
  e.preventDefault(); const el = document.getElementById(id); if (!el) return;
  el.scrollIntoView({ behavior: calm() ? "auto" : "smooth" }); el.focus({ preventScroll: true });
}
const Ext = ({ href, children, cls }) => html`<a class=${cls} href=${href} target="_blank" rel="noopener noreferrer">${children}</a>`;
const Head = ({ n, title, id, children }) => html`<header class="bp-head">${n && html`<span class="bp-num" aria-hidden="true">${n}</span>`}<h2 id=${id} tabindex="-1">${title}</h2>${children}</header>`;
const CHAPTERS = [["bp-idea", "Story"], ["bp-stage0", "First check"], ["bp-sonar", "Sonar"], ["bp-ocs", "OCS"], ["bp-bleh", "bleh"], ["bp-fit", "Together"], ["bp-misses", "What didn't"], ["bp-licence", "Licences"]];

/* Our notes on what each picture shows, written after looking at every one. Short, and only about this seed and these settings. */
const NOTES = {
  "son-sd15-sonar_euler": "Same layout as core euler; the engraving and the light differ.",
  "son-sd15-sonar_euler_ancestral": "A different picture from core euler_ancestral: the astrolabe stands on a stack of charts.",
  "son-sd15-sonar_dpmpp_sde": "No picture: a flat brown field. That's what these default settings gave on SD 1.5 with karras; we didn't tune it.",
  "son-sdxl-noise-pyramid": "At full ancestral strength, pyramid noise swamped the picture: blue and white blotches, no astrolabe.",
  "son-sdxl-noise-onef_greenish": "Strong, saturated colour and a new close-up composition.",
  "son-sdxl-noise-collatz": "A blurred table crossed by hard, patterned shadows.",
  "son-sdxl-noise-onef_pinkish": "Close to the Gaussian result, a little softer.",
  "son-sdxl-waveletcfg-14": "Failed: the pytorch_wavelets library is installed in our environment but can't load (it needs pkg_resources, which our setuptools no longer has).",
  "ocs-sd15-default": "OCS runs its step methods ancestrally by default (eta 1), so this is read against core euler_ancestral. The camera moves in close, as it does for most OCS renders here.",
  "ocs-sd15-euler-eta0": "With eta 0, OCS euler lands almost exactly on core euler. The sanity check passes.",
  "ocs-sd15-tde": "torchdiffeq's solver adds no noise, and it lands near core heun.",
  "ocs-sd15-ttm_jvp": "Failed: a float and half-precision mismatch inside the step. SD 1.5 runs in half precision here.",
  "bleh-sdxl-sage": "The same picture, with small changes in fine detail.",
  "bleh-sdxl-1536-hypertile": "Pixel for pixel the same as core HyperTile at the same settings.",
  "bleh-sdxl-1536-deepshrink": "Practically the same as core Deep Shrink at the same settings.",
  "son-sd35-sonar_euler": "On a flow model, Sonar's momentum keeps the layout and changes the detail.",
};

function Contents() {
  const [now, setNow] = useState("");
  useEffect(() => {
    const seen = CHAPTERS.map(([id]) => document.getElementById(id)).filter(Boolean);
    if (!seen.length || typeof IntersectionObserver === "undefined") return undefined;
    const io = new IntersectionObserver((list) => { for (const x of list) if (x.isIntersecting) setNow(x.target.id); }, { rootMargin: "-20% 0px -70% 0px" });
    seen.forEach((el) => io.observe(el)); return () => io.disconnect();
  }, []);
  return html`<nav class="bp-toc" aria-label="Chapters on this page"><ol>${CHAPTERS.map(([id, t], i) => html`<li><a href="#blepping" aria-current=${now === id ? "true" : undefined} onClick=${(e) => jump(e, id)}><i>${String(i + 1).padStart(2, "0")}</i>${t}</a></li>`)}</ol></nav>`;
}

function Shot({ r, label }) {
  if (!r) return html`<figure class="bp-shot bp-none"><div class="bp-noimg">No picture</div><figcaption><b>${label}</b></figcaption></figure>`;
  const w = r.size ? r.size[0] : 768, h = r.size ? r.size[1] : 768;
  return html`<figure class="bp-shot">${r.src ? html`<img src=${r.src} alt=${r.what} loading="lazy" width=${w} height=${h}/>` : html`<div class="bp-noimg">Failed: ${r.error}</div>`}
    <figcaption><b>${label}</b><span>${r.what}</span><span class="bp-meta">${r.model}, ${secs(r.seconds)}, peak ${gib(r.peak)}. <a href=${r.graph} download>Graph</a></span></figcaption></figure>`;
}

/* Two pictures, same prompt and seed: the core render it should be read against, then the pack's. */
function Compare({ ids, start }) {
  const list = ids.filter((id) => byId(R, id));
  const [id, setId] = useState(start && list.includes(start) ? start : list[0]);
  const p = pairFor(R, id); if (!p) return null;
  const note = NOTES[id];
  return html`<div class="bp-compare">
    <div class="bp-pick" role="group" aria-label="Pick a render">${list.map((x) => { const r = byId(R, x); return html`<button type="button" class="bp-chip" aria-pressed=${x === id} onClick=${() => setId(x)}>${r.label || x.replace(/^[a-z]+-(sd15|sdxl|sd35)-/, "")}${r.ok ? "" : " (failed)"}</button>`; })}</div>
    <div class="bp-pair">${p.a ? html`<${Shot} r=${p.a} label="Read it against"/>` : null}<${Shot} r=${p.b} label=${p.b.pack === "core" ? "Core" : "With the pack"}/></div>
    <p class="bp-read">${p.b.ok ? diffWord(p.b.diff) : "This one failed."}${note ? " " + note : ""}</p>
  </div>`;
}

function Grid({ ids }) {
  return html`<ul class="bp-grid">${ids.map((id) => byId(R, id)).filter(Boolean).map((r) => html`<li><figure>${r.src ? html`<img src=${r.src} alt=${r.what} loading="lazy" width="384" height="384"/>` : html`<div class="bp-noimg">Failed</div>`}<figcaption><code>${r.id.replace(/^[a-z]+-(sd15|sdxl|sd35)-(noise-)?/, "")}</code><span>${diffWord(r.diff)}</span></figcaption></figure></li>`)}</ul>`;
}

const ids = (pack, re) => ofPack(R, pack).filter((r) => !re || re.test(r.id)).map((r) => r.id);

export function Blepping() {
  useEffect(() => { document.body.classList.add("on-blepping"); return () => document.body.classList.remove("on-blepping"); }, []);
  const cover = byId(R, "son-sdxl-noise-onef_pinkish") || R.find((r) => r.src);
  const seedA = byId(R, "bleh-sd15-seed-core-a"), seedB = byId(R, "bleh-sd15-seed-core-b"), fa = byId(R, "bleh-sd15-seed-force-a"), fb = byId(R, "bleh-sd15-seed-force-b");
  const prevCore = byId(R, "core-sdxl-batch4-preview"), prevBleh = byId(R, "bleh-sdxl-batch4-preview");
  const failed = R.filter((r) => r.pack !== "core" && !r.ok && !r.expected_refusal);
  return html`<div class="bp">
    <section class="bp-hero film">
      ${cover && html`<figure class="bp-coverart"><img src=${cover.src} alt=${cover.what} width="768" height="768"/></figure>`}
      <div class="bp-herotext">
        <div class="bp-eyebrow">A thank-you</div>
        <h2>blepping</h2>
        <p class="bp-by">Sonar, Overly Complicated Sampling and bleh</p>
        <p class="bp-lead">Three ComfyUI node packs by one author: momentum sampling and a box of strange noises, a sampler you can rebuild step by step, and the plumbing that makes previews and seeds behave. One README calls its own pack <em>“Experimental and mathematically unsound (but fun!)”</em>.</p>
        <div class="bp-actions"><${Ext} cls="btn primary" href=${OWNER}>The author's repos<//><a class="btn" href="#blepping" onClick=${(e) => jump(e, "bp-licence")}>Licences</a></div>
      </div>
      ${cover && html`<p class="bp-covercap">Cover: our render, ${cover.model}. ${cover.what}</p>`}
    </section>

    <div class="bp-notes">
      <div class="card bp-status" role="note"><b>These packs don't ship with Parametric Studio.</b> We ran them in a separate, throwaway ComfyUI on our own machine, with no internet, and made every render on this page that way. The container is gone now. Our code and installs don't bundle any of them.</div>
      <div class="bp-licnote" role="note"><b>The licences, plainly.</b> Sonar and Overly Complicated Sampling are MIT, bleh is Apache-2.0. All three would allow bundling. We still don't, because two of them change ComfyUI's own sampler list and previewer as they load. <a href="#blepping" onClick=${(e) => jump(e, "bp-licence")}>More below.</a></div>
    </div>

    <dl class="bp-stats">
      <div><dt>${C.ok}</dt><dd>renders with the packs, of ${C.all} tried</dd></div>
      <div><dt>${DATA.packs.sonar ? DATA.packs.sonar.nodes : "?"}</dt><dd>Sonar nodes</dd></div>
      <div><dt>${DATA.packs.ocs ? DATA.packs.ocs.nodes : "?"}</dt><dd>OCS nodes</dd></div>
      <div><dt>${DATA.packs.bleh ? DATA.packs.bleh.nodes : "?"}</dt><dd>bleh nodes</dd></div>
      <div><dt>${DATA.noise_types.length}</dt><dd>noise types in Sonar's picker</dd></div>
    </dl>
    <p class="small bp-src">Counted from the lab's own node list with the packs loaded, at commits ${Object.values(DATA.packs).map((p) => html`<code>${p.folder} ${p.commit}</code> `)}. One seed (${DATA.seed}), ${DATA.steps} steps, one prompt for every render, and no picking: every result is kept.</p>

    <${Contents}/>

    <section class="bp-sect"><${Head} n="01" title="The idea" id="bp-idea"/>
      <p class="bp-story">A sampler walks from noise to a picture, one guess at a time. blepping's packs open that walk up in three ways. Sonar adds momentum to the step and lets you choose what kind of noise goes in. Overly Complicated Sampling lets one sampler switch method by step, split steps into substeps and merge them. bleh fixes the small things around it: previews of whole batches and videos, seeds that hold when noise is off, and model patches on a timer.</p>
      <div class="bp-two">
        <blockquote class="bp-quote">“This started out as an implementation of Sonar sampling and has evolved into something more like a noise toybox.”<cite>The Sonar README</cite></blockquote>
        <blockquote class="bp-quote">“I can move code around but sampling math and creating samplers generally beyond my ability.”<cite>The OCS README, before crediting every sampler's source</cite></blockquote>
      </div>
      <p>The packs know about each other. Sonar's noise can feed OCS, OCS's noise can be handed back to Sonar's nodes, and both use bleh's blend modes when it's there. We used that once below, on purpose: <a href="#blepping" onClick=${(e) => jump(e, "bp-fit")}>Together</a>.</p>
    </section>

    <section class="bp-sect" aria-labelledby="bp-stage0"><${Head} n="02" title="First check: do they change core?" id="bp-stage0"><p class="sectsub">Sonar and bleh add to ComfyUI's sampler list and reload its sampling module when they load, and bleh swaps in its own previewer. So before anything else we rendered the same core graphs twice, once with no packs loaded and once with all four, and compared the pixels. The files themselves always differ a little, because each PNG carries its own graph.</p><//>
      <div class=${"card bp-verdict " + (S0.ok ? "ok" : "warn")} role="status"><b>${S0.ok ? "Unchanged." : S0.word === "not run" ? "Not run." : "Changed."}</b> ${S0.of ? `${S0.same} of ${S0.of} core graphs gave pixel-identical pictures with the packs loaded.` : ""}</div>
      <ul class="bp-s0">${DATA.stage0.map((s) => html`<li><code>${s.id.replace("s0-", "")}</code> <span>${s.same_pixels ? "same pixels" : diffWord(s.diff)}</span></li>`)}</ul>
      <p class="small">With the packs loaded, the plain sampler list also offered ${DATA.added_samplers.map((s) => html`<code>${s}</code> `)}after core's own, in core's order.</p>
    </section>

    <section class="bp-sect bp-wide"><${Head} n="03" title="Sonar" id="bp-sonar"><p class="sectsub">Momentum sampling after Kahsolt's A1111 extension, and a toybox of noise. Our renders, against core renders made the same way.</p><//>
      <h3 class="bp-sub">Momentum samplers</h3>
      <p>Picked straight from the normal sampler list, at Sonar's defaults, and read against the core sampler each one builds on.</p>
      <${Compare} ids=${ids("sonar", /sonar_|momentum/)}/>
      <h3 class="bp-sub">The noise types</h3>
      <p>Core euler_ancestral with one change: the noise it adds each step comes from Sonar. Same seed, same everything else. The picker holds ${DATA.noise_types.length} types; we rendered ${ids("sonar", /noise-/).length}.</p>
      <${Grid} ids=${ids("sonar", /noise-/)}/>
      <${Compare} ids=${ids("sonar", /noise-|scheduled/)} start="son-sdxl-noise-onef_pinkish"/>
      <details class="bp-more"><summary>Every noise type in the picker</summary><p class="bp-chips">${DATA.noise_types.map((n) => html`<code>${n}</code> `)}</p></details>
      <h3 class="bp-sub">Guidance and FreeU</h3>
      <${Compare} ids=${ids("sonar", /waveletcfg|freeu/)}/>
    </section>

    <section class="bp-sect bp-wide"><${Head} n="04" title="Overly Complicated Sampling" id="bp-ocs"><p class="sectsub">One sampler node built from groups and substeps. We ran one step method at a time, on SD 1.5 with the karras schedule.</p><//>
      <p>The step methods come from many places, and the README names each: ComfyUI's own samplers, Clybius's Extra-Samplers, Katherine Crowson, Extraltodeus, zju-pi's diff-sampler and ACE-Step. The number after a name is how many extra model calls it makes per step.</p>
      <p class="bp-chips">${DATA.step_methods.map((m) => { const s = stepMethod(m); return html`<span class="bp-step"><code>${s.name}</code>${s.calls && html`<small>${s.calls}</small>`}</span> `; })}</p>
      <${Grid} ids=${ids("ocs", /^ocs-sd15-(default|reversible|res|rk4|rkf45|bogacki|clybius|ttm|pingpong|extraltodeus|tde)/)}/>
      <${Compare} ids=${ids("ocs").filter((x) => x !== "ocs-unsafe-refused")}/>
      <h3 class="bp-sub">Its safety switch</h3>
      <p>OCS has its own small expression language, read by its own parser. Calls into torch stay off unless an environment variable turns them on. We left them off and asked for one anyway: ${byId(R, "ocs-unsafe-refused") && !byId(R, "ocs-unsafe-refused").ok ? html`it refused, with <code>${((byId(R, "ocs-unsafe-refused").error || "").match(/Unsafe Torch access not allowed/) || ["an error"])[0]}</code>.${byId(R, "ocs-unsafe-refused").retry ? " " + byId(R, "ocs-unsafe-refused").retry : ""}` : "see the render sheet."}</p>
    </section>

    <section class="bp-sect bp-wide"><${Head} n="05" title="bleh" id="bp-bleh"><p class="sectsub">Utilities and model patches. Most of them change how things run rather than how a picture looks.</p><//>
      <h3 class="bp-sub">The seed fix</h3>
      <p>The README says that with noise turned off, samplers like euler_ancestral get no seed at all, so the same graph gives a different picture each time. We ran an img2img pass with noise off twice plainly, and twice wrapped in BlehForceSeedSampler, clearing ComfyUI's cache between.</p>
      <div class="bp-seed">
        <${Shot} r=${seedA} label="Plain, run 1"/><${Shot} r=${seedB} label="Plain, run 2"/><${Shot} r=${fa} label="Wrapped, run 1"/><${Shot} r=${fb} label="Wrapped, run 2"/>
      </div>
      <p class="bp-read">${seedA && seedB && fa && fb ? html`Plain: ${samePixels(seedA, seedB) ? "the two runs gave the same pixels" : "the two runs differ"}. Wrapped: ${samePixels(fa, fb) ? "the two runs gave the same pixels" : "the two runs differ"}. ${samePixels(seedA, fa) ? "And the wrapped runs matched the plain ones exactly. On the ComfyUI version we ran, a sampler with noise turned off already gets a fixed seed (zero), so the problem this node works around didn't show up here. It may on older versions." : ""}` : "Not all four ran."}</p>
      <p class="small">With noise off and denoise at 0.6, the sampler starts from a clean latent at a high noise level, so all four pictures come out soft. That's expected for this test, which is about repeatability, not looks.</p>
      <h3 class="bp-sub">Patches and samplers</h3>
      <${Compare} ids=${ids("bleh", /discard|insane|blockcfg|deepshrink|hypertile|sage/)}/>
      <h3 class="bp-sub">The previewer</h3>
      <p>bleh replaces ComfyUI's preview function when it loads. We watched the preview stream of one batch of four, once without the packs and once with them.</p>
      <div class="bp-pair">
        ${prevCore && html`<figure class="bp-shot">${prevCore.preview_src ? html`<img src=${prevCore.preview_src} alt="The last preview frame without the packs" loading="lazy"/>` : html`<div class="bp-noimg">No frame</div>`}<figcaption><b>Without the packs</b><span>${prevCore.preview_frames} preview frames${prevCore.preview_size ? `, last one ${prevCore.preview_size[0]}×${prevCore.preview_size[1]}` : ""}.</span></figcaption></figure>`}
        ${prevBleh && html`<figure class="bp-shot">${prevBleh.preview_src ? html`<img src=${prevBleh.preview_src} alt="The last preview frame with bleh's previewer" loading="lazy"/>` : html`<div class="bp-noimg">No frame</div>`}<figcaption><b>With bleh</b><span>${prevBleh.preview_frames} preview frames${prevBleh.preview_size ? `, last one ${prevBleh.preview_size[0]}×${prevBleh.preview_size[1]}` : ""}.</span></figcaption></figure>`}
      </div>
      ${prevCore && prevBleh && prevCore.preview_src && prevBleh.preview_src ? html`<p class="bp-read">Core's preview showed only the first picture of the batch. bleh's showed all four as a grid. ${samePixels(prevCore, prevBleh) ? "The finished pictures were pixel-identical either way: the previewer changes what you watch, not what you get." : ""}</p>` : null}
      <p class="small">bleh also decodes video previews for Wan, Hunyuan, LTX, Mochi and MiniMax H3, and draws previews for audio models including MiniMax Music3. We didn't test those here.</p>
    </section>

    <section class="bp-sect" aria-labelledby="bp-fit"><${Head} n="06" title="How they fit together" id="bp-fit"/>
      <p>Each pack looks for the others as it loads and adds nodes when it finds them. One of our renders uses that on purpose: Perlin noise made by an OCS node, converted, and handed to Sonar's sampler override as the noise euler_ancestral adds.</p>
      <${Compare} ids=${["ocs-sd15-perlin"]}/>
    </section>

    <section class="bp-sect" aria-labelledby="bp-misses"><${Head} n="07" title="What didn't work, and what we didn't try" id="bp-misses"/>
      ${failed.length ? html`<ul class="bp-fails">${failed.map((r) => html`<li><code>${r.id}</code>: ${r.what} <span class="bp-err">${r.error}</span></li>`)}</ul>` : html`<p>Every graph we built ran.</p>`}
      <p>We didn't load <code>BlehGlobalSageAttention</code>: it rewrites ComfyUI's attention for the whole server until a restart. We didn't try bleh's video previews, the diffrax or torchode solvers (their libraries aren't installed), or anything on video models. A picture here means the graph ran with these settings, one seed and one prompt. It is not a ranking.</p>
    </section>

    <section class="bp-sect" aria-labelledby="bp-licence"><${Head} n="08" title="Licences" id="bp-licence"/>
      <div class="bp-licence">
        <ul class="bp-lic">${["sonar", "ocs", "bleh"].map((k) => html`<li><b>${REPOS[k].label}</b> <span>${DATA.packs[k] ? DATA.packs[k].licence : "?"}</span> <${Ext} href=${REPOS[k].href + "/blob/main/LICENSE"}>LICENSE<//></li>`)}</ul>
        <p>MIT and Apache-2.0 both fit inside Parametric Studio's AGPL-3.0 licence. The packs' own READMEs credit code they adapted from others; two of those sources matter if anyone copies code from Sonar: its 1/f and power-law noise is credited as referenced from a GPL-3.0 pack, and its pattern-break noise as adapted from a repo with no licence file.</p>
        <p>This page holds no code from the packs: only names, counts, short credited quotes, our own notes, and our own graphs and renders. The page itself is part of Parametric Studio, under its AGPL-3.0 licence. This is a reading of the files, not legal advice.</p>
        <p><b>A safety note:</b> OCS's expression language can be opened up to run torch calls by setting <code>COMFYUI_OCS_ALLOW_ALL_UNSAFE</code>. With that set, a shared workflow can do anything ComfyUI can. Leave it unset.</p>
      </div>
    </section>

    <section class="bp-thanks film">
      <p class="bp-eyebrow">The last word</p>
      <p class="bp-thankline"><span>Thank you,</span> <span>blepping.</span></p>
      <p>The work belongs to the author, the contributors and everyone the READMEs credit. Any mistake in how this page reads it is ours.</p>
      <div class="bp-actions">${["sonar", "ocs", "bleh"].map((k) => html`<${Ext} cls="btn" href=${REPOS[k].href}>${REPOS[k].label}<//>`)}</div>
    </section>
  </div>`;
}
