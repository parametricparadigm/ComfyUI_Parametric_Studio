/* Which word painted what: a picture and one heatmap per prompt word, read out of SD 1.5 and SDXL cross-attention by our PSN nodes while the picture was made.
Hover or focus a word to see where it looked. Hover or tap the picture to see which words looked at that spot. Proof renders come from /api/words; a run of your own reads its maps back from ComfyUI. */
import { useEffect, useMemo, useRef, useState } from "preact/hooks";
import { html, api, post } from "./common.js";
import { copyText } from "./fx.js";
import { PHASES, phaseIndex, fromSprite, spriteWords, liveWords, cellAt, ranked, paint, checkLine, pct } from "./words_logic.js";

const SHOW = 512;
function useImage(src) {
  const [img, setImg] = useState(null);
  useEffect(() => { if (!src) return; let on = true; const im = new Image(); im.onload = () => on && setImg(im); im.onerror = () => on && setImg(null); im.src = src; return () => { on = false; }; }, [src]);
  return img;
}
function pixels(im, w, h) { const c = document.createElement("canvas"); c.width = w; c.height = h; const x = c.getContext("2d", { willReadFrequently: true }); x.drawImage(im, 0, 0, w, h); return x.getImageData(0, 0, w, h).data; }

/* The viewer: one picture, its words, and the maps. words: [{word, share, peak, maps: [all, early, middle, late]}] */
function Viewer({ src, words, mh, mw, startShare, endShare, label }) {
  const im = useImage(src); const cv = useRef(null); const [hover, setHover] = useState(null); const [pin, setPin] = useState(null); const [phase, setPhase] = useState("all"); const [cell, setCell] = useState(null);
  const base = useMemo(() => im ? pixels(im, SHOW, SHOW) : null, [im]); const ph = phaseIndex(phase);
  const at = useMemo(() => cell ? ranked(words, cell, mw) : null, [cell, words, mw]);
  const shown = hover != null ? hover : pin != null ? pin : at ? at[0].i : null;
  useEffect(() => { setPin(null); setHover(null); setCell(null); }, [words]);
  useEffect(() => {
    if (!base || !cv.current) return; const x = cv.current.getContext("2d"), o = x.createImageData(SHOW, SHOW); const m = shown != null && words[shown] ? words[shown].maps[ph] : null;
    paint(base, o.data, SHOW, SHOW, m, mh, mw); x.putImageData(o, 0, 0);
  }, [base, shown, ph, words]);
  const point = (e) => { const r = e.currentTarget.getBoundingClientRect(); setCell(cellAt(e.clientX - r.left, e.clientY - r.top, r.width, r.height, mh, mw)); };
  const top = at ? at.slice(0, 4) : []; const total = top.reduce((t, r) => t + r.v, 0) || 1; const name = shown != null && words[shown] ? words[shown].word : null;
  return html`<div class="ww-view">
    <figure class="ww-pic"><canvas ref=${cv} width=${SHOW} height=${SHOW} role="img" aria-label=${name ? `${label}, with the attention of the word ${name} laid over it` : label} onPointerMove=${point} onPointerDown=${point} onPointerLeave=${() => setCell(null)}></canvas>
      <figcaption class="small">${name ? html`Showing <b>${name}</b>${pin != null && hover == null && !cell ? " (pinned)" : ""}. Bright means the picture looked at this word there.` : "Hover a word, or the picture."}</figcaption></figure>
    <div class="ww-side">
      <div class="ww-seg" role="group" aria-label="Which steps">${PHASES.map(([k, l]) => html`<button type="button" class="btn small" aria-pressed=${phase === k} onClick=${() => setPhase(k)}>${l}</button>`)}</div>
      <ul class="ww-words" aria-label="Prompt words, by share of the picture's attention">${words.map((w, i) => html`<li key=${i}><button type="button" class=${"ww-word" + (shown === i ? " on" : "")} aria-pressed=${pin === i}
          onPointerEnter=${() => setHover(i)} onPointerLeave=${() => setHover(null)} onFocus=${() => setHover(i)} onBlur=${() => setHover(null)} onClick=${() => setPin(pin === i ? null : i)}>
          <span>${w.word}</span><i style=${{ "--w": Math.min(1, w.share / Math.max(...words.map((x) => x.share), 1e-9)) }}></i><b>${pct(w.share)}</b></button></li>`)}</ul>
      <div class="ww-here" aria-live="polite">${at ? html`<p class="small">At this spot, among the words:</p><ol>${top.map((r) => html`<li key=${r.i}><span>${words[r.i].word}</span><b>${pct(r.v / total)}</b></li>`)}</ol>` : html`<p class="small">Tap or hover the picture to see which words looked there.</p>`}</div>
      ${startShare != null && html`<p class="small">Of all the attention, the start token took ${pct(startShare)} and the end and padding tokens ${pct(endShare || 0)}. The words share the rest. SD 1.5 sends most of it to the start token; SDXL hardly any.</p>`}
      <p class="small">Each map is stretched between its own lowest and highest value, so a word that looks everywhere still shows where it looked most. SDXL spreads much of each word evenly over the picture.</p>
    </div></div>`;
}

