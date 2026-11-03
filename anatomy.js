/* Model Anatomy: every model file on this machine, opened up from its header. Routes: #anatomy, #anatomy/<id>, #anatomy/compare/<id>,<id>. Data: /api/anatomy (studio/feature_anatomy.py), built by scripts/build_model_anatomy.py. */
import { useEffect, useMemo, useState } from "preact/hooks";
import { html, api } from "./common.js";
import { KINDS, KIND_WORD, fmtN, fmtBytes, bitsPerWeight, pct, parseRoute, filterModels, folderCounts, kindShares, attnMlp, stacks, treemapItems, squarify, compareRows, rankLine } from "./anatomy_logic.js";

const PAGE = 60;
const said = (e) => (e && e.message) || String(e || "");
const nameOf = (m) => m.file.replace(/\.(safetensors|gguf|sft)$/i, "");
function useNarrow() {
  const q = "(max-width: 700px)"; const [n, setN] = useState(() => matchMedia(q).matches);
  useEffect(() => { const m = matchMedia(q), f = () => setN(m.matches); m.addEventListener("change", f); return () => m.removeEventListener("change", f); }, []);
  return n;
}
function useCompare() {
  const read = () => { try { return JSON.parse(sessionStorage.getItem("an_cmp") || "[]").slice(0, 4); } catch { return []; } };
  const [ids, setIds] = useState(read);
  const save = (next) => { setIds(next); try { sessionStorage.setItem("an_cmp", JSON.stringify(next)); } catch {} };
  return [ids, (id) => save(ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id].slice(-4)), () => save([])];
}

/* ---------- small pieces */
function KindBar({ kinds, label }) {
  const s = kindShares(kinds);
  if (!s.length) return html`<p class="small">No weights to split.</p>`;
  return html`<div class="an-kbar"><div class="an-bar" role="img" aria-label=${(label || "Where the weights are") + ": " + s.map((x) => `${KIND_WORD[x.k]} ${pct(x.f, 1)}`).join(", ")}>${s.map((x) => html`<i key=${x.k} class=${"k-" + x.k} style=${{ flexGrow: x.f }}></i>`)}</div>
    <ul class="an-legend">${s.map((x) => html`<li key=${x.k}><i class=${"k-" + x.k}></i>${KIND_WORD[x.k]} <b>${pct(x.f, x.f < 0.01 ? 1 : 0)}</b></li>`)}</ul></div>`;
}
function DtypeBar({ m }) {
  const total = m.data_bytes || 1;
  return html`<div class="an-kbar"><div class="an-bar" role="img" aria-label=${"Bytes by number format: " + m.dtypes.map((d) => `${d[0]} ${pct(d[3] / total, 1)}`).join(", ")}>${m.dtypes.map((d, i) => html`<i key=${d[0]} class=${"d-" + (i % 6)} style=${{ flexGrow: d[3] / total }}></i>`)}</div>
    <ul class="an-legend">${m.dtypes.map((d, i) => html`<li key=${d[0]}><i class=${"d-" + (i % 6)}></i>${d[0]} <b>${pct(d[3] / total, d[3] / total < 0.01 ? 1 : 0)}</b><small>${d[1]} tensors, ${fmtBytes(d[3])}</small></li>`)}</ul></div>`;
}

