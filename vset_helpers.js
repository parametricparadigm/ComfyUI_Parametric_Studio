// Pure helpers for the Virtual Set page (no browser, no preact: node tests import this file). The server (studio/vset/shot.py problems, needs.py) is the authority on every limit; these only give instant feedback.
export const PRESET_LABELS = { push_in: "Slow push-in", orbit: "Orbit", walk_along: "Tracking alongside", pov: "Point of view", handheld: "Handheld", static: "Static", custom: "Custom path" };
export const MODE_NAMES = { A: "A: guide passes", B: "B: restyle", C: "C: keyframes", D: "D: motion copy" };
export const fileUrl = (id, name) => `/api/vset/shots/${encodeURIComponent(id)}/file/${name}`;
export const glbUrl = (id) => `/api/worldkit/assets/${encodeURIComponent(id)}/file/asset.glb`;

export function blankForm() {
  return { id: "", name: "", place: "", props: [], marks: "0,0", cast: [], preset: "push_in", params: {}, lens: "", startPos: "", startLook: "", endPos: "", endLook: "", easing: "ease_in_out",
           aspect: "16:9", seconds: "5", look: "day_clear", time: "", weather: "", lookAsset: "", mode: "C", control: "depth", engine: "h3", keyframes: "qwen", seed: "4242", prompt: "" };
}

export function parseMarks(text) {
  const pts = String(text || "").split(/[;\n]/).map((s) => s.trim()).filter(Boolean).map((s) => s.split(/[,\s]+/).map(Number));
  if (!pts.length || pts.some((p) => p.length !== 2 || p.some((v) => !Number.isFinite(v)))) return null;
  return pts.slice(0, 8);
}
export const marksText = (marks) => (marks || []).map(([x, y]) => `${x},${y}`).join("; ");

export function parseVec3(text) {
  const p = String(text || "").split(/[,\s]+/).filter(Boolean).map(Number);
  return p.length === 3 && p.every((v) => Number.isFinite(v)) ? p : null;
}
const vec3Text = (v) => (v ? v.join(",") : "");

export function numericParams(params) {
  const out = {};
  for (const [k, v] of Object.entries(params || {})) {
    if (v === "" || v === null || v === undefined) continue;
    out[k] = k === "easing" ? v : Number(v);
  }
  return out;
}

export function modeSettings(form) {
  if (form.mode === "A" && form.engine === "ltx") return { engine: "ltx", keyframes: form.keyframes };
  if (form.mode === "A") return { control: form.control, engine: form.engine };
  if (form.mode === "C") return { keyframes: form.keyframes };
  return {};
}

export function buildShot(form) {
  const lens = parseFloat(form.lens);
  const camera = form.preset === "custom"
    ? { preset: "custom", ...(lens > 0 ? { lens_mm: lens } : {}), path: { start: { pos: parseVec3(form.startPos), look: parseVec3(form.startLook) }, end: { pos: parseVec3(form.endPos), look: parseVec3(form.endLook) }, easing: form.easing } }
    : { preset: form.preset, params: numericParams(form.params), ...(lens > 0 ? { lens_mm: lens } : {}) };
  const look = form.lookAsset ? { asset: form.lookAsset } : { preset: form.look, time: form.time || null, weather: form.weather || null };
  return { ...(form.id ? { id: form.id } : {}), name: form.name || "",
    set: { place: form.place, props: (form.props || []).filter((p) => p.asset).map((p) => ({ asset: p.asset, pos: [Number(p.x) || 0, Number(p.y) || 0, 0], rot_deg: [0, 0, Number(p.yaw) || 0], scale: Number(p.scale) || 1 })) },
    cast: (form.cast || []).filter((c) => c.asset).map((c) => ({ asset: c.asset, clip: c.clip, marks: parseMarks(c.marks) || [[0, 0]] })), marks: parseMarks(form.marks) || [[0, 0]],
    camera, format: { aspect: form.aspect, seconds: Number(form.seconds) }, look, mode: form.mode, mode_settings: modeSettings(form), seed: Number(form.seed) || 0, prompt: form.prompt || "" };
}

