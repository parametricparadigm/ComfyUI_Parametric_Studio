// A persona picker for the Voices page's design models: 56 ready voice descriptions from GET /api/voices/personas.
// Picking one fills the "Describe the voice" box with its description, which you can still edit. Adults only; no real person's voice.
import { useState, useEffect } from "preact/hooks";
import { html, api } from "./common.js";

export function PersonaPick({ onPick }) {
  const [d, setD] = useState(null), [err, setErr] = useState(""), [id, setId] = useState("");
  useEffect(() => { api("/api/voices/personas").then(setD).catch((e) => setErr(e.message)); }, []);
  if (err) return html`<p class="small" role="alert">The voice personas didn't load: ${err}</p>`;
  if (!d) return null;
  const cur = d.personas.find((p) => p.id === id);
  return html`<label class="fx-lab">Start from a persona<select class="fx-in" value=${id} onChange=${(e) => { const p = d.personas.find((x) => x.id === e.target.value); setId(e.target.value); if (p) onPick(p.text); }}><option value="">Write my own</option>${d.personas.map((p) => html`<option key=${p.id} value=${p.id}>${p.label}</option>`)}</select></label>
    ${cur && html`<p class="small">${cur.blurb} The description below is yours to change. Design models read it as a guide, not a promise.</p>`}`;
}
