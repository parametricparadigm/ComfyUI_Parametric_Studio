/* Which word painted what: the maths of the page, with no DOM, so node can test it. A map is a Float32Array of mh × mw cells in 0..1, stretched between
the word's own floor and peak; floor + v · (peak - floor) gives the real attention back. */

export const PHASES = [["all", "All steps"], ["early", "Early steps"], ["middle", "Middle steps"], ["late", "Late steps"]];

/* The same ramp as the PSN node draws: dark violet, through red, to pale yellow. */
export const STOPS = [[0, [0.02, 0.02, 0.10]], [0.3, [0.35, 0.05, 0.45]], [0.6, [0.85, 0.25, 0.20]], [0.85, [0.98, 0.65, 0.10]], [1, [1.0, 0.98, 0.75]]];
export function ramp(v) {
  const x = Math.max(0, Math.min(1, v));
  for (let i = 1; i < STOPS.length; i++) {
    const [a, ca] = STOPS[i - 1], [b, cb] = STOPS[i];
    if (x <= b) { const t = (x - a) / (b - a); return [0, 1, 2].map((k) => ca[k] * (1 - t) + cb[k] * t); }
  }
  return STOPS[STOPS.length - 1][1].slice();
}

/* Base64 of row-major bytes, as the node writes them, to a 0..1 map. */
export function fromB64(b64) {
  if (!b64) return null;
  const s = atob(b64), out = new Float32Array(s.length);
  for (let i = 0; i < s.length; i++) out[i] = s.charCodeAt(i) / 255;
  return out;
}

/* The proof renders' grey sprite: a row per word, columns all, early, middle, late. rgba is the sprite's ImageData.data. */
export function fromSprite(rgba, spriteW, words, mh, mw) {
  const out = [];
  for (let r = 0; r < words; r++) {
    const row = [];
    for (let c = 0; c < 4; c++) {
      const m = new Float32Array(mh * mw);
      for (let y = 0; y < mh; y++) for (let x = 0; x < mw; x++) m[y * mw + x] = rgba[4 * ((r * mh + y) * spriteW + c * mw + x)] / 255;
      row.push(m);
    }
    out.push(row);
  }
  return out;
}

/* The value at (u, v) in 0..1 picture coordinates, bilinear between cell centres, as the node's upsampling does. */
export function sample(m, mh, mw, u, v) {
  const fx = Math.max(0, Math.min(mw - 1, u * mw - 0.5)), fy = Math.max(0, Math.min(mh - 1, v * mh - 0.5));
  const x0 = Math.floor(fx), y0 = Math.floor(fy), x1 = Math.min(mw - 1, x0 + 1), y1 = Math.min(mh - 1, y0 + 1), tx = fx - x0, ty = fy - y0;
  const a = m[y0 * mw + x0] * (1 - tx) + m[y0 * mw + x1] * tx, b = m[y1 * mw + x0] * (1 - tx) + m[y1 * mw + x1] * tx;
  return a * (1 - ty) + b * ty;
}

/* Which cell a point on the shown picture falls in. */
export function cellAt(px, py, shownW, shownH, mh, mw) {
  return [Math.max(0, Math.min(mh - 1, Math.floor(py / shownH * mh))), Math.max(0, Math.min(mw - 1, Math.floor(px / shownW * mw)))];
}

/* At one cell, each word's real attention over all steps, largest first. -> [{i, v}]. Phase maps carry no floor, so this always reads the overall map. */
export function ranked(words, cell, mw) {
  const k = cell[0] * mw + cell[1];
  return words.map((w, i) => { const f = w.floor || 0; return { i, v: f + (w.maps[0] ? w.maps[0][k] : 0) * (w.peak - f) }; }).sort((a, b) => b.v - a.v);
}

/* Paint the picture dimmed where the word did not look and coloured where it did. base and out are RGBA arrays of W × H. map null: the plain picture. */
export function paint(base, out, W, H, m, mh, mw, alpha = 0.6) {
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const p = 4 * (y * W + x);
    if (!m) { out[p] = base[p]; out[p + 1] = base[p + 1]; out[p + 2] = base[p + 2]; out[p + 3] = 255; continue; }
    const v = sample(m, mh, mw, (x + 0.5) / W, (y + 0.5) / H), a = alpha * v, dim = 0.3 + 0.7 * v, c = ramp(v);
    for (let k = 0; k < 3; k++) out[p + k] = Math.round(Math.max(0, Math.min(255, base[p + k] * dim * (1 - a) + 255 * c[k] * a)));
    out[p + 3] = 255;
  }
  return out;
}

/* One phase index from its key. */
export const phaseIndex = (k) => Math.max(0, PHASES.findIndex(([x]) => x === k));

/* A plain sentence for a colour check. */
export function checkLine(c, high, low) {
  if (c.attention_inside == null) return `${c.word}: ${c.why || "not checked"}`;
  const pct = (x) => (x * 100).toFixed(0) + "%";
  const want = c.expect === "high" ? `at least ${high}× as dense there` : `less dense there than on average (under ${low}×)`;
  return `${pct(c.attention_inside)} of “${c.word}” falls on ${c.region} pixels, which cover ${pct(c.picture_share)} of the picture: ${c.lift}× as dense. Expected ${want}.` + (c.lift_above_floor != null ? ` Above the word's floor: ${pct(c.above_floor_inside)}, ${c.lift_above_floor}×.` : "");
}

/* Words of a live result (base64 maps) or a proof render (sprite rows) as one shape for the viewer. */
export function liveWords(maps, skipPunct = true) {
  return (maps.words || []).filter((w) => !(skipPunct && w.punct)).map((w) => ({ word: w.word, share: w.share, floor: w.floor || 0, peak: w.peak, maps: [fromB64(w.map), ...(w.phases || []).map(fromB64)] }));
}
export function spriteWords(render, rows) {
  return render.words.map((w, i) => ({ word: w.word, share: w.share, floor: w.floor || 0, peak: w.peak, maps: rows[i] }));
}

/* Share as a short percent: small shares keep a decimal. */
export const pct = (x) => (x == null ? "" : x * 100 >= 10 ? (x * 100).toFixed(0) + "%" : (x * 100).toFixed(1) + "%");
