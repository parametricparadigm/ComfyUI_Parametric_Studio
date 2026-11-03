import { h } from "preact";
import htm from "htm";
export const html = htm.bind(h);
export const api = async (path, opts) => {
  const r = await fetch(path, opts);
  if (!r.ok) { let m = r.statusText; try { const j = await r.json(); m = j.detail || (j.problems && j.problems.join("; ")) || m; } catch {} const e = new Error(typeof m === "string" ? m : JSON.stringify(m)); e.status = r.status; throw e; }
  return r.json();
};
export const post = (p, body) => api(p, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
/** "auto" under prefers-reduced-motion, so a scroll the page starts itself jumps instead of gliding. */
export const smooth = () => (typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth");
export default html;
