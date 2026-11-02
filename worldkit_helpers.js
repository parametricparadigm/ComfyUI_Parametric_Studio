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
           failed_step: failed ? failed.name : "", lost_motions: lostMotions(meta.build) };
}

// Clips whose optional motion or fit failed, once the build has ended (steps.lost_motions on the server).
export function lostMotions(build) {
  if (!build || !["done", "failed"].includes(build.state)) return [];
  return (build.steps || []).filter((r) => /^(motion|retarget)_/.test(r.name) && r.status === "failed").map((r) => r.name.replace(/^[a-z]+_/, ""));
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
  return st.rig === "failed" && (st.remesh === "done" || st.flat === "done" || st.mesh === "done");
}

export const parseTags = (s) => String(s || "").split(",").map((t) => t.trim().toLowerCase()).filter(Boolean).slice(0, 12);

// The mesh models a prop can use, for a picture or for words, from /api/3d/models. Only what can run now; "" lets the studio pick.
export function meshChoices(models, via) {
  const job = via === "text" ? ["mesh_from_text", "mesh_from_image"] : ["mesh_from_image"];
  return (models || []).filter((m) => m.ready && job.includes(m.job)).map((m) => ({ id: m.id, label: m.label + (m.job === "mesh_from_text" ? " (words straight to a mesh)" : "") }));
}

export function createPayload(type, form) {
  const out = { type, name: String(form.name || "").trim(), tags: parseTags(form.tags), source: {} };
  if (type === "character") {
    out.source = { character_id: form.characterId };
    const recipe = {}, h = parseFloat(form.height);
    if (h > 0) recipe.height_m = h;
    if (form.clips) recipe.clips = cleanClips(form.clips);
    if (Object.keys(recipe).length) out.recipe = recipe;
  }
  else if (type === "prop") {
    const via = form.via || "mesh";
    out.source = via === "mesh" ? { mesh: form.mesh } : via === "image" ? { image: form.image } : { prompt: String(form.prompt || "").trim() };
    const size = parseFloat(form.size);
    if (size > 0) out.recipe = { size_m: size };
    if (via !== "mesh" && form.meshModel) out.recipe = { ...(out.recipe || {}), mesh_model: form.meshModel };
  } else if (type === "place") {
    out.source = { brief: String(form.brief || "").trim() };
    const recipe = {};
    if (form.preset) recipe.look = { preset: form.preset, time: form.time || null, weather: form.weather || null };
    if (form.textures) recipe.textures = form.textures;
    if (Object.keys(recipe).length) out.recipe = recipe;
  } else out.source = { preset: form.preset || "day_clear", time: form.time || null, weather: form.weather || null };
  return out;
}

// The motions a new character starts with, as the server's own default. A clip's name is short lowercase letters; people type whatever they like and this keeps it legal.
export const MAX_CLIPS = 4;
export const START_CLIPS = [{ name: "idle", text: "a person stands relaxed in place, breathing, shifting weight slightly" }, { name: "walk", text: "a person walks forward at a relaxed pace" }, { name: "wave", text: "a person stands and waves with the right hand" }];
export const clipSlug = (s) => String(s || "").toLowerCase().replace(/[^a-z_]+/g, "_").replace(/^_+/, "").slice(0, 24);
export const cleanClips = (rows) => (rows || []).map((c) => ({ name: clipSlug(c.name).replace(/_+$/, ""), text: String(c.text || "").trim() })).filter((c) => c.name || c.text).slice(0, MAX_CLIPS);
export function clipProblem(rows) {
  const clips = cleanClips(rows);
  if (!clips.length) return "Give the character at least one motion.";
  if (clips.some((c) => !c.name)) return "Each motion needs a short name.";
  if (clips.some((c) => !c.text)) return `Say what happens in "${clips.find((c) => !c.text).name}".`;
  if (new Set(clips.map((c) => c.name)).size !== clips.length) return "Two motions have the same name.";
  return "";
}
// Invented people to start from, so a blank box is not the first thing someone has to solve. Every word still goes through the same checks.
export const CHARACTER_IDEAS = [
  ["Night-market cook", "a stocky night-market cook in his fifties with a greying moustache and laughing eyes, wearing a green apron over a white shirt, dark trousers and work shoes"],
  ["Lighthouse keeper", "a tall lighthouse keeper in her forties with short silver-streaked black hair, wearing a rust-orange canvas work jacket, dark wool trousers and brown leather boots"],
  ["Desert courier", "a lean desert courier in his thirties with a short beard and sun-worn skin, wearing a long sand-coloured coat, a scarf, cargo trousers and scuffed boots"],
  ["Stage magician", "a graceful stage magician in her sixties with a silver bob and red lipstick, wearing a tailored midnight-blue suit, a white shirt and polished shoes"],
];
// What a built character still gets wrong, said on the page. Each line was seen on our own test characters.
export const CHARACTER_ROUGH = ["The back and sides are the model's guess: only the front comes from the sheet.", "Clothes can pull when it moves: trouser legs that stay joined near the ankles, sleeves folding, hands going through a coat.", "Feet stay flat and only turn: no heel-to-toe in a walk.", "A motion may not be exactly what the words said, and if the graphics card is full one can fail: the build goes on without it, and the making steps show which.", "The age in a sheet can differ from the age you asked for.", "In a Virtual Set video the words dress the character: the face and some colours will not match the sheet."];
export function sheetState(c) {
  if (!c) return { cls: "dim", label: "" };
  if (c.running || c.status === "building") return { cls: "warn", label: "making the sheet" };
  if (c.status === "ready" && c.ok) return { cls: "ok", label: "sheet passed" };
  if (c.status === "blocked") return { cls: "danger", label: "did not pass" };
  if (c.status === "failed") return { cls: "danger", label: "could not be made" };
  if (c.status === "interrupted") return { cls: "warn", label: "interrupted" };
  return { cls: "dim", label: c.status || "words saved" };
}
export const sheetUrl = (id, take = 0) => `/api/worldkit/characters/${encodeURIComponent(id)}/sheet?take=${take}`;

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
  if (key === "character" && caps.characters_on === false) return { ...row, cls: "off", state: "Off on this machine", why: problems[0] || "", more: problems.slice(1) };
  const gone = (r.needs || []).filter((n) => n.state === "missing").map((n) => n.label);
  if (gone.length) return { ...row, cls: "off", state: "Model not on this machine", why: `Still needs ${gone.join(" and ")}.`, more: problems };
  return { ...row, cls: "warn", state: "Not ready", why: problems[0] || "", more: problems.slice(1) };
}
export const makerBoard = (caps) => MAKERS.map((m) => makerRow(caps, m));

// Step names on disk, in words. An unknown step keeps its own name, with spaces.
const STEP_WORDS = { tiles: "Lay out the set", build: "Build the 3D file", preview: "Film a turntable", ingest: "Check and shelve it", image: "Make a picture", cutout: "Cut out the object", mesh: "Picture to mesh", cleanup: "Clean up, set real scale", remesh: "Remesh", rig: "Rig", clips: "Motion clips", retarget: "Fit the motion", sheet: "Check the sheet", flat: "Bake the pose", assemble: "Put it together" };
export function stepLabel(name) {
  const n = String(name || "");
  if (n.startsWith("motion_")) return `Make motion: ${n.slice(7).replace(/_/g, " ")}`;
  if (n.startsWith("retarget_")) return `Fit to the rig: ${n.slice(9).replace(/_/g, " ")}`;
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
