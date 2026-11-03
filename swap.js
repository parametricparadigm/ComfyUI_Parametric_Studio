/* Swap on any model: every graph here that swaps a person, side by side, each with its core model, a render made on our card and its licence. The rows come from studio/swap_showcase.json through /api/swap.
   A graph whose proof is still rendering is listed as coming, with no picture. Nothing here runs a model: each card opens the page that does. */
import { useEffect, useState } from "preact/hooks";
import { html, api } from "./common.js";
import { said, FxHero, FxMosaic, FxSkeleton } from "./fx.js";
import { Media, Strip, Head } from "./look.js";

export const KINDS = [["all", "Everything"], ["video", "Video"], ["still", "Stills"]];
export const shown = (rows, kind) => rows.filter((r) => r.status === "rendered" && (kind === "all" || r.output === kind));
export const coming = (rows) => rows.filter((r) => r.status !== "rendered");
export const families = (rows) => new Set(shown(rows, "all").map((r) => r.family)).size;
/* The graph to download: from the server, or in the read-only demo from the answer saved for it. */
export const graphHref = (id, demo = typeof window !== "undefined" && window.STUDIO_DEMO) => (demo ? `demo-api/swap__graph__${id}.json` : `/api/swap/graph/${id}`);
const secs = (s) => (s == null ? "not measured" : s >= 90 ? `${Math.round(s / 6) / 10} min` : `${Math.round(s)} s`);

/* Open the page that runs this graph. Recast is a Create goal, so the goal is picked after the page opens, the way the home page does it. */
function open(o) {
  location.hash = o.hash;
  if (o.goal) setTimeout(() => dispatchEvent(new CustomEvent("prime-action", { detail: { type: "set_goal", goal: o.goal } })), 80);
}

function Card({ r }) {
  const p = r.proof;
  return html`<li class="fx-card sw-card" id=${"sw-" + r.id}>
    <figure class="sw-media film"><${Media} src=${p.src} poster=${p.poster} alt=${`${r.name}: ${r.looked}`}/><figcaption><span class="sw-ai">AI-generated</span></figcaption></figure>
    <header><h3>${r.name}</h3><p class="small">${r.core}</p></header>
    <div class="fx-row"><span class="fx-tag ok">${r.output === "video" ? "Video" : "Still"}</span><span class="fx-tag measured">rendered here</span>${r.commercial === false ? html`<span class="fx-tag warn">not for commercial use</span>` : r.commercial === "conditional" ? html`<span class="fx-tag warn">commercial use has conditions</span>` : null}</div>
    <dl class="sw-facts">
      <div><dt>Swaps</dt><dd>${r.swaps}</dd></div>
      <div><dt>Give it</dt><dd>${r.inputs}</dd></div>
      <div><dt>Time and memory</dt><dd>${secs(p.seconds)}${p.step ? ` for the ${p.step} step` : ""}, peak ${p.peak_vram_gib} GB, seed ${p.seed}</dd></div>
      <div><dt>What we saw</dt><dd>${r.looked}</dd></div>
      <div><dt>What's wrong</dt><dd>${r.flaw}</dd></div>
      <div><dt>Licence</dt><dd>${r.licence}</dd></div>
    </dl>
    <p class="small sw-src">Graph <code>${r.graph}</code>. Render on record in <code>${p.record}</code> (${p.key}).</p>
    <div class="fx-row"><button class="btn primary" onClick=${() => open(r.open)}>${r.open.label}</button><a class="btn" href=${graphHref(r.id)} download=${r.id + "_api.json"}>Download the graph</a></div>
  </li>`;
}

export function Swap() {
  const [d, setD] = useState(null), [err, setErr] = useState(""), [kind, setKind] = useState("all");
  useEffect(() => { api("/api/swap").then(setD).catch((e) => setErr(said(e))); }, []);
  if (err) return html`<div class="fx"><p class="fx-err" role="alert">${err}</p></div>`;
  if (!d) return html`<div class="fx"><${FxSkeleton} label="Loading the swap graphs."/></div>`;
  const all = shown(d.rows, "all"), rows = shown(d.rows, kind), later = coming(d.rows);
  const art = html`<${FxMosaic} items=${all.slice(0, 4).map((r) => ({ src: r.proof.hero || r.proof.poster, alt: `${r.name}, on ${r.core}`, label: r.core.split(" + ")[0] }))}/>`;
  return html`<div class="fx sw">
    <${FxHero} kicker="Swap the person" line="One swap. Many models." lede=${d.about} art=${art} note="Our own renders of invented people."
      stats=${[[all.length, "swap graphs with a render", "measured"], [families(d.rows), "model families"], [all.filter((r) => r.output === "video").length, "for video"], [all.filter((r) => r.output === "still").length, "for stills"]]}/>
    <${Strip} label="Which swaps" value=${kind} onPick=${setKind} items=${KINDS.map(([k, b]) => ({ k, b, s: `${shown(d.rows, k).length} rendered` }))}/>
    <${Head} sub="Each card is one graph in this repo and one render we made with it on our card. Open the page that runs it, or download the graph for ComfyUI.">${KINDS.find((x) => x[0] === kind)[1]}<//>
    <ul class="fx-grid sw-grid">${rows.map((r) => html`<${Card} key=${r.id} r=${r}/>`)}</ul>
    ${later.length > 0 && html`<section class="sw-later" aria-labelledby="sw-later-h"><h2 id="sw-later-h">Coming</h2><p class="small">These graphs are written and their proof renders are under way. They show here with a picture once a render is on record, and not before.</p>
      <ul>${later.map((r) => html`<li key=${r.id}><b>${r.name}</b>, on ${r.core}: swaps ${r.swaps}. ${r.output === "video" ? "Video" : "Still"}. Licence: ${r.licence}.</li>`)}</ul></section>`}
    <section class="sw-rules" aria-label="Real people"><h2>Real people</h2><p>Every person on this page is invented and AI-generated. Swap only invented adults, or people who gave you permission. The Motion page asks you to confirm that before SCAIL 2 or Wan Animate 2 runs, and marks the result as AI-generated; Recast and Try-on don't ask yet. No check here can tell a real person from an invented one, so that part is your word. Checked ${d.checked}.</p></section>
  </div>`;
}
