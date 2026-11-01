/* Pages that arrive as one file each: studio/feature_<name>.py says what the shell needs, and this loads its script and stylesheet. A page that fails to load is left out, and the rest still work. */
import { api } from "./common.js";

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
