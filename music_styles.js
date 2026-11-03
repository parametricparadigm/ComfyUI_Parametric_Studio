// The Music goal's style picker: browse or search families, open a style, pick a card. The card fills the prompt box; nothing else changes.
import { useState, useEffect, useRef } from "preact/hooks";
import { html, api } from "./common.js";
import { searchStyles, styleLine, cardLine, cardTags, applyCard, clearCard } from "./music_styles_logic.js";

const PAGE = 40;

export function MusicStyles({ prompt, setPrompt, appliedRef }) {
  const [lib, setLib] = useState(null); const [err, setErr] = useState(""); const [q, setQ] = useState(""); const [fam, setFam] = useState(""); const [open, setOpen] = useState(null); const [picked, setPicked] = useState(null); const [more, setMore] = useState(PAGE); const [left, setLeft] = useState(false);
  const want = useRef("");
  const load = () => { setErr(""); api("/api/music-styles").then(setLib).catch((e) => setErr(e.message)); };
  useEffect(load, []);
  useEffect(() => setMore(PAGE), [q, fam]);
  const openStyle = (id) => { want.current = id; setErr(""); api("/api/music-styles/" + encodeURIComponent(id)).then((s) => { if (want.current === id) setOpen(s); }).catch((e) => setErr(e.message)); };
  const pick = (c) => {
    const r = applyCard(prompt, cardTags(open, c), appliedRef.current);
    setLeft(r.structured);
    if (r.structured) return;
    appliedRef.current = r.applied; setPrompt(r.prompt); setPicked({ id: c.id, style: open.label, line: cardLine(c), note: c.source === "studio" ? open.note : "" });
  };
  const clear = () => { setPrompt(clearCard(prompt, appliedRef.current)); appliedRef.current = []; setPicked(null); setLeft(false); };
  const hits = lib ? searchStyles(lib.families, q, fam) : [];
  return html`<div class="field mstyles"><label>Style library</label>
    ${err && html`<p class="small" style="color:var(--err);margin:0 0 6px" role="alert">${err} <button class="btn small" onClick=${open || !lib ? load : () => setErr("")}>Try again</button></p>`}
    ${!lib && !err && html`<div class="pp-rowskel" role="status"><span class="fx-sr">Loading styles.</span><i aria-hidden="true"></i><i aria-hidden="true"></i></div>`}
    ${lib && !open && html`<div class="mstyles-find"><input type="search" placeholder="Search: trap, bossa nova, dubstep" value=${q} onInput=${(e) => setQ(e.target.value)} aria-label="search styles"/>
      <select value=${fam} onChange=${(e) => setFam(e.target.value)} aria-label="style family"><option value="">All families</option>${lib.families.map((f) => html`<option value=${f.id}>${f.label} (${f.styles.length})</option>`)}</select></div>
      ${!q.trim() && !fam && html`<p class="small" style="margin:6px 0 0">${lib.counts.styles} styles in ${lib.counts.families} families. Search, or pick a family.</p>`}
      ${(q.trim() || fam) && !hits.length && html`<p class="small" style="margin:6px 0 0">No style matches that. Try one word.</p>`}
      ${hits.length > 0 && html`<div class="mstyles-list">${hits.slice(0, more).map(({ family, style }) => html`<button class="mstyle" onClick=${() => openStyle(style.id)}><b>${style.label}</b><small>${fam ? "" : family.label + " · "}${styleLine(style)}</small></button>`)}
        ${hits.length > more && html`<button class="btn small" onClick=${() => setMore(more + PAGE)}>Show more (${hits.length - more} left)</button>`}</div>`}`}
    ${lib && open && html`<div class="row" style="margin:0 0 6px"><button class="btn small" onClick=${() => { want.current = ""; setOpen(null); }}>Back to styles</button><b class="grow" style="font-size:13px">${open.label}</b></div>
      ${open.note && html`<p class="small warn" style="margin:0 0 6px">${open.note}</p>`}
      ${open.tempo_line && html`<p class="small" style="margin:0 0 6px">${open.tempo_line}</p>`}
      <div class="mstyles-list">${open.cards.map((c) => html`<button class=${"mstyle" + (picked && picked.id === c.id ? " on" : "")} aria-pressed=${!!(picked && picked.id === c.id)} onClick=${() => pick(c)}><b>${cardLine(c)}</b><small>${c.mood}</small></button>`)}</div>`}
    ${left && html`<p class="small warn" style="margin:6px 0 0" role="status">Your prompt is a full caption already, so the card left it alone. Empty the prompt to use a card.</p>`}
    ${picked && html`<div class="row" style="margin:6px 0 0" role="status"><span class="small grow">Filled from ${picked.style}: ${picked.line}. Your own tags stay.</span><button class="btn small" onClick=${clear}>Remove card tags</button></div>
      ${picked.note && html`<p class="small warn" style="margin:4px 0 0">${picked.note}</p>`}`}
    ${lib && html`<p class="small" style="margin:6px 0 0;opacity:.8">Official styles come from the MiniMax-Music3 caption library. Copyright (c) 2026 MiniMax, under the MiniMax-Music3 Community License.</p>`}
  </div>`;
}
