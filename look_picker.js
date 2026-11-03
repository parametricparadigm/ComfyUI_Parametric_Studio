// The Create page's look picker: grouped prompt fragments (light, colour, framing, camera, motion, styles) from GET /api/presets/library.
// One pick per group, one camera move per clip. Picks are added to the end of the prompt and taken out again cleanly; your own words stay.
import { useState, useEffect, useRef } from "preact/hooks";
import { html, api } from "./common.js";
import { groupsFor, searchLooks, togglePick, keepFor, applyLooks, phrasesOf } from "./look_picker_logic.js";

const PAGE = 40;

export function LookPicker({ prompt, setPrompt, kind }) {
  const [lib, setLib] = useState(null); const [err, setErr] = useState(""); const [open, setOpen] = useState(false);
  const [section, setSection] = useState("light"); const [group, setGroup] = useState(""); const [q, setQ] = useState(""); const [picked, setPicked] = useState({}); const [more, setMore] = useState(PAGE);
  const added = useRef([]);
  const load = () => { setErr(""); api("/api/presets/library").then(setLib).catch((e) => setErr(e.message)); };
  useEffect(() => { if (open && !lib) load(); }, [open]);
  useEffect(() => setMore(PAGE), [q, group, section]);
  const byId = lib ? Object.fromEntries(lib.looks.map((e) => [e.id, e])) : {};
  const groups = lib ? groupsFor(lib.groups, kind) : [];
  const commit = (next) => { const after = phrasesOf(next, byId, lib.groups); setPrompt(applyLooks(prompt, added.current, after)); added.current = after; setPicked(next); };
  useEffect(() => { if (lib) { const kept = keepFor(picked, byId, kind); if (Object.keys(kept).length !== Object.keys(picked).length) commit(kept); } }, [kind]);
  const inSection = groups.filter((g) => g.section === section); const gNow = group && inSection.some((g) => g.id === group) ? group : "";
  const hits = lib ? searchLooks(lib.looks, lib.groups, q, q.trim() ? "" : gNow, kind).filter((e) => q.trim() || inSection.some((g) => g.id === e.group)) : [];
  const chosen = Object.values(picked).map((id) => byId[id]).filter(Boolean);
  const label = (id) => (lib.groups.find((g) => g.id === id) || {}).label || id;
  return html`<div class="field lookpick"><label>Look library</label>
    ${!open && html`<div class="row" style="margin:0"><button class="btn small" aria-expanded="false" onClick=${() => setOpen(true)}>Browse looks</button><span class="small grow">Light, colour, framing, camera${kind === "video" ? ", motion" : ""} and styles. One per group.</span></div>`}
    ${open && err && html`<p class="small" style="color:var(--err);margin:0 0 6px" role="alert">${err} <button class="btn small" onClick=${load}>Try again</button></p>`}
    ${open && !lib && !err && html`<div class="pp-rowskel" role="status"><span class="fx-sr">Loading looks.</span><i aria-hidden="true"></i><i aria-hidden="true"></i></div>`}
    ${open && lib && html`<div>
      <div class="mstyles-find"><input type="search" placeholder="Search: golden hour, 16mm, noir" value=${q} onInput=${(e) => setQ(e.target.value)} aria-label="search looks"/></div>
      ${!q.trim() && html`<div class="chips" role="group" aria-label="Look sections" style="margin-top:6px">${lib.sections.filter((s) => groups.some((g) => g.section === s.id)).map((s) => html`<button key=${s.id} class=${"chip" + (section === s.id ? " on" : "")} aria-pressed=${section === s.id} onClick=${() => { setSection(s.id); setGroup(""); }}>${s.label}</button>`)}</div>
        <div class="chips" role="group" aria-label="Look groups" style="margin-top:6px"><button class=${"chip" + (!gNow ? " on" : "")} aria-pressed=${!gNow} onClick=${() => setGroup("")}>All</button>${inSection.map((g) => html`<button key=${g.id} class=${"chip" + (gNow === g.id ? " on" : "")} aria-pressed=${gNow === g.id} title=${g.blurb} onClick=${() => setGroup(g.id)}>${g.label} ${g.count}</button>`)}</div>
        ${gNow && html`<p class="small" style="margin:6px 0 0">${(groups.find((g) => g.id === gNow) || {}).blurb}</p>`}`}
      ${!hits.length && html`<p class="small" style="margin:6px 0 0">No look matches that. Try one word.</p>`}
      ${hits.length > 0 && html`<div class="mstyles-list">${hits.slice(0, more).map((e) => html`<button key=${e.id} class=${"mstyle" + (picked[e.group] === e.id ? " on" : "")} aria-pressed=${picked[e.group] === e.id} onClick=${() => commit(togglePick(picked, e, byId))}><b>${e.label}${q.trim() || !gNow ? html` <span style="font-weight:400;opacity:.7">· ${label(e.group)}</span>` : ""}${e.move ? html` <span style="font-weight:400;opacity:.7">· camera move</span>` : ""}</b><small>${e.phrase}</small></button>`)}
        ${hits.length > more && html`<button class="btn small" onClick=${() => setMore(more + PAGE)}>Show more (${hits.length - more} left)</button>`}</div>`}
      <div class="row" style="margin:6px 0 0"><button class="btn small" aria-expanded="true" onClick=${() => setOpen(false)}>Close looks</button><span class="small grow" style="opacity:.8">${lib.total} looks, our own wording. Aspect words suggest a shape; the aspect option sets the real size.</span></div>
    </div>`}
    ${chosen.length > 0 && html`<div class="row" style="margin:6px 0 0;flex-wrap:wrap" role="status"><span class="small">Added:</span>${chosen.map((e) => html`<button key=${e.id} class="chip on" title=${"Remove " + e.label} aria-label=${"Remove " + e.label} onClick=${() => commit(togglePick(picked, e, byId))}>${e.label} ×</button>`)}<button class="btn small" onClick=${() => commit({})}>Remove all</button></div>`}
  </div>`;
}
