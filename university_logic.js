/* ComfyUniversity page logic. Pure functions, no DOM: lesson parsing, progress, graph layout and a browser copy of ComfyUI's graph validation. tests/test_university_page.py runs these in node. */

/* ---------- progress, kept on this device ---------- */
export const PROGRESS_KEY = "cu.progress.v1";
export function loadProgress(store) { try { const s = store || globalThis.localStorage; const v = JSON.parse(s.getItem(PROGRESS_KEY) || "{}"); return v && typeof v === "object" && !Array.isArray(v) ? v : {}; } catch { return {}; } }
export function saveProgress(p, store) { try { (store || globalThis.localStorage).setItem(PROGRESS_KEY, JSON.stringify(p)); return true; } catch { return false; } }
export function markLesson(p, code, patch) { const c = p[code] || {}; const next = { ...c, ...patch, plays: { ...(c.plays || {}), ...(patch.plays || {}) } }; return { ...p, [code]: next }; }
export function lessonParts(course, entry) {
  const e = entry || {}, plays = (course.plays || []); const donePlays = plays.filter((x) => (e.plays || {})[x]).length; const quiz = !!e.quiz; const parts = [["read", !!e.read], ["quiz", quiz]]; if (plays.length) parts.push(["play", donePlays === plays.length]);
  return { parts, done: parts.every(([, v]) => v), plays: [donePlays, plays.length] };
}
export function trackProgress(codes, byCode, p) { let done = 0; for (const c of codes) if (byCode[c] && lessonParts(byCode[c], p[c]).done) done++; return { done, total: codes.length, pct: codes.length ? Math.round(100 * done / codes.length) : 0 }; }
export function nextLesson(tracks, byCode, p) { for (const t of tracks) for (const c of t.codes) if (byCode[c] && !lessonParts(byCode[c], p[c]).done) return { track: t, code: c }; return null; }
export function neighbours(code, track) { if (!track) return {}; const i = track.codes.indexOf(code); return { prev: i > 0 ? track.codes[i - 1] : null, next: i >= 0 && i < track.codes.length - 1 ? track.codes[i + 1] : null, at: i + 1, of: track.codes.length }; }
export function parseRoute(route) { const p = String(route || "").split("/"); if (p[1] === "track") return { view: "track", slug: p[2] || "" }; if (/^CU-\d{3}$/.test(p[1] || "")) return { view: "lesson", code: p[1] }; if (p[1] === "all") return { view: "all" }; return { view: "home" }; }

/* ---------- searching the catalogue ---------- */
export function filterCourses(courses, q, level = "all") { const w = String(q || "").toLowerCase().split(/\s+/).filter(Boolean); return courses.filter((c) => (level === "all" || c.level === level) && w.every((x) => (c.code + " " + c.title + " " + c.hook).toLowerCase().includes(x))); }