/* A proof render: picture, sprite of maps, checks, and the proof that recording changes nothing. */
function Proof({ r, high, low }) {
  const sp = useImage(r.maps); const [mh, mw] = r.map_size;
  const rows = useMemo(() => sp ? fromSprite(pixels(sp, sp.naturalWidth, sp.naturalHeight), sp.naturalWidth, r.words.length, mh, mw) : null, [sp, r]);
  const words = useMemo(() => rows ? spriteWords(r, rows) : [], [rows, r]);
  const p = r.proof || {};
  return html`<div class="fx-card">
    <p class="fx-kick">${r.model === "sdxl" ? "SDXL base 1.0" : "SD 1.5"} · seed ${r.seed} · ${r.steps} steps · ${r.sampler} ${r.scheduler} · CFG ${r.cfg}</p>
    <h3>“${r.prompt}”</h3>
    ${rows ? html`<${Viewer} src=${r.image} words=${words} mh=${mh} mw=${mw} startShare=${r.start_share} endShare=${r.end_share} label=${`Render of: ${r.prompt}`}/>` : html`<p class="small">Loading the maps.</p>`}
    ${r.checks && r.checks.length ? html`<div class="ww-checks"><h3>Does it make sense?</h3><ul>${r.checks.map((c, i) => html`<li key=${i}><span class=${"fx-tag " + (c.ok ? "ok" : "bad")}>${c.ok ? "as expected" : "not as expected"}</span>${c.ok_above_floor != null && html` <span class=${"fx-tag " + (c.ok_above_floor ? "ok" : "bad")}>above the floor: ${c.ok_above_floor ? "as expected" : "not as expected"}</span>`} ${checkLine(c, high, low)}</li>`)}</ul>
      <p class="small">Colour regions are plain hue thresholds on the finished picture, set before these renders were made. They are a check on the maps, not ground truth: a blue background counts as blue as much as a blue cup does. The first verdict reads raw attention and was set before any render. The second reads only what rises above each word's floor; we added it after the first SDXL run showed that floor, and judge it by the same thresholds.</p></div>` : null}
    <dl class="ww-facts">
      <div><dt>Cross-attention layers recorded</dt><dd>${r.layers} (${r.calls} calls over ${r.steps_recorded} steps)</dd></div>
      <div><dt>Map grid</dt><dd>${mw} × ${mh} cells, from a ${r.latent ? r.latent.join(" × ") : "?"} latent</dd></div>
      ${p.same_picture_mean_abs != null && html`<div><dt>Same picture as without the recorder?</dt><dd>Mean difference ${p.same_picture_mean_abs} of 255, largest ${p.same_picture_max_abs}${p.pixels_off_by_over_10 != null ? `, ${pct(p.pixels_off_by_over_10)} of pixels off by more than 10` : ""}. Our attention runs in float32, the default in half precision, and 20 steps carry the rounding forward; the method is the same.</dd></div>`}
      ${p.seconds_recorded != null && html`<div><dt>Time, recorded / plain</dt><dd>${p.seconds_recorded} s / ${p.seconds_plain_warm} s, model already loaded</dd></div>`}
      <div><dt>Peak VRAM of the ComfyUI process</dt><dd>${r.peak_vram_gib} GiB, measured on ${r.ran_on || "our GPU"}, ${r.when}</dd></div>
    </dl></div>`;
}

/* Run one of your own on this studio's ComfyUI. */
function RunOwn() {
  const [model, setModel] = useState("sd15"); const [prompt, setPrompt] = useState("a red hat on a wooden table"); const [seed, setSeed] = useState(424242); const [st, setSt] = useState(null); const [res, setRes] = useState(null); const [err, setErr] = useState(""); const [copied, setCopied] = useState("");
  const timer = useRef(null); useEffect(() => () => clearTimeout(timer.current), []);
  const poll = (jid) => { timer.current = setTimeout(async () => {
    try { const j = await api(`/api/jobs/${jid}`); if (j.status === "error") { setErr(j.error || "The job failed."); setSt(null); return; }
      if (j.status !== "done") { setSt(j.status === "queued" ? `Queued, position ${j.position || 1}` : "Drawing and recording"); poll(jid); return; }
      const r = await api(`/api/words/result/${jid}`); if (r.status === "error") { setErr(r.error); setSt(null); return; } if (r.status !== "done") { poll(jid); return; }
      setRes(r); setSt(null);
    } catch (e) { setErr(e.message); setSt(null); } }, 1500); };
  const go = async () => { setErr(""); setRes(null); setSt("Sending"); try { const r = await post("/api/words/run", { model, prompt, seed }); poll(r.job); } catch (e) { setErr(e.message); setSt(null); } };
  const copy = async () => { try { const g = await api(`/api/words/graph?${new URLSearchParams({ model, prompt, seed })}`); setCopied(await copyText(JSON.stringify(g.graph, null, 1)) ? "Copied the graph." : "Your browser would not copy."); } catch (e) { setErr(e.message); } };
  const words = useMemo(() => res ? liveWords(res.maps) : [], [res]);
  return html`<div class="fx-card"><h2>Try your own</h2><p class="small">Runs on this studio's ComfyUI with the two PSN nodes. It needs SD 1.5 or SDXL base on disk, and draws one picture.</p>
    <div class="ww-form"><div class="ww-seg" role="group" aria-label="Model">${[["sd15", "SD 1.5"], ["sdxl", "SDXL"]].map(([k, l]) => html`<button type="button" class="btn small" aria-pressed=${model === k} onClick=${() => setModel(k)}>${l}</button>`)}</div>
      <label class="fx-lab">Prompt<input class="fx-in" value=${prompt} maxlength="300" onInput=${(e) => setPrompt(e.target.value)}/></label>
      <label class="fx-lab">Seed<input class="fx-in" type="number" min="0" value=${seed} onInput=${(e) => setSeed(+e.target.value || 0)}/></label></div>
    <div class="fx-row"><button type="button" class="fx-go" disabled=${!!st || !prompt.trim()} onClick=${go}>${st || "Draw and record"}</button><button type="button" class="btn" onClick=${copy}>Copy the graph</button>${copied && html`<span class="small" role="status">${copied}</span>`}</div>
    ${err && html`<p class="fx-err" role="alert">${err}</p>`}
    ${res && html`<${Viewer} src=${res.image} words=${words} mh=${res.maps.map_size[0]} mw=${res.maps.map_size[1]} startShare=${res.maps.start_share} endShare=${res.maps.end_share} label=${`Your render of: ${prompt}`}/>`}</div>`;
}

export function WhichWord() {
  const [d, setD] = useState(null); const [err, setErr] = useState(""); const [pick, setPick] = useState(0);
  useEffect(() => { api("/api/words").then(setD).catch((e) => setErr(e.message)); }, []);
  if (err) return html`<div class="fx"><p class="fx-err" role="alert">The renders did not load: ${err}</p></div>`;
  if (!d) return html`<div class="fx"><p class="small">Loading.</p></div>`;
  const rs = d.renders || []; const r = rs[Math.min(pick, rs.length - 1)];
  return html`<div class="fx ww">
    <div class="fx-note"><p><b>How this works.</b> In SD 1.5 and SDXL, every cell of the picture asks the prompt's tokens a question at each cross-attention layer and gets back a share of attention for each token, adding to 100%. Our record node keeps those shares while the picture is drawn, averages them over the attention heads, the layers and the steps, and the maps node turns them into one heatmap per word.</p>
      <p class="small">It reads attention, which is where the model looked. It is not proof that a word caused a pixel. DiT models such as Flux and SD3 mix text and picture in one attention, so these two nodes refuse them. The idea of resizing cross-attention scores into per-word heatmaps comes from Tang et al. 2022, <a class="sllink" href="https://arxiv.org/abs/2210.04885" rel="noopener" target="_blank">What the DAAM</a>; the code here is our own.</p></div>
    ${rs.length ? html`<div class="ww-seg wide" role="group" aria-label="Which render">${rs.map((x, i) => html`<button type="button" class="btn small" aria-pressed=${i === pick} onClick=${() => setPick(i)}>${x.model === "sdxl" ? "SDXL" : "SD 1.5"}: ${x.prompt.length > 34 ? x.prompt.slice(0, 32) + "…" : x.prompt}</button>`)}</div>
      <${Proof} key=${r.id} r=${r} high=${d.high} low=${d.low}/>` : html`<p class="small">No proof renders yet.</p>`}
    ${d.sheet && html`<div class="fx-card"><h2>What the node gives you in ComfyUI</h2><p class="small">Wire <code>Attention Record</code> between the checkpoint and the sampler, and <code>Attention Maps per word</code> after the decode. It outputs this sheet, the maps as a MASK batch in word order, and the numbers as JSON.</p>
      <img class="ww-sheet" src=${d.sheet} alt="The node's sheet: the picture, then one overlay per word with its share of attention" loading="lazy"/></div>`}
    <${RunOwn}/>
  </div>`;
}
