import { h } from "preact";
import htm from "htm";
export const html = htm.bind(h);
export const api = async (path, opts) => {
  const r = await fetch(path, opts);
  if (!r.ok) { let m = r.statusText; try { const j = await r.json(); m = j.detail || (j.problems && j.problems.join("; ")) || m; } catch {} throw new Error(typeof m === "string" ? m : JSON.stringify(m)); }
  return r.json();
};
export const post = (p, body) => api(p, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
export default html;
