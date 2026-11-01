/* The one list behind the Pro, API and Apps pages: /api/all-graphs. Pure helpers plus a hook. A runner or a tool is shown as what it is: no graph, and the real call that runs it. */
import { useEffect, useState } from "preact/hooks";
import { api } from "./common.js";

export const SECTIONS = [["goal", "Studio apps"], ["model3d", "3D models"], ["workflow", "World Kit and Virtual Set"], ["family", "Family graphs"], ["recipe", "Recipes"]];
export const sectionOf = (r) => r.section || r.kind;
export const hasGraph = (r) => !!(r && r.graph_url);
export const tagOf = (r) => (r.kind === "runner" ? "Runner" : r.kind === "tool" ? "Tool" : r.kind === "goal" ? "App" : r.kind === "recipe" ? "Recipe" : r.kind === "workflow" ? r.sub : r.section === "model3d" ? "3D graph" : r.sub);
export function matches(r, q) { const w = String(q || "").trim().toLowerCase(); return !w || w.split(/\s+/).every((x) => [r.label, r.sub, r.desc, r.cat, r.group, r.id].join(" ").toLowerCase().includes(x)); }
export function useAllGraphs() {
  const [d, setD] = useState({ rows: [], counts: {}, err: "" });
  useEffect(() => { let on = true; api("/api/all-graphs").then((x) => on && setD({ rows: x.rows, counts: x.counts, err: "" })).catch((e) => on && setD({ rows: [], counts: {}, err: e.message })); return () => { on = false; }; }, []);
  return d;
}
/* What a page needs to show a row's graph: {format, graph, fills} for one graph, {steps} for a recipe, and nothing to fetch for a runner or a tool. */
export async function loadRow(row) {
  if (!hasGraph(row)) return { notGraph: true };
  const d = await api(row.graph_url);
  return d.steps ? { steps: d.steps } : { format: d.format || "api", graph: d.graph, fills: d.fills };
}
export const firstGraph = (d) => (!d ? null : d.graph && d.format !== "ui" ? d.graph : d.steps ? (d.steps.find((s) => s.graph) || {}).graph || null : null);
/* A row's call in each language, from its own call record. */
export function callCode(lang, row, b) {
  const { method, path, body, poll } = row.call, url = b + path, J = JSON.stringify(body), pu = (x) => b + poll.replace("ID", x), key = /^\/api\/recipes\//.test(path) ? "run" : /worldkit\/assets/.test(path) ? "asset" : /vset\/shots/.test(path) ? "shot" : "job";
  const idOf = key === "asset" ? `["asset"]["id"]` : key === "shot" ? `["shot"]["id"]` : `["${key}"]`, jsId = key === "asset" ? "r.asset.id" : key === "shot" ? "r.shot.id" : `r.${key}`;
  const said = row.call.note ? (lang === "curl" || lang === "Python" ? `# ${row.call.note}\n` : `// ${row.call.note}\n`) : "";
  const fills = /NAME_FROM|PATH_FROM|PLACE_ASSET/.test(J) ? (lang === "curl" ? "# first replace the placeholders: upload with POST /api/upload, list meshes with GET /api/models3d, places with GET /api/worldkit/assets?type=place\n" : "") : "";
  if (lang === "curl") return `${said}${fills}curl -s -X ${method} ${url} \\\n  -H 'Content-Type: application/json' \\\n  -d '${J}'\n\n# then follow what it returns\ncurl -s ${pu("ID")}`;
  if (lang === "Python") return `${said}import requests\nr = requests.post("${url}", json=${J.replace(/\btrue\b/g, "True").replace(/\bfalse\b/g, "False").replace(/\bnull\b/g, "None")}).json()\nprint(requests.get("${b}${poll.replace("ID", "")}" + r${idOf}).json())`;
  return `${said}const r = await (await fetch("${url}", { method: "${method}", headers: { "Content-Type": "application/json" }, body: JSON.stringify(${J}) })).json();\nconsole.log(await (await fetch("${b}${poll.replace("ID", "")}" + ${jsId})).json());`;
}