export function formFromShot(shot) {
  const cam = shot.camera || {}, ms = shot.mode_settings || {}, look = shot.look || {}, path = cam.path || {};
  return { ...blankForm(), id: shot.id || "", name: shot.name || "", place: shot.set.place,
    props: (shot.set.props || []).map((p) => ({ asset: p.asset, x: String(p.pos[0]), y: String(p.pos[1]), yaw: String((p.rot_deg || [0, 0, 0])[2]), scale: String(p.scale ?? 1) })),
    cast: (shot.cast || []).map((c) => ({ asset: c.asset, clip: c.clip, marks: marksText(c.marks) })), marks: marksText(shot.marks) || "0,0",
    preset: cam.preset, params: { ...(cam.params || {}) }, lens: cam.lens_mm ? String(cam.lens_mm) : "",
    startPos: vec3Text(path.start && path.start.pos), startLook: vec3Text(path.start && path.start.look), endPos: vec3Text(path.end && path.end.pos), endLook: vec3Text(path.end && path.end.look), easing: path.easing || "ease_in_out",
    aspect: shot.format.aspect, seconds: String(shot.format.seconds), look: look.preset || "day_clear", time: look.time || "", weather: look.weather || "", lookAsset: look.asset || "",
    mode: shot.mode, control: ms.control || "depth", engine: ms.engine || "h3", keyframes: ms.keyframes || "qwen", seed: String(shot.seed), prompt: shot.prompt || "" };
}

// Which route in /api/vset/capabilities a form uses.
export function routeName(form) {
  if (form.mode === "A" && form.engine === "wan") return "A_wan";
  if (form.mode === "A" && form.engine === "ltx") return form.keyframes === "raw" ? "A_ltx_raw" : "A_ltx";
  if (form.mode === "C" && form.keyframes === "raw") return "C_raw";
  return form.mode;
}
export function blockers(caps, form) {
  if (!caps) return [];
  const r = caps.routes && caps.routes[routeName(form)];
  return [...(caps.blender ? [caps.blender] : []), ...(r && !r.ready ? r.problems || [] : [])];
}
export function formatProblem(meta, form) {
  const spec = meta && meta.modes && (form.mode === "A" && form.engine === "wan" ? { ...meta.modes.A, ...meta.wan } : form.mode === "A" && form.engine === "ltx" ? { ...meta.modes.A, ...meta.ltx } : meta.modes[form.mode]);
  if (!spec) return "";
  if (!spec.aspects.includes(form.aspect)) return `this mode renders ${spec.aspects.join(", ")} only`;
  if (!spec.seconds.includes(Number(form.seconds))) return `this mode renders ${spec.seconds.join(", ")} s`;
  return "";
}
export function poseProblem(form) {
  return form.mode === "A" && form.control === "pose" && !(form.cast || []).some((c) => c.asset) ? "A pose pass draws the cast, and this shot has none. Use the depth pass." : "";
}

export function stateChip(sum) {
  if (!sum) return { cls: "dim", label: "new" };
  if (sum.running) return { cls: "warn", label: sum.progress && sum.progress[1] ? `rendering ${sum.progress[0]}/${sum.progress[1]}` : "rendering" };
  if (sum.state === "building") return { cls: "warn", label: "interrupted, press Retry" };
  if (sum.state === "done" && sum.scope === "passes") return { cls: "ok", label: "passes ready" };
  return ({ done: { cls: "ok", label: "done" }, review: { cls: "warn", label: "needs review" }, failed: { cls: "danger", label: sum.failed_step ? `failed at ${sum.failed_step}` : "failed" }, new: { cls: "dim", label: "not rendered" } })[sum.state] || { cls: "dim", label: String(sum.state) };
}
export const canRetry = (sum) => !!sum && !sum.running && ["failed", "review", "building"].includes(sum.state);

export function qcText(qc) {
  if (!qc) return "";
  const parts = [];
  if (qc.face !== null && qc.face !== undefined) parts.push(`face ${Number(qc.face).toFixed(2)}`);
  if (qc.flicker !== null && qc.flicker !== undefined) parts.push(`flicker ${Number(qc.flicker).toFixed(1)}`);
  if (qc.layout !== null && qc.layout !== undefined) parts.push(`layout ${Number(qc.layout).toFixed(2)}`);
  if (qc.reasons && qc.reasons.length) parts.push(qc.reasons.join("; "));
  return parts.join(", ");
}

export function moveItem(list, from, to) {
  const out = [...list];
  const [x] = out.splice(from, 1);
  out.splice(Math.max(0, Math.min(to, out.length)), 0, x);
  return out;
}