/* ---------- lesson markdown: a small, safe subset ---------- */
export const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
export function inline(t) {
  const code = []; let s = String(t).replace(/`([^`]+)`/g, (_, c) => { code.push(`<code>${esc(c)}</code>`); return `\u0001${code.length - 1}\u0001`; }); s = esc(s);
  s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>").replace(/\[([^\]]+)\]\((https?:[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>').replace(/\[([^\]]+)\]\((#[^)\s]+)\)/g, '<a href="$2">$1</a>');
  s = s.replace(/(^|[^-\w#/])(CU-\d{3})\b/g, '$1<a class="cu-ref" href="#university/$2">$2</a>');
  return s.replace(/\u0001(\d+)\u0001/g, (_, i) => code[+i]);
}
export const slug = (t) => String(t).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
const DIRECTIVE = /^\{\{(play|graph|wipe|video|audio):([^}]*)\}\}\s*$/;
function directive(kind, body) {
  if (kind === "play") { const [name, ...rest] = body.trim().split(/\s+/); const args = {}; for (const r of rest) { const [k, v] = r.split("="); args[k] = v; } return { t: "play", name, args }; }
  if (kind === "graph") return { t: "graph", id: body.trim() };
  const parts = body.split("|").map((x) => x.trim());
  if (kind === "wipe") return { t: "wipe", a: parts[0], b: parts[1], la: parts[2] || "", lb: parts[3] || "", caption: parts[4] || "" };
  if (kind === "video") return { t: kind, src: parts[0], caption: parts[1] || "", poster: parts[2] || "" };
  return { t: kind, src: parts[0], caption: parts[1] || "" };
}
export function lessonBlocks(body) {
  const out = []; const lines = String(body).split("\n"); let i = 0;
  const isSpecial = (l) => /^(#{3,4}\s|\s*[-*]\s|\s*\d+[.)]\s|>|\|.*\|\s*$|```|---+\s*$)/.test(l) || DIRECTIVE.test(l) || /^!\[/.test(l);
  while (i < lines.length) {
    const l = lines[i]; let m;
    if (!l.trim()) { i++; continue; }
    if ((m = l.match(/^```(\w*)\s*$/))) { const c = []; i++; while (i < lines.length && !/^```\s*$/.test(lines[i])) c.push(lines[i++]); i++; out.push({ t: "code", lang: m[1] || "", code: c.join("\n") }); continue; }
    if ((m = l.match(DIRECTIVE))) { out.push(directive(m[1], m[2])); i++; continue; }
    if ((m = l.match(/^!\[([^\]]*)\]\(([^)\s]+)\)\s*$/))) { out.push({ t: "img", src: m[2], caption: m[1] }); i++; continue; }
    if ((m = l.match(/^(#{3,4})\s+(.*)/))) { out.push({ t: "h", level: m[1].length, html: inline(m[2]) }); i++; continue; }
    if (/^\s*[-*]\s+/.test(l)) { const it = []; while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) it.push(inline(lines[i++].replace(/^\s*[-*]\s+/, ""))); out.push({ t: "ul", items: it }); continue; }
    if (/^\s*\d+[.)]\s+/.test(l)) { const it = []; while (i < lines.length && /^\s*\d+[.)]\s+/.test(lines[i])) it.push(inline(lines[i++].replace(/^\s*\d+[.)]\s+/, ""))); out.push({ t: "ol", items: it }); continue; }
    if (/^\|.*\|\s*$/.test(l) && /^\|[\s:|-]+\|\s*$/.test(lines[i + 1] || "")) { const cells = (r) => r.trim().replace(/^\||\|$/g, "").split("|").map((c) => inline(c.trim())); const head = cells(l); i += 2; const rows = []; while (i < lines.length && /^\|.*\|\s*$/.test(lines[i])) rows.push(cells(lines[i++])); out.push({ t: "table", head, rows }); continue; }
    if (/^>\s?/.test(l)) { const q = []; while (i < lines.length && /^>\s?/.test(lines[i])) q.push(lines[i++].replace(/^>\s?/, "")); out.push({ t: "quote", html: inline(q.join(" ")) }); continue; }
    if (/^---+\s*$/.test(l)) { out.push({ t: "hr" }); i++; continue; }
    const p = []; while (i < lines.length && lines[i].trim() && !isSpecial(lines[i])) p.push(lines[i++]); if (!p.length) { p.push(lines[i++]); } out.push({ t: "p", html: inline(p.join(" ")) });
  }
  return out;
}
export function parseLesson(md) {
  const text = String(md || ""); const first = text.split("\n", 1)[0]; let rest = text.slice(first.length + 1); const head = first.replace(/^#\s*/, ""); const hm = head.match(/^(CU-\d{3})\s*-\s*(.*)$/); const res = { code: hm ? hm[1] : "", title: hm ? hm[2] : head, draft: "", objective: "", intro: [], sections: [] };
  const parts = rest.split(/^## /m); let lead = parts.shift() || "";
  const dm = lead.match(/^>\s*(Draft\..*)$/m); if (dm) { res.draft = dm[1]; lead = lead.replace(dm[0], ""); }
  const om = lead.match(/\*\*Objective\.\*\*\s*(.*)/); if (om) { res.objective = om[1].trim(); lead = lead.replace(om[0], ""); }
  res.intro = lessonBlocks(lead);
  for (const p of parts) { const nl = p.indexOf("\n"); const title = (nl < 0 ? p : p.slice(0, nl)).trim(); res.sections.push({ id: slug(title), title, blocks: lessonBlocks(nl < 0 ? "" : p.slice(nl + 1)) }); }
  return res;
}
/* Words a reader will read, at a modest 200 a minute. Code and directives do not count. */
export function readingMinutes(md) { const prose = String(md || "").replace(/```[\s\S]*?```/g, "").replace(/\{\{[^}]*\}\}/g, ""); return Math.max(1, Math.round(prose.split(/\s+/).filter(Boolean).length / 200)); }

/* ---------- graphs ---------- */
export const isLink = (v) => Array.isArray(v) && v.length === 2 && typeof v[1] === "number" && (typeof v[0] === "string" || typeof v[0] === "number");
export const WIRE = { MODEL: "#b39ddb", CLIP: "#f5c518", VAE: "#ff6e6e", CONDITIONING: "#ffa931", LATENT: "#ff9cf9", IMAGE: "#64b5f6", MASK: "#81c784", SIGMAS: "#cdffcd", SAMPLER: "#ecb4b4", GUIDER: "#66ffff", NOISE: "#b0b0b0", AUDIO: "#7dd3c0", VIDEO: "#9fc5ff", STRING: "#a0d8a0", INT: "#a0c4ff", FLOAT: "#c0e0ff" };
export function graphEdges(g) { const out = []; for (const [id, n] of Object.entries(g)) for (const [inp, v] of Object.entries(n.inputs || {})) if (isLink(v) && g[String(v[0])]) out.push({ from: String(v[0]), slot: v[1], to: id, input: inp }); return out; }
export function layoutGraph(g, defs = {}, { nodeW = 196, rowGap = 22, colGap = 54, headH = 34, rowH = 15 } = {}) {
  const ids = Object.keys(g), edges = graphEdges(g), layer = {}; const inc = {}; ids.forEach((k) => { inc[k] = []; }); edges.forEach((e) => inc[e.to].push(e.from));
  const depth = (k, seen = new Set()) => { if (layer[k] != null) return layer[k]; if (seen.has(k)) return 0; seen.add(k); const d = inc[k].length ? 1 + Math.max(...inc[k].map((x) => depth(x, seen))) : 0; layer[k] = d; return d; }; ids.forEach((k) => depth(k));
  const cols = {}; ids.forEach((k) => { (cols[layer[k]] = cols[layer[k]] || []).push(k); });
  const pos = {}; const seq = Object.keys(cols).map(Number).sort((a, b) => a - b); let height = 0;
  for (const c of seq) { // keep nodes near the things that feed them
    const ord = cols[c].map((k, i) => [k, inc[k].length ? inc[k].reduce((t, x) => t + (pos[x] ? pos[x].y : 0), 0) / inc[k].length : i * 40]); ord.sort((a, b) => a[1] - b[1]); let y = 0;
    for (const [k] of ord) { const rows = Object.values(g[k].inputs || {}).filter(isLink).length + Math.min(3, Object.values(g[k].inputs || {}).filter((v) => !isLink(v)).length); const h = headH + Math.max(1, rows) * rowH + 10; pos[k] = { x: c * (nodeW + colGap), y, w: nodeW, h }; y += h + rowGap; } height = Math.max(height, y);
  }
  const typed = edges.map((e) => { const d = defs[g[e.from].class_type]; return { ...e, type: d && d.output ? d.output[e.slot] || "*" : "*" }; });
  return { pos, edges: typed, width: (seq.length ? seq[seq.length - 1] + 1 : 0) * (nodeW + colGap) - colGap, height: height - rowGap, order: [...ids].sort((a, b) => pos[a].x - pos[b].x || pos[a].y - pos[b].y) };
}
/* What an edit to one value re-runs: the node it belongs to, then everything downstream of that node. */
export function dirtyFrom(g, id) { const edges = graphEdges(g), hit = new Set([String(id)]); let again = true; while (again) { again = false; for (const e of edges) if (hit.has(e.from) && !hit.has(e.to)) { hit.add(e.to); again = true; } } return hit; }
/* Nodes the engine would start: outputs, and what they pull on. */
export function reachable(g, defs) { const edges = graphEdges(g), keep = new Set(Object.keys(g).filter((k) => (defs[g[k].class_type] || {}).is_output)); let again = true; while (again) { again = false; for (const e of edges) if (keep.has(e.to) && !keep.has(e.from)) { keep.add(e.from); again = true; } } return keep; }

/* A copy of the checks in ComfyUI's execution.py validate_prompt and validate_inputs: same error types, same order for each node. File menus can't be known here, so they are not checked. */
export function typesMatch(got, want) { if (got === want) return true; if (got === "*" || want === "*") return true; if (typeof got !== "string" || typeof want !== "string") return false; const a = got.split(","), b = want.split(","); return a.every((x) => b.includes(x)); }
export function validateGraph(prompt, defs) {
  const errors = []; const push = (node, type, message, details = "", input = null) => errors.push({ node, class_type: prompt && prompt[node] ? prompt[node].class_type : null, type, message, details, input });
  if (!prompt || typeof prompt !== "object" || Array.isArray(prompt)) return [{ node: null, type: "invalid_prompt", message: "Not a graph: expected an object of nodes" }];
  for (const [id, n] of Object.entries(prompt)) { if (!n || !n.class_type) { push(id, "missing_node_type", `Node 'ID #${id}' has no class_type. The workflow may be corrupted or a custom node is missing.`, `Node ID '#${id}'`); return errors; } if (!defs[n.class_type]) { push(id, "missing_node_type", `Node '${n.class_type}' not found. The custom node may not be installed.`, `Node ID '#${id}'`); return errors; } }
  const outputs = Object.keys(prompt).filter((k) => defs[prompt[k].class_type].is_output); if (!outputs.length) { errors.push({ node: null, type: "prompt_no_outputs", message: "Prompt has no outputs", details: "" }); return errors; }
  const seen = new Set(), visit = (id, stack) => {
    if (stack.has(id)) { push(id, "dependency_cycle", "Dependency cycle detected", "Node is part of a loop"); return; } if (seen.has(id)) return; seen.add(id); const n = prompt[id], d = defs[n.class_type], inputs = n.inputs || {}; const req = (d.input || {}).required || {}, opt = (d.input || {}).optional || {}, stk = new Set(stack); stk.add(id);
    for (const name of Object.keys(req)) if (!(name in inputs)) push(id, "required_input_missing", "Required input is missing", name, name);
    for (const [name, v] of Object.entries(inputs)) {
      const spec = req[name] || opt[name]; if (!spec) continue; const want = spec[0], lim = spec[1] || {};
      if (Array.isArray(v)) {
        if (v.length !== 2) { push(id, "bad_linked_input", "Bad linked input, must be a length-2 list of [node_id, slot_index]", name, name); continue; }
        const src = prompt[String(v[0])]; if (!src) { push(id, "exception_during_inner_validation", "Exception when validating inner node", `'${v[0]}'`, name); continue; }
        const got = (defs[src.class_type].output || [])[v[1]]; if (got === undefined) { push(id, "bad_linked_input", `Node ${v[0]} has no output ${v[1]}`, name, name); continue; }
        const wantT = Array.isArray(want) ? "COMBO" : want; if (want !== "FILE" && !typesMatch(got, wantT)) push(id, "return_type_mismatch", "Return type mismatch between linked nodes", `${name}, received_type(${got}) mismatch input_type(${wantT})`, name);
        visit(String(v[0]), stk);
      } else if (want === "INT" || want === "FLOAT") {
        const num = Number(v); if (v === "" || v === null || typeof v === "boolean" || !Number.isFinite(num) || (want === "INT" && !Number.isInteger(Math.trunc(num)))) { push(id, "invalid_input_type", `Failed to convert an input value to a ${want} value`, `${name}, ${v}`, name); continue; }
        if (lim.min != null && num < lim.min) push(id, "value_smaller_than_min", `Value ${v} smaller than min of ${lim.min}`, name, name);
        if (lim.max != null && num > lim.max) push(id, "value_bigger_than_max", `Value ${v} bigger than max of ${lim.max}`, name, name);
      } else if (Array.isArray(want) && !want.includes(v)) push(id, "value_not_in_list", "Value not in list", `${name}: ${JSON.stringify(v)} not in the list`, name);
    }
  };
  for (const o of outputs) visit(o, new Set());
  return errors;
}

/* ---------- wiring walkthrough ---------- */
export function missingWires(prompt, defs) { return validateGraph(prompt, defs).filter((e) => e.type === "required_input_missing"); }
export function canWire(srcClass, slot, dstClass, input, defs) { const got = (defs[srcClass].output || [])[slot]; const spec = (defs[dstClass].input.required || {})[input] || (defs[dstClass].input.optional || {})[input]; if (!spec) return { ok: false, why: `${dstClass} has no input called ${input}` }; const want = spec[0]; return typesMatch(got, want) ? { ok: true, type: got } : { ok: false, why: `That socket gives ${got}. ${input} wants ${want}.`, type: got }; }
export const linkInputs = (cls, defs) => Object.entries({ ...(defs[cls].input.required || {}) }).filter(([, s]) => typeof s[0] === "string" && !["INT", "FLOAT", "STRING", "BOOLEAN", "FILE", "COMBO"].includes(s[0])).map(([k, s]) => [k, s[0]]);
