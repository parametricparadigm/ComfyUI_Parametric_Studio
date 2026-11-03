/* Model Anatomy: the sums and shapes behind the page, with no DOM, so node can test them. */
export const KINDS = [["attention", "Attention"], ["mlp", "MLP"], ["modulation", "Modulation"], ["norm", "Norms"], ["embedding", "Embeddings"], ["conv", "Convolutions"], ["unclassified", "Names don't say"], ["quant_aux", "Quant scales"]];
export const KIND_WORD = Object.fromEntries(KINDS);

export function fmtN(n) {
  if (n == null || !isFinite(n)) return "?";
  const a = Math.abs(n);
  if (a >= 1e12) return (n / 1e12).toFixed(2) + " T";
  if (a >= 1e9) return (n / 1e9).toFixed(a >= 1e11 ? 0 : 2) + " B";
  if (a >= 1e6) return (n / 1e6).toFixed(a >= 1e8 ? 0 : 1) + " M";
  if (a >= 1e3) return (n / 1e3).toFixed(1) + " k";
  return String(Math.round(n));
}
export function fmtBytes(b) {
  if (b == null || !isFinite(b)) return "?";
  if (b >= 1e12) return (b / 1e12).toFixed(2) + " TB";
  if (b >= 1e9) return (b / 1e9).toFixed(b >= 1e11 ? 0 : 2) + " GB";
  if (b >= 1e6) return (b / 1e6).toFixed(1) + " MB";
  if (b >= 1e3) return (b / 1e3).toFixed(1) + " kB";
  return b + " B";
}
/* Bits stored per weight, over the whole file: scales and buffers included, so it is a little above the nominal format. */
export const bitsPerWeight = (bytes, weights) => (weights > 0 ? (bytes * 8) / weights : null);
export const pct = (x, digits = 0) => (x == null ? "?" : (x * 100).toFixed(digits) + "%");

/* The route after #anatomy: a file, a comparison, or the list. */
export function parseRoute(route) {
  const p = String(route || "").split("/").slice(1);
  if (p[0] === "compare") return { view: "compare", ids: (p[1] || "").split(",").filter(Boolean).slice(0, 4) };
  if (p[0]) return { view: "model", id: p[0] };
  return { view: "list" };
}

export function filterModels(rows, f) {
  const q = (f.q || "").trim().toLowerCase().split(/\s+/).filter(Boolean);
  const out = rows.filter((r) => {
    if (f.read === "read" && !r.read) return false;
    if (f.read === "unread" && r.read) return false;
    if (f.lora === "lora" && !r.lora) return false;
    if (f.lora === "base" && r.lora) return false;
    if (f.folder && f.folder !== "all" && r.folder !== f.folder) return false;
    if (!q.length) return true;
    const hay = `${r.file} ${r.rel || ""} ${r.family || ""} ${r.arch || ""} ${r.dtype || ""} ${r.format || ""}`.toLowerCase();
    return q.every((w) => hay.includes(w));
  });
  const by = { weights: (a, b) => (b.weights || 0) - (a.weights || 0), name: (a, b) => a.file.localeCompare(b.file), size: (a, b) => (b.size || 0) - (a.size || 0) }[f.sort || "weights"];
  return out.sort(by);
}
export function folderCounts(rows) {
  const c = {};
  for (const r of rows) c[r.folder || "other"] = (c[r.folder || "other"] || 0) + 1;
  return Object.entries(c).sort((a, b) => b[1] - a[1]);
}

/* Weight shares by kind, in KINDS order, leaving out what isn't there. Values are weights, or fractions when the input is fractions. */
export function kindShares(kinds) {
  const out = []; let total = 0;
  for (const [k] of KINDS) { const v = kinds && kinds[k] != null ? (Array.isArray(kinds[k]) ? kinds[k][0] : kinds[k]) : 0; if (v > 0) { out.push([k, v]); total += v; } }
  return out.map(([k, v]) => ({ k, v, f: total ? v / total : 0 }));
}
/* Attention against MLP alone, for the line "attention : MLP". Null when the names show neither. */
export function attnMlp(kinds) {
  const g = (k) => (kinds && kinds[k] ? (Array.isArray(kinds[k]) ? kinds[k][0] : kinds[k]) : 0);
  const a = g("attention"), m = g("mlp");
  return a + m > 0 ? { attention: a / (a + m), mlp: m / (a + m) } : null;
}

/* The stacks of repeated blocks the header shows, biggest first: "blocks x 40". */
export function stacks(model) {
  const out = [];
  const walk = (n, path, depth) => {
    if (!n || depth > 4) return;
    if (n.r >= 2) { out.push({ path: path || n.n, r: n.r, u: n.u, w: n.w }); return; }
    for (const c of n.c || []) walk(c, path ? path + "." + c.n : c.n, depth + 1);
  };
  for (const c of (model.tree && model.tree.c) || []) walk(c, c.n, 1);
  return out.sort((a, b) => b.w - a.w);
}

