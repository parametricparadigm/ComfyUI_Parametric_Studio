// Pure helpers for the Commercials page, so its rules can be tested without a browser.
export const GROUPS = ["All", "Parody", "Comedy", "Premium", "Retail", "Sincere", "Sport"];
export const clock = (s) => { if (!isFinite(s) || s < 0) return "0:00"; const m = Math.floor(s / 60); return `${m}:${String(Math.floor(s % 60)).padStart(2, "0")}`; };
export const secs = (s) => (s == null || !isFinite(s) ? "-" : `${Math.round(s * 10) / 10} s`);

/** Genres that fit a group chip and a search, in library order. */
export function pick(genres, group, q) {
  const words = String(q || "").toLowerCase().split(/\s+/).filter(Boolean);
  return (genres || []).filter((g) => (group === "All" || g.group === group) && words.every((w) => `${g.title} ${g.pitch} ${g.group}`.toLowerCase().includes(w)));
}

/** The spot as segments across a bar: each beat, the end card, and the parody card when there is one. Widths are shares of the whole. */
export function segments(script) {
  if (!script) return [];
  const L = script.length; const out = script.beats.map((b, i) => ({ id: b.id, n: i + 1, kind: "beat", start: b.start, seconds: b.seconds, share: b.seconds / L, parts: (b.parts || []).length }));
  const e = script.end_card; out.push({ id: "end", n: null, kind: "end", start: e.start, seconds: e.seconds, share: e.seconds / L });
  const p = script.parody_card; if (p) out.push({ id: "parody", n: null, kind: "parody", start: p.start, seconds: p.seconds, share: p.seconds / L });
  return out;
}

/** What the page sends to render a spot: the genre, the brief, and the voice-over lines as shown (edited or not). Empty fields fall back to the genre's example on the server. */
export function runBody(genre, brief, script, engine) {
  const b = {}; for (const [k, v] of Object.entries(brief || {})) if (String(v || "").trim()) b[k] = String(v).trim();
  return { genre: genre.id, brief: b, length: script.length, tone: script.tone, engine, vo: script.beats.map((x) => x.vo), end_vo: script.end_card.vo, writer: script.writer };
}

/** A proof's status as a word and a tag colour. A flawed spot says so. */
export function statusWord(s) { return { passed: ["Passed", "ok"], flawed: ["Passed with flaws", "warn"], failed: ["Failed", "bad"] }[s] || ["Not run", "warn"]; }

/** The Whisper line for a spot: what it heard, never a claim that a person listened. */
export function heardWord(a) {
  if (!a) return ["Not measured", "warn"];
  if (a.whisper_match == null) return ["Whisper didn't run", "warn"];
  return [`Whisper heard ${a.whisper_match}% of the script`, a.whisper_match >= 85 ? "ok" : a.whisper_match >= 60 ? "warn" : "bad"];
}

/** Licence class as words. */
export const classWord = (c) => ({ open: "Open", community: "Community licence", noncommercial: "Non-commercial" }[c] || "Check the licence");

/** Counts for the header. */
export function totals(genres, proof) {
  const spots = (proof && proof.spots) || [];
  return { genres: (genres || []).length, rendered: spots.filter((s) => s.status !== "failed").length, flawed: spots.filter((s) => s.status === "flawed").length, shots: spots.reduce((n, s) => n + (s.shots || []).length, 0) };
}