// The plan view of a camera move: metres to an SVG box, north (+Y) up. Returns point strings and a mapper, so the page only draws.
export function planView(preview, width = 420, height = 280, pad = 16) {
  if (!preview || !preview.keys || !preview.keys.length) return null;
  const xs = [], ys = [];
  const add = (x, y) => { xs.push(x); ys.push(y); };
  if (preview.bounds) { add(preview.bounds.lo[0], preview.bounds.lo[1]); add(preview.bounds.hi[0], preview.bounds.hi[1]); }
  for (const k of preview.keys) { add(k.pos[0], k.pos[1]); add(k.look[0], k.look[1]); }
  for (const p of preview.subject || []) add(p[0], p[1]);
  const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
  const scale = Math.min((width - 2 * pad) / Math.max(x1 - x0, 1e-3), (height - 2 * pad) / Math.max(y1 - y0, 1e-3));
  const ox = (width - scale * (x1 - x0)) / 2, oy = (height - scale * (y1 - y0)) / 2;
  const at = (x, y) => [ox + (x - x0) * scale, height - oy - (y - y0) * scale];
  const line = (pts) => pts.map(([x, y]) => at(x, y).map((v) => v.toFixed(1)).join(",")).join(" ");
  const box = preview.bounds ? (() => { const [a, b] = at(preview.bounds.lo[0], preview.bounds.hi[1]), [c, d] = at(preview.bounds.hi[0], preview.bounds.lo[1]); return { x: a, y: b, w: c - a, h: d - b }; })() : null;
  return { at, box, camera: line(preview.keys.map((k) => k.pos)), subject: line(preview.subject || []), scale };
}

// What each mode's choices are in /api/vset/capabilities. The readiness and the proof always come from the server.
export const MODE_ROUTES = { A: [["A", "MiniMax H3"], ["A_wan", "Wan 2.2"], ["A_ltx", "LTX-2.5, Qwen stills"], ["A_ltx_raw", "LTX-2.5, Blender stills"]], B: [["B", "MiniMax H3"]], C: [["C", "Qwen stills"], ["C_raw", "Blender stills"]], D: [["D", "MiniMax H3"]] };

// "B: restyle (the shaded render, H3 follows its exact depth)" from the server, as a name and a plain line.
export function modeParts(key, label) {
  const m = /^[A-Z]:\s*([^(]+?)\s*(?:\((.*)\))?$/.exec(String(label || ""));
  const words = m ? m[2] || "" : "";
  return { name: m ? m[1] : (MODE_NAMES[key] || key).replace(/^[A-Z]:\s*/, ""), what: words && words[0].toUpperCase() + words.slice(1) };
}

// One route's honest state, from the server's own fields. Nothing here is decided by the page.
export function routeStatus(route) {
  if (!route) return { cls: "dim", label: "Status unknown", detail: "" };
  if (!route.ready) return { cls: "danger", label: "Model not on this machine", detail: (route.problems || []).join(" ") };
  const p = route.proof;
  if (!p) return { cls: "dim", label: "Ready, proof not reported", detail: "" };
  const times = (n) => (n > 1 ? ` (${n} shots)` : "");
  return ({ passed: { cls: "ok", label: `Rendered here, checks passed${times(p.passed)}` }, review: { cls: "warn", label: `Rendered here, flagged for review${times(p.review)}` }, running: { cls: "warn", label: "Test running now" }, failed: { cls: "danger", label: `Ready, but failed here${times(p.failed)}` } })[p.state] || { cls: "dim", label: "Ready, not yet rendered here" };
}
export const modeStatus = (caps, key) => (MODE_ROUTES[key] || []).map(([route, name]) => { const r = caps && caps.routes && caps.routes[route]; return { route, name, proofShot: (r && r.proof && r.proof.shot) || "", ...routeStatus(r) }; });

// A schematic of each camera move for its picker: start, path and where it looks, in a 48 x 32 box. A diagram, not a preview; the plan below is the real path.
export const MOVE_GLYPHS = { push_in: "M6 16H34", orbit: "M10 24A16 16 0 0 1 38 24", walk_along: "M6 24H42", pov: "M8 26L24 8", handheld: "M8 16l5-3 5 4 5-4 5 4 5-3", static: "", custom: "M6 26C16 4 30 30 42 8" };

// The camera's field of view on the plan: two edge lines from the camera toward what it looks at.
export function frustum([cx, cy], [lx, ly], lens = 35, sensor = 36, reach = 60) {
  const half = Math.atan(sensor / (2 * Math.max(lens, 1))), a = Math.atan2(ly - cy, lx - cx);
  const end = (t) => [cx + reach * Math.cos(t), cy + reach * Math.sin(t)].map((v) => Number(v.toFixed(1)));
  return [end(a - half), end(a + half)];
}

// Two clips running side by side drift; this says when to pull one back.
export const needsSync = (a, b, tolerance = 0.08) => Math.abs(a - b) > tolerance;
