// Pure logic for the Create page's look picker. No DOM, so node can test it (tests/studio_lanes/test_look_picker.mjs).

/* Groups a goal can use: video-only groups are hidden for pictures. */
export const groupsFor = (groups, kind) => groups.filter((g) => kind === "video" || g.kind !== "video");

/* Entries a goal can use, optionally in one group and matching a search over label, phrase and group label. */
export function searchLooks(looks, groups, q, group, kind) {
  const ok = new Set(groupsFor(groups, kind).map((g) => g.id)); const label = Object.fromEntries(groups.map((g) => [g.id, g.label.toLowerCase()]));
  const words = String(q || "").toLowerCase().split(/\s+/).filter(Boolean);
  return looks.filter((e) => ok.has(e.group) && (kind === "video" || e.kind !== "video") && (!group || e.group === group)
    && words.every((w) => e.label.toLowerCase().includes(w) || e.phrase.toLowerCase().includes(w) || label[e.group].includes(w)));
}

/* Toggle one entry. One per group: a new pick in a group replaces the old one, and the same pick again removes it.
   One camera move per clip: a move replaces any other move, whatever its group. picked is { group: id }. */
export function togglePick(picked, entry, byId) {
  const next = { ...picked };
  if (next[entry.group] === entry.id) { delete next[entry.group]; return next; }
  if (entry.move) for (const [g, id] of Object.entries(next)) if (byId[id] && byId[id].move) delete next[g];
  next[entry.group] = entry.id; return next;
}

/* Drop picks a goal can't use (video-only ones on a picture goal). */
export const keepFor = (picked, byId, kind) => Object.fromEntries(Object.entries(picked).filter(([, id]) => byId[id] && (kind === "video" || byId[id].kind !== "video")));

const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/* Take out the phrases this picker added before, then add the new ones at the end. The person's own words stay where they are. */
export function applyLooks(prompt, before, after) {
  let t = String(prompt || "");
  for (const p of before || []) t = t.replace(new RegExp("(,\\s*)?" + esc(p), "i"), "");
  t = t.replace(/\s+/g, " ").replace(/^[\s,]+|[\s,]+$/g, "");
  const add = (after || []).filter((p) => !t.toLowerCase().includes(p.toLowerCase()));
  return [t, ...add].filter(Boolean).join(", ");
}

/* The phrases for a picks map, in the library's own group order. */
export const phrasesOf = (picked, byId, groups) => groups.map((g) => picked[g.id]).filter((id) => id && byId[id]).map((id) => byId[id].phrase);
