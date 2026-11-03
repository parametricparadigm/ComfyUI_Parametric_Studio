// Pure helpers for the Dub & Voice page, so its rules can be tested without a browser.
export const MODE_WORDS = { dubit: "New mouth and voice (LTX DubIt)", voice: "New voice only", relip: "New voice, then LatentSync" };
export const MODE_NOTES = {
  dubit: "LTX redraws the mouth and speaks your line in the speaker's own voice, taken from the clip's sound. Up to 5 seconds. Needs the GPU (about 42 GB).",
  voice: "Qwen3-TTS reads your line, stretched to the clip's length and laid on it. The mouth doesn't move to the new words.",
  relip: "Qwen3-TTS reads your line, then the Motion page's LatentSync redraws the mouth to it.",
};
export const CONSENT_WORDS = { own: "It is my own voice", permission: "The speaker gave me permission", synthetic: "It is a made-up voice (made by a model)" };

/** Word error rate as a person reads it. 0 is every word heard as written. */
export const werWord = (w) => (w == null ? "not measured" : `${Math.max(0, Math.round((1 - w) * 100))}% of words heard as written (WER ${w.toFixed(2)})`);
export const db = (x, unit = "dB") => (x == null || !isFinite(x) ? "not measured" : `${x > 0 ? "+" : ""}${(Math.round(x * 10) / 10).toFixed(1)} ${unit}`);

/** Did a mastering report meet its own target? Each check by itself, so the page can say which one failed. */
export function masterChecks(rep) {
  if (!rep || !rep.master) return [];
  const m = rep.master, f = m.final || {}, d = rep.ducking || {};
  return [
    { k: "lufs", label: "Integrated loudness", value: db(f.lufs, "LUFS"), want: `${m.target_lufs} ±${m.tolerance}`, ok: f.lufs != null && Math.abs(f.lufs - m.target_lufs) <= m.tolerance },
    { k: "tp", label: "True peak", value: db(f.true_peak, "dBTP"), want: `at or under ${m.target_tp}`, ok: f.true_peak != null && f.true_peak <= m.target_tp },
    { k: "duck", label: "Music under the voice", value: db(d.depth_db), want: "8 dB or more", ok: d.depth_db != null && d.depth_db >= 8 },
  ];
}

/** The request body for a dub. The voice and its yes only go with the modes that use them. */
export function dubBody(clip, f) {
  const b = { clip, mode: f.mode, language: f.language, text: (f.text || "").trim(), seed: Number(f.seed) || 7, permission: !!f.permission };
  if (f.mode === "dubit") b.scene = (f.scene || "").trim();
  else { b.voice = f.voice; if (f.voice === "clone") { b.consent = f.consent; b.source_text = f.source_text || ""; } }
  return b;
}

/** Why the Dub button is off, in words, or "" when it can go. */
export function dubBlocked(clip, f, d) {
  if (!clip) return "Pick a clip first.";
  if (!(f.text || "").trim()) return "Write the line in the new language.";
  if (f.mode === "dubit" && d && d.dubit && !d.dubit.ready) return d.dubit.why_not;
  if (f.mode !== "dubit" && d && d.tts && !d.tts.ready) return d.tts.why_not;
  if (f.mode !== "dubit" && f.voice === "clone" && !f.consent) return "Say whose voice it is before cloning it.";
  if (!f.permission) return "Confirm the person in the clip is invented or gave permission.";
  return "";
}

/** How long a translation is next to the original, in syllable-ish units (vowel groups), so a person can keep the dub near the original's length. */
export const beats = (s) => ((s || "").toLowerCase().match(/[aeiouyáéíóúàèìòùâêîôûäëïöüãõœæ]+/g) || []).length;
export function lengthNote(src, line) {
  const a = beats(src), b = beats(line); if (!a || !b) return "";
  const r = b / a; if (r > 1.25) return `About ${Math.round((r - 1) * 100)}% longer than the original: DubIt may skip words. Try a shorter wording.`;
  if (r < 0.8) return `About ${Math.round((1 - r) * 100)}% shorter than the original: it may sound slow. Try a longer wording.`;
  return "Close to the original's length.";
}
