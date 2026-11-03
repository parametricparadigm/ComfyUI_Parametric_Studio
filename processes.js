/* Processes: every process from the author's earlier studio, with what it needs, an Open button when something here does the job, and its guide. Nothing to open means coming soon. */
import { html, api } from "./common.js";
import { useState, useEffect, useMemo } from "preact/hooks";
import { Stage, Stats, Strip } from "./look.js";
import { FxSkeleton } from "./fx.js";
const CSS = `
.pcontrols{display:flex;flex-direction:column;gap:10px;margin-bottom:14px}
.psearch{width:100%;max-width:520px;box-sizing:border-box;padding:10px 12px;border-radius:10px;border:1px solid var(--line);background:var(--panel2);color:inherit;font:inherit}
.pchips{display:flex;flex-wrap:wrap;gap:6px}
.pchip{all:unset;cursor:pointer;padding:5px 10px;border-radius:999px;font-size:12px;outline:1px solid var(--line)}
.pchip.on{background:var(--a1);color:var(--on-accent,#141007);outline-color:var(--a1);font-weight:600}
.pchip:focus-visible,.pbtn:focus-visible{outline:2px solid var(--a1);outline-offset:2px}
.fgrid .gcard.pcard{height:auto;aspect-ratio:auto;display:flex;flex-direction:column;cursor:default}
.fgrid .gcard.pcard{transition:transform .18s,box-shadow .18s}.fgrid .gcard.pcard:hover{transform:translateY(-3px);box-shadow:0 14px 34px rgba(0,0,0,.45)}
.pband{position:relative;height:128px;flex:none;overflow:hidden;background:linear-gradient(135deg,color-mix(in srgb,var(--k,var(--a1)) 42%,transparent),color-mix(in srgb,var(--k,var(--a2)) 10%,transparent))}
.pband img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;transition:transform .35s}.pcard:hover .pband img{transform:scale(1.05)}
.pband:after{content:"";position:absolute;inset:0;background:linear-gradient(180deg,transparent 55%,rgba(0,0,0,.5))}
.pband .gflag{max-width:calc(100% - 18px);box-sizing:border-box;left:9px;z-index:1}.gflag.soon{background:var(--a1);color:#141007}.gflag.near{background:rgba(0,0,0,.62);color:#fff;backdrop-filter:blur(8px)}
.pinitial{position:absolute;right:10px;bottom:-14px;font-size:92px;font-weight:700;opacity:.28;line-height:1}
.pcard.soon .pband{height:76px}.pcard.soon .pinitial{font-size:64px}.pcard.soon{opacity:.86}
.psec{display:flex;align-items:baseline;gap:10px;margin:26px 0 4px}.psec h3{margin:0;font-size:22px}.psec span{font-size:13px;opacity:.7}.psecnote{margin:0 0 12px;font-size:13px;opacity:.72}
.pbody{padding:12px;display:flex;flex-direction:column;gap:7px;flex:1;min-width:0}
.pkind{font-size:11px;letter-spacing:.04em;opacity:.7}
.pbody b{font-size:15px;overflow-wrap:anywhere}
.pbody p{margin:0;font-size:13px;line-height:1.4;overflow-wrap:anywhere}
.pnote{font-size:12px;opacity:.72}
.pmodels{display:flex;flex-wrap:wrap;gap:4px}
.pmodels span{font-size:11px;padding:2px 6px;border-radius:6px;outline:1px solid var(--line);overflow-wrap:anywhere;max-width:100%;box-sizing:border-box}
.pact{display:flex;flex-wrap:wrap;gap:6px;margin-top:auto;padding-top:6px}
.pbtn{all:unset;cursor:pointer;padding:6px 10px;border-radius:8px;font-size:13px;font-weight:600;outline:1px solid var(--line);text-align:center}
.pbtn.on{background:var(--a1);color:var(--on-accent,#141007);outline-color:var(--a1)}
.pmd{max-width:860px;line-height:1.55;overflow-wrap:anywhere}.pmd table{display:block;overflow-x:auto;border-collapse:collapse;font-size:13px;margin:10px 0}.pmd td,.pmd th{border:1px solid var(--line);padding:5px 8px;text-align:left}.pmd pre{overflow-x:auto;padding:10px;border-radius:8px;background:var(--panel2)}.pmd blockquote{margin:10px 0;padding:8px 12px;border-left:3px solid var(--a1);background:var(--panel2);border-radius:0 8px 8px 0}
`;
if (!document.getElementById("processes-css")) { const s = document.createElement("style"); s.id = "processes-css"; s.textContent = CSS; document.head.appendChild(s); }
const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
/* tiny, safe markdown: escape first, then format. A line nothing matches is a paragraph, so the loop always moves on. */
function md(src) {
  const blocks = []; src = String(src || "").replace(/```[a-z]*\n([\s\S]*?)```/g, (_, c) => { blocks.push(`<pre><code>${esc(c)}</code></pre>`); return `\u0000${blocks.length - 1}\u0000`; });
  const inline = (t) => esc(t).replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>").replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  const out = [], lines = src.split("\n"); let i = 0;
  const list = (rx, tag) => { const it = []; while (i < lines.length && rx.test(lines[i])) it.push(`<li>${inline(lines[i++].replace(rx, ""))}</li>`); out.push(`<${tag}>${it.join("")}</${tag}>`); };
  while (i < lines.length) {
    const l = lines[i]; let m;
    if (!l.trim()) { i++; continue; }
    if (/^\u0000\d+\u0000$/.test(l.trim())) { out.push(blocks[+l.trim().slice(1, -1)]); i++; continue; }
    if ((m = l.match(/^(#{1,4})\s+(.*)/))) { out.push(`<h${m[1].length}>${inline(m[2])}</h${m[1].length}>`); i++; continue; }
    if (/^\s*[-*]\s+/.test(l)) { list(/^\s*[-*]\s+/, "ul"); continue; }
    if (/^\s*\d+[.)]\s+/.test(l)) { list(/^\s*\d+[.)]\s+/, "ol"); continue; }
    if (/^\|.*\|\s*$/.test(l) && /^\|[\s:|-]+\|\s*$/.test(lines[i + 1] || "")) { const cells = (r) => r.trim().replace(/^\||\|$/g, "").split("|").map((c) => inline(c.trim())); const head = cells(l); i += 2; const rows = []; while (i < lines.length && /^\|.*\|\s*$/.test(lines[i])) rows.push(cells(lines[i++])); out.push(`<table><tr>${head.map((c) => `<th>${c}</th>`).join("")}</tr>${rows.map((r) => `<tr>${r.map((c) => `<td>${c}</td>`).join("")}</tr>`).join("")}</table>`); continue; }
    if (/^>\s?/.test(l)) { const q = []; while (i < lines.length && /^>\s?/.test(lines[i])) q.push(lines[i++].replace(/^>\s?/, "")); out.push(`<blockquote>${inline(q.join(" "))}</blockquote>`); continue; }
    out.push(`<p>${inline(l)}</p>`); i++;
  }
  return out.join("");
}
const WORD = { goal: "goal", recipe: "recipe", designer: "designer", edit: "AI edit", family: "" };
const HUE = { "3d": "#6aa8ff", image: "#f5c518", video: "#ff7a59", audio: "#b98cff", character: "#ff6fb5", finish: "#3ddc97", prompt: "#59d0ff", helper: "#9aa4b2" };
const STATE = { here: ["ok", "Tested here"], open: ["ok", "Opens here"], near: ["near", "Closest match"], soon: ["soon", "Coming soon"] };
const stateOf = (p) => (!p.open ? "soon" : p.status === "here" ? "here" : p.open.near ? "near" : "open");
function Card({ p, kinds, art, onOpen, onDoc }) {
  const o = p.open, st = stateOf(p), [flag, word] = STATE[st];
  return html`<article class=${"gcard pcard" + (st === "soon" ? " soon" : "")}><div class="pband" style=${{ "--k": HUE[p.kind] }}>${art && html`<img src=${art} alt="" loading="lazy" onError=${(e) => { e.target.remove(); }}/>`}<span class=${"gflag " + flag} title=${p.status_note || p.status_label}>${word}</span>${!art && html`<span class="pinitial" aria-hidden="true">${p.name[0]}</span>`}</div>
    <div class="pbody"><span class="pkind">${kinds[p.kind] || p.kind}</span><b>${p.name}</b><p>${p.description}</p>${p.status_note && html`<span class="pnote">${p.status_note.replace(/\bthere\b/g, "on the earlier studio")}</span>`}
      ${p.models.length > 0 && html`<div class="pmodels" aria-label="Models it needs">${p.models.map((m) => html`<span>${m}</span>`)}</div>`}
      ${st === "near" && html`<span class="pnote">Same main model. The full pipeline is coming soon.</span>`}${(st === "open" || st === "near") && !p.status_note && html`<span class="pnote">${p.status_label}.</span>`}
      <div class="pact">${o && html`<button class="pbtn on" onClick=${() => onOpen(p)}>Open ${o.label}${WORD[o.type] ? " " + WORD[o.type] : ""}</button>`}${p.doc && html`<button class="pbtn" onClick=${() => onDoc(p)}>${o ? "Guide" : "Read the guide"}</button>`}</div></div></article>`;
}
export function Processes({ goTab }) {
  const [d, setD] = useState(null), [err, setErr] = useState(""), [kind, setKind] = useState("all"), [status, setStatus] = useState("all"), [q, setQ] = useState(""), [doc, setDoc] = useState(null), [Sub, setSub] = useState(null), [fams, setFams] = useState({}), [shots, setShots] = useState([]), [recs, setRecs] = useState([]);
  useEffect(() => { api("/api/processes").then(setD).catch((e) => setErr(e.message)); api("/api/families").then((x) => { const m = {}; for (const f of (x.families || x)) { const a = (f.media || []).find((y) => y.kind !== "audio" && y.poster); if (a) m[f.slug] = a.poster; } setFams(m); }).catch(() => {}); fetch("showcase/showcase.json").then((r) => r.json()).then(setShots).catch(() => {}); api("/api/recipes").then((x) => setRecs(x.recipes || x)).catch(() => {}); }, []);
  const artOf = (p) => { const o = p.open; if (!o) return null; if (o.type === "family") return fams[o.id] || null; if (o.type === "designer") return `designer_art/${o.id}.webp`; if (o.type === "goal") { const m = shots.find((x) => x.goal === o.id && x.poster); return m ? m.poster : null; } if (o.type === "edit") return `edit_art/${o.id}.webp`; if (o.type === "recipe") { const g = ((recs.find((r) => r.id === o.id) || {}).steps || []).map((x) => x.goal).find(Boolean), m = shots.find((x) => x.goal === g && x.poster); return m ? m.poster : null; } return null; };
  const rows = (d && d.processes) || [], kinds = (d && d.kinds) || {};
  const shown = useMemo(() => { const w = q.trim().toLowerCase(); return rows.filter((p) => (kind === "all" || p.kind === kind) && (status === "all" || (status === "soon" ? !p.open : status === "open" ? !!p.open : p.status === "here")) && (!w || [p.name, p.description, kinds[p.kind], ...p.models].join(" ").toLowerCase().includes(w))); }, [rows, kind, status, q]);
  const go = goTab || ((t) => { location.hash = t; });
  const open = async (p) => { const o = p.open; if (!o) return;
    if (o.type === "goal") { go("create"); setTimeout(() => dispatchEvent(new CustomEvent("prime-action", { detail: { type: "set_goal", goal: o.id } })), 80); }
    else if (o.type === "family") go("families/" + o.id);
    else if (o.type === "designer") { try { sessionStorage.setItem("designer_open", o.id); } catch {} go("design"); }
    else if (o.type === "edit") { try { sessionStorage.setItem("edit_open", o.id); } catch {} go("edit"); }
    else if (o.type === "recipe") { try { const m = await import("./recipes.js"); try { sessionStorage.setItem("recipe_open", JSON.stringify({ id: o.id, run: null })); } catch {} setSub(() => m.Recipes); scrollTo(0, 0); } catch (e) { setErr("Could not open that recipe: " + e.message); } }
  };
  const readDoc = (p) => api(`/api/processes/${p.id}/doc`).then((x) => { setDoc(x); scrollTo(0, 0); }).catch((e) => setErr(e.message));
  if (Sub) return html`<div class="pr-page"><button class="pbtn" style="margin-bottom:12px" onClick=${() => setSub(null)}>Back to processes</button><${Sub}/></div>`;
  if (doc) return html`<div class="pr-page"><button class="pbtn" style="margin-bottom:12px" onClick=${() => setDoc(null)}>Back to processes</button><div class="pmd" dangerouslySetInnerHTML=${{ __html: md(doc.markdown) }}></div></div>`;
  if (!d) return (err ? html`<p class="small">${err}</p>` : html`<${FxSkeleton} label="Loading the processes." rows=${4}/>`);
  const count = (f) => rows.filter(f).length;
  const ready = shown.filter((p) => p.open).sort((x, y) => "here open near".indexOf(stateOf(x)) - "here open near".indexOf(stateOf(y))), soon = shown.filter((p) => !p.open), opens = count((p) => p.open), cards = (list) => html`<div class="fgrid">${list.map((p) => html`<${Card} key=${p.id} p=${p} kinds=${kinds} art=${artOf(p)} onOpen=${open} onDoc=${readDoc}/>`)}</div>`;
    const lead = rows.filter((p) => p.open && stateOf(p) === "here" && artOf(p)).concat(rows.filter((p) => p.open && stateOf(p) === "open" && artOf(p))).slice(0, 6).map((p) => ({ id: p.id, src: artOf(p), kind: "image", title: p.name, sub: kinds[p.kind] || p.kind, kicker: STATE[stateOf(p)][1] }));
  return html`<div class="lk pr-page">${err && html`<p class="small" role="alert">${err}</p>`}
    <div class="lk-lead"><p class="lk-plain">${rows.length} production methods, written up from real work. ${opens} open something in this studio today. The rest are coming soon, with their guides ready to read.</p><${Stats} items=${[[opens, "open here"], [count((p) => p.doc), "guides"], [rows.length - opens, "coming soon"]]}/></div>
    ${lead.length > 0 && html`<${Stage} items=${lead} label="Processes that open here" note="These pictures are our own renders, not yours."/>`}
    <${Strip} label="Filter by status" value=${status} onPick=${setStatus} items=${[{ k: "all", b: "Any status", s: `${rows.length} methods` }, { k: "here", b: "Tested here", s: `${count((p) => p.status === "here")} tested in this studio` }, { k: "open", b: "Opens here", s: `${opens} with a real tool to open` }, { k: "soon", b: "Coming soon", s: `${rows.length - opens} with a guide to read` }]}/>
    <div class="pcontrols"><input class="psearch" type="search" placeholder="Search by name, model or what it does" aria-label="Search processes" value=${q} onInput=${(e) => setQ(e.target.value)}/>
      <div class="pchips" role="group" aria-label="Filter by kind"><button class=${"pchip" + (kind === "all" ? " on" : "")} aria-pressed=${kind === "all"} onClick=${() => setKind("all")}>All ${rows.length}</button>${Object.entries(kinds).map(([k, l]) => html`<button class=${"pchip" + (kind === k ? " on" : "")} aria-pressed=${kind === k} onClick=${() => setKind(k)}>${l} ${count((p) => p.kind === k)}</button>`)}</div></div>
    ${ready.length > 0 && html`<section><div class="psec"><h3>Open it now</h3><span>${ready.length}</span></div><p class="psecnote">Each one opens a real tool or family page here.</p>${cards(ready)}</section>`}
    ${soon.length > 0 && html`<section><div class="psec"><h3>Coming soon</h3><span>${soon.length}</span></div><p class="psecnote">Not in this edition yet. Read how it works in the guide.</p>${cards(soon)}</section>`}
    ${!shown.length && html`<p class="small">Nothing matches. Try fewer words or another kind.</p>`}</div>`;
}
export default Processes;
