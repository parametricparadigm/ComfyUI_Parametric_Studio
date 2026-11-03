// The Create page's "Improve" button: turns a short idea into a prompt for the chosen goal's model, using that model's kit (GET /api/prompt-kits).
// The local writer does it when it is running and its answer passes the checks; otherwise a fixed formula does, and the note says which. Undo puts your words back.
import { useState, useEffect } from "preact/hooks";
import { html, api, post } from "./common.js";

let kits = null;
export function ImprovePrompt({ goal, prompt, setPrompt }) {
  const [list, setList] = useState(kits), [busy, setBusy] = useState(false), [res, setRes] = useState(null), [before, setBefore] = useState(null), [err, setErr] = useState("");
  useEffect(() => { if (!kits) api("/api/prompt-kits").then((d) => { kits = d.kits; setList(kits); }).catch(() => setList([])); }, []);
  useEffect(() => { setRes(null); setBefore(null); setErr(""); }, [goal]);
  const kit = (list || []).find((k) => k.goals.includes(goal));
  if (!kit) return null;
  const go = async () => { if (!prompt.trim()) { setErr("Write a few words first."); return; } setErr(""); setBusy(true); try { const r = await post("/api/prompt-kits/enhance", { goal, prompt }); setBefore(prompt); setPrompt(r.prompt); setRes(r); } catch (e) { setErr(e.message); } setBusy(false); };
  const undo = () => { setPrompt(before); setBefore(null); setRes(null); };
  return html`<span class="improve"><button class="btn small" disabled=${busy} title=${"Rewrite your idea the way " + kit.label + " reads prompts best"} onClick=${go}>${busy ? "Improving..." : "Improve for " + kit.label}</button>${before != null && html`<button class="btn small" onClick=${undo}>Undo</button>`}
    ${err && html`<p class="small generr" role="alert" style="margin:4px 0 0">${err}</p>`}
    ${res && html`<p class="small" role="status" style="margin:4px 0 0">${res.source === "model" ? "The local writer rewrote it with the " + kit.label + " notes." : "The local writer was off or its answer failed the checks, so a fixed formula wrote this."}${res.problems.length ? " Check: " + res.problems.slice(0, 3).join("; ") + "." : ""}</p>`}</span>`;
}
