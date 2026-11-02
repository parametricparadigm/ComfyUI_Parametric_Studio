// Pure helpers for the Captions & Sound page, so the rules can be tested without a browser.
export const clock = (s) => { if (!isFinite(s) || s < 0) return "0:00.0"; const m = Math.floor(s / 60); const r = s - m * 60; return `${m}:${r < 10 ? "0" : ""}${r.toFixed(1)}`; };

/** Can a person use this commercially, by the licence on the card? Only ever says yes when the card does. */
export const licenceWord = (l) => { if (!l) return ["Licence unread", "warn"]; if (l.commercial === true) return ["Commercial use OK", "ok"]; if (l.commercial === false) return ["Non-commercial", "bad"]; return ["Check the licence", "warn"]; };

export const STYLE_WORDS = { outline: "White, black edge", box: "White on a dark box", yellow: "Yellow, black edge" };
export const SIZE_WORDS = { small: "Small", medium: "Medium", large: "Large" };
export const PLACE_WORDS = { bottom: "Bottom", top: "Top" };

/** The cue on screen at time t, or null. */
export const cueAt = (cues, t) => (cues || []).find((c) => t >= c.start && t < c.end) || null;

/** A clip the page can name to the server: from the output folder (picked) or the input folder (uploaded). */
export const clipRef = (key) => {
  if (!key) return null;
  const [type, ...rest] = key.split(":"); const path = rest.join(":"); const i = path.lastIndexOf("/");
  return { type: type === "input" ? "input" : "output", subfolder: i < 0 ? "" : path.slice(0, i), filename: i < 0 ? path : path.slice(i + 1) };
};
export const clipKey = (c) => `${c.type || "output"}:${c.subfolder ? c.subfolder + "/" : ""}${c.filename}`;
export const viewUrl = (c) => "/api/view?filename=" + encodeURIComponent(c.filename) + "&subfolder=" + encodeURIComponent(c.subfolder || "") + "&type=" + (c.type || "output");

/** The request body for a caption run. The language only goes to a model that can hear more than English. */
export function captionBody(clip, m, f) {
  return { clip: clipRef(clip), model: m.id, language: m.english_only ? "" : (f.language || "").trim().toLowerCase(), burn: !!f.burn, style: f.style, size: f.size, place: f.place };
}
export const canCaption = (clip, m) => !!(clip && m && m.ready);

/** Seconds as the proof shows them. */
export const secs = (s) => (s == null ? "not measured" : s >= 90 ? `${Math.round(s / 6) / 10} min` : `${Math.round(s * 10) / 10} s`);
