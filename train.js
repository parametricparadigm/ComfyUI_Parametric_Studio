// Train page: pictures on the light table -> caption check -> a base the code can prove -> settings -> Train -> live loss from the real run -> the LoRA in the library, with an A/B against the base. Routes: /api/train/* (studio/train.py).
import { useEffect, useRef, useState } from "preact/hooks";
import { html, api, post } from "./common.js";
import { abPrompt, abVerdict, baseBadge, baseFacts, estimateLines, flowSteps, fmtClock, fmtDuration, fmtGib, fmtLoss, isLive, jobPayload, orderBases, pictureFlag, trainBlockers } from "./train_logic.js";
import { Example, Run, Wipe } from "./train_stage.js";

const errText = (e) => String((e && e.message) || e);
const BLANK = { name: "", trigger: "", size: "", steps: 300, rank: 8, batch: 1, learning_rate: 0.0005, seed: 0, rights: false, first_run: false, continue_from: "" };
const GREASE = "M7 8C30 3 70 3 95 6c3 24 3 62-1 88-25 3-65 3-89-1C2 70 2 32 6 6c20-4 40-4 58-2";
const jump = (id, focus) => { const el = document.getElementById(id); if (!el) return; el.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" }); if (focus) { const f = document.getElementById(focus); if (f) f.focus({ preventScroll: true }); } };

function Flow({ steps }) {
  return html`<nav class="tr-flow" aria-label="Steps"><ol>${steps.map((s) => html`<li class=${"is-" + s.state}><button type="button" aria-current=${s.state === "now" ? "step" : undefined} onClick=${() => jump(s.key === "tr3" && document.getElementById("tr-run") && s.state === "now" ? "tr-run" : s.key)}><i>${s.state === "done" ? html`<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M3 8.5l3.2 3.2L13 4.8"/></svg>` : s.n}</i><span><b>${s.title}</b><small>${s.note}</small></span></button></li>`)}</ol></nav>`;
}

function Pictures({ report, setReport, form, setForm, showExample }) {
  const [sets, setSets] = useState([]); const [folder, setFolder] = useState(""); const [busy, setBusy] = useState(""); const [err, setErr] = useState(""); const [skipped, setSkipped] = useState([]); const [over, setOver] = useState(false); const [fill, setFill] = useState(""); const inp = useRef();
  const loadSets = () => api("/api/train/datasets").then((d) => setSets(d.datasets)).catch(() => {});
  useEffect(() => { loadSets(); }, []);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const q = `trigger=${encodeURIComponent(form.trigger.trim())}${form.size ? `&size=${form.size}` : ""}`;
  useEffect(() => { if (!report) return; let on = true; const t = setTimeout(() => api(`/api/train/datasets/${report.id}?${q}`).then((r) => on && setReport(r)).catch(() => {}), 300); return () => { on = false; clearTimeout(t); }; }, [q, report && report.id]);
  const ensure = async () => report || (await post("/api/train/datasets", { name: form.name.trim() || "New pictures" }));
  const send = async (files) => {
    if (!files.length) return; setErr(""); setBusy(`Adding ${files.length} files`); const miss = [];
    try {
      const r0 = await ensure(); let last = r0;
      for (let i = 0; i < files.length; i += 24) { const fd = new FormData(); files.slice(i, i + 24).forEach((f) => fd.append("files", f, f.name)); setBusy(`Adding files ${i + 1} to ${Math.min(i + 24, files.length)} of ${files.length}`); last = await api(`/api/train/datasets/${r0.id}/upload`, { method: "POST", body: fd }); miss.push(...(last.skipped || [])); }
      setSkipped(miss); setReport(await api(`/api/train/datasets/${r0.id}?${q}`)); loadSets();
    } catch (e) { setErr(errText(e)); }
    setBusy("");
  };
  const importFolder = async () => { setErr(""); setBusy("Reading the folder"); try { const r0 = await ensure(); const r = await post(`/api/train/datasets/${r0.id}/import`, { folder }); setSkipped(r.skipped || []); setReport(await api(`/api/train/datasets/${r0.id}?${q}`)); loadSets(); } catch (e) { setErr(errText(e)); } setBusy(""); };
  const act = async (body) => { setErr(""); try { setReport(await post(`/api/train/datasets/${report.id}/fix`, { trigger: form.trigger.trim(), size: form.size ? +form.size : undefined, ...body })); } catch (e) { setErr(errText(e)); } };
  const saveCaption = async (file, text) => { try { setReport(await post(`/api/train/datasets/${report.id}/captions`, { captions: { [file]: text }, trigger: form.trigger.trim(), size: form.size ? +form.size : undefined })); } catch (e) { setErr(errText(e)); } };
  const openSet = async (id) => { if (!id) { setReport(null); return; } try { setReport(await api(`/api/train/datasets/${id}?${q}`)); } catch (e) { setErr(errText(e)); } };
  const trigger = form.trigger.trim();
  return html`<section class="tr-step tr-pictures" aria-labelledby="tr1"><h2 id="tr1" tabindex="-1"><i>1</i>Pictures</h2>
    <div class=${"tr-bench" + (report ? " has-set" : "")}>
      <div class="tr-benchmain">${report ? html`<${LightTable} report=${report} act=${act} saveCaption=${saveCaption}/>` : showExample ? html`<${Example}/>` : html`<div class="tr-table film tr-tablebare"><p>Your pictures go here, big enough to judge, with each caption beside its picture.</p></div>`}</div>
      <div class="tr-side">
        ${report && html`<div class="tr-tally" role="status"><p class="tr-count"><b>${report.items.length}</b><span>picture${report.items.length === 1 ? "" : "s"} in <em>${report.name}</em></span></p>
          <p class=${"tr-verdict " + (report.blocks ? "bad" : "ok")}>${report.blocks ? `${report.blocks} to fix before training` : "Nothing blocks training"}</p>${report.warns > 0 && html`<p class="tr-verdict warn">${report.warns} to look at</p>`}
          ${report.problems.map((p) => html`<p class=${"small " + (p.level === "block" ? "tr-err" : "tr-warn")}>${p.text}</p>`)}</div>
        <div class="tr-namegrid"><div><label class="small" for="tr-name">LoRA name</label><input id="tr-name" class="tr-in" type="text" maxlength="40" placeholder="Brass lighthouse" value=${form.name} onInput=${set("name")}/></div>
          <div><label class="small" for="tr-trigger">Trigger word</label><input id="tr-trigger" class="tr-in" type="text" maxlength="40" placeholder="brasslight" value=${form.trigger} onInput=${set("trigger")}/></div></div>
        <div class="tr-fixes"><h3>Caption fixes</h3><button class="btn small" disabled=${!/^[A-Za-z0-9][A-Za-z0-9_-]{1,39}$/.test(trigger)} onClick=${() => act({ action: "add_trigger" })}>${trigger ? `Add "${trigger}" to every caption` : "Add the trigger to every caption"}</button>
          <div class="tr-inline"><input class="tr-in" type="text" placeholder="Text for empty captions" aria-label="text for empty captions" value=${fill} onInput=${(e) => setFill(e.target.value)}/><button class="btn small" disabled=${!fill.trim()} onClick=${() => act({ action: "fill_empty", text: fill })}>Fill empty captions</button></div></div>`}
        <div class=${"tr-drop" + (over ? " over" : "") + (report ? "" : " big")} role="button" tabindex="0" aria-label="Add pictures: drop them here, or press to choose" onClick=${() => inp.current.click()} onKeyDown=${(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); inp.current.click(); } }} onDragOver=${(e) => { e.preventDefault(); setOver(true); }} onDragLeave=${() => setOver(false)} onDrop=${(e) => { e.preventDefault(); setOver(false); send([...e.dataTransfer.files]); }}>
          <b>${report ? "Add more pictures" : "Lay out your pictures"}</b><span>Drop them here, or click to choose. PNG, JPG or WEBP, or FLAC, WAV, MP3 or OGG clips for an audio base. Add .txt files with the same names to bring captions along. They are kept in the studio's own data folder.</span>
          <input ref=${inp} type="file" multiple accept="image/png,image/jpeg,image/webp,audio/flac,audio/wav,audio/mpeg,audio/ogg,.txt" hidden aria-label="choose pictures" onClick=${(e) => e.stopPropagation()} onChange=${(e) => { send([...e.target.files]); e.target.value = ""; }}/></div>
        ${busy && html`<p class="small" role="status">${busy}...</p>`}${err && html`<p class="small tr-err" role="alert">${err}</p>`}
        ${skipped.length > 0 && html`<div class="tr-box warn" role="status"><b>Not added</b>${skipped.slice(0, 8).map((s) => html`<p class="small">${s}</p>`)}${skipped.length > 8 && html`<p class="small">and ${skipped.length - 8} more</p>`}</div>`}
        <div class="tr-row"><label class="small" for="tr-folder">Or a folder on this machine</label><div class="tr-inline"><input id="tr-folder" class="tr-in" type="text" placeholder="/home/you/pictures/lighthouses" value=${folder} onInput=${(e) => setFolder(e.target.value)}/><button class="btn" disabled=${!folder.trim() || !!busy} onClick=${importFolder}>Import</button></div></div>
        <div class="tr-row"><label class="small" for="tr-set">Picture set</label><select id="tr-set" class="tr-in" value=${report ? report.id : ""} onChange=${(e) => openSet(e.target.value)}><option value="">A new set</option>${sets.map((s) => html`<option value=${s.id}>${s.name} (${s.pictures})</option>`)}</select></div>
        <p class="tr-plain"><b>This check reads words and file details. It does not look at what a picture shows.</b> Step 3 says exactly what is and is not checked.</p>
      </div>
    </div>
  </section>`;
}

function LightTable({ report, act, saveCaption }) {
  const [only, setOnly] = useState(false);
  const issues = report.items.filter((it) => it.problems.length).length, showing = only && issues ? report.items.filter((it) => it.problems.length) : report.items;
  return html`<div class="tr-table film">
    <div class="tr-tablebar"><h3>The light table</h3><p>Each picture is shown cropped to the square it will train on.</p>${issues > 0 && html`<button class="tr-only" type="button" aria-pressed=${only} onClick=${() => setOnly(!only)}>${only ? `Show all ${report.items.length}` : `Only the ${issues} with a mark`}</button>`}</div>
    ${report.items.length === 0 ? html`<p class="tr-tableempty">This set has no pictures yet. Add some on the right.</p>` : html`<ul class="tr-items">${showing.map((it, i) => { const flag = pictureFlag(it.problems), bad = flag && flag.level === "block"; return html`<li key=${it.file} class=${"tr-print" + (bad ? " bad" : flag ? " marked" : "")} style=${{ "--i": Math.min(i, 16) }}>
      <div class="tr-photo">${it.audio ? html`<audio controls preload="none" src=${it.listen} aria-label=${`listen to ${it.file}`}></audio>` : html`<img src=${it.thumb} alt=${`${it.file}, ${it.width} by ${it.height}`} loading="lazy" width="320" height="320"/>`}<span class="tr-frame">${String(report.items.indexOf(it) + 1).padStart(2, "0")}</span>
        ${bad && html`<svg class="tr-grease" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true"><path d=${GREASE}/></svg>`}
        ${flag && html`<span class=${"tr-flag " + flag.level}>${flag.text}${flag.more > 0 ? ` +${flag.more}` : ""}</span>`}</div>
      <div class="tr-cap"><div class="tr-fileline"><span>${it.file}<br/>${it.width} x ${it.height}</span><button class="btn small" aria-label=${`remove ${it.file}`} onClick=${() => act({ action: "remove", file: it.file })}>Remove</button></div>
        <textarea class="tr-in" rows="4" aria-label=${`caption for ${it.file}`} placeholder="Describe the picture, with your trigger word" value=${it.caption} onBlur=${(e) => { if (e.target.value.trim() !== it.caption) saveCaption(it.file, e.target.value); }}></textarea>
        ${it.problems.map((p) => html`<p class=${"tr-prob " + (p.level === "block" ? "tr-err" : "tr-warn")}>${p.text}</p>`)}</div></li>`; })}</ul>`}</div>`;
}

function Settings({ info, base, setBaseId, form, setForm, library }) {
  const [est, setEst] = useState(null); const [graph, setGraph] = useState(null); const [showAll, setShowAll] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });
  const key = JSON.stringify([base && base.id, form.size, form.rank, form.batch, form.steps, library.length]);
  useEffect(() => { if (!base) { setEst(null); return; } let on = true; setEst(null); post("/api/train/estimate", { base: base.id, size: +form.size || base.sizes[base.sizes.length - 1], rank: +form.rank, batch: +form.batch, steps: +form.steps }).then((d) => on && setEst(d)).catch((e) => on && setEst({ measured: false, note: errText(e) })); return () => { on = false; }; }, [key]);
  const look = estimateLines(est), clock = est && est.measured ? fmtClock(est.train_seconds) : null;
  const showGraph = async () => { if (graph) { setGraph(null); return; } try { setGraph(await post("/api/train/graph", { base: base.id, size: +form.size || undefined, rank: +form.rank, batch: +form.batch, steps: +form.steps, learning_rate: +form.learning_rate, seed: +form.seed })); } catch (e) { setGraph({ problems: [errText(e)], checked: false }); } };
  return html`<section class="tr-step" aria-labelledby="tr2"><h2 id="tr2" tabindex="-1"><i>2</i>Base and settings</h2>
    <div class="tr-spec"><div class="tr-specmain">
      <ul class="tr-bases">${orderBases(info.bases).filter((b) => showAll || b.status !== "blocked" || (base && base.id === b.id)).map((b) => { const badge = baseBadge(b), open = b.trainable || b.can_try; return html`<li><label class=${(base && base.id === b.id ? "on " : "") + (open ? "" : "off")}><input type="radio" name="tr-base" disabled=${!open} checked=${base && base.id === b.id} onChange=${() => setBaseId(b.id)}/><span><b>${b.label}</b><em class=${"tr-badge " + badge.kind}>${badge.text}</em><small class="tr-basefacts">${b.media === "audio" ? "Trains on audio clips · " : b.media === "image-for-video" ? "Video base, proved on stills · " : ""}${baseFacts(b)}</small><small>${b.status === "proven" ? b.proof : b.status === "not_run" ? "Everything is here, but no run is on record. The first run is the test." : b.why_not}</small>${b.ab_effect && html`<small class=${b.ab_effect === "none" ? "tr-warn" : ""}>${b.ab_effect === "none" ? "On that run the A/B showed no visible effect." : `A/B on that run: ${b.ab_effect}.`}</small>`}</span></label>
        ${!open && b.install && html`<details class="tr-install small"><summary>How to install ${b.trainer_label}</summary><ol>${b.install.map((x) => html`<li><code>${x}</code></li>`)}</ol></details>`}</li>`; })}</ul>
      ${(info.bases || []).some((b) => b.status === "blocked") && html`<button class="btn small" type="button" aria-pressed=${showAll} onClick=${() => setShowAll(!showAll)}>${showAll ? "Hide bases with missing pieces" : `Show ${(info.bases || []).filter((b) => b.status === "blocked").length} with missing pieces`}</button>`}
      ${base && html`<div class="tr-who small" role="status"><p><b>Trainer:</b> ${base.trainer_label}${base.trainer_note ? `. ${base.trainer_note}` : ""}</p><p><b>Base:</b> ${base.file}</p>${base.licence && html`<p><b>Licence:</b> ${base.licence.url ? html`<a href=${base.licence.url} target="_blank" rel="noopener">${base.licence.name}</a>` : base.licence.name}. ${base.licence.note}</p>`}${!base.trainable && base.can_try && html`<label class="tr-tick"><input type="checkbox" checked=${!!form.first_run} onChange=${set("first_run")}/><span>I know this base has no run on record. Try it anyway, and record what happens.</span></label>`}</div>`}
      <div class="tr-grid"><div><label class="small" for="tr-size">Size (px, square)</label><select id="tr-size" class="tr-in" value=${form.size} onChange=${set("size")}>${(base ? base.sizes : []).map((s) => html`<option value=${s}>${s}</option>`)}</select></div>
        <div><label class="small" for="tr-steps">Steps</label><input id="tr-steps" class="tr-in" type="number" inputmode="numeric" min=${info.limits.steps[0]} max=${info.limits.steps[1]} value=${form.steps} onInput=${set("steps")}/></div></div>
      <details class="tr-fine"><summary>Finer settings: rank ${form.rank}, batch ${form.batch}, learning rate ${form.learning_rate}, seed ${form.seed}</summary><div class="tr-grid">
        <div><label class="small" for="tr-rank">Rank</label><select id="tr-rank" class="tr-in" value=${form.rank} onChange=${set("rank")}>${info.ranks.map((r) => html`<option value=${r}>${r}</option>`)}</select></div>
        <div><label class="small" for="tr-batch">Batch</label><select id="tr-batch" class="tr-in" value=${form.batch} onChange=${set("batch")}>${info.batches.map((r) => html`<option value=${r}>${r}</option>`)}</select></div>
        <div><label class="small" for="tr-lr">Learning rate</label><input id="tr-lr" class="tr-in" type="number" step="0.0001" value=${form.learning_rate} onInput=${set("learning_rate")}/></div>
        <div><label class="small" for="tr-seed">Seed</label><input id="tr-seed" class="tr-in" type="number" inputmode="numeric" min="0" value=${form.seed} onInput=${set("seed")}/></div></div></details>
      ${library.length > 0 && html`<div class="tr-row"><label class="small" for="tr-cont">Continue from a finished LoRA (optional)</label><select id="tr-cont" class="tr-in" value=${form.continue_from} onChange=${set("continue_from")}><option value="">No, start fresh</option>${library.filter((l) => !base || l.base === base.id).map((l) => html`<option value=${l.job}>${l.name} (${l.total_steps} steps)</option>`)}</select><p class="small">Adds steps on top of its weights. The optimizer's state is not saved by the node, so this is a new run on old weights rather than an exact resume.</p></div>`}
      <button class="btn small" disabled=${!base} onClick=${showGraph}>${graph ? "Hide it" : base && base.trainer !== "comfy" ? "See the config it will run" : "See the graph it will run"}</button>
      ${graph && graph.config && html`<div class="tr-box quiet"><p class="small">The job file written for ${base ? base.trainer_label : "the trainer"}. Your name, trigger and paths fill in when the run starts.</p><pre class="tr-pre">${graph.config}</pre></div>`}
      ${graph && !graph.config && html`<div class="tr-box quiet"><p class="small">${graph.checked ? (graph.problems.length ? `Checked against this ComfyUI: ${graph.problems.join("; ")}` : "Checked against this ComfyUI's node list: every node, link and value fits.") : graph.problems && graph.problems.length ? graph.problems.join("; ") : "ComfyUI is not reachable, so this has not been checked."}</p>${graph.graph && html`<pre class="tr-pre">${JSON.stringify(graph.graph, null, 1)}</pre>`}</div>`}
    </div>
    <div class=${"tr-slate" + (look.measured ? " measured" : "")} role="status"><p class="tr-kicker">${look.measured ? "Measured time and VRAM" : "No measured figure"}</p>
      ${look.measured && html`<div class="tr-slatenums"><div><b>${clock}</b><span>training time</span></div><div><b>${fmtGib(est.peak_own_gib != null ? est.peak_own_gib : est.peak_vram_gib)}</b><span>${est.peak_own_gib != null ? "peak, this run" : "peak, whole card"}</span></div></div>`}
      ${look.lines.map((l) => html`<p class="small">${l}</p>`)}<p class="small">Pictures are centre-cropped to a square. ${base && base.trainer !== "comfy" ? "This trainer saves as it goes, so a stopped run can resume from its last save." : "The node saves only at the end of a run, so a cancel or a crash loses that run."}</p></div></div>
  </section>`;
}

function Result({ job, onChanged, report, onNext }) {
  const [prompt, setPrompt] = useState(() => (job.ab && job.ab.prompt) || abPrompt(job.trigger, report)); const [seed, setSeed] = useState((job.ab && job.ab.seed) || 1234); const [strength, setStrength] = useState((job.ab && job.ab.strength) || 1); const [err, setErr] = useState(""); const ab = job.ab;
  const running = ab && (ab.state === "queued" || ab.state === "running");
  const go = async () => { setErr(""); try { onChanged(await post(`/api/train/jobs/${job.id}/ab`, { prompt, seed: +seed, strength: +strength })); } catch (e) { setErr(errText(e)); } };
  const next = async (kind) => { setErr(""); const why = await onNext(kind); if (why) setErr(why); };
  const verdict = abVerdict(ab), shown = ab && ab.state === "done" && ab.base && ab.lora;
  return html`<section class="tr-result film" aria-labelledby="tr4"><div class="perfs" aria-hidden="true"></div><div class="tr-resultgrid">
    <div class="tr-resultpic">${shown && ab.audio ? html`<div class="tr-listen"><figure><figcaption>Base only</figcaption><audio controls preload="none" src=${ab.base.url}></audio></figure><figure><figcaption>With the LoRA</figcaption><audio controls preload="none" src=${ab.lora.url}></audio></figure></div>` : shown ? html`<${Wipe} key=${ab.base.url} base=${ab.base.url} lora=${ab.lora.url} loraLabel=${`With the LoRA, strength ${ab.strength}`} baseAlt=${`Base only: ${ab.prompt}`} loraAlt=${`With the LoRA: ${ab.prompt}`}/>` : html`<div class="tr-nopic"><b>${running ? (ab.state === "queued" ? "Waiting in the queue" : "Rendering both pictures") : "Nothing rendered yet"}</b><span>One picture on the base and one with the LoRA, same seed, same sampler. Then you wipe between them here.</span></div>`}</div>
    <div class="tr-resultside">
      <p class="tr-kicker">Result</p><h2 id="tr4" tabindex="-1">${job.name}</h2><p class="small">${job.trainer_label || "ComfyUI TrainLoraNode"} on ${job.base_label || job.base}${job.licence ? `. Licence: ${job.licence.name}` : ""}</p>
      ${shown && html`<dl class="tr-abfacts"><div><dd>${(+ab.strength).toFixed(1)}</dd><dt>LoRA strength</dt></div><div><dd>${ab.seed}</dd><dt>same seed, both pictures</dt></div></dl>`}
      ${shown && verdict.map((v) => html`<p class=${"small " + (v.warn ? "tr-warn" : "")}>${v.text}</p>`)}
      <div class="tr-abform"><div class="tr-grid"><div class="wide"><label class="small" for="tr-ab">Test prompt</label><textarea id="tr-ab" class="tr-in" rows="2" value=${prompt} onInput=${(e) => setPrompt(e.target.value)}></textarea></div><div><label class="small" for="tr-abseed">Seed</label><input id="tr-abseed" class="tr-in" type="number" value=${seed} onInput=${(e) => setSeed(e.target.value)}/></div><div><label class="small" for="tr-abst">LoRA strength</label><input id="tr-abst" class="tr-in" type="number" step="0.1" min="0.1" max="2" value=${strength} onInput=${(e) => setStrength(e.target.value)}/></div></div>
        <button class=${shown ? "btn" : "gobtn"} disabled=${running} onClick=${go}>${running ? (ab.state === "queued" ? "Waiting in the queue" : "Rendering both") : ab ? "Render again" : "Render the A/B"}</button>
        ${err && html`<p class="small tr-err" role="alert">${err}</p>`}${ab && ab.state === "error" && html`<p class="small tr-err" role="alert">${ab.error}</p>`}</div>
    </div></div>
    <div class="tr-next"><h3>What next</h3><ol>
      <li><b>Use it</b><p>It is in the Library page and in any LoRA loader in ComfyUI. Put <code>${job.trigger}</code> in your prompt.</p><a class="btn small" href="#library">Open the Library</a></li>
      ${job.trainer === "comfy" || !job.trainer ? html`<li><b>Continue</b><p>More steps on top of these weights. A new run on old weights, not an exact resume.</p><button class="btn small" onClick=${() => next("continue")}>Set up a continue</button></li>` : null}
      <li><b>Retrain</b><p>Same pictures, fresh weights. Change the captions, steps or base first if the A/B let you down.</p><button class="btn small" onClick=${() => next("retrain")}>Set up a retrain</button></li></ol>
      <p class="tr-file">Saved as <code>${job.lora.name}</code> (${(job.lora.bytes / 2 ** 20).toFixed(1)} MB). SHA-256: <code class="tr-hash">${job.lora.sha256}</code></p></div>
  </section>`;
}

export function TrainedLoras({ goTrain }) {
  const [rows, setRows] = useState(null); const [q, setQ] = useState(""); const [found, setFound] = useState(null);
  useEffect(() => { api("/api/train/loras").then((d) => setRows(d.loras)).catch(() => setRows([])); }, []);
  useEffect(() => { if (!q.trim()) { setFound(null); return; } let on = true; const t = setTimeout(() => api(`/api/loras?limit=30&q=${encodeURIComponent(q)}`).then((d) => on && setFound(d.items)).catch(() => on && setFound([])), 250); return () => { on = false; clearTimeout(t); }; }, [q]);
  if (rows === null) return null;
  return html`<section class="tr-lib" aria-label="LoRAs"><h2>LoRAs</h2>
    ${rows.length > 0 ? html`<ul class="tr-libs">${rows.map((r) => html`<li><b class="tr-libname">${r.name}</b><a class="btn small" href=${"#lorashow/" + r.job}>Showcase</a><span class="small">Trigger <code>${r.trigger}</code>, ${r.base_label}, ${r.total_steps} steps, last loss ${fmtLoss(r.last_loss)}, ${(r.bytes / 2 ** 20).toFixed(1)} MB</span><code class="small">${r.lora_name}</code>${r.ab && r.ab.state === "done" && html`<div class="tr-ab small"><figure><img src=${r.ab.base.url} alt="Base only" loading="lazy"/><figcaption>Base only</figcaption></figure><figure><img src=${r.ab.lora.url} alt="With the LoRA" loading="lazy"/><figcaption>With the LoRA</figcaption></figure></div>`}${goTrain && html`<button class="btn small" onClick=${() => goTrain(r.job)}>Open in Train</button>`}</li>`)}</ul>` : html`<p class="small">You have not trained one yet. The Train page makes them.</p>`}
    <div class="tr-row"><label class="small" for="tr-q">Search every LoRA on this machine</label><input id="tr-q" class="tr-in" type="search" value=${q} onInput=${(e) => setQ(e.target.value)} placeholder="name, family or kind"/></div>
    ${found && html`<ul class="tr-found">${found.map((f) => html`<li><code class="small">${f.name}</code><span class="small">${f.family}, ${f.kind}, ${f.size_mb} MB${f.trained ? html` · trigger <code>${f.trigger}</code> · <a href=${"#train/" + f.trained}>its run</a>` : ""}</span></li>`)}${!found.length && html`<li class="small">Nothing matches.</li>`}</ul>`}
  </section>`;
}

export function Train({ route }) {
  const [info, setInfo] = useState(null); const [err, setErr] = useState(""); const [report, setReport] = useState(null); const [form, setForm] = useState(BLANK); const [baseId, setBaseId] = useState(null); const [job, setJob] = useState(null); const [starting, setStarting] = useState(false); const [cancelling, setCancelling] = useState(false); const [library, setLibrary] = useState([]); const top = useRef();
  const loadLib = () => api("/api/train/loras").then((d) => setLibrary(d.loras)).catch(() => {});
  const loadInfo = () => api("/api/train/info").then(setInfo).catch((e) => setErr(errText(e)));
  const want = (route || "").split("/")[1] || "";
  useEffect(() => { loadInfo(); loadLib(); }, []);
  useEffect(() => { let on = true; (want ? api(`/api/train/jobs/${want}`) : api("/api/train/jobs").then((d) => d.jobs.find(isLive) || d.jobs[0] || null)).then((j) => { if (on) setJob(j); }).catch(() => {}); return () => { on = false; }; }, [want]);
  useEffect(() => { if (!job || report || !job.dataset) return; let on = true; api(`/api/train/datasets/${job.dataset}`).then((r) => { if (!on) return; setReport(r); setForm((f) => (f.name || f.trigger ? f : { ...f, name: job.name || "", trigger: job.trigger || "" })); }).catch(() => {}); return () => { on = false; }; }, [job && job.id]);    // reopening the page: the pictures of the run on show
  const bases = (info && info.bases) || []; const base = bases.find((b) => b.id === baseId && (b.trainable || b.can_try)) || bases.find((b) => b.trainable) || null;
  useEffect(() => { if (base) setForm((f) => (base.sizes.includes(+f.size) ? f : { ...f, size: base.sizes[base.sizes.length - 1] })); if (base) setForm((f) => ({ ...f, first_run: false, learning_rate: base.lr || BLANK.learning_rate })); }, [base && base.id]);
  const live = isLive(job);
  useEffect(() => { document.body.classList.add("on-train"); return () => document.body.classList.remove("on-train", "train-busy"); }, []);
  useEffect(() => { document.body.classList.toggle("train-busy", !!(report || job)); }, [!!(report || job)]);
  useEffect(() => { if (!job || !(live || (job.ab && ["queued", "running"].includes(job.ab.state)))) return; const t = setInterval(() => api(`/api/train/jobs/${job.id}`).then((j) => { setJob(j); if (!isLive(j)) { setCancelling(false); loadLib(); loadInfo(); } }).catch(() => {}), 1500); return () => clearInterval(t); }, [job && job.id, live, job && job.ab && job.ab.state]);
  const blockers = info ? trainBlockers({ report, base, form, active: live }) : [];
  const go = async () => { setErr(""); setStarting(true); try { setJob(await post("/api/train/jobs", jobPayload(form, report && report.id, base && base.id))); setForm({ ...form, rights: false }); } catch (e) { setErr(errText(e)); } setStarting(false); };
  const onNext = async (kind) => {
    setForm((f) => ({ ...f, name: job.name, trigger: job.trigger, continue_from: kind === "continue" ? job.id : "", rights: false })); setBaseId(job.base);
    if (!report || report.id !== job.dataset) { try { setReport(await api(`/api/train/datasets/${job.dataset}`)); } catch { return "The picture set from that run is no longer here. Add the pictures again in step 1."; } }
    setTimeout(() => jump(kind === "continue" ? "tr2" : "tr1", kind === "continue" ? "tr-cont" : "tr1"), 60); return "";
  };
  const cancel = async () => { setCancelling(true); try { setJob(await post(`/api/train/jobs/${job.id}/cancel`, {})); } catch (e) { setErr(errText(e)); setCancelling(false); } };
  const resume = async () => { setErr(""); try { setJob(await post(`/api/train/jobs/${job.id}/resume`, {})); } catch (e) { setErr(errText(e)); } };
  if (!info) return html`<p class="small">${err || "Loading..."}</p>`;
  const finished = job && job.state === "done" && job.lora;
  const baseLabel = job && (job.base_label || (bases.find((b) => b.id === job.base) || {}).label);
  const stageFirst = job && (live || !report || job.dataset === report.id);    // what is happening now, or what this set just made, goes on top; a different set being laid out goes on top of an older run
  const stage = job && html`${finished && html`<${Result} key=${job.id} job=${job} report=${report} onChanged=${setJob} onNext=${onNext}/>`}<${Run} job=${job} onCancel=${cancel} onResume=${resume} cancelling=${cancelling} baseLabel=${baseLabel} first=${stageFirst}/>`;
  return html`<div class="tr" ref=${top}>
    ${!info.comfy && html`<div class="tr-box warn" role="alert"><b>ComfyUI is not reachable at ${info.comfy_url}</b><p class="small">Nothing can be checked or trained until it is running.</p></div>`}
    ${info.queue && (info.queue.running > 0 || info.queue.pending > 0) && !live && html`<div class="tr-box quiet" role="status"><b>ComfyUI is busy</b><p class="small">${info.queue.running} running, ${info.queue.pending} waiting. A training job would wait behind them.</p></div>`}
    <${Flow} steps=${flowSteps({ report, base, form, job, blockers })}/>
    ${stageFirst && stage}
    <${Pictures} report=${report} setReport=${setReport} form=${form} setForm=${setForm} showExample=${!job}/>
    <${Settings} info=${info} base=${base} setBaseId=${setBaseId} form=${form} setForm=${setForm} library=${library}/>
    <section class="tr-step tr-sign" aria-labelledby="tr3"><h2 id="tr3" tabindex="-1"><i>3</i>Train</h2>
      <div class="tr-signgrid"><div class="tr-box tr-checked" aria-label="what is checked"><b>What this page checks, and what it does not</b>
        <p class="small">Checked: the words in your captions, file names, LoRA name, trigger and test prompt, against this studio's safe-for-work word list.</p>
        <p class="small tr-notchecked"><b>Not checked: the pictures themselves.</b> The studio has no image classifier yet, so nothing here looks at what a picture shows. A word list misses plenty, so this is not a safety guarantee.</p>
        <p class="small">This studio does not train sexual content, and never anything sexual involving minors, under any setting.</p></div>
      <div class="tr-signoff"><label class="tr-tick"><input type="checkbox" checked=${form.rights} onChange=${(e) => setForm({ ...form, rights: e.target.checked })}/><span>I own these pictures or have the rights to them, and no real person's likeness is being trained without their consent.</span></label>
        ${blockers.length > 0 && !live && html`<ul class="tr-blockers">${blockers.map((b) => html`<li>${b}</li>`)}</ul>`}
        ${live && html`<p class="small">A training job is already running. One at a time.</p>`}
        ${err && html`<p class="small tr-err" role="alert">${err}</p>`}
        <button class="gobtn tr-go" disabled=${blockers.length > 0 || starting} onClick=${go}>${starting ? (base && base.trainer !== "comfy" ? `Starting ${base.trainer_label}` : "Sending to ComfyUI") : "Train"}</button>
        <p class="small">Every number on this page is read from a real run, or says it was not measured.</p></div></div>
    </section>
    ${!stageFirst && stage}
    <${TrainedLoras} key=${library.length + "/" + ((job && job.ab && job.ab.state) || "")} goTrain=${(id) => { location.hash = "train/" + id; }}/>
  </div>`;
}
