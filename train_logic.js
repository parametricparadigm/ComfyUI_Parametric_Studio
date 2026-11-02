// Train page logic with no DOM, so node can test it. Every number here comes from the job the server sent. A null stays a null and reads as "not measured yet".

export const fmtDuration = (s) => {
  if (s == null || !Number.isFinite(+s)) return "not measured yet";
  s = Math.round(+s);
  if (s < 60) return `${s} s`;
  if (s < 3600) return `${Math.floor(s / 60)} min ${s % 60} s`;
  return `${Math.floor(s / 3600)} h ${Math.floor((s % 3600) / 60)} min`;
};
export const fmtLoss = (v) => (v == null || !Number.isFinite(+v) ? "not measured yet" : (+v).toFixed(4));
export const fmtSpeed = (sps) => (sps == null ? "not measured yet" : sps >= 1 ? `${(+sps).toFixed(2)} s per step` : `${(1 / sps).toFixed(2)} steps per s`);
export const fmtGib = (g) => (g == null ? "not measured" : `${(+g).toFixed(1)} GB`);

const ticksFor = (lo, hi, n = 4) => Array.from({ length: n + 1 }, (_, i) => lo + ((hi - lo) * i) / n);

/** The drawing for a loss curve. x runs over the whole planned run, so the unfinished part stays visibly empty. A null value breaks the line instead of being joined over. */
export function lossChart(curve, total, w = 720, h = 240, pad = { l: 56, r: 14, t: 12, b: 30 }) {
  const pts = (curve || []).filter((c) => Array.isArray(c));
  const vals = pts.map((c) => c[1]).filter((v) => v != null && Number.isFinite(v));
  if (!vals.length) return { empty: true, w, h, pad, path: "", points: [], xTicks: [], yTicks: [] };
  let lo = Math.min(...vals), hi = Math.max(...vals);
  if (lo === hi) { lo -= Math.abs(lo) * 0.05 || 0.5; hi += Math.abs(hi) * 0.05 || 0.5; }
  const xMax = Math.max(total || 0, pts[pts.length - 1][0], 1);
  const X = (s) => pad.l + (s / xMax) * (w - pad.l - pad.r), Y = (v) => h - pad.b - ((v - lo) / (hi - lo)) * (h - pad.t - pad.b);
  let path = "", open = false; const points = [];
  for (const [s, v] of pts) {
    if (v == null || !Number.isFinite(v)) { open = false; continue; }
    const x = +X(s).toFixed(1), y = +Y(v).toFixed(1);
    path += `${open ? "L" : "M"}${x} ${y}`; open = true; points.push({ step: s, loss: v, x, y });
  }
  return { empty: false, w, h, pad, path, points, lo, hi, xMax, xTicks: ticksFor(0, xMax).map((s) => ({ s: Math.round(s), x: +X(s).toFixed(1) })), yTicks: ticksFor(lo, hi).map((v) => ({ v, y: +Y(v).toFixed(1) })) };
}

/** Seconds as m:ss for the big readout. A null stays a null, so the page can say "not measured yet". */
export const fmtClock = (s) => {
  if (s == null || !Number.isFinite(+s)) return null;
  s = Math.max(0, Math.round(+s));
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), r = String(s % 60).padStart(2, "0");
  return h ? `${h}:${String(m).padStart(2, "0")}:${r}` : `${m}:${r}`;
};

export const averageWindow = (total) => Math.max(10, Math.round((total || 0) / 12));

/** A trailing mean of the chart's real points, worked out here and labelled as such on the page. It starts only when a whole window has passed, and restarts after a gap in the values. */
export function averageLine(chart, windowSteps) {
  if (!chart || chart.empty) return { path: "", points: [] };
  const { pad, h, lo, hi } = chart, Y = (v) => +(h - pad.b - ((v - lo) / (hi - lo)) * (h - pad.t - pad.b)).toFixed(1);
  const pts = chart.points; let path = "", prev = null; const points = [];
  for (let i = 0; i < pts.length; i++) {
    const p = pts[i], inWindow = [];
    for (let k = i; k >= 0 && pts[k].step > p.step - windowSteps; k--) inWindow.push(pts[k].loss);
    if (p.step < windowSteps || inWindow.length < 3) { prev = null; continue; }
    const v = inWindow.reduce((a, b) => a + b, 0) / inWindow.length, y = Y(v);
    path += `${prev == null ? "M" : "L"}${p.x} ${y}`; prev = y; points.push({ step: p.step, loss: v, x: p.x, y });
  }
  return { path, points };
}

const FLAG = { no_caption: "No caption", word_list: "Word list", no_trigger: "No trigger", long_caption: "Long caption", small: "Too small", flat: "Flat colour", duplicate: "Duplicate" };
/** The mark drawn on a picture: its worst problem in two words, and how many more there are. Null for a clean picture. */
export function pictureFlag(problems) {
  if (!problems || !problems.length) return null;
  const worst = problems.find((p) => p.level === "block") || problems[0];
  return { level: worst.level, text: FLAG[worst.code] || "Look at this", more: problems.length - 1 };
}