/* Treemap tiles: each top group, split into its parts. A stack of blocks splits by kind, since its blocks are copies of one design; any other group splits into its children. */
export function treemapItems(model, maxKids = 10) {
  const groups = ((model.tree && model.tree.c) || []).filter((g) => g.w > 0);
  if (!groups.length && model.tree && model.tree.w > 0) groups.push(model.tree);
  return groups.map((g) => {
    let kids;
    if (g.r >= 2 && g.k) kids = kindShares(g.k).map((s) => ({ n: `${KIND_WORD[s.k]}`, w: s.v, kind: s.k }));
    else if (g.c && g.c.length) {
      const sorted = [...g.c].filter((c) => c.w > 0).sort((a, b) => b.w - a.w), top = sorted.slice(0, maxKids), rest = sorted.slice(maxKids).reduce((s, c) => s + c.w, 0);
      kids = top.map((c) => ({ n: c.n, w: c.w, kind: c.kind || dominant(c.k) })); if (rest > 0) kids.push({ n: `${sorted.length - maxKids} more`, w: rest, kind: "unclassified" });
    } else kids = [{ n: g.n, w: g.w, kind: g.kind || dominant(g.k) }];
    return { n: g.n, w: g.w, r: g.r, kids };
  }).sort((a, b) => b.w - a.w);
}
export function dominant(k) {
  let best = null, v = -1;
  for (const [key, x] of Object.entries(k || {})) if (x > v) { v = x; best = key; }
  return best || "unclassified";
}

/* Squarified treemap (Bruls, Huizing and van Wijk): rows of tiles kept as close to square as the values allow. Returns {x, y, w, h, item}. */
export function squarify(items, x, y, w, h) {
  const list = items.filter((i) => i.w > 0).sort((a, b) => b.w - a.w), total = list.reduce((s, i) => s + i.w, 0), out = [];
  if (!list.length || w <= 0 || h <= 0) return out;
  const scale = (w * h) / total; let rx = x, ry = y, rw = w, rh = h, row = [], i = 0;
  const worst = (r, side) => { const s = r.reduce((a, it) => a + it.w * scale, 0), mx = Math.max(...r.map((it) => it.w * scale)), mn = Math.min(...r.map((it) => it.w * scale)); return Math.max((side * side * mx) / (s * s), (s * s) / (side * side * mn)); };
  const lay = (r) => {
    const s = r.reduce((a, it) => a + it.w * scale, 0);
    if (rw >= rh) { const cw = s / rh; let yy = ry; for (const it of r) { const hh = (it.w * scale) / cw; out.push({ x: rx, y: yy, w: cw, h: hh, item: it }); yy += hh; } rx += cw; rw -= cw; }
    else { const ch = s / rw; let xx = rx; for (const it of r) { const ww = (it.w * scale) / ch; out.push({ x: xx, y: ry, w: ww, h: ch, item: it }); xx += ww; } ry += ch; rh -= ch; }
  };
  while (i < list.length) {
    const it = list[i], side = Math.min(rw, rh);
    if (!row.length || worst([...row, it], side) <= worst(row, side)) { row.push(it); i++; }
    else { lay(row); row = []; }
  }
  if (row.length) lay(row);
  return out;
}

/* One line per fact for the side by side table. Every value comes from the header. */
export function compareRows(models) {
  const g = (m, f) => (m && m.read ? f(m) : "not read");
  return [
    ["Weights", (m) => g(m, (x) => fmtN(x.weights))],
    ["Stored", (m) => g(m, (x) => fmtBytes(x.data_bytes))],
    ["Bits per weight", (m) => g(m, (x) => { const b = bitsPerWeight(x.data_bytes, x.weights); return b == null ? "?" : b.toFixed(1); })],
    ["Tensors", (m) => g(m, (x) => String(x.tensors))],
    ["Main format", (m) => g(m, (x) => (x.dtypes && x.dtypes[0] ? `${x.dtypes[0][0]}, ${pct(x.dtypes[0][3] / x.data_bytes)} of bytes` : "?"))],
    ["Attention : MLP", (m) => g(m, (x) => { const s = attnMlp(x.kinds); return s ? `${pct(s.attention)} : ${pct(s.mlp)}` : "names don't say"; })],
    ["Unsplit by name", (m) => g(m, (x) => pct(((x.kinds.unclassified || [0])[0]) / (x.weights || 1)))],
    ["Repeated blocks", (m) => g(m, (x) => stacks(x).slice(0, 2).map((s) => `${s.path} x ${s.r}`).join(", ") || "none named by number")],
    ["Common width", (m) => g(m, (x) => (x.widths && x.widths[0] ? String(x.widths[0][0]) : "?"))],
    ["Architecture in the header", (m) => g(m, (x) => x.arch || "none named")],
  ].map(([label, f]) => ({ label, cells: models.map(f) }));
}

/* LoRA rank as a line: "rank 16 on all 104 modules" or "ranks 64 (200), 32 (8)". */
export function rankLine(lora) {
  if (!lora || !lora.ranks || !lora.ranks.length) return "rank not in the shapes";
  if (lora.ranks.length === 1) return `rank ${lora.ranks[0][0]} on all ${lora.ranks[0][1]} modules`;
  return "ranks " + lora.ranks.slice(0, 4).map(([r, c]) => `${r} (${c})`).join(", ") + (lora.ranks.length > 4 ? `, ${lora.ranks.length - 4} more` : "");
}
