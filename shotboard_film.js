// Shot Board's small reckonings, kept apart from the page so plain node tests can run them. Everything here reads numbers the studio really has.
export const clock = (seconds) => {
  const s = Math.max(0, Math.round(seconds || 0)), h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), x = String(s % 60).padStart(2, "0");
  return h ? `${h}:${String(m).padStart(2, "0")}:${x}` : `${m}:${x}`;
};
export const elapsed = (j, now) => (j.seconds != null ? j.seconds : j.started ? Math.round((now - j.started) / 1000) : 0);
export const totalSeconds = (jobs, now) => jobs.reduce((sum, j) => sum + (j.status === "done" || j.status === "running" ? elapsed(j, now) : 0), 0);
export const isStopped = (status) => ["error", "lost", "cancelled"].includes(status);
const WORDS = { queued: "In line", running: "Rendering", done: "Done", error: "Failed", lost: "Lost", cancelled: "Cancelled" };
export const stateWord = (status) => WORDS[status] || status;

/** One answer from /api/live, for one job. null: nothing is running. waiting: ComfyUI is busy with something else. No total: ComfyUI gave no node detail, so the page shows elapsed time alone. */
export function readLive(r, job, graphSize = 0) {
  if (!r || !r.running) return null;
  if (r.job !== job) return { waiting: true, pending: r.pending || 0 };
  if (r.mode !== "nodes") return { total: 0, preview: r.preview || 0 };
  const n = r.nodes || {}, running = Object.entries(n.running || {}), done = (n.done || []).length, cached = (n.cached || []).length;
  const [node, step] = running.find(([, s]) => s && s[1] > 0) || running[0] || [null, null];
  return { total: Math.max(graphSize, done + cached + running.length), done, cached, running: running.length, node, value: step ? step[0] : 0, max: step ? step[1] : 0, preview: r.preview || 0 };
}

/** One perforation per node of the running graph, in the order: ran, reused from cache, running, still to run. */
export function perforations(live) {
  if (!live || !live.total) return [];
  const { total, done, cached, running } = live, out = [];
  for (let i = 0; i < total; i++) out.push(i < done ? "ran" : i < done + cached ? "cached" : i < done + cached + running ? "now" : "todo");
  return out;
}

export const nodeName = (graph, id) => { const n = graph && id != null ? graph[id] : null; return n ? (n._meta && n._meta.title) || n.class_type || String(id) : ""; };
export const scrubTime = (x, left, width, duration) => (width > 0 && duration > 0 ? Math.max(0, Math.min(1, (x - left) / width)) * duration : 0);

/** A small left-to-right map of an API-format graph: each node sits one column after the deepest node it reads from. */
export function miniGraph(graph) {
  const ids = Object.keys(graph || {}).filter((k) => graph[k] && graph[k].class_type);
  const from = (id) => Object.values(graph[id].inputs || {}).filter((v) => Array.isArray(v) && v.length === 2 && graph[v[0]]).map((v) => String(v[0]));
  const depth = {}, walking = new Set();
  const dig = (id) => { if (depth[id] != null) return depth[id]; if (walking.has(id)) return 0; walking.add(id); const d = from(id).reduce((m, p) => Math.max(m, dig(p) + 1), 0); walking.delete(id); return (depth[id] = d); };
  ids.forEach(dig);
  const cols = {}; ids.forEach((id) => (cols[depth[id]] = cols[depth[id]] || []).push(id));
  const at = {}, width = Object.keys(cols).length, height = Math.max(1, ...Object.values(cols).map((c) => c.length));
  Object.entries(cols).forEach(([x, col]) => col.forEach((id, i) => (at[id] = { id, x: +x, y: i + (height - col.length) / 2, cls: graph[id].class_type })));
  return { width, height, nodes: Object.values(at), links: ids.flatMap((id) => from(id).filter((p) => at[p]).map((p) => [at[p].x, at[p].y, at[id].x, at[id].y])) };
}
