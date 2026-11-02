// The Game Builder page's sums, kept apart from the page so a test can run them without a browser.
export const STATUS_WORD = { pending: "Waiting", running: "Working", done: "Done", failed: "Failed", skipped: "Skipped", fallback: "Stand-in" };

export function bytes(n) {
  if (!n && n !== 0) return "";
  if (n >= 1e9) return (n / 1e9).toFixed(1) + " GB";
  if (n >= 1e6) return Math.round(n / 1e6) + " MB";
  return Math.round(n / 1e3) + " KB";
}

export function clock(s) {
  if (s == null || !isFinite(s)) return "";
  s = Math.round(s);
  if (s < 60) return s + " s";
  return Math.floor(s / 60) + " min " + String(s % 60).padStart(2, "0");
}

// How far along a board is: finished stages out of all of them.
export function progress(stages) {
  const all = stages || [];
  const done = all.filter((s) => s.status === "done" || s.status === "skipped").length;
  return { done, all: all.length, pct: all.length ? Math.round((done / all.length) * 100) : 0 };
}

export function cleanPrompts(list) {
  return (list || []).map((p) => String(p || "").trim()).filter(Boolean);
}

// What the build button says it can't do yet, in one sentence, or "".
export function whyNot(prompts, running, ready) {
  if (running) return "A game is being built. They go one at a time.";
  if (!cleanPrompts(prompts).length) return "Say what the game is first.";
  if (ready && !ready.godot) return "Godot isn't installed on this machine, so a game can't be checked or exported. Set STUDIO_GODOT.";
  return "";
}

export function endWord(state) {
  const r = (state.playtest || {}).result;
  if (state.state === "failed") return "The build stopped";
  if (state.state === "cancelled") return "Cancelled";
  if (state.state !== "done") return "Building";
  return r === "won" ? "Built, and the bot reached the win" : "Built, but the bot didn't finish it";
}

// Plain words for what a stand-in count means.
export function standIns(n) {
  if (!n) return "Every asset came from a model or from this repo's drawing code, as listed.";
  return n === 1 ? "1 thing in this game is a stand-in drawn by code, because its model step failed." : `${n} things in this game are stand-ins drawn by code, because their model steps failed.`;
}