/** The four steps across the top, each with what is true of it right now. */
export function flowSteps({ report, base, form, job, blockers }) {
  const live = isLive(job), done = !!job && job.state === "done" && !!job.lora, n = report ? report.items.length : 0, left = (blockers || []).length;
  const word = (x) => `${x} picture${x === 1 ? "" : "s"}`;
  const steps = [
    { key: "tr1", n: 1, title: "Pictures", note: !report ? "None yet" : report.blocks ? `${word(n)}, ${report.blocks} to fix` : word(n), state: !report || !n ? "todo" : report.blocks ? "fix" : "done" },
    { key: "tr2", n: 2, title: "Base", note: base ? `${base.arch}, ${form.size || base.sizes[base.sizes.length - 1]} px, ${form.steps} steps` : "No base to train on", state: base ? "done" : "fix" },
    { key: "tr3", n: 3, title: "Train", note: live ? (job.step ? `Step ${job.step} of ${job.total}` : "Starting") : done ? `${job.total} steps run` : left ? `${left} thing${left === 1 ? "" : "s"} left` : "Ready", state: live ? "now" : done ? "done" : "todo" },
    { key: "tr4", n: 4, title: "Result", note: !done ? "Nothing yet" : job.ab && job.ab.state === "done" ? "A/B rendered" : "A/B to render", state: done ? (job.ab && job.ab.state === "done" ? "done" : "now") : "todo" },
  ];
  if (!steps.some((s) => s.state === "now")) { const first = steps.find((s) => s.state !== "done"); if (first) first.state = first.state === "fix" ? "fix" : "now"; }
  return steps;
}

/** The point nearest the pointer, for the crosshair. */
export function nearestPoint(chart, x) {
  let best = null, gap = Infinity;
  for (const p of chart.points || []) { const d = Math.abs(p.x - x); if (d < gap) { gap = d; best = p; } }
  return best;
}

/** Plain means of the first and last tenth of the real values, or null for a run too short to say. */
export function lossTrend(curve) {
  const v = (curve || []).map((c) => c[1]).filter((x) => x != null && Number.isFinite(x));
  if (v.length < 20) return null;
  const n = Math.floor(v.length / 10), mean = (a) => a.reduce((x, y) => x + y, 0) / a.length;
  return { first: mean(v.slice(0, n)), last: mean(v.slice(-n)) };
}

export const curveNote = (job) => {
  if (!job || !job.curve_points) return "No loss value has been reported yet.";
  if (job.curve_source === "loss_map") {
    const t = lossTrend(job.curve);
    return `Every step, read from the training node's own loss record (${job.curve_points} values). Each step uses a random noise level, so the line jumps and need not fall in a short run.${t ? ` Average of the first tenth ${t.first.toFixed(4)}, last tenth ${t.last.toFixed(4)}.` : ""} The A/B shows what the LoRA learned better than this number does.`;
  }
  if (job.curve_source === "trainer log") return `Read from the trainer's own log (${job.curve_points} values). Each step uses a random noise level, so the line jumps and need not fall in a short run.`;
  return `Read live from ComfyUI's training log. ${job.curve_points} of ${job.step} steps were logged; the full record replaces this when the run ends.`;
};

export function statusLine(job) {
  if (!job) return "";
  const outside = job.trainer && job.trainer !== "comfy", who = job.trainer_label || "The trainer";
  if (outside) switch (job.state) {
    case "queued": return `${who} is starting: it may wait for the GPU, then loads the base. No step has run yet.`;
    case "running": return job.step ? `Training: step ${job.step} of ${job.total}.` : "Loading the base. No step has run yet.";
    case "cancelling": return `Stopping ${who}.`;
    case "cancelled": return job.can_resume ? `Stopped. ${job.checkpoints.length} save${job.checkpoints.length === 1 ? "" : "s"} kept, so this run can resume from the last one.` : "Stopped before its first save, so nothing from this run was kept.";
    default: break;
  }
  if (job.unreachable) return "ComfyUI is not answering, so this job's state is unknown right now.";
  switch (job.state) {
    case "queued": return job.position ? `Waiting in ComfyUI's queue, position ${job.position}.` : "Waiting in ComfyUI's queue.";
    case "running": return job.step ? `Training: step ${job.step} of ${job.total}.` : "Loading the base and encoding your pictures. No step has run yet.";
    case "cancelling": return "Cancelling. ComfyUI stops at the end of the current step.";
    case "cancelled": return "Cancelled. The training node saves only at the end, so nothing from this run was kept.";
    case "lost": return job.error || "ComfyUI lost this job.";
    case "error": return job.error ? `Failed: ${job.error}` : "Failed.";
    case "done": return `Finished: ${(job.lora && job.lora.total_steps) || job.total} steps in all.`;
    default: return job.state || "";
  }
}
export const isLive = (job) => !!job && ["preparing", "queued", "running", "cancelling"].includes(job.state);

