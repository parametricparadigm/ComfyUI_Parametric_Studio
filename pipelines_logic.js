/* Words and sums for the Pipelines page. No DOM, so a test can run it. */
export const clockOf = (s) => { const n = Math.round(Number(s) || 0); return n < 60 ? `${n} s` : `${Math.floor(n / 60)} min ${String(n % 60).padStart(2, "0")} s`; };
export const minutesOf = (s) => { const m = (Number(s) || 0) / 60; return m < 10 ? m.toFixed(1) : String(Math.round(m)); };
const STATUS = { passed: "Passed review", partial: "Partly passed", failed: "Failed", ok: "Passed", flawed: "Kept, with a flaw" };
export const statusWord = (s) => STATUS[s] || "Not reviewed";
const CLASS = { open: "Open", community: "Own terms", noncommercial: "Non-commercial" };
export const classWord = (c) => CLASS[c] || "Check terms";
export const stageMeta = (s) => [s.seconds == null ? "" : clockOf(s.seconds), s.peak_gib ? `${s.peak_gib} GiB` : "", s.seed != null ? `seed ${s.seed}` : ""].filter(Boolean).join(" · ");
export function pageTotals(list) {
  const ran = list.filter((p) => p.proof && p.proof.status !== "failed"), names = new Set(), secs = ran.reduce((a, p) => a + (p.proof.seconds || 0), 0); let stages = 0;
  for (const p of ran) { stages += p.proof.stages.filter((s) => s.ran === "done").length; for (const s of p.proof.stages) if (s.model) names.add(s.model); }
  return { ran: ran.length, stages, families: names.size, minutes: Math.round(secs / 60), notRun: list.filter((p) => !p.proof).length };
}
