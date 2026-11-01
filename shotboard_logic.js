// Shot Board job states, kept apart from the page so plain node tests can run them.
const OPEN = ["queued", "running"];
// A late answer must not bring a job back after its owner cancelled it.
export const applyPatch = (jobs, id, patch) => jobs.map((j) => (j.id === id && j.status !== "cancelled" ? { ...j, ...patch } : j));
export const cancelOpen = (jobs) => jobs.map((j) => (OPEN.includes(j.status) ? { ...j, status: "cancelled", error: "Cancelled." } : j));
export const canRetry = (j) => ["error", "lost", "cancelled"].includes(j.status);
export const stoppedStatus = (s) => (s.lost ? "lost" : "error");
