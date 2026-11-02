// Pure helpers for the Voices page, so the rules can be tested without a browser.
export const KINDS = { speech: "Built-in voice", design: "Voice from a description", reference: "Needs a reference clip", convert: "Voice converter", codec: "Speech codec", listen: "Speech to text", clean: "Clean-up" };
export const READS_A_LINE = new Set(["speech", "design", "reference"]);
export const clock = (s) => { if (!isFinite(s) || s < 0) return "0:00"; const m = Math.floor(s / 60); return `${m}:${String(Math.floor(s % 60)).padStart(2, "0")}`; };

/** Can a person use this commercially, by the licence on the card? Only ever says yes when the card does. */
export const licenceWord = (l) => { if (!l) return ["Licence unread", "warn"]; if (l.commercial === true) return ["Commercial use OK", "ok"]; if (l.commercial === false) return ["Non-commercial", "bad"]; return ["Check the licence", "warn"]; };

/** The proof label for a render. "Heard" is Whisper, never a person. */
export function proofWord(r) {
  if (!r || r.status === "not run") return ["Not run here", "warn"];
  if (r.match_pct == null) return ["Rendered, not measured", "warn"];
  if (r.match_pct >= 90) return [`Whisper: ${r.match_pct}% of the words`, "ok"];
  if (r.match_pct >= 60) return [`Whisper: ${r.match_pct}% of the words`, "warn"];
  return [`Whisper: only ${r.match_pct}% of the words`, "bad"];
}

const by = (f, dir = 1) => (a, b) => { const x = f(a), y = f(b); if (x == null && y == null) return 0; if (x == null) return 1; if (y == null) return -1; return (x - y) * dir; };
export const SORTS = {
  match: ["Words matched", by((m) => m.proof.match_pct, -1)],
  fast: ["Fastest", by((m) => m.proof.secs)],
  light: ["Least memory", by((m) => m.proof.peak_gib)],
  name: ["Name", (a, b) => a.label.localeCompare(b.label)],
};
export const FILTERS = {
  all: ["All", () => true],
  builtin: ["Built-in voice", (m) => m.kind === "speech"],
  design: ["From a description", (m) => m.kind === "design"],
  clip: ["Needs a clip", (m) => m.kind === "reference"],
  open: ["Commercial OK", (m) => m.licence && m.licence.commercial === true],
};
export const speakers = (models) => models.filter((m) => READS_A_LINE.has(m.kind) && m.proof && m.proof.audio);
export function board(models, filter, sort) { return speakers(models).filter(FILTERS[filter][1]).sort(SORTS[sort][1]); }

export function counts(models) {
  const made = speakers(models);
  return { speaking: made.length, tools: models.filter((m) => !READS_A_LINE.has(m.kind) && m.state === "rendered").length, blocked: models.filter((m) => m.state !== "rendered").length, files: models.reduce((n, m) => n + (m.state === "rendered" ? (m.files || []).length : 0), 0) };
}

/** Bars for a waveform: reduce a list of peaks to n. */
export function bars(peaks, n = 96) {
  if (!peaks || !peaks.length) return []; const out = []; const step = peaks.length / n;
  for (let i = 0; i < n; i++) { const a = Math.floor(i * step), b = Math.max(a + 1, Math.floor((i + 1) * step)); out.push(Math.max(...peaks.slice(a, b))); }
  return out;
}

/** The body for /api/voices/run. A reference never goes without the yes, so the server's refusal is a second line, not the only one. */
export function runBody(m, f) {
  const b = { model: m.id, text: (f.text || "").trim() }; if ((f.voice || "").trim()) b.voice = f.voice.trim();
  if (f.reference && m.reference !== "none") { b.reference = f.reference; if (f.consent) b.consent = f.consent; if ((f.referenceText || "").trim()) b.reference_text = f.referenceText.trim(); }
  return b;
}
export function canRun(m, f) {
  if (!m || !(f.text || "").trim()) return false;
  if (m.reference === "required" && !f.reference) return false;
  if (f.reference && m.reference !== "none" && !f.consent) return false;
  return true;
}
/** Group Kokoro's voices by language for the voice grid. */
export function byLanguage(kokoro) {
  const g = {}; for (const [v, r] of Object.entries(kokoro || {})) { (g[r.lang] = g[r.lang] || []).push({ voice: v, ...r }); }
  return Object.entries(g).sort((a, b) => (a[0] === "en" ? -1 : b[0] === "en" ? 1 : a[0].localeCompare(b[0])));
}
