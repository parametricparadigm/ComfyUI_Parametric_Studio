/* Camera Paths: the numbers behind the page, kept apart from the drawing so they read on their own.
   Units and axes match psn_nodes/camera_path.py: x right, y down, z forward from the first frame; the subject sits SUBJECT units ahead. */
export const SUBJECT = 4;
export const RADIUS = 4;
export const MAX_KEYS = 8;

/* A point on the globe around the subject. round: degrees around to the camera's right; up: degrees above the starting height. */
export function globePos(round, up, r = RADIUS) {
  const a = (round * Math.PI) / 180, e = (up * Math.PI) / 180;
  const k = (v) => Math.round(v * 10000) / 10000;
  return [k(r * Math.sin(a) * Math.cos(e)), k(-r * Math.sin(e)), k(SUBJECT - r * Math.cos(a) * Math.cos(e))];
}

/* The other way: a position on (or near) the globe -> {round, up} in whole degrees. */
export function globeAngles(pos) {
  const [x, y, z] = pos, dz = SUBJECT - z, flat = Math.hypot(x, dz);
  return { round: Math.round((Math.atan2(x, dz) * 180) / Math.PI), up: Math.round((Math.atan2(-y, flat) * 180) / Math.PI) };
}

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
export const tidyKey = (k) => ({ round: clamp(Math.round(Number(k.round) || 0), -170, 170), up: clamp(Math.round(Number(k.up) || 0), -10, 70) });

/* Globe keys -> the path JSON the node and the server take. The first key is always where the shot starts. */
export function globePath(keys) {
  const ks = keys.map(tidyKey);
  return { keys: ks.map((k, i) => ({ t: ks.length > 1 ? Math.round((i / (ks.length - 1)) * 1000) / 1000 : 0, pos: globePos(k.round, k.up) })), look_at: [0, 0, SUBJECT] };
}

/* A preset path from the server, as globe keys when it is one (it looks at the subject), else null. */
export function presetKeys(path) {
  if (!path || !Array.isArray(path.look_at) || path.look_at[2] !== SUBJECT) return null;
  const ks = path.keys.map((k) => globeAngles(k.pos));
  return ks.every((k, i) => Math.abs(Math.hypot(path.keys[i].pos[0], path.keys[i].pos[1], SUBJECT - path.keys[i].pos[2]) - RADIUS) < 0.05) ? ks : null;
}

/* A new key after the last one, a little further round. */
export function addKey(keys) {
  if (keys.length >= MAX_KEYS) return keys;
  const last = keys[keys.length - 1] || { round: 0, up: 0 };
  return [...keys, tidyKey({ round: last.round + 15, up: last.up })];
}

export function removeKey(keys, i) { return keys.length <= 2 || i === 0 ? keys : keys.filter((_, j) => j !== i); }

/* Node axes -> three.js axes (y up, looking down -z). */
export const toThree = ([x, y, z]) => [x, -y, -z];

/* A drawn line (pointer positions in the box) -> points in 0..1, thinned so neighbours are at least `gap` apart. */
export function thin(points, gap = 0.01) {
  const out = [];
  for (const p of points) {
    const q = [clamp(p[0], 0, 1), clamp(p[1], 0, 1)];
    if (!out.length || Math.hypot(q[0] - out[out.length - 1][0], q[1] - out[out.length - 1][1]) >= gap) out.push(q);
  }
  return out.map(([a, b]) => [Math.round(a * 10000) / 10000, Math.round(b * 10000) / 10000]);
}

export const lineLength = (pts) => pts.reduce((s, p, i) => (i ? s + Math.hypot(p[0] - pts[i - 1][0], p[1] - pts[i - 1][1]) : 0), 0);

/* Ready-made object lines for when drawing by hand is not an option (keyboard, screen reader). */
export const LINE_PRESETS = {
  left_to_right: { label: "Left to right", pts: [[0.15, 0.7], [0.5, 0.62], [0.85, 0.7]] },
  right_to_left: { label: "Right to left", pts: [[0.85, 0.7], [0.5, 0.62], [0.15, 0.7]] },
  rise: { label: "Up and over", pts: [[0.2, 0.8], [0.5, 0.3], [0.8, 0.8]] },
  toward: { label: "Towards the camera", pts: [[0.5, 0.45], [0.5, 0.6], [0.5, 0.85]] },
};

export const VERDICT_CLASS = { MATCH: "ok", MISMATCH: "bad", INCONCLUSIVE: "warn" };
export const verdictWord = (v) => ({ MATCH: "Match", MISMATCH: "Mismatch", INCONCLUSIVE: "Not enough to tell" }[v] || v);
export const moveWord = (m) => String(m || "").replace(/_/g, " ");

/* Counts for the proof's confusion table: requested move x verdict, inconclusive kept apart. */
export function confusion(rows) {
  const t = {};
  for (const r of rows || []) { t[r.requested] = t[r.requested] || { MATCH: 0, MISMATCH: 0, INCONCLUSIVE: 0 }; t[r.requested][r.verdict] += 1; }
  return t;
}
