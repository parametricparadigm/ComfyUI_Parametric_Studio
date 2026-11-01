/* The board and the Shot Board's own saved state. Kept apart from the page so plain node tests can run it. */
export const KEY = "shotboard_v1";
export function applyOps(board, ops) {
  let b = { ...board, picked: { ...board.picked } };
  for (const o of ops || []) {
    if (o.op === "add") b.picked[o.job] = true;
    else if (o.op === "remove") delete b.picked[o.job];
    else if (o.op === "camera") { b.camera = o.camera; b.picked.reshoot = true; }
    else if (o.op === "scene") b.scene = o.text;
    else if (o.op === "clear") b = { ...b, picked: {}, scene: "" };
  }
  return b;
}
/* Writes the plan into what the Shot Board reads, and leaves its clips and finished jobs as they are. It adds no job: only the Shot Board's own button makes those. */
export function toSaved(saved, board) { return { ...saved, picked: board.picked, camera: board.camera, scene: board.scene }; }
export const fromSaved = (saved) => ({ picked: saved.picked || {}, camera: saved.camera || "orbit_right", scene: saved.scene || "" });