function Treemap({ m, tall, bare }) {
  const narrow = useNarrow(), W = 1000, H = narrow ? 1100 : tall ? 620 : 520;
  const items = useMemo(() => treemapItems(m), [m]);
  const tiles = useMemo(() => {
    const out = [];
    for (const g of squarify(items, 0, 0, W, H)) {
      const pad = g.w > 40 && g.h > 40 ? 3 : 0, head = g.h > 70 && g.w > 90 ? 26 : 0;
      out.push({ ...g, group: true });
      for (const k of squarify(g.item.kids, g.x + pad, g.y + pad + head, g.w - 2 * pad, g.h - 2 * pad - head)) out.push({ ...k, group: false, parent: g.item });
    }
    return out;
  }, [items, H]);
  const total = m.weights || 1;
  return html`<figure class="an-tm film"><div class="an-tmbox" style=${{ aspectRatio: `${W} / ${H}` }} role="img" aria-label=${"Where the parameters live: " + items.slice(0, 8).map((g) => `${g.n} ${pct(g.w / total, 1)}`).join(", ")}>
    ${tiles.map((t, i) => { const st = { left: (t.x / W) * 100 + "%", top: (t.y / H) * 100 + "%", width: (t.w / W) * 100 + "%", height: (t.h / H) * 100 + "%" };
      if (t.group) return html`<div key=${"g" + i} class="an-tg" style=${st}>${t.h > 70 && t.w > 90 ? html`<span class="an-tgl"><b>${t.item.n}</b> ${t.item.r ? `x ${t.item.r} ` : ""}${pct(t.item.w / total, 1)}</span>` : null}</div>`;
      return html`<div key=${"t" + i} class=${"an-tt k-" + (t.item.kind || "unclassified")} style=${st} title=${`${t.parent.n} / ${t.item.n}: ${fmtN(t.item.w)} weights, ${pct(t.item.w / total, 1)}`}>${t.w > 70 && t.h > 34 ? html`<span>${t.item.n}<small>${fmtN(t.item.w)}</small></span>` : null}</div>`; })}
  </div>${bare ? null : html`<figcaption class="small">Area is weight count, read from the header. Big groups are split by what their layers are called; a stack of repeated blocks is split by kind, since every block is a copy of one design. Hover a tile for its numbers.</figcaption>`}</figure>`;
}

function TreeNode({ n, total, depth }) {
  const [open, setOpen] = useState(depth < 1);
  const kids = n.c || [];
  const share = n.w / (total || 1), line = html`<span class="an-tn"><b>${n.n || "(root)"}</b>${n.r ? html`<span class="fx-tag">x ${n.r}${n.u ? `, ${n.u} design${n.u === 1 ? "" : "s"}` : ""}</span>` : null}${n.s != null ? html`<span class="an-same">same as ${n.s}</span>` : null}</span><span class="an-tnum"><span>${fmtN(n.w)}</span><small>${fmtBytes(n.b)} · ${n.t} tensor${n.t === 1 ? "" : "s"}</small></span><i class="an-share" aria-hidden="true"><em style=${{ width: Math.max(0.5, share * 100) + "%" }}></em></i>`;
  if (n.x) return html`<li class="an-leaf"><div class="an-row"><span class="an-tn"><b>${n.n}</b><code>${n.x[1]} [${n.x[0].join(", ")}]</code><span class=${"an-kdot k-" + (n.kind || "unclassified")} title=${KIND_WORD[n.kind] || ""}></span></span><span class="an-tnum"><span>${fmtN(n.w)}</span><small>${fmtBytes(n.b)}</small></span><i class="an-share" aria-hidden="true"><em style=${{ width: Math.max(0.5, share * 100) + "%" }}></em></i></div></li>`;
  if (!kids.length) return html`<li><div class="an-row">${line}</div></li>`;
  return html`<li><details open=${open} onToggle=${(e) => setOpen(e.currentTarget.open)}><summary class="an-row">${line}</summary>
    ${open ? html`<ul class="an-tree">${kids.map((c) => html`<${TreeNode} key=${c.n} n=${c} total=${total} depth=${depth + 1}/>`)}${n.more ? html`<li class="small an-more">${n.more} more parts are left out of this cache to keep it small; their weights are in the totals above.</li>` : null}</ul>` : null}</details></li>`;
}

