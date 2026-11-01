// Pure helpers for the World Kit page (no browser, no preact: node tests import this file).
export const TYPES = ["place", "prop", "look", "character"];
export const TYPE_LABELS = { character: "Character", prop: "Prop or vehicle", place: "Place", look: "Look" };
export const PROP_SOURCES = [["mesh", "A 3D result from this studio"], ["image", "A picture"], ["text", "Words"]];
const STEP_CLS = { done: "ok", skipped: "dim", running: "warn", failed: "danger", pending: "dim" };

export const exportUrl = (zip) => `/api/worldkit/exports/${encodeURIComponent(zip)}`;
export const fileUrl = (id, name) => `/api/worldkit/assets/${encodeURIComponent(id)}/file/${name}`;

export function statusChip(a) {
  if (a.running) return { cls: "dim", label: `building ${a.progress[0]}/${a.progress[1]}` };
  if (a.build === "failed") return { cls: "danger", label: `failed at ${a.failed_step || "a step"}` };
  if (a.build === "building") return { cls: "warn", label: "interrupted, press Retry" };
  if (a.build !== "done") return { cls: "dim", label: "not built" };
  return a.status === "approved" ? { cls: "ok", label: "approved" } : { cls: "warn", label: "draft, review and approve" };
}

// The list summary's fields from a full meta (GET /api/worldkit/assets/<id>), for the detail view's chip and buttons.
export function summaryOf(meta) {
  const steps = (meta.build && meta.build.steps) || [];
  const failed = steps.find((r) => r.status === "failed" && !String(r.note || "").includes("optional"));
  return { build: (meta.build && meta.build.state) || "pending", status: meta.status, running: !!meta.running,
           progress: [steps.filter((r) => r.status === "done" || r.status === "skipped").length, steps.length],
           failed_step: failed ? failed.name : "" };
}

export function filterAssets(list, { type = "", q = "", status = "" } = {}) {
  const words = String(q).toLowerCase().split(/\s+/).filter(Boolean);
  return (list || []).filter((a) => (!type || a.type === type) && (!status || a.status === status)
    && words.every((w) => [a.name, a.type, ...(a.tags || [])].join(" ").toLowerCase().includes(w)));
}

export const canApprove = (a) => !!a && a.build === "done" && a.status !== "approved" && !a.running;
export const canRetry = (a) => !!a && !a.running && (a.build === "failed" || a.build === "building");

export function canMakeProp(meta) {
  if (!meta || meta.type !== "character" || meta.running) return false;
  const st = Object.fromEntries(((meta.build && meta.build.steps) || []).map((r) => [r.name, r.status]));
  return st.rig === "failed" && (st.remesh === "done" || st.mesh === "done");
}

export const parseTags = (s) => String(s || "").split(",").map((t) => t.trim().toLowerCase()).filter(Boolean).slice(0, 12);

export function createPayload(type, form) {
  const out = { type, name: String(form.name || "").trim(), tags: parseTags(form.tags), source: {} };
  if (type === "character") out.source = { character_id: form.characterId };
  else if (type === "prop") {
    const via = form.via || "mesh";
    out.source = via === "mesh" ? { mesh: form.mesh } : via === "image" ? { image: form.image } : { prompt: String(form.prompt || "").trim() };
    const size = parseFloat(form.size);
    if (size > 0) out.recipe = { size_m: size };
  } else if (type === "place") {
    out.source = { brief: String(form.brief || "").trim() };
    const recipe = {};
    if (form.preset) recipe.look = { preset: form.preset, time: form.time || null, weather: form.weather || null };
    if (form.textures) recipe.textures = form.textures;
    if (Object.keys(recipe).length) out.recipe = recipe;
  } else out.source = { preset: form.preset || "day_clear", time: form.time || null, weather: form.weather || null };
  return out;
}

export const stepRows = (meta) => ((meta && meta.build && meta.build.steps) || []).map((r) => ({
  name: r.name, status: r.status, cls: STEP_CLS[r.status] || "dim", error: r.error || "", note: r.note || "" }));

