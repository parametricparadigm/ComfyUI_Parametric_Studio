/* Inside a mixture of experts: the sums behind the page, with no DOM, so node can test them. Data shapes come from scripts/pack_moe_routing.py. */

export const pct = (x, digits = 0) => (x == null || !isFinite(x) ? "?" : (x * 100).toFixed(digits) + "%");

/* "moe" -> the first prompt; "moe/<id>" -> that prompt. */
export function parseRoute(tab) {
  const parts = String(tab || "").split("/");
  return { prompt: parts[1] ? decodeURIComponent(parts[1]) : null };
}

/* How a token piece is shown: spaces and line breaks made visible, and an empty piece (the rest of a character split over tokens) marked. */
export function showPiece(s) {
  if (s === "") return "↳";
  return s.replace(/\n/g, "↵").replace(/\t/g, "⇥").replace(/^ /, "␣");
}

/* One token at one layer: its experts, largest weight first, weights as fractions. */
export function pick(prompt, t, l) {
  const e = prompt.experts[t][l], w = prompt.weights[t][l];
  return e.map((x, i) => ({ e: x, w: w[i] / 1000 }));
}

/* How many of a token's experts two neighbouring layers share is always ~0 (each layer has its own 128); what is comparable is the same layer across two tokens. */
export function overlap(prompt, t1, t2, l) {
  const a = new Set(prompt.experts[t1][l]);
  return prompt.experts[t2][l].filter((x) => a.has(x)).length;
}

/* Across all layers: how many of the 8 slots a token shares with another token, on average. */
export function meanOverlap(prompt, t1, t2) {
  const L = prompt.experts[t1].length; let s = 0;
  for (let l = 0; l < L; l++) s += overlap(prompt, t1, t2, l);
  return s / L;
}

/* The router's uncertainty, as a share of the most it could be: entropy / ln(E). 0 = one expert takes everything, 1 = all equal. */
export const spread = (entropy, E) => entropy / Math.log(E);

/* Sum the counts of the chosen categories (all of them when none are chosen). -> { count: L x E, tokens } */
export function combine(categories, names) {
  const use = names && names.length ? categories.filter((c) => names.includes(c.name)) : categories;
  if (!use.length) return null;
  const L = use[0].count.length, E = use[0].count[0].length;
  const count = Array.from({ length: L }, () => new Array(E).fill(0)); let tokens = 0;
  for (const c of use) { tokens += c.tokens; for (let l = 0; l < L; l++) for (let e = 0; e < E; e++) count[l][e] += c.count[l][e]; }
  return { count, tokens };
}

/* Share of a layer's picks that went to each expert: count / (tokens x k). Even routing would give k / E... per token, 1 / E of the slots. */
export function shares(load, K) {
  return load.count.map((row) => row.map((n) => n / (load.tokens * K)));
}

/* How evenly a layer spreads its work: normalised entropy of its expert shares (1 = perfectly even, lower = a few experts take most). */
export function balance(row) {
  const s = row.reduce((a, b) => a + b, 0); if (!s) return null;
  let h = 0; for (const x of row) if (x > 0) { const p = x / s; h -= p * Math.log(p); }
  return h / Math.log(row.length);
}

/* Colour position for a share: 0 at "never picked", 0.5 at the even share 1/E, 1 at 4x the even share or more (log scale). */
export function heat(share, E) {
  if (!(share > 0)) return 0;
  const r = Math.log2(share * E);            // 0 = even, +2 = 4x even, -2 = a quarter of even
  return Math.max(0, Math.min(1, 0.5 + r / 4));
}

/* A colour for heat h in [0,1]: dark, through the page's green, to gold. */
export function heatRGB(h) {
  const stops = [[11, 16, 13], [22, 74, 48], [46, 204, 113], [212, 175, 55], [255, 236, 170]];
  const x = Math.max(0, Math.min(1, h)) * (stops.length - 1), i = Math.min(stops.length - 2, Math.floor(x)), f = x - i;
  return stops[i].map((v, k) => Math.round(v + (stops[i + 1][k] - v) * f));
}

/* Specialists: at one layer, the experts whose share in one category is furthest above their share over all the text.
   Only experts picked at least `min` times in that category count, so a lucky few picks don't top the list. -> [{ e, cat, ratio, share }] */
export function specialists(categories, layer, K, n = 6, min = 8) {
  const all = combine(categories, []), out = [];
  if (!all) return out;
  const tot = all.count[layer].map((x) => x / (all.tokens * K));
  for (const c of categories) {
    c.count[layer].forEach((x, e) => {
      if (x < min || !tot[e]) return;
      const share = x / (c.tokens * K); out.push({ e, cat: c.name, ratio: share / tot[e], share });
    });
  }
  out.sort((a, b) => b.ratio - a.ratio);
  const seen = new Set(), best = [];
  for (const r of out) { if (seen.has(r.e)) continue; seen.add(r.e); best.push(r); if (best.length >= n) break; }
  return best;
}

/* Which cell of the heatmap a point falls in. */
export function cellAt(x, y, width, height, L, E) {
  if (x < 0 || y < 0 || x >= width || y >= height) return null;
  return { l: Math.min(L - 1, Math.floor((y / height) * L)), e: Math.min(E - 1, Math.floor((x / width) * E)) };
}

/* Active share: what fraction of the expert weights one token touches in a layer. */
export const activeShare = (K, E) => K / E;

export function fmtB(n) {
  if (n == null || !isFinite(n)) return "?";
  if (n >= 1e9) return (n / 1e9).toFixed(1) + " B";
  if (n >= 1e6) return (n / 1e6).toFixed(0) + " M";
  return String(n);
}

/* Parameters in one layer's experts and in the active ones: three matrices of hidden x moe_intermediate per expert. */
export function expertParams(meta) {
  const per = 3 * meta.hidden * meta.moe_intermediate;
  return { perExpert: per, layerAll: per * meta.experts, layerActive: per * meta.top_k, allLayers: per * meta.experts * meta.layers, activeLayers: per * meta.top_k * meta.layers };
}