/* ---------- one file */
function Facts({ m }) {
  const b = bitsPerWeight(m.data_bytes, m.weights), am = attnMlp(m.kinds);
  return html`<dl class="an-stats">
    <div class="big"><dt>${fmtN(m.weights)}</dt><dd>weights, counted from ${m.tensors} tensor shapes</dd></div>
    <div><dt>${fmtBytes(m.data_bytes)}</dt><dd>stored, ${b ? b.toFixed(1) : "?"} bits a weight</dd></div>
    <div><dt>${am ? pct(am.attention) : "?"}</dt><dd>${am ? "of attention plus MLP is attention" : "attention and MLP not named"}</dd></div>
    <div><dt>${fmtBytes(m.header_bytes)}</dt><dd>of header read, out of ${fmtBytes(m.size)}</dd></div>
  </dl>`;
}
function Groups({ m }) {
  const total = m.weights || 1;
  return html`<ol class="an-groups">${m.groups.filter((g) => g.t).sort((a, b) => b.w - a.w).map((g) => { const bw = bitsPerWeight(g.b, g.w); return html`<li key=${g.n}><div class="an-gname"><b>${g.n}</b>${g.label ? html`<span class="fx-tag" title="named by the key prefix the checkpoint format uses">${g.label}</span>` : null}${g.r ? html`<span class="fx-tag">x ${g.r}</span>` : null}</div>
    <div class="an-gnum"><span><b>${fmtN(g.w)}</b> weights</span><span>${pct(g.w / total, 1)}</span><span>${fmtBytes(g.b)}</span><span>${bw ? bw.toFixed(1) + " bits" : ""}</span><span>${g.t} tensors</span></div>${g.k && Object.keys(g.k).length > 1 ? html`<${KindBar} kinds=${g.k} label=${g.n}/>` : null}</li>`; })}</ol>`;
}
function Lora({ l }) {
  const max = Math.max(...l.targets.map((t) => t[1]), 1);
  return html`<section class="fx-card an-lora" aria-labelledby="an-lora-h"><span class="fx-kick">LoRA</span><h3 id="an-lora-h">${rankLine(l)}</h3>
    <p>${l.modules} adapted modules. ${Object.entries(l.layouts).map(([k, v]) => `${v} as ${k}`).join(", ")}.${l.alpha_tensors ? ` ${l.alpha_tensors} carry an alpha value; it isn't read here, so the strength it sets isn't shown.` : " No alpha tensors, so the loader's default scale applies."}</p>
    <h4>What it adapts</h4><ul class="an-targets">${l.targets.map(([t, c]) => html`<li key=${t}><code>${t}</code><i aria-hidden="true"><em style=${{ width: (c / max) * 100 + "%" }}></em></i><b>${c}</b></li>`)}</ul>
    ${l.more_targets ? html`<p class="small">and ${l.more_targets} more layer names.</p>` : null}<p class="small">Layer names with their block number taken off, counted. The rank is the short side of each down matrix.</p></section>`;
}
function ModelView({ id, index, cmp, toggle }) {
  const [m, setM] = useState(null), [err, setErr] = useState("");
  useEffect(() => { setM(null); setErr(""); api("/api/anatomy/model/" + id).then(setM).catch((e) => setErr(said(e))); scrollTo(0, 0); }, [id]);
  const row = index.models.find((x) => x.id === id);
  if (err) return html`<div class="fx-note bad" role="alert"><p>${err}</p><a class="btn small" href="#anatomy">Every file</a></div>`;
  if (!m) return html`<p class="small" role="status">Opening ${row ? row.file : "the file"}.</p>`;
  const same = m.same_header_as && index.models.find((x) => x.id === m.same_header_as);
  return html`<article class="an-model" aria-labelledby="an-mh">
    <nav class="fx-row an-crumbs" aria-label="Anatomy"><a class="btn small" href="#anatomy">Every file</a><button class="btn small" type="button" aria-pressed=${cmp.includes(id)} onClick=${() => toggle(id)}>${cmp.includes(id) ? "In the comparison" : "Add to the comparison"}</button>${cmp.length >= 2 ? html`<a class="btn small" href=${"#anatomy/compare/" + cmp.join(",")}>Compare ${cmp.length}</a>` : null}</nav>
    <header class="an-mhead"><span class="fx-kick">${m.folder || m.format}${m.family ? " · " + m.family : ""}</span><h2 id="an-mh">${nameOf(m)}</h2><p class="small an-rel">${m.rel}${m.also ? html`<br/>Also linked as ${m.also.join(", ")}` : null}</p></header>
    ${!m.read ? html`<div class="fx-note warn"><b>Not opened</b><p>This file is ${m.why}.</p><p class="small">${fmtBytes(m.size)} on disk, ${m.format} format.</p></div>` : html`
    <${Facts} m=${m}/>
    ${same ? html`<p class="fx-note">Its header is identical to <a href=${"#anatomy/" + same.id}>${same.file}</a>, and the files are the same size. That says the layout matches, not that the weights do.</p>` : null}
    <div class="fx-two"><section class="fx-card"><span class="fx-kick">What the layers are</span><${KindBar} kinds=${m.kinds}/><p class="small">By the layer's own name: q, k, v and out projections are attention; fc, up, down and gate are MLP. "Names don't say" is left unsplit rather than guessed.</p></section>
      <section class="fx-card"><span class="fx-kick">Number formats</span><${DtypeBar} m=${m}/>${m.quant_notes.length ? html`<ul class="small an-notes">${m.quant_notes.map(([t, c]) => html`<li key=${t}>${c} layers: ${t}</li>`)}</ul>` : null}</section></div>
    ${m.lora ? html`<${Lora} l=${m.lora}/>` : null}
    <section class="an-sect" aria-labelledby="an-tmh"><h3 id="an-tmh">Where the parameters live</h3><${Treemap} m=${m} tall/></section>
    <section class="an-sect" aria-labelledby="an-gh"><h3 id="an-gh">Bytes per group</h3>${m.prefix ? html`<p class="small">Every key starts <code>${m.prefix}</code>, so that is left off.</p>` : null}<${Groups} m=${m}/></section>
    <section class="an-sect" aria-labelledby="an-th"><h3 id="an-th">The block tree</h3><p class="small">Open any part. A numbered stack shows each block, and a block built exactly like an earlier one says so instead of repeating it.</p><ul class="an-tree an-root">${(m.tree.c || [m.tree]).map((c) => html`<${TreeNode} key=${c.n} n=${c} total=${m.weights} depth=${1}/>`)}</ul></section>
    <section class="fx-card an-cant" aria-labelledby="an-ch"><span class="fx-kick">Read from the header</span><h3 id="an-ch">What it can't tell</h3><ul>${m.cant_tell.map((t) => html`<li key=${t}>${t}</li>`)}</ul>
      ${Object.keys(m.meta).length ? html`<h4>What the file says about itself</h4><dl class="an-meta">${Object.entries(m.meta).map(([k, v]) => html`<div key=${k}><dt>${k}</dt><dd>${String(v)}</dd></div>`)}</dl>` : html`<p class="small">The file carries no metadata this page shows.</p>`}</section>`}
  </article>`;
}

