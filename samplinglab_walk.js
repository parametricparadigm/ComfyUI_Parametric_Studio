/* Sampling Lab, Walk: two seeds with the starting noise slerped, two prompts with the conditioning lerped, a straight blend against slerp, and every sampler step of one render. All rendered on this machine by scripts/latent_walk_renders.py; data from /api/sampling/walk. */
import { useEffect, useState } from "preact/hooks";
import { html, api } from "./common.js";
import { Wipe } from "./samplinglab_kit.js";

const IMG = (f) => "sampling_lab/walk/" + f;
const t8 = (t) => (t === 0 ? "0" : t === 1 ? "1" : t.toFixed(3).replace(/0+$/, ""));

function Scrub({ frames, label, left, right, id }) {
  const [i, setI] = useState(Math.floor(frames.length / 2)), f = frames[i];
  return html`<div class="slwk-scrub">
    <figure class="slwk-big film"><img src=${IMG(f.img)} alt=${`${label}, t = ${t8(f.t)}`} width="512" height="512"/><figcaption><b>t = ${t8(f.t)}</b><span>${f.t === 0 ? left : f.t === 1 ? right : `${Math.round((1 - f.t) * 100)}% ${left}, ${Math.round(f.t * 100)}% ${right}`}</span></figcaption></figure>
    <label class="slwk-range"><span>Move along the walk</span><input id=${id} type="range" min="0" max=${frames.length - 1} step="1" value=${i} aria-valuetext=${`t = ${t8(f.t)}`} onInput=${(e) => setI(+e.target.value)}/></label>
    <ol class="slwk-film" aria-label=${label + ", every frame"}>${frames.map((x, k) => html`<li key=${k}><button type="button" aria-pressed=${k === i} aria-label=${`t = ${t8(x.t)}`} onClick=${() => setI(k)}><img src=${IMG(x.img)} alt="" width="96" height="96" loading="lazy"/><span>${t8(x.t)}</span></button></li>`)}</ol>
  </div>`;
}

