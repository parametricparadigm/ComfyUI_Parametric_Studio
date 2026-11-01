/* Pack Lab: read each pick's risks, then try one in a sandbox. No wording here may vouch for a pack, and it never goes near the live ComfyUI. */
import { useEffect, useMemo, useState } from "preact/hooks";
import { html, api, post } from "./common.js";

const ACTION = { "install-candidate": "Can try in the sandbox", "borrow-the-idea": "Idea only, no install", "docs-only": "Docs only, no install" };
const STATE = { fetching: "Getting its files", starting: "Starting the sandbox", loading: "Loading in the sandbox", loaded: "Loaded in the sandbox", failed: "Did not load" };
const BUSY = ["fetching", "starting", "loading"]; const PAGE = 30;

function Tried({ pack, onGone }) {
  const [s, setS] = useState(null);
  useEffect(() => { let on = true; const f = () => api("/api/packlab/sandbox/" + pack).then((x) => { if (on) setS(x); }).catch(() => {}); f(); const t = setInterval(f, 3000); return () => { on = false; clearInterval(t); }; }, [pack]);
  if (!s || !s.state) return null;
  return html`<div class=${"fx-note " + (s.state === "failed" ? "bad" : "")} role="status" aria-live="polite"><b>${STATE[s.state] || s.state}</b><p>${s.note}</p>
    ${s.no_internet && html`<p class="small">Tried to reach the internet from inside: <span class="fx-tag measured">blocked, measured</span></p>`}${s.home_hidden && html`<p class="small">Looked for your home folder from inside: <span class="fx-tag measured">not visible, measured</span></p>`}${s.origin && html`<p class="small">From ${s.origin}.</p>`}
    ${(s.nodes || []).length > 0 && html`<details><summary>${s.node_count} nodes it added</summary><p class="small pl-nodes">${s.nodes.join(", ")}</p></details>`}
    ${s.log && html`<details><summary>The log</summary><pre class="fx-pre" tabindex="0">${s.log}</pre></details>`}
    ${!BUSY.includes(s.state) && html`<p class="small">Loading proves it loads, and nothing about its safety.</p><div><button class="btn small" type="button" onClick=${async () => { await api("/api/packlab/sandbox/" + pack, { method: "DELETE" }); setS(null); onGone(); }}>Delete this sandbox</button></div>`}</div>`;
}

function Pick({ p, can, warnings, refresh }) {
  const [open, setOpen] = useState(false), [err, setErr] = useState(""), [went, setWent] = useState(!!p.sandbox_state);
  const go = async () => { setErr(""); try { await post("/api/packlab/sandbox", { pack: p.pack, understood: true }); setWent(true); } catch (e) { setErr(e.message); } };
  return html`<li class="fx-card pl-pick"><div class="fx-row"><span class=${"fx-tag " + (p.installable ? "" : "warn")}>${ACTION[p.action] || p.action}</span><span class="small">Licence as stated: ${p.licence || "not found"}</span></div>
    <h3>${p.repo}</h3><p>${p.adds || "No summary."}</p>
    <div class="pl-risk"><b>Risk notes</b><p>${p.risk || "No notes written. That is not a clean result."}</p></div>
    <button class="btn small" type="button" aria-expanded=${open} onClick=${() => setOpen(!open)}>${open ? "Less" : "More"}</button>
    ${open && html`<dl class="pl-more">${p.nodes && html`<dt>Nodes</dt><dd>${p.nodes}</dd>`}${p.needs && html`<dt>Models it wants</dt><dd>${p.needs}</dd>`}<dt>Our load test</dt><dd>${p.sandbox}</dd><dt>Section</dt><dd>${(p.sections || []).join(", ")}</dd>${p.note && html`<dt>Note</dt><dd>${p.note}</dd>`}<dt>Source</dt><dd><a href=${"https://github.com/" + p.repo} rel="noreferrer noopener" target="_blank">github.com/${p.repo}</a></dd></dl>`}
    ${p.installable && !went && (can.ok ? html`<details class="pl-warn"><summary class="fx-go">Try it in a sandbox</summary><ul>${warnings.map((w) => html`<li key=${w}>${w}</li>`)}</ul><button class="fx-go" type="button" onClick=${go}>I have read this. Install in the sandbox</button></details>` : null)}
    ${err && html`<p class="fx-err" role="alert">${err}</p>`}
    ${went && html`<${Tried} pack=${p.pack} onGone=${() => { setWent(false); refresh(); }}/>`}</li>`;
}

export function PackLab() {
  const [d, setD] = useState(null), [err, setErr] = useState(""), [q, setQ] = useState(""), [show, setShow] = useState("install-candidate"), [n, setN] = useState(PAGE);
  const load = () => api("/api/packlab/picks").then(setD).catch((e) => setErr(e.message));
  useEffect(() => { load(); }, []); useEffect(() => setN(PAGE), [q, show]);
  const shown = useMemo(() => { if (!d) return []; const w = q.trim().toLowerCase(); return d.picks.filter((p) => (!show || p.action === show) && (!w || (p.repo + " " + (p.adds || "") + " " + (p.sections || []).join(" ")).toLowerCase().includes(w))); }, [d, q, show]);
  if (err) return html`<div class="fx"><div class="fx-note bad" role="alert"><p>${err}</p></div></div>`;
  if (!d) return html`<div class="fx"><p class="small" role="status">Reading the picks.</p></div>`;
  return html`<div class="fx">
    <div class=${"fx-note " + (d.can.ok ? "warn" : "bad")} role=${d.can.ok ? undefined : "alert"}><b>${d.can.ok ? "Reviewed does not mean safe" : "Pack Lab will not install anything on this machine"}</b><p>${d.can.ok ? d.about : d.can.why}</p></div>
    <div class="pl-filters"><label class="fx-lab">Find a pack<input class="fx-in" type="search" value=${q} onInput=${(e) => setQ(e.target.value)} placeholder="upscale, sigma, storyboard"/></label><label class="fx-lab">Show<select class="fx-in" value=${show} onChange=${(e) => setShow(e.target.value)}><option value="install-candidate">Can try in the sandbox</option><option value="borrow-the-idea">Ideas to borrow</option><option value="docs-only">Docs</option><option value="">All</option></select></label></div>
    <p class="small" role="status">${shown.length} of ${d.picks.length} picks, reviewed ${d.made}.</p>
    <ul class="pl-list">${shown.slice(0, n).map((p) => html`<${Pick} key=${p.pack} p=${p} can=${d.can} warnings=${d.warnings} refresh=${load}/>`)}</ul>
    ${shown.length > n && html`<button class="btn" type="button" onClick=${() => setN(n + PAGE)}>Show more</button>`}
    <section class="fx-card" aria-label="Flagged in review"><h2>Flagged in review</h2><p>${d.flag_note}</p></section>
  </div>`;
}