/** What still stops Train, in the words the page shows. Empty means the button works. */
export function trainBlockers({ report, base, form, active }) {
  // a base with no run on record can still be tried, once the person says they know

  const out = [];
  if (active) out.push("A training job is already running. One at a time.");
  if (!report) out.push("Add a set of pictures.");
  else if (!report.ready) out.push(`The caption check found ${report.blocks} problem${report.blocks === 1 ? "" : "s"} to fix.`);
  if (!base) out.push("No base can be trained on this machine.");
  else if (!base.trainable && base.can_try && !form.first_run) out.push("This base has no run on record. Tick the first-run box to try it.");
  if (!/^[A-Za-z0-9][A-Za-z0-9 _-]{0,39}$/.test((form.name || "").trim())) out.push("Name the LoRA.");
  if (!/^[A-Za-z0-9][A-Za-z0-9_-]{1,39}$/.test((form.trigger || "").trim())) out.push("Choose a one-word trigger.");
  if (!form.rights) out.push("Tick the rights and consent box.");
  return out;
}

export function jobPayload(form, datasetId, baseId) {
  const num = (v) => (v === "" || v == null ? undefined : +v);
  return { dataset: datasetId, base: baseId, name: form.name.trim(), trigger: form.trigger.trim(), size: num(form.size), steps: num(form.steps), rank: num(form.rank), batch: num(form.batch), learning_rate: num(form.learning_rate), seed: num(form.seed), rights_confirmed: form.rights === true, ...(form.first_run === true ? { first_run: true } : {}), ...(form.continue_from ? { continue_from: form.continue_from } : {}) };
}

/** The badge for a base: proven by a real run, ready but not run yet, or missing something. */
export function baseBadge(b) {
  if (!b) return null;
  if (b.status === "proven") return { kind: "proven", text: "Proven" };
  if (b.status === "not_run") return { kind: "notrun", text: "Not run" };
  return { kind: "missing", text: "Missing pieces" };
}

/** Bases in the order the page lists them: proven first, then ready to try, then missing, keeping the registry's order inside each. */
export function orderBases(bases) {
  const rank = { proven: 0, not_run: 1, blocked: 2 };
  return [...(bases || [])].map((b, i) => [b, i]).sort((x, y) => (rank[x[0].status] ?? 3) - (rank[y[0].status] ?? 3) || x[1] - y[1]).map((x) => x[0]);
}

/** The one line on a base's licence and peak VRAM, with where the peak figure came from. */
export function baseFacts(b) {
  const out = [];
  if (b.trainer_label) out.push(b.trainer_label);
  if (b.licence && b.licence.name) out.push(b.licence.name);
  if (b.peak_gib != null) out.push(`${b.peak_kind === "measured" ? "peak measured" : "peak expected"} ${b.peak_gib} GB`);
  return out.join(" · ");
}

/** The honest words for a time and VRAM figure, or the reason there is none. */
export function estimateLines(est) {
  if (!est) return { measured: false, lines: ["Asking for measured figures..."] };
  if (!est.measured) return { measured: false, lines: [est.note] };
  const lines = [`Training time about ${fmtDuration(est.train_seconds)} at ${fmtSpeed(est.s_per_step)}.`];
  if (est.setup_seconds != null) lines.push(`Loading and encoding took ${fmtDuration(est.setup_seconds)} on that run.`);
  lines.push(`Peak VRAM on the whole card during that run: ${fmtGib(est.peak_vram_gib)}.`);
  if (est.from) lines.push(`From a real run of ${est.from.steps} steps${est.from.date ? ` on ${est.from.date}` : ""}. ${est.note}`);
  return { measured: true, lines };
}

export function abPrompt(trigger, report) {
  const first = report && report.items && report.items[0] ? report.items[0].caption : "";
  if (!first) return trigger || "";
  return !trigger || new RegExp(`(^|\\W)${trigger.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}(\\W|$)`, "i").test(first) ? first : `${trigger}, ${first}`;
}

/** What one A/B says, in words. A difference shows the LoRA changed the render. It does not show that the change is good. */
export function abVerdict(ab) {
  if (!ab || ab.state !== "done") return null;
  const bits = [];
  if (ab.pixel_diff == null) bits.push({ warn: true, text: "The two pictures could not be compared." });
  else if (ab.pixel_diff < 0.05) bits.push({ warn: true, text: `The two pictures are almost identical (difference ${ab.pixel_diff} of 255). This LoRA did nothing visible at this strength.` });
  else bits.push({ warn: false, text: `The LoRA changed the render: average pixel difference ${ab.pixel_diff} of 255. Same seed, same sampler. Whether the change is good is for your eye.` });
  if (ab.source === "trainer samples") { bits.push({ warn: false, text: "These are the trainer's own samples: its first, before any training, against its last, same seed and prompt. ComfyUI did not render them." }); return bits; }
  if (ab.unbound_keys == null) bits.push({ warn: true, text: "ComfyUI's log could not be read, so it is not known whether every LoRA weight loaded." });
  else if (ab.unbound_keys > 0) bits.push({ warn: true, text: `ComfyUI could not place ${ab.unbound_keys} LoRA weights on this base.` });
  else bits.push({ warn: false, text: "ComfyUI reported no LoRA weight it could not place." });
  return bits;
}
