// Pure helpers of the Music goal's style picker. No imports. The prompt box is the only thing a card changes.
export const SHORT_NOTE = "studio-authored, untested";

const fold = (t) => String(t || "").trim().toLowerCase();
const BPM = /\b\d{2,3}\s*bpm\b/i;
const KEY = /\b[A-G](?:#|b|-flat|-sharp)?\s+(?:major|minor)\b/;
const HEADINGS = ["Global Metadata", "Vocal Details", "Arrangement"];

/** The whole phrase in a label, id or one alias first; if nothing has it, every typed word somewhere in the style or its family. */
export function searchStyles(families, q, familyId = "") {
  const words = fold(q).split(/\s+/).filter(Boolean), pool = [];
  for (const f of families || []) if (!familyId || f.id === familyId) for (const s of f.styles || []) pool.push({ family: f, style: s });
  if (!words.length) return familyId ? pool : [];
  const phrase = words.join(" ");
  const exact = pool.filter(({ style: s }) => [s.label, s.id, ...(s.aliases || [])].some((t) => fold(t).includes(phrase)));
  if (exact.length) return exact;
  return pool.filter(({ family: f, style: s }) => { const hay = fold(`${s.label} ${s.id} ${(s.aliases || []).join(" ")} ${f.label} ${f.cues || ""}`); return words.every((w) => hay.includes(w)); });
}

export function styleLine(s) {
  return [s.bpm ? `${s.bpm} BPM` : "", s.cards > 1 ? `${s.cards} variations` : "", s.source === "studio" ? SHORT_NOTE : ""].filter(Boolean).join(" · ");
}

const SINGER = { female: "female singer", male: "male singer", mixed: "female + male", choir: "choir" };
export function cardLine(c) {
  return [c.bpm ? `${c.bpm} BPM${c.felt_bpm ? ` (felt ${c.felt_bpm})` : ""}` : "", c.key || "", SINGER[c.gender] || "", c.rap ? "rap" : "", c.instrumental_led ? "instrumental-led" : "", c.language && c.language !== "English" ? c.language : "", c.source === "studio" ? SHORT_NOTE : ""].filter(Boolean).join(" · ");
}

/** "Dubstep / Riddim (Hypnotic Loops, Sparse)" -> ["Dubstep", "Riddim", "Hypnotic Loops", "Sparse"]: the genre stays first, as the model's captions put it. */
export function labelTags(label) {
  const inner = []; const bare = String(label || "").replace(/\(([^)]*)\)/g, (_, x) => { inner.push(x); return ""; });
  return [...bare.split("/"), ...inner.flatMap((x) => x.split(","))].map((t) => t.replace(/,/g, " ").replace(/\s+/g, " ").trim()).filter(Boolean);
}

const VOICE = { female: "female vocals", male: "male vocals", mixed: "female and male vocals", choir: "choir" };
/** The tags a card puts in the prompt: the style's name, the voice, the key and the typical BPM. */
export function cardTags(style, c) {
  const voice = c.instrumental_led ? "instrumental" : c.rap && (c.gender === "female" || c.gender === "male") ? `${c.gender} rap` : c.rap ? "rap vocals" : VOICE[c.gender] || "";
  const felt = c.felt_bpm && c.felt_bpm < c.bpm ? "half-time feel" : "";
  return [...labelTags(style.label), voice, c.language && c.language !== "English" ? `${c.language} lyrics` : "", c.key || "", c.bpm ? `${c.bpm} BPM` : "", felt].filter(Boolean);
}

/** A full three-block caption, pasted or written by hand. The card leaves it alone. */
export const isStructured = (prompt) => HEADINGS.every((h) => new RegExp(`^\\W*${h}\\b`, "im").test(String(prompt || "")));

const split = (prompt) => String(prompt || "").split(",").map((t) => t.trim()).filter(Boolean);

/** Take the card's earlier tags out again. Only an exact match goes, so a tag the person edited is theirs now. */
export function clearCard(prompt, applied) {
  const mine = new Set((applied || []).map(fold));
  return split(prompt).filter((t) => !mine.delete(fold(t))).join(", ");
}

/**
 * Put a card's tags in front of the person's own. Their tags stay, in their order, and their own BPM or key wins over the card's.
 * `applied` is what the last card added: it is swapped out, and what comes back lists only the tags this card really added, so clearing never takes away something they typed.
 * -> { prompt, applied, structured }
 */
export function applyCard(prompt, tags, applied = []) {
  if (isStructured(prompt)) return { prompt, applied, structured: true };
  const own = split(clearCard(prompt, applied)), text = own.join(", "), seen = new Set(own.map(fold)), added = [];
  for (const t of tags) {
    if (seen.has(fold(t)) || (BPM.test(t) && BPM.test(text)) || (KEY.test(t) && KEY.test(text))) continue;
    seen.add(fold(t)); added.push(t);
  }
  return { prompt: [...added, ...own].join(", "), applied: added, structured: false };
}
