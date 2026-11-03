// Pure helpers of the Music page. No imports, so a test can run them with plain node.

export const clock = (s) => { const t = Math.max(0, Math.floor(Number(s) || 0)); return `${Math.floor(t / 60)}:${String(t % 60).padStart(2, "0")}`; };

export const STATE_WORD = { proven: "Rendered here", unproven: "On disk, not rendered", missing: "Weights not here", unknown: "Not checked" };
export const STATE_NOTE = {
  proven: "Rendered here on this page's brief. Measured, and transcribed by Whisper. No person has listened.",
  unproven: "The weights are here, but nothing has been rendered for this page. Treat every claim as the model card's, not ours.",
  missing: "The weights aren't on this machine, so it has not run here.",
  unknown: "This machine's model folder isn't set, so nothing was checked.",
};
const ORDER = { proven: 0, unproven: 1, missing: 2, unknown: 3 };
export const sortModels = (rows) => [...(rows || [])].sort((a, b) => (ORDER[a.state] ?? 9) - (ORDER[b.state] ?? 9));
export const counts = (rows) => (rows || []).reduce((n, m) => { n[m.state] = (n[m.state] || 0) + 1; return n; }, { proven: 0, unproven: 0, missing: 0, unknown: 0 });
export const rendered = (rows) => (rows || []).filter((m) => m.state === "proven" && m.render && m.render.audio);

/** What the lyric check means in words. Whisper can miss a clear line and hear one that is rough, so this is a score and not a verdict. */
export function lyricWord(m) {
  if (!m || !m.lines_total) return "No lyrics in this brief";
  return `${m.lines_heard} of ${m.lines_total} lines`;
}

/** Bars for a waveform. Evenly thins or stretches stored peaks to n bars, keeping each span's loudest point. */
export function bars(peaks, n) {
  const p = peaks || []; if (!p.length || n < 1) return [];
  const out = [];
  for (let i = 0; i < n; i++) {
    const a = Math.floor((i * p.length) / n), b = Math.max(a + 1, Math.floor(((i + 1) * p.length) / n));
    let top = 0; for (let j = a; j < b && j < p.length; j++) top = Math.max(top, p[j]);
    out.push(top);
  }
  return out;
}

/** One value of a feature track at a time in seconds. Out of range reads as silence, so the visual rests when the audio ends. */
export function featureAt(track, fps, t) {
  if (!track || !track.length || !(fps > 0)) return 0;
  const x = t * fps; if (x < 0 || x >= track.length) return 0;
  const i = Math.floor(x), f = x - i, a = track[i], b = i + 1 < track.length ? track[i + 1] : a;
  return a + (b - a) * f;
}

/** A polyline for a feature, in a box of w by h. */
export function trackPath(track, w, h) {
  const t = track || []; if (t.length < 2) return "";
  const step = Math.max(1, Math.floor(t.length / w));
  let d = "", first = true;
  for (let i = 0; i < t.length; i += step) { const x = (i / (t.length - 1)) * w, y = h - Math.max(0, Math.min(1, t[i])) * h; d += `${first ? "M" : "L"}${x.toFixed(1)} ${y.toFixed(1)}`; first = false; }
  return d;
}

/** The share of a stacked band bar. Rounds for display and keeps the widths honest. */
export const BANDS = [["sub", "Sub", "20-120 Hz"], ["low", "Low", "120-500 Hz"], ["mid", "Mid", "500 Hz-2 kHz"], ["high", "High", "2-6 kHz"], ["air", "Air", "6-11 kHz"]];

/** The difference in two numbers in words, for the side-by-side table. */
export function versus(a, b, unit = "") {
  if (a == null || b == null) return "";
  const d = Math.round((a - b) * 10) / 10;
  return d === 0 ? "same" : `${d > 0 ? "+" : ""}${d}${unit}`;
}

/** Song forms. Each section name goes on its own line, because Music 3 doesn't sing text on the same line as a tag. */
export const FORMS = [
  { id: "vcvc", label: "Verse, chorus, verse, chorus", lines: 16, text: "[Verse]\n\n\n\n\n[Chorus]\n\n\n\n\n[Verse]\n\n\n\n\n[Chorus]\n\n\n\n" },
  { id: "vcvcbc", label: "With a bridge", lines: 22, text: "[Verse]\n\n\n\n\n[Chorus]\n\n\n\n\n[Verse]\n\n\n\n\n[Chorus]\n\n\n\n\n[Bridge]\n\n\n\n[Chorus]\n\n\n\n" },
  { id: "aaba", label: "AABA, thirty-two bar", lines: 16, text: "[Verse]\n\n\n\n\n[Verse]\n\n\n\n\n[Bridge]\n\n\n\n\n[Verse]\n\n\n\n" },
  { id: "instrumental", label: "Instrumental", lines: 0, text: "[intro]\n[instrumental]\n[solo]\n[instrumental]\n[outro]\n" },
];

export const sungLines = (lyrics) => String(lyrics || "").split("\n").filter((l) => l.trim() && !/^\s*\[.*\]\s*$/.test(l)).length;
/** About six seconds a sung line, plus a tenth, kept between 30 and 300: what same-seed tests on Music 3 found. It's a ceiling, and the model may stop early. */
export const seconds = (lyrics) => { const n = sungLines(lyrics); return n ? Math.max(30, Math.min(300, Math.ceil(n * 6 * 1.1))) : 60; };
/** A section tag with words after it on the same line. Music 3 won't sing those words. */
export const sameLineTags = (lyrics) => String(lyrics || "").split("\n").filter((l) => /^\s*\[[^\]]+\]\s*\S/.test(l));

/** A three-part caption for Music 3 from one plain style line. A caption that already has the three parts stays as written. */
export function captionFrom(style) {
  const s = String(style || "").trim();
  if (/global metadata/i.test(s) && /vocal details/i.test(s) && /arrangement/i.test(s)) return s;
  return `Global Metadata: ${s}.\n\nVocal Details: Clear lead vocal, every lyric line sung plainly and in order.\n\nArrangement: Follow the style above, with a clear intro and ending.`;
}

/** The body the page posts to /api/music/run, shaped for how a model reads its words. */
export function runBody(model, f) {
  const lyr = model.lyrics ? String(f.lyrics || "") : "";
  const secs = model.id === "stable_open" ? Math.min(47, Number(f.seconds) || 47) : Number(f.seconds) || seconds(lyr);
  const body = { graph: model.graph, seed: Number(f.seed) || 7701, seconds: secs, bpm: Number(f.bpm) || 90, key: f.key || "C major", style: String(f.style || ""), lyrics: lyr };
  if (model.takes === "caption") body.caption = captionFrom(f.style);
  const slider = f.slider && f.slider !== "none" ? f.slider : "";
  if (model.id === "music3" && (slider || f.turbo)) {      // the style kit: its own graph, so the plain Music 3 graph stays exactly as proven
    body.graph = "music_music3_kit_api.json"; body.slider = slider || "none"; body.turbo = !!f.turbo;
    if (slider) body.slider_strength = Math.max(0, Math.min(1.5, Number(f.strength ?? 1)));
  }
  return body;
}

/** A curl line anyone can paste. */
export function curlFor(body, origin = "") {
  return `curl -X POST ${origin}/api/music/run -H 'Content-Type: application/json' -d '${JSON.stringify(body).replace(/'/g, "'\\''")}'`;
}

/** Who can sell the song: the page's short answer. */
export const COMMERCIAL = { yes: "Commercial use allowed", conditional: "Commercial use with conditions", no: "Non-commercial only", unknown: "Licence unknown" };