export function addClip(clips, name, text) {
  return [...(clips || []).filter((c) => c.name !== name), { name, text }].slice(-4);
}

// Which capability route a form uses, and what stands in its way: the server's own plain sentences.
export function routeFor(type, via) {
  return type === "prop" ? `prop_${via || "mesh"}` : type;
}
export function blockers(caps, type, via) {
  const r = caps && caps.makers && caps.makers[routeFor(type, via)];
  return r && !r.ready ? r.problems || [] : [];
}

// The workshop board: one row per maker, with the server's own sentence for why one cannot run.
export const MAKERS = [["place", "Place", "place", ""], ["look", "Look", "look", ""], ["prop_mesh", "Prop from a 3D result", "prop", "mesh"], ["prop_image", "Prop from a picture", "prop", "image"], ["prop_text", "Prop from words", "prop", "text"], ["character", "Character", "character", ""]];
export function makerRow(caps, [key, label, type, via]) {
  const r = caps && caps.makers && caps.makers[key];
  const row = { key, label, type, via };
  if (!r) return { ...row, cls: "dim", state: "Checking", why: "", more: [] };
  if (r.ready) return { ...row, cls: "ok", state: "Ready", why: "", more: [] };
  const problems = r.problems || [];
  if (key === "character") return { ...row, cls: "off", state: "Off", why: problems[0] || "", more: problems.slice(1) };
  const gone = (r.needs || []).filter((n) => n.state === "missing").map((n) => n.label);
  if (gone.length) return { ...row, cls: "off", state: "Model not on this machine", why: `Still needs ${gone.join(" and ")}.`, more: problems };
  return { ...row, cls: "warn", state: "Not ready", why: problems[0] || "", more: problems.slice(1) };
}
export const makerBoard = (caps) => MAKERS.map((m) => makerRow(caps, m));

// Step names on disk, in words. An unknown step keeps its own name, with spaces.
const STEP_WORDS = { tiles: "Lay out the set", build: "Build the 3D file", preview: "Film a turntable", ingest: "Check and shelve it", image: "Make a picture", cutout: "Cut out the object", mesh: "Picture to mesh", cleanup: "Clean up, set real scale", remesh: "Remesh", rig: "Rig", clips: "Motion clips", retarget: "Fit the motion" };
export function stepLabel(name) {
  const n = String(name || "");
  if (n.startsWith("tex_")) return `${n.slice(4).replace(/\d+$/, (d) => " " + d).replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase())} texture`;
  return STEP_WORDS[n] || n.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());
}
export const stepDone = (rows) => rows.filter((r) => r.status === "done" || r.status === "skipped").length;

// The real-scale badge's ruler: the asset's longest side against a 1.8 m person, both as parts of the longer one.
export function scaleCompare(scale_m, person = 1.8) {
  const s = Number(scale_m);
  if (!(s > 0)) return null;
  const top = Math.max(s, person);
  return { asset: s / top, person: person / top, text: s >= 10 ? `${Math.round(s * 10) / 10} m` : `${Math.round(s * 100) / 100} m` };
}

// The shop's flow, from what the library holds.
export function shopCounts(list) {
  const a = list || [];
  return { total: a.length, building: a.filter((x) => x.running).length, review: a.filter((x) => canApprove(x)).length, approved: a.filter((x) => x.status === "approved").length };
}
// What the page opens on: the asset a link asked for, or the newest finished one with something to look at.
export function firstAsset(list) {
  const a = list || [];
  return a.find((x) => x.status === "approved" && (x.files || []).includes("asset.glb")) || a.find((x) => (x.files || []).includes("asset.glb")) || a[0] || null;
}
export const nextStep = (sum) => {
  if (!sum) return "";
  if (sum.running) return "Building. It can be approved when every step has finished.";
  if (sum.build === "failed" || sum.build === "building") return "This build stopped. Press Retry to pick up from the failed step.";
  if (sum.build !== "done") return "Not built yet.";
  return sum.status === "approved" ? "Approved. It can go into Virtual Set shots and game packs." : "Look it over in the viewer and the turntable, then approve it. Only approved assets reach Virtual Set and game packs.";
};
