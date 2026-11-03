/* Pages that arrive as one file each: studio/feature_<name>.py says what the shell needs, and this loads its script and stylesheet. A page that fails to load is left out, and the rest still work. */
import { api, html } from "./common.js";

export async function loadFeaturePages() {
  let pages = [];
  try { pages = (await api("/api/feature-pages")).pages || []; } catch { return []; }
  const loaded = await Promise.all(pages.map(async (p) => {
    try {
      if (p.css && !document.querySelector(`link[href="${p.css}"]`)) { const l = document.createElement("link"); l.rel = "stylesheet"; l.href = p.css; document.head.appendChild(l); }
      const mod = await import("./" + p.module);
      return { ...p, Page: mod[p.export] };
    } catch (e) { console.warn("page not loaded:", p.tab, e); return null; }
  }));
  return loaded.filter((p) => p && p.Page);
}

/* What a number is. Every figure these pages show is one of the two, and says which. */
export const measuredWord = (m) => (m ? "measured" : "estimate");

/* A problem turned into a sentence for the page. */
export const said = (e) => (e && e.message) || String(e || "");

/* Copy text, and say when the browser would not. */
export async function copyText(text) {
  try { await navigator.clipboard.writeText(text); return true; } catch { return false; }
}

/* Hand the browser a file made on this page. */
export function saveFile(name, text, type = "application/json") {
  const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([text], { type })); a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}

/* The opening panel these pages share: a dark film stage with a kicker, a line, real figures and real pictures. Every figure and picture is passed in from the page's own data; a figure that is not there yet is left out. */
export const FxStats = ({ items }) => html`<dl class="fxh-stats">${items.filter((x) => x && x[0] != null && x[0] !== "").map(([v, l, tag]) => html`<div key=${l}><dd>${v}</dd><dt>${l}${tag ? html` <span class=${"fx-tag " + tag}>${tag}</span>` : null}</dt></div>`)}</dl>`;
export const FxHero = ({ kicker, line, lede, stats, art, note, children, cls = "" }) => html`<section class=${"fxh film" + (art ? "" : " fxh-noart") + (cls ? " " + cls : "")}>
  <div class="fxh-text">${kicker && html`<span class="fx-kick">${kicker}</span>`}${line && html`<p class="fxh-line">${line}</p>`}${lede && html`<p class="fxh-lede">${lede}</p>`}${stats && html`<${FxStats} items=${stats}/>`}${children}</div>
  ${art && html`<div class="fxh-art">${art}${note && html`<p class="fxh-note">${note}</p>`}</div>`}
</section>`;
/* A row of real pictures for a hero: each with its own label. */
export const FxMosaic = ({ items }) => html`<ul class="fxh-mosaic" style=${{ "--n": items.length }}>${items.map((x, i) => html`<li key=${x.src} class=${i === 0 ? "lead" : ""}><img src=${x.src} alt=${x.alt || ""} loading=${i < 2 ? "eager" : "lazy"} decoding="async"/>${x.label && html`<span>${x.label}</span>`}</li>`)}</ul>`;
/* A placeholder in the shape of what is coming, instead of "Loading" text. The words stay for screen readers. */
export const FxSkeleton = ({ label, rows = 3 }) => html`<div class="fx-skel" role="status" aria-live="polite"><span class="fx-sr">${label}</span>${Array.from({ length: rows }, (_, i) => html`<i key=${i} aria-hidden="true"></i>`)}</div>`;
