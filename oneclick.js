/* One click (on the Edit page): one photo or clip in, a finished set out. A coverage set of camera angles, a relight, a photo effect with an optional clip,
   and an alpha matte dropped onto a new set. Each tool lists every model it loads with its licence, and shows our own render as its example, labelled so. */
import { useState, useEffect } from "preact/hooks";
import { html, api, post } from "./common.js";
import { Empty, Head, Media, Offline, Stage, Stats, useHealth } from "./look.js";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
if (typeof document !== "undefined" && !document.querySelector('link[href="oneclick.css"]')) { const l = document.createElement("link"); l.rel = "stylesheet"; l.href = "oneclick.css"; document.head.appendChild(l); }
const OURS = "Our own render with this tool, not yours";

/* every model the tool loads, with its licence and the words a person must see before picking it */
export function Licences({ models }) {
  return html`<div class="oc-lic"><h4>Models and licences</h4><ul>${models.map((m) => html`<li key=${m.id}><b>${m.name}</b><span>${m.licence}</span>${m.badge && html`<em class="oc-limit">${m.badge}</em>`}${m.url && html`<a href=${m.url} target="_blank" rel="noopener noreferrer">licence page</a>`}</li>`)}</ul></div>`;
}

/* one result or one example frame; an alpha clip plays over a checkerboard so its transparency shows */
function Out({ f }) {
  const body = f.kind === "video" ? html`<video src=${f.url} controls loop muted playsinline preload="metadata"></video>` : html`<img src=${f.url} alt=${f.label} loading="lazy"/>`;
  return html`<figure class=${"oc-out" + (f.alpha ? " oc-alpha" : "")}>${f.alpha && /\.mov($|&)/i.test(f.url) ? html`<div class="oc-file">ProRes 4444 with alpha. Browsers can't play it; download it for your editor.</div>` : body}
    <figcaption><b>${f.label}</b><a class="btn small" href=${f.url} download>Download</a></figcaption></figure>`;
}

function Example({ ex }) {
  if (!ex) return null;
  return html`<div class="oc-example"><p class="small oc-ours"><span class="lk-tag">Our render</span>${OURS}.</p><p class="small oc-ours">${ex.note || ""}</p>
    ${ex.source && html`<figure class="oc-out oc-src">${/\.(mp4|webm)$/i.test(ex.source) ? html`<video src=${ex.source} muted loop playsinline controls preload="metadata"></video>` : html`<img src=${ex.source} alt="The source" loading="lazy"/>`}<figcaption><b>Source</b></figcaption></figure>`}
    <div class="oc-grid">${(ex.items || []).map((x) => html`<${Out} key=${x.src} f=${{ url: x.src, label: x.label, kind: /\.(mp4|webm|mov)$/i.test(x.src) ? "video" : "image", alpha: x.alpha }}/>`)}</div>
    ${(ex.seconds || ex.peak_vram_gib) && html`<p class="small oc-meta">${ex.seconds ? `${ex.seconds} s` : ""}${ex.peak_vram_gib ? ` · ${ex.peak_vram_gib} GB VRAM at peak` : ""}${ex.gpu ? ` on ${ex.gpu}` : ""}</p>`}</div>`;
}

function ToolForm({ t, onBack, health }) {
  const [vals, setVals] = useState({ ...t.defaults }), [text, setText] = useState({}), [file, setFile] = useState(null), [seed, setSeed] = useState(""), [busy, setBusy] = useState(false), [err, setErr] = useState(""), [res, setRes] = useState(null), [tick, setTick] = useState(0);
  const isVideo = t.input === "video";
  const upload = async (f) => { if (!f) return; const fd = new FormData(); fd.append("file", f); setErr(""); try { const r = await api("/api/upload", { method: "POST", body: fd }); setFile({ name: r.name, url: URL.createObjectURL(f) }); } catch (e) { setErr(e.message); } };
  const run = async () => {
    if (!file) { setErr(isVideo ? "Add a source clip first" : "Add a photo first"); return; }
    setBusy(true); setErr(""); setRes(null); setTick(0); const t0 = Date.now();
    try {
      const { job } = await post(`/api/oneclick/${t.id}/run`, { [isVideo ? "video" : "image"]: file.name, options: vals, text, seed: seed === "" ? null : +seed });
      for (let i = 0; i < 2400; i++) { await sleep(1500); setTick(Math.round((Date.now() - t0) / 1000)); const s = await api("/api/oneclick/jobs/" + job); if (s.status === "done") { setRes(s); break; } if (s.status === "error") { setErr(s.error || "The job failed"); break; } }
    } catch (e) { setErr(e.message); }
    setBusy(false);
  };
  const clip = t.id === "effects" && vals.output !== "still";
  const models = t.models.filter((m) => m.id !== "ltx" || t.id !== "effects" || clip);
  return html`<div class="lk ed-form oc-form"><button class="btn small ed-back" onClick=${onBack}>Back to every one-click tool</button><${Head} sub=${t.blurb}>${t.label}<//>
    <${Offline} health=${health}>The form works, but nothing can run until ComfyUI is back.<//>
    <div class="ed-layout"><div class="card"><h3>Inputs</h3>
      <label class="small oc-field">${isVideo ? "Source clip (one continuous shot)" : "Photo"}<input type="file" accept=${isVideo ? "video/mp4,video/webm,video/quicktime,video/x-matroska" : "image/png,image/jpeg,image/webp"} onChange=${(e) => upload(e.target.files[0])}/></label>
      ${file && (isVideo ? html`<video class="oc-preview" src=${file.url} muted loop playsinline controls></video>` : html`<img class="oc-preview" src=${file.url} alt="Your photo"/>`)}
      ${Object.entries(t.options).map(([k, opts]) => html`<div class="oc-field small" key=${k}><span class="oc-k">${k}</span><div class="chips">${opts.map((o) => html`<button type="button" class=${"chip" + (vals[k] === o ? " on" : "")} aria-pressed=${vals[k] === o} onClick=${() => setVals({ ...vals, [k]: o })}>${k === "seconds" ? o + " s" : o}</button>`)}</div></div>`)}
      ${Object.entries(t.text || {}).map(([k, ph]) => html`<label class="small oc-field" key=${k}><span class="oc-k">${k}</span><input type="text" placeholder=${ph} value=${text[k] || ""} onInput=${(e) => setText({ ...text, [k]: e.target.value })}/></label>`)}
      <label class="small oc-field"><span class="oc-k">Seed</span><input type="text" inputmode="numeric" placeholder="random" value=${seed} onInput=${(e) => setSeed(e.target.value.replace(/\D/g, ""))}/></label>
      <${Licences} models=${models}/>
      <div class="row"><span class="small">${clip ? "Two models in one run: the edit, then the clip." : ""}</span><span class="grow"></span><button class="btn primary" disabled=${busy || !(health && health.comfy)} onClick=${run}>${busy ? `Running ${tick}s` : "Run"}</button></div>
      ${err && html`<p class="small" style="color:var(--err)" role="alert">${err}</p>`}</div>
      <div class="card ed-result"><h3>Result</h3>
        ${res ? html`<div class="oc-grid">${res.files.map((f) => html`<${Out} key=${f.url} f=${f}/>`)}</div>${res.note && html`<p class="small">${res.note}</p>`}<p class="small oc-meta">Seed ${res.seed} · ${res.seconds} s · ${res.workflow}</p>`
          : busy ? html`<p class="small">Running on your GPU. ${t.input === "video" || clip ? "A clip takes a few minutes." : "A still takes under a minute once the model is loaded."}</p>`
          : html`<${Example} ex=${t.example}/>${!t.example && html`<p class="small">The result appears here.</p>`}`}</div></div></div>`;
}

export function OneClick() {
  const [data, setData] = useState(null), [err, setErr] = useState(""), [sel, setSel] = useState(null), health = useHealth();
  useEffect(() => { api("/api/oneclick").then(setData).catch((e) => setErr(e.message)); }, []);
  if (!data) return html`<${Empty} kicker="One click" title=${err ? "The list did not load" : "Loading"}><p>${err || "Reading the one-click tools."}</p><//>`;
  const t = sel && data.tools.find((x) => x.id === sel);
  if (t) return html`<${ToolForm} t=${t} health=${health} onBack=${() => setSel(null)}/>`;
  const lead = data.tools.filter((x) => x.example && x.example.items && x.example.items.length).map((x) => { const it = x.example.items.find((i) => !i.alpha) || x.example.items[0]; return { id: x.id, src: it.src, poster: it.poster || (/\.(mp4|webm)$/i.test(it.src) ? undefined : it.src), kind: /\.(mp4|webm)$/i.test(it.src) ? "video" : "image", title: x.label, sub: it.label, kicker: "Our render" }; });
  const nModels = new Set(data.tools.flatMap((x) => x.models.map((m) => m.id))).size;
  return html`<div class="lk ed-page oc-page">
    <${Stage} items=${lead} label="What the one-click tools do" note="These are our own renders, not yours."/>
    <section><${Head} sub="One photo or clip in, a finished set out: four camera angles, a new light, a viral effect, or a clean alpha matte on a new set. Each runs one graph on your own GPU, and each lists every model it loads with its licence.">One click<//>
      <div class="ed-tally"><${Stats} items=${[[data.tools.length, "one-click tools"], [nModels, "open-weights models and LoRAs"], [0, "credits on your GPU"]]}/></div>
      <div class="lk-tiles">${data.tools.map((x) => { const it = x.example && x.example.items && (x.example.items.find((i) => !i.alpha) || x.example.items[0]); const clipOnly = x.id === "effects", lim = [...new Set(x.models.filter((m) => !clipOnly || m.id !== "ltx").map((m) => m.badge).filter(Boolean))], clipLim = clipOnly && (x.models.find((m) => m.id === "ltx") || {}).badge;
        return html`<article key=${x.id} class="lk-tile ed-tile" tabindex="0" role="button" aria-label=${x.label} onClick=${() => setSel(x.id)} onKeyDown=${(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setSel(x.id); } }}>
        <div class="lk-tilepic">${it && html`<${Media} src=${it.src} poster=${it.poster} alt=${"Our own render of " + x.label} still/>`}${it && html`<span class="estate chk">Our render</span>`}</div>
        <div class="lk-tilebody"><h3>${x.label}</h3><p>${x.blurb}</p><div class="lk-tilefoot">${x.input === "video" ? "Clip in" : "Photo in"} · ${lim.length ? lim.join(", ") : "Apache-2.0 throughout"}${clipLim ? `; the LTX clip: ${clipLim}` : ""}</div></div></article>`; })}</div></section></div>`;
}
