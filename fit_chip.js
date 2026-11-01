/* One line for other pages: does this run on the machine you told Hardware Fit about? Shows nothing until the table has answered. */
import { useEffect, useState } from "preact/hooks";
import { html, api } from "./common.js";

let table = null;
const settings = () => { try { return JSON.parse(localStorage.getItem("hardware_fit_v1")) || {}; } catch { return {}; } };
async function get() {
  if (table) return table;
  let { vram, ram } = settings();
  if (vram == null || vram === "") { const d = await api("/api/fit/detect"); vram = d.vram_gib; ram = d.ram_gib; }
  table = Object.fromEntries((await api(`/api/fit/table?vram=${encodeURIComponent(vram ?? "")}&ram=${encodeURIComponent(ram ?? "")}`)).rows.map((r) => [r.key, r]));
  return table;
}
const tone = { runs: "ok", offload: "warn", no: "bad", unknown: "" };
export function FitChip({ k }) {
  const [r, setR] = useState(null);
  useEffect(() => { let on = true; get().then((t) => on && setR(t[k] || null)).catch(() => {}); return () => { on = false; }; }, [k]);
  if (!r || r.verdict === "unknown") return null;
  return html`<a class="ft-chip" href="#fit" title=${r.why}><span class=${"fx-tag " + tone[r.verdict]}>${r.word} here</span>${r.need != null && html` <small>${r.need} GiB, ${r.basis}</small>`}</a>`;
}