/* ---------- side by side */
function Scale({ models }) {
  const max = Math.max(...models.map((m) => m.weights || 0), 1);
  return html`<section class="an-scale film" aria-labelledby="an-sh"><h3 id="an-sh">Same scale</h3>
    <ol>${models.map((m) => html`<li key=${m.id}><span class="an-sn"><b>${nameOf(m)}</b><small>${fmtN(m.weights)} weights · ${fmtBytes(m.data_bytes)}</small></span><span class="an-sbar" style=${{ width: ((m.weights || 0) / max) * 100 + "%" }}>${kindShares(m.kinds).map((x) => html`<i key=${x.k} class=${"k-" + x.k} style=${{ flexGrow: x.f }}></i>`)}</span></li>`)}</ol>
    <ul class="an-legend">${KINDS.map(([k, l]) => html`<li key=${k}><i class=${"k-" + k}></i>${l}</li>`)}</ul></section>`;
}
function CompareView({ ids, index, toggle, clear }) {
  const [ms, setMs] = useState(null), [err, setErr] = useState("");
  useEffect(() => { setMs(null); Promise.all(ids.map((i) => api("/api/anatomy/model/" + i))).then(setMs).catch((e) => setErr(said(e))); }, [ids.join(",")]);
  const presets = index.presets || [];
  const head = html`<div class="an-presets"><span class="fx-kick">Ready-made</span><div class="fx-row">${presets.map((p) => html`<a key=${p.id} class=${"btn small" + (p.ids.join(",") === ids.join(",") ? " on" : "")} href=${"#anatomy/compare/" + p.ids.join(",")}>${p.label}</a>`)}<a class="btn small" href="#anatomy">Pick your own</a></div></div>`;
  if (ids.length < 2) return html`<div class="an-cmp">${head}<p>Pick two to four files in the list, then compare them here.</p></div>`;
  if (err) return html`<div class="an-cmp">${head}<div class="fx-note bad" role="alert"><p>${err}</p></div></div>`;
  if (!ms) return html`<div class="an-cmp">${head}<p class="small" role="status">Opening ${ids.length} files.</p></div>`;
  const read = ms.filter((m) => m.read), rows = compareRows(ms);
  return html`<div class="an-cmp">${head}
    ${read.length ? html`<${Scale} models=${read}/>` : null}
    <div class="an-cols" style=${{ "--n": ms.length }}>${ms.map((m, i) => html`<section key=${m.id} class="fx-card an-col" aria-labelledby=${"an-c" + i}>
      <span class="fx-kick">${m.folder || m.format}${m.family ? " · " + m.family : ""}</span><h3 id=${"an-c" + i}><a href=${"#anatomy/" + m.id}>${nameOf(m)}</a></h3>
      <dl class="an-cdl">${rows.map((r) => html`<div key=${r.label}><dt>${r.label}</dt><dd>${r.cells[i]}</dd></div>`)}</dl>
      ${m.read ? html`<${KindBar} kinds=${m.kinds}/><${Treemap} m=${m} bare/>` : html`<p class="small">${m.why}</p>`}
      <button class="btn small" type="button" onClick=${() => { toggle(m.id); location.hash = "anatomy/compare/" + ids.filter((x) => x !== m.id).join(","); }}>Take it out</button></section>`)}</div>
    <p class="small">Weights are counted from shapes, and a quantized layer counts the weights it stands for, not the bytes it takes. These files differ in format as well as design, so bits per weight shows how each is stored, not how good it is. In each small map, area is weight count: stacks of blocks split by kind, other groups by their parts. <button class="btn small" type="button" onClick=${clear}>Clear my picks</button></p>
  </div>`;
}