function Strip({ s }) {
  const [k, setK] = useState(4), st = s.steps[k - 1], n = s.steps.length;
  return html`<div class="slwk-strip">
    <div class="slwk-pair"><figure class="film"><img src=${IMG(st.x)} alt=${`What the sampler holds after step ${k}`} width="256" height="256"/><figcaption><b>Holds</b> after step ${k} of ${n}: the latent, still part noise, decoded as it is</figcaption></figure>
      <figure class="film"><img src=${IMG(st.x0)} alt=${`The model's guess at the finished picture during step ${k}`} width="256" height="256"/><figcaption><b>Predicts</b> during step ${k}: the finished picture the model aims at from there</figcaption></figure></div>
    <label class="slwk-range"><span>Step ${k} of ${n}</span><input type="range" min="1" max=${n} step="1" value=${k} aria-valuetext=${`step ${k} of ${n}`} onInput=${(e) => setK(+e.target.value)}/></label>
    <div class="slwk-rows">${[["x", "Holds"], ["x0", "Predicts"]].map(([key, word]) => html`<div key=${key}><span class="slkick">${word}</span><ol class="slwk-grid" aria-label=${word + ", every step"}>${s.steps.map((x) => html`<li key=${x.k}><button type="button" aria-pressed=${x.k === k} aria-label=${`${word}, step ${x.k}`} onClick=${() => setK(x.k)}><img src=${IMG(x[key])} alt="" width="72" height="72" loading="lazy"/><span>${x.k}</span></button></li>`)}</ol></div>`)}</div>
  </div>`;
}

function Graph({ name, g }) {
  const [msg, setMsg] = useState("");
  const copy = async () => { try { await navigator.clipboard.writeText(JSON.stringify(g, null, 1)); setMsg("Copied. Paste it into ComfyUI to run it."); } catch { setMsg("The browser would not copy it."); } };
  return html`<li><b>${name}</b><span class="slnote">${Object.keys(g).length} nodes</span><button class="btn small" type="button" onClick=${copy}>Copy the graph</button><span class="slnote" role="status">${msg}</span></li>`;
}

export function Walk() {
  const [w, setW] = useState(null), [err, setErr] = useState("");
  useEffect(() => { api("/api/sampling/walk").then(setW).catch((e) => setErr((e && e.message) || "The walk didn't load.")); }, []);
  if (err) return html`<div class="slview"><p class="slnote">${err}</p></div>`;
  if (!w) return html`<div class="slview"><p class="slnote" role="status">Loading the walk.</p></div>`;
  const s = w.settings, m = w.measured, n = w.blend.noise, frames = w.seed_walk.frames.length + w.prompt_walk.frames.length + 1 + w.strip.steps.length * 2 + 3;
  return html`<div class="slview slwk">
    <section class="slwk-head film" aria-labelledby="slwk-h"><div><span class="slkick">Rendered on this machine</span><h2 id="slwk-h">The latent walk</h2>
      <p>Every picture here starts as random noise in a small grid of numbers, the latent. Change the noise and you get a different picture; change the prompt and the same noise lands somewhere else. Walk smoothly between two of either, and the picture moves smoothly too. Then watch one render, step by step.</p></div>
      <div class="slfigs"><div><b class="gold">${frames}</b><span>pictures, all ${w.model.name} at ${s.size} px, ${s.steps} ${s.sampler} steps, ${s.scheduler} schedule, CFG ${s.cfg}</span></div><div><b>${m.peak_vram_gib}</b><span>GiB peak of the ComfyUI that drew them, measured. ${m.declared_gib} GiB was declared to the GPU gate first.</span></div><div><b>${Object.values(m.seconds).reduce((a, b) => a + b, 0).toFixed(0)}</b><span>seconds for all of it on ${m.gpu || "one GPU"}, loading included</span></div></div></section>

    <section class="slpanel" aria-labelledby="slwk-seed"><div class="slpanel-head"><div><span class="slkick">One prompt, two seeds</span><h3 id="slwk-seed">Walking the noise</h3>
      <p class="slnote">"${w.seed_walk.prompt}". Seeds ${w.seed_walk.seeds[0]} and ${w.seed_walk.seeds[1]} each make a field of ${n.elements.toLocaleString()} random numbers. In between, the noise is slerped: it turns along the sphere from one field to the other, so it stays the size of real noise all the way. Nothing else changes.</p></div></div>
      <${Scrub} frames=${w.seed_walk.frames} label="The seed walk" left=${"seed " + w.seed_walk.seeds[0]} right=${"seed " + w.seed_walk.seeds[1]} id="slwk-r1"/>
      <p class="slnote"><span class="slp proof">Measured here</span> The ends check out: t = 0 against an ordinary KSampler on seed ${w.seed_walk.seeds[0]} differs by ${w.seed_walk.check.t0_vs_plain} on average (0 to 255 per channel), and t = 1 against seed ${w.seed_walk.seeds[1]} by ${w.seed_walk.check.t1_vs_plain}. The walk hands the sampler noise it made itself, scaled by the same ${s.sigma_max} that KSampler uses, and turns its own noise off.</p></section>

    <section class="slpanel" aria-labelledby="slwk-why"><div class="slpanel-head"><div><span class="slkick">Why slerp</span><h3 id="slwk-why">The halfway point, two ways</h3>
      <p class="slnote">A straight average of two unrelated noises is smaller than either: the two point in nearly unrelated directions (${n.angle_degrees}° apart here), so half of each partly cancels. The sampler still treats it as full-strength noise, and the picture goes flat. Slerp keeps the size.</p></div></div>
      <div class="slfigs small"><div><b>${n.norm.a}</b><span>size of seed ${w.seed_walk.seeds[0]}'s noise (its length as one long vector)</span></div><div><b class="gold">${n.norm.slerp}</b><span>slerp at t = 0.5</span></div><div><b>${n.norm.lerp}</b><span>straight average at t = 0.5, ${(n.norm.lerp / n.norm.a).toFixed(2)} times the size</span></div></div>
      <div class="slwk-wipe"><${Wipe} a=${{ id: "slerp", url: IMG(w.blend.slerp), label: "slerp at t = 0.5" }} b=${{ id: "lerp", url: IMG(w.blend.lerp), label: "straight average at t = 0.5" }} sized=${512}/></div>
      <p class="slnote"><span class="slp proof">Measured here</span> Sizes from the same random generator ComfyUI uses, on the CPU. The two pictures differ by ${w.blend.pixel_diff} on average. One seed pair, one prompt: it shows the effect, it doesn't measure how often.</p></section>

    <section class="slpanel" aria-labelledby="slwk-prompt"><div class="slpanel-head"><div><span class="slkick">One seed, two prompts</span><h3 id="slwk-prompt">Walking the prompt</h3>
      <p class="slnote">Seed ${w.prompt_walk.seed} throughout. "${w.prompt_walk.prompts[0]}" becomes "${w.prompt_walk.prompts[1]}". Each frame mixes the two text encodings in a straight line with ComfyUI's ConditioningAverage, so the starting noise is the same and only what the model is told to look for moves.</p></div></div>
      <${Scrub} frames=${w.prompt_walk.frames} label="The prompt walk" left="the cottage prompt" right="the sailboat prompt" id="slwk-r2"/>
      <p class="slnote">A straight line is the usual way to mix encodings, since they aren't random noise and slerp's reason for keeping the size doesn't apply. The middle frames are the model's answer to a prompt nobody wrote.</p></section>

    <section class="slpanel" aria-labelledby="slwk-strip"><div class="slpanel-head"><div><span class="slkick">One render, every step</span><h3 id="slwk-strip">From noise to a picture</h3>
      <p class="slnote">"${w.strip.prompt}", seed ${w.strip.seed}. Each step is its own run, stopped after k of the ${s.steps} steps of the same schedule, and both of its outputs are decoded with the full VAE: what the sampler holds, and what the model predicted the finished picture would be. Early on the guess is a blur and the latent is mostly noise; by the end they meet.</p></div></div>
      <${Strip} s=${w.strip}/>
      <p class="slnote"><span class="slp proof">Measured here</span> The last step against an ordinary KSampler with the same seed differs by ${w.strip.check.last_vs_plain} on average, so stopping early didn't change the path. The strip pictures are shrunk to 256 px for this page.</p></section>

    <section class="slpanel" aria-labelledby="slwk-how"><div class="slpanel-head"><div><span class="slkick">How it was made</span><h3 id="slwk-how">The graphs</h3>
      <p class="slnote">${w.model.name} (${w.model.ckpt}, ${w.model.licence}). Nodes: ${m.packs.join("; ")}. Run ${m.date} on a ComfyUI of its own (version ${m.comfyui || "not reported"}, ${m.flags.join(" ")}), never the studio's main one, after a turn from the shared GPU gate. The noise node is kijai's GenerateNoise from KJNodes; the slerp is the studio pack's PSN_LatentSlerp.</p></div></div>
      <ul class="slwk-graphs">${Object.entries(w.graphs).map(([k, g]) => html`<${Graph} key=${k} name=${{ seed_walk: "Seed walk", prompt_walk: "Prompt walk", strip: "Step strip" }[k] || k} g=${g}/>`)}</ul>
      <p class="slnote">The seed walk graph needs KJNodes and the Parametric Studio node pack; the other two are ComfyUI core only.</p></section>
  </div>`;
}
