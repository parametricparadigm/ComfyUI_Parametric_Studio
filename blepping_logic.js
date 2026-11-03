/* blepping page: the pure logic, so tests can run it with no browser. */
export const OWNER = "https://github.com/blepping";
export const REPOS = {
  sonar: { name: "ComfyUI-sonar", href: "https://github.com/blepping/ComfyUI-sonar", label: "Sonar" },
  ocs: { name: "comfyui_overly_complicated_sampling", href: "https://github.com/blepping/comfyui_overly_complicated_sampling", label: "Overly Complicated Sampling" },
  bleh: { name: "ComfyUI-bleh", href: "https://github.com/blepping/ComfyUI-bleh", label: "bleh" },
};
export const byId = (renders, id) => (renders || []).find((r) => r.id === id) || null;
/* A pack render and the render it should be read against. Both must exist and have pictures, or there is no pair. */
export function pairFor(renders, id) {
  const b = byId(renders, id); if (!b || !b.src) return null;
  const a = b.base ? byId(renders, b.base) : null;
  return a && a.src ? { a, b } : { a: null, b };
}
export const ofPack = (renders, pack) => (renders || []).filter((r) => r.pack === pack);
export function counts(renders) {
  const c = { all: 0, ok: 0, failed: 0 };
  for (const r of renders || []) { if (r.pack === "core" || r.expected_refusal) continue; c.all++; r.ok ? c.ok++ : c.failed++; }
  return c;
}
/* Stage 0 passes only when every core graph made the same pixels with the packs loaded as without them. */
export function stage0Verdict(stage0) {
  if (!stage0 || !stage0.length) return { ok: false, word: "not run" };
  const same = stage0.filter((s) => s.same_pixels).length;
  return { ok: same === stage0.length, same, of: stage0.length, word: same === stage0.length ? "unchanged" : "changed" };
}
export const secs = (s) => (s == null ? "?" : s < 10 ? s.toFixed(1) + " s" : Math.round(s) + " s");
export const gib = (g) => (g ? g.toFixed(1) + " GiB" : "not caught");
export const diffWord = (d) => (d == null ? "" : d === 0 ? "identical pixels" : `mean pixel difference ${d.toFixed(1)} of 255`);
/* "dpmpp_sde (1)" -> name and the extra model calls OCS lists for it. */
export function stepMethod(label) {
  const m = /^(.*?)(?: \(([^)]*)\))?$/.exec(String(label || "")); return { name: m[1], calls: m[2] || "" };
}
/* Two renders show the same picture when their decoded pixels hash the same (the PNG files differ: each embeds its own graph). */
export const samePixels = (a, b) => !!(a && b && a.pixels && a.pixels === b.pixels);
