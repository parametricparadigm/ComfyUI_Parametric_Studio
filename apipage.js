/* The API page: every graph the studio runs, as something you can call. Pick a graph, copy working code, inspect the real JSON. GraphPanel shows the same graph on the Apps page. */
import { Offline, Stats, Strip, useHealth } from "./look.js";
import { useEffect, useMemo, useState } from "preact/hooks";
import { html, api, post } from "./common.js";
import { useShowcase, LiveMedia } from "./showcase.js";

const KIND = { goal: "Studio app", recipe: "Recipe", family: "Family graph" };
const base = () => (location.origin === "null" || window.STUDIO_DEMO ? "http://localhost:8310" : location.origin);
const nameOf = (o) => o.title || o.name || o.id;
export const rowsOf = (graphs, recipes, famg, items) => [
  ...graphs.map((g) => ({ key: "goal:" + g.goal, kind: "goal", id: g.goal, label: g.label, sub: g.model, media: items.find((x) => x.goal === g.goal && x.kind !== "audio") })),
  ...recipes.map((r) => { const g = (r.steps || []).map((s) => s.goal).find(Boolean), m = items.find((x) => x.goal === g && x.poster); return { key: "recipe:" + r.id, kind: "recipe", id: r.id, label: nameOf(r), sub: (r.models || []).map((m) => m.name || m).join(", ") || "Recipe", art: m && m.poster }; }),
  ...famg.map((g) => ({ key: `family:${g.slug}/${g.name}`, kind: "family", id: g.name, slug: g.slug, label: g.title, sub: g.family, art: g.art })),
];
export async function loadGraph(row) {
  if (row.kind === "goal") { const d = await api("/api/graphs/" + row.id); return { format: "api", graph: d.graph, fills: d.fills }; }
  if (row.kind === "family") return api(`/api/family-graphs/${row.slug}/${encodeURIComponent(row.id)}`);
  return { steps: (await api("/api/recipe-graphs/" + row.id)).steps };
}
export const openRow = (row) => {
  if (row.kind === "goal") { location.hash = "create"; setTimeout(() => dispatchEvent(new CustomEvent("prime-action", { detail: { type: "set_goal", goal: row.id } })), 80); }
  else if (row.kind === "recipe") { try { sessionStorage.setItem("recipe_open", JSON.stringify({ id: row.id, run: null })); } catch {} location.hash = "recipes"; }
  else { try { sessionStorage.setItem("family_tpl", row.id); } catch {} location.hash = "families/" + row.slug; }
};
const nodesOf = (d) => (!d || !d.graph ? [] : d.format === "ui" ? (d.graph.nodes || []).map((n) => [String(n.id), n.type]) : Object.entries(d.graph).map(([id, n]) => [id, n.class_type]));
const code = (lang, row) => {
  const b = base();
  if (row.kind === "family") {
    const run = `${b}/api/families/${row.slug}/templates/${encodeURIComponent(row.id)}/run`, poll = `${b}/api/families/${row.slug}/jobs/`;
    if (lang === "curl") return `curl -s -X POST '${run}' \\\n  -H 'Content-Type: application/json' -d '{"values": {}}'\n\n# then poll the job it returns\ncurl -s ${poll}JOB_ID`;
    if (lang === "Python") return `import requests, time\njob = requests.post("${run}", json={"values": {}}).json()["job"]\nwhile (s := requests.get("${poll}" + job).json())["status"] not in ("done", "error"):\n    time.sleep(2)\nprint(s.get("files"))`;
    if (lang === "JavaScript") return `const { job } = await (await fetch("${run}", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ values: {} }) })).json();\nlet s;\ndo { await new Promise((r) => setTimeout(r, 2000)); s = await (await fetch("${poll}" + job)).json(); } while (s.status !== "done" && s.status !== "error");\nconsole.log(s.files);`;
    return `# pip install comfy-sdk\nimport requests\nfrom comfy_sdk import Comfy\ngraph = requests.get("${b}/api/family-graphs/${row.slug}/${encodeURIComponent(row.id)}").json()["graph"]\nclient = Comfy()   # your server with COMFY_BASE_URL, or Comfy Cloud with COMFY_API_KEY\njob = client.run(client.workflows.from_json(graph))\nfor out in job.outputs: out.to_file(out.name)`;
  }
  if (row.kind === "recipe") {
    const run = `${b}/api/recipes/${row.id}/run`;
    if (lang === "curl") return `curl -s -X POST ${run} \\\n  -H 'Content-Type: application/json' -d '{"values": {}}'\n\n# then follow the run it returns\ncurl -s ${b}/api/recipes/${row.id}/runs/RUN_ID`;
    if (lang === "Python") return `import requests, time\nrun = requests.post("${run}", json={"values": {}}).json()["run"]\nwhile (s := requests.get(f"${b}/api/recipes/${row.id}/runs/{run}").json())["status"] not in ("done", "error"):\n    time.sleep(5)\nprint(s)`;
    if (lang === "JavaScript") return `const { run } = await (await fetch("${run}", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ values: {} }) })).json();\nconsole.log(await (await fetch("${b}/api/recipes/${row.id}/runs/" + run)).json());`;
    return `# each step is a plain ComfyUI graph, so you can run them yourself\nimport requests\nfrom comfy_sdk import Comfy\nclient = Comfy()\nfor step in requests.get("${b}/api/recipe-graphs/${row.id}").json()["steps"]:\n    if step["graph"]: print(step["label"], client.workflows.from_json(step["graph"]))`;
  }
  const body = JSON.stringify({ goal: row.id, prompt: "a lighthouse at dawn" });
  if (lang === "curl") return `curl -s -X POST ${b}/api/generate \\\n  -H 'Content-Type: application/json' \\\n  -d '${body}'\n\n# then poll the job it returns\ncurl -s ${b}/api/jobs/JOB_ID`;
  if (lang === "Python") return `import requests, time\nbase = "${b}"\njob = requests.post(base + "/api/generate", json=${body}).json()["job"]\nwhile (s := requests.get(f"{base}/api/jobs/{job}").json())["status"] not in ("done", "error"):\n    time.sleep(2)\nprint(s["files"])`;
  if (lang === "JavaScript") return `const base = "${b}";\nconst { job } = await (await fetch(base + "/api/generate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(${body}) })).json();\nlet s;\ndo { await new Promise((r) => setTimeout(r, 2000)); s = await (await fetch(base + "/api/jobs/" + job)).json(); } while (s.status !== "done" && s.status !== "error");\nconsole.log(s.files);`;
  return `# pip install comfy-sdk\nimport requests\nfrom comfy_sdk import Comfy\ngraph = requests.post("${b}/api/graph", json=${body}).json()["graph"]\nclient = Comfy()   # your server with COMFY_BASE_URL, or Comfy Cloud with COMFY_API_KEY\njob = client.run(client.workflows.from_json(graph))\nfor out in job.outputs: out.to_file(out.name)`;
};
function GraphBody({ detail }) {
  const [json, setJson] = useState(false), [step, setStep] = useState(0), [copied, setCopied] = useState(false);
  useEffect(() => { setStep(0); }, [detail]);
  const steps = (detail && detail.steps) || null, withGraph = steps ? steps.filter((s) => s.graph) : [], cur = steps ? (withGraph[step] ? { format: "api", graph: withGraph[step].graph } : null) : detail, nodes = useMemo(() => nodesOf(cur), [cur]);
  const text = cur && cur.graph ? JSON.stringify(cur.graph, null, 2) : "";
  const copy = async () => { try { await navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 1500); } catch {} };
  if (!detail) return html`<p class="small">Loading the graph...</p>`;
  return html`<div>
    ${steps && html`<div class="chips" style="margin:0 0 8px">${withGraph.map((s, i) => html`<button class=${"chip" + (step === i ? " on" : "")} onClick=${() => setStep(i)}>${i + 1}. ${s.label}</button>`)}</div>`}
    ${steps && !withGraph.length && html`<p class="small">This recipe writes its plan first, so its graphs are built when it runs.</p>`}
    ${cur && cur.graph && html`<div class="row" style="margin:6px 0 8px"><b>The real graph: ${nodes.length} nodes</b>${cur.format === "ui" && html`<span class="small"> (ComfyUI workflow format)</span>`}<span class="grow"></span><button class="btn small" onClick=${copy}>${copied ? "Copied" : "Copy JSON"}</button><button class="btn small" onClick=${() => setJson(!json)}>${json ? "Show nodes" : "Show JSON"}</button></div>
    ${json ? html`<pre class="apicode apijson"><code>${text}</code></pre>` : html`<div class="apinodes">${nodes.map(([id, t]) => html`<span class="apinode"><i>${id}</i>${t}</span>`)}</div>`}`}
  </div>`;
}
/* The same graph as a panel over the Apps page. */
export function GraphPanel({ row, onClose }) {
  const [detail, setDetail] = useState(null), [err, setErr] = useState("");
  useEffect(() => { setDetail(null); setErr(""); loadGraph(row).then(setDetail).catch((e) => setErr(e.message)); }, [row.key]);
  const toApi = () => { try { sessionStorage.setItem("api_pick", row.key); } catch {} location.hash = "api"; };
  return html`<div class="modal" onClick=${onClose}><div class="box graphpanel" onClick=${(e) => e.stopPropagation()}>
    <div class="row" style="margin:0 0 4px"><div><span class="small">${KIND[row.kind]} · ${row.sub}</span><h2 style="margin:2px 0 0">${row.label}</h2></div><span class="grow"></span><button class="btn small" onClick=${onClose}>Close</button></div>
    <div class="row" style="margin:10px 0 12px"><button class="btn primary" onClick=${() => { onClose(); openRow(row); }}>Open it</button><button class="btn" onClick=${toApi}>Use it from code</button></div>
    ${err ? html`<p class="small" style="color:var(--err)">${err}</p>` : html`<${GraphBody} detail=${detail}/>`}</div></div>`;
}
export function ApiPage() {
  const [graphs, setGraphs] = useState([]), [recipes, setRecipes] = useState([]), [famg, setFamg] = useState([]), [cur, setCur] = useState(null), [detail, setDetail] = useState(null), [lang, setLang] = useState("curl"), [copied, setCopied] = useState(false), [live, setLive] = useState(null), [err, setErr] = useState(""), [q, setQ] = useState(""), [sec, setSec] = useState("all"), items = useShowcase(), health = useHealth();
  useEffect(() => { api("/api/graphs").then(setGraphs).catch((e) => setErr(e.message)); api("/api/recipes").then((d) => setRecipes(d.recipes || d)).catch(() => {}); api("/api/family-graphs").then((d) => setFamg(d.graphs)).catch(() => {}); }, []);
  const rows = useMemo(() => rowsOf(graphs, recipes, famg, items), [graphs, recipes, famg, items]);
  useEffect(() => { if (cur || !rows.length || (!graphs.length && !err)) return; let pick = null; try { pick = sessionStorage.getItem("api_pick"); } catch {} const found = pick && rows.find((r) => r.key === pick); if (pick && !found && !famg.length) return; try { sessionStorage.removeItem("api_pick"); } catch {} setCur(found || rows[0]); }, [rows, err]);
  useEffect(() => { if (!cur) return; setDetail(null); setLive(null); setErr(""); loadGraph(cur).then(setDetail).catch((e) => setErr(e.message)); }, [cur && cur.key]);
  const shown = rows.filter((r) => (sec === "all" || r.kind === sec) && (!q.trim() || [r.label, r.sub].join(" ").toLowerCase().includes(q.trim().toLowerCase()))), snippet = cur ? code(lang, cur) : "";
  const copy = async () => { try { await navigator.clipboard.writeText(snippet); setCopied(true); setTimeout(() => setCopied(false), 1500); } catch {} };
  const fill = async () => { setErr(""); try { const r = await post("/api/graph", { goal: cur.id, prompt: "a lighthouse at dawn" }); setLive(Object.keys(r.graph).length); } catch (e) { setErr(e.message); } };
  return html`<div class="lk ai-page">
    <div class="lk-lead"><p class="lk-plain">Every graph here is real ComfyUI JSON. Call it from your app, an agent or a script. No account, no key, and on your own GPU no credits.</p><${Stats} items=${[[rows.length, "graphs"], [0, "keys needed"], [1, "call to render"]]}/></div>
    <${Offline} health=${health}>You can read every graph and copy its code. A call only renders once it is back.<//>
    <${Strip} label="Which graphs" value=${sec} onPick=${setSec} items=${[{ k: "all", b: "All", s: `${rows.length} graphs` }, { k: "goal", b: "Apps", s: `${graphs.length} built in` }, { k: "recipe", b: "Recipes", s: `${recipes.length} chained` }, { k: "family", b: "Families", s: `${famg.length} templates` }]}/>
    <div class="apigrid">
      <div><input class="apisearch" type="search" placeholder="Search every graph" aria-label="Search graphs" value=${q} onInput=${(e) => setQ(e.target.value)}/>
        <div class="apilist" role="listbox" aria-label="graphs">${shown.map((g) => html`<button key=${g.key} role="option" aria-selected=${!!cur && cur.key === g.key} class=${"apirow" + (cur && cur.key === g.key ? " on" : "")} onClick=${() => setCur(g)}>${g.media ? html`<${LiveMedia} item=${g.media} cls="apithumb"/>` : g.art ? html`<img class="apithumb" src=${g.art} alt="" loading="lazy" onError=${(e) => e.target.remove()}/>` : html`<span class="apithumb gblank"></span>`}<span><b>${g.label}</b><small>${g.sub}</small></span></button>`)}</div></div>
      ${cur && html`<div class="apimain">
        <div class="apihead"><div><span class="small">${KIND[cur.kind]}</span><h3>${cur.label}</h3><code>${cur.kind === "goal" ? "POST /api/generate" : cur.kind === "recipe" ? `POST /api/recipes/${cur.id}/run` : `POST /api/families/${cur.slug}/templates/.../run`}</code></div><div class="row" style="margin:0">${cur.kind === "goal" && html`<button class="btn small" onClick=${fill}>Fill it in live</button>`}<button class="btn small" onClick=${() => openRow(cur)}>Open it</button></div></div>
        ${err && html`<p class="small" style="color:var(--err)">${err}</p>`}
        ${live != null && html`<p class="small" style="color:var(--a2)">Filled in: ${live} nodes, ready to run. Nothing was rendered.</p>`}
        <div class="chips" style="margin:12px 0 8px">${["curl", "Python", "JavaScript", "Comfy SDK"].map((l) => html`<button class=${"chip" + (lang === l ? " on" : "")} onClick=${() => setLang(l)}>${l}</button>`)}<span class="grow"></span><button class="btn small primary" onClick=${copy}>${copied ? "Copied" : "Copy"}</button></div>
        <pre class="apicode"><code>${snippet}</code></pre>
        ${detail && detail.fills && html`<div class="apifills"><span class="small">The studio fills in:</span> ${detail.fills.map((f) => html`<code>${f}</code>`)}</div>`}
        <div style="margin-top:14px"><${GraphBody} detail=${detail}/></div>
      </div>`}
    </div></div>`;
}