/* ---------- every file */
function Hero({ index }) {
  const nr = Object.values(index.not_read || {}).reduce((a, b) => a + b, 0);
  return html`<section class="an-hero film" aria-label="What was read">
    <dl class="an-stats">
      <div class="big"><dt>${index.read}</dt><dd>of ${index.files} model files opened from the header alone</dd></div>
      <div><dt>${fmtN(index.weights)}</dt><dd>weights counted in them</dd></div>
      <div><dt>${fmtBytes(index.header_bytes)}</dt><dd>of headers read to describe ${fmtBytes(index.file_bytes)} of files</dd></div>
      <div><dt>0</dt><dd>weights loaded, and no GPU used</dd></div>
    </dl>
    <p class="an-lead">A safetensors file starts with eight bytes giving a length, then that much JSON naming every tensor: its number format, its shape and where its bytes are. A GGUF file starts with its metadata and a table of tensors. Reading only that much gives the whole layout of a network, so every figure here is counted, not looked up.</p>
    ${nr ? html`<p class="small">${nr} files weren't opened.${index.not_read.pickle ? ` ${index.not_read.pickle} are Python pickles (.pt, .pth, .ckpt, .bin and the like): listing their tensors means running their unpickler, which can run code.` : ""}${index.not_read.other ? ` ${index.not_read.other} are other formats, such as ONNX graphs, with no tensor header to read.` : ""}${index.not_read.failed ? ` ${index.not_read.failed} had a header that didn't read.` : ""}</p>` : null}
    ${index.skipped_names ? html`<p class="small">${index.skipped_names} more are left off this page by their file names, under the studio's safe-for-work rule.</p>` : null}
    <p class="small">Read on ${index.built} from ${index.source}. On your own machine, <code>scripts/build_model_anatomy.py --models your/models/folder</code> rebuilds it from yours.</p>
  </section>`;
}
function Row({ r, on, toggle }) {
  return html`<li class=${"an-li" + (r.read ? "" : " unread")}><a href=${"#anatomy/" + r.id}><span class="an-lname"><b>${nameOf(r)}</b><small>${r.folder}${r.family ? " · " + r.family : ""}${r.arch ? " · " + r.arch : ""}</small></span>
    <span class="an-lnum">${r.read ? html`<b>${fmtN(r.weights)}</b><small>${r.dtype || ""}${r.lora ? ` · LoRA rank ${r.lora_rank ?? "?"}` : r.blocks ? ` · ${r.blocks} blocks` : ""}</small>` : html`<small>not opened: ${r.format}</small>`}</span>
    ${r.read && r.kinds ? html`<span class="an-lbar" aria-hidden="true">${kindShares(r.kinds).map((x) => html`<i key=${x.k} class=${"k-" + x.k} style=${{ flexGrow: x.f }}></i>`)}</span>` : html`<span class="an-lbar empty" aria-hidden="true"></span>`}</a>
    ${r.read ? html`<button class="an-pick" type="button" aria-pressed=${on} aria-label=${(on ? "Take out of" : "Add to") + " the comparison: " + r.file} onClick=${() => toggle(r.id)}>${on ? "Picked" : "Compare"}</button>` : null}</li>`;
}
const CLEAR = { q: "", folder: "all", read: "read", lora: "all", sort: "weights" };
function ListView({ index, cmp, toggle, clear }) {
  const [f, setF] = useState(() => { try { return { ...CLEAR, ...JSON.parse(sessionStorage.getItem("an_f") || "{}") }; } catch { return CLEAR; } }), [n, setN] = useState(PAGE);
  const set = (x) => { setF(x); setN(PAGE); try { sessionStorage.setItem("an_f", JSON.stringify(x)); } catch {} };
  const rows = useMemo(() => filterModels(index.models, f), [index, f]), folders = useMemo(() => folderCounts(index.models), [index]);
  const ch = (k) => (e) => set({ ...f, [k]: e.target.value });
  return html`<div class="an-list">
    <${Hero} index=${index}/>
    <section class="an-presets" aria-label="Side by side"><span class="fx-kick">Side by side</span><div class="fx-row">${(index.presets || []).map((p) => html`<a key=${p.id} class="btn small" href=${"#anatomy/compare/" + p.ids.join(",")}>${p.label}</a>`)}</div></section>
    <section class="an-find" aria-label="Find a file">
      <label class="fx-lab an-q">Find a file<input class="fx-in" type="search" placeholder="klein, wan, lora, gguf, Q8_0" value=${f.q} onInput=${ch("q")}/></label>
      <div class="an-filters"><label class="fx-lab">Folder<select class="fx-in" value=${f.folder} onChange=${ch("folder")}><option value="all">All ${index.models.length}</option>${folders.map(([k, c]) => html`<option key=${k} value=${k}>${k || "other"} (${c})</option>`)}</select></label>
        <label class="fx-lab">Kind<select class="fx-in" value=${f.lora} onChange=${ch("lora")}><option value="all">Everything</option><option value="base">Not LoRAs</option><option value="lora">LoRAs only</option></select></label>
        <label class="fx-lab">Opened<select class="fx-in" value=${f.read} onChange=${ch("read")}><option value="read">Opened (${index.read})</option><option value="unread">Not opened (${index.files - index.read})</option><option value="all">Both</option></select></label>
        <label class="fx-lab">Order<select class="fx-in" value=${f.sort} onChange=${ch("sort")}><option value="weights">Most weights</option><option value="size">Biggest file</option><option value="name">A to Z</option></select></label></div>
      <p class="small" aria-live="polite">${rows.length} file${rows.length === 1 ? "" : "s"}${JSON.stringify(f) !== JSON.stringify(CLEAR) ? html` <button class="btn small" type="button" onClick=${() => set(CLEAR)}>Clear</button>` : null}</p></section>
    ${cmp.length ? html`<div class="an-tray" role="region" aria-label="Your comparison"><span><b>${cmp.length}</b> picked</span>${cmp.length >= 2 ? html`<a class="fx-go" href=${"#anatomy/compare/" + cmp.join(",")}>Compare them</a>` : html`<span class="small">Pick one more.</span>`}<button class="btn small" type="button" onClick=${clear}>Clear</button></div>` : null}
    <ul class="an-rows">${rows.slice(0, n).map((r) => html`<${Row} key=${r.id} r=${r} on=${cmp.includes(r.id)} toggle=${toggle}/>`)}</ul>
    ${rows.length > n ? html`<button class="btn an-moreb" type="button" onClick=${() => setN(n + PAGE * 2)}>Show ${Math.min(PAGE * 2, rows.length - n)} more of ${rows.length - n}</button>` : null}
  </div>`;
}

export function Anatomy({ route }) {
  const r = parseRoute(route), [index, setIndex] = useState(null), [err, setErr] = useState(""), [cmp, toggle, clear] = useCompare();
  useEffect(() => { api("/api/anatomy").then(setIndex).catch((e) => setErr(said(e))); }, []);
  useEffect(() => { document.body.classList.add("on-anatomy"); return () => document.body.classList.remove("on-anatomy"); }, []);
  if (err) return html`<div class="fx an"><div class="fx-note bad" role="alert"><p>${err}</p></div></div>`;
  if (!index) return html`<div class="fx an"><p class="small" role="status">Reading the anatomy.</p></div>`;
  return html`<div class="fx an">
    ${r.view === "model" ? html`<${ModelView} id=${r.id} index=${index} cmp=${cmp} toggle=${toggle}/>` : r.view === "compare" ? html`<${CompareView} ids=${r.ids} index=${index} toggle=${toggle} clear=${clear}/>` : html`<${ListView} index=${index} cmp=${cmp} toggle=${toggle} clear=${clear}/>`}
  </div>`;
}
