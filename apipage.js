/* The API page: every graph the studio runs, as something you can call. Pick a graph, copy working code, inspect the real JSON. GraphPanel shows the same graph on the Apps page. */
import { Offline, Stats, Strip, useHealth } from "./look.js";
import { useEffect, useMemo, useState } from "preact/hooks";
import { html, api, post } from "./common.js";
import { useShowcase, LiveMedia } from "./showcase.js";
import { SECTIONS, callCode, hasGraph, loadRow, matches, sectionOf, useAllGraphs } from "./graph_rows.js";

const KIND = { goal: "Studio app", recipe: "Recipe", family: "Family graph", runner: "Runner", tool: "Tool", workflow: "World Kit or Virtual Set graph" };
const base = () => (location.origin === "null" || window.STUDIO_DEMO ? "http://localhost:8310" : location.origin);
const nameOf = (o) => o.title || o.name || o.id;
export const loadGraph = loadRow;
export const openRow = (row) => {
  if (row.kind === "goal") { location.hash = "create"; setTimeout(() => dispatchEvent(new CustomEvent("prime-action", { detail: { type: "set_goal", goal: row.id } })), 80); }
  else if (row.kind === "recipe") { try { sessionStorage.setItem("recipe_open", JSON.stringify({ id: row.id, run: null })); } catch {} location.hash = "recipes"; }
  else if (row.section === "model3d" || row.kind === "workflow") location.hash = row.open;
  else { try { sessionStorage.setItem("family_tpl", row.id); } catch {} location.hash = "families/" + row.slug; }
};
const nodesOf = (d) => (!d || !d.graph ? [] : d.format === "ui" ? (d.graph.nodes || []).map((n) => [String(n.id), n.type]) : Object.entries(d.graph).map(([id, n]) => [id, n.class_type]));
const code = (lang, row) => {
  const b = base();
  if (row.section === "model3d" || row.kind === "workflow") return lang === "Comfy SDK" ? (hasGraph(row) ? `# pip install comfy-sdk\nimport requests\nfrom comfy_sdk import Comfy\ngraph = requests.get("${b}${row.graph_url}").json()["graph"]\nclient = Comfy()\nprint(client.workflows.from_json(graph))` : `# ${row.label} is not a ComfyUI graph, so the Comfy SDK cannot run it. Use the curl, Python or JavaScript call.`) : callCode(lang, row, b);
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
  if (detail.notGraph) return html`<div class="apinotgraph"><b>This one is not a ComfyUI graph.</b><p class="small" style="margin:4px 0 0">It runs as its own program on this machine, so there is no graph to show or to open in ComfyUI. The call above is the way to run it.</p></div>`;
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
  const toPro = () => { try { sessionStorage.setItem("pro_pick", row.key); } catch {} location.hash = "pro"; };
  return html`<div class="modal" onClick=${onClose}><div class="box graphpanel" onClick=${(e) => e.stopPropagation()}>
    <div class="row" style="margin:0 0 4px"><div><span class="small">${KIND[row.kind]} · ${row.sub}</span><h2 style="margin:2px 0 0">${row.label}</h2></div><span class="grow"></span><button class="btn small" onClick=${onClose}>Close</button></div>
    <div class="row" style="margin:10px 0 12px"><button class="btn primary" onClick=${() => { onClose(); openRow(row); }}>Open it</button><button class="btn" onClick=${toApi}>Use it from code</button><button class="btn" onClick=${() => { onClose(); toPro(); }}>See it on Pro</button></div>${row.runs_as && html`<p class="small" style="margin:0 0 10px">${row.runs_as}.</p>`}
    ${err ? html`<p class="small" style="color:var(--err)">${err}</p>` : html`<${GraphBody} detail=${detail}/>`}</div></div>`;
}
export function ApiPage() {
  const all = useAllGraphs(), rows = all.rows, c = all.counts, [cur, setCur] = useState(null), [detail, setDetail] = useState(null), [lang, setLang] = useState("curl"), [copied, setCopied] = useState(false), [live, setLive] = useState(null), [err, setErr] = useState(""), [q, setQ] = useState(""), [sec, setSec] = useState("all"), items = useShowcase(), health = useHealth();
  useEffect(() => { if (all.err) setErr(all.err); }, [all.err]);
  useEffect(() => { if (cur || !rows.length) return; let pick = null; try { pick = sessionStorage.getItem("api_pick"); sessionStorage.removeItem("api_pick"); } catch {} setCur(rows.find((r) => r.key === pick) || rows[0]); }, [rows]);
  useEffect(() => { if (!cur) return; setDetail(null); setLive(null); setErr(""); loadGraph(cur).then(setDetail).catch((e) => setErr(e.message)); }, [cur && cur.key]);
  const shown = rows.filter((r) => (sec === "all" || sectionOf(r) === sec) && matches(r, q)), snippet = cur ? code(lang, cur) : "";
  const copy = async () => { try { await navigator.clipboard.writeText(snippet); setCopied(true); setTimeout(() => setCopied(false), 1500); } catch {} };
  const fill = async () => { setErr(""); try { const r = await post("/api/graph", { goal: cur.id, prompt: "a lighthouse at dawn" }); setLive(Object.keys(r.graph).length); } catch (e) { setErr(e.message); } };
  return html`<div class="lk ai-page">
    <div class="lk-lead"><p class="lk-plain">Everything the studio runs, callable from your app, an agent or a script. ${c.graph || 0} are real ComfyUI JSON; ${c.not_graph || 0} are small programs, and they say so. No account, no key, and on your own GPU no credits.</p><${Stats} items=${[[rows.length, "ways to run"], [0, "keys needed"], [1, "call to render"]]}/></div>
    <${Offline} health=${health}>You can read every graph and copy its code. A call only renders once it is back.<//>
    <${Strip} label="Which graphs" value=${sec} onPick=${setSec} items=${[{ k: "all", b: "All", s: `${rows.length} in all` }, ...SECTIONS.map(([k, b]) => ({ k, b, s: `${c[k] || 0}` }))]}/>
    <div class="apigrid">
      <div><input class="apisearch" type="search" placeholder="Search every graph" aria-label="Search graphs" value=${q} onInput=${(e) => setQ(e.target.value)}/>
        <div class="apilist" role="listbox" aria-label="graphs">${shown.map((g) => html`<button key=${g.key} role="option" aria-selected=${!!cur && cur.key === g.key} class=${"apirow" + (cur && cur.key === g.key ? " on" : "")} onClick=${() => setCur(g)}>${g.media ? html`<${LiveMedia} item=${g.media} cls="apithumb"/>` : g.art ? html`<img class="apithumb" src=${g.art} alt="" loading="lazy" onError=${(e) => e.target.remove()}/>` : html`<span class="apithumb gblank"></span>`}<span><b>${g.label}</b><small>${g.sub}</small></span></button>`)}</div></div>
      ${cur && html`<div class="apimain">
        <div class="apihead"><div><span class="small">${KIND[cur.kind]}</span><h3>${cur.label}</h3><code>${`${cur.call.method} ${cur.call.path}`}</code></div><div class="row" style="margin:0">${cur.kind === "goal" && html`<button class="btn small" onClick=${fill}>Fill it in live</button>`}<button class="btn small" onClick=${() => openRow(cur)}>Open it</button></div></div>
        ${err && html`<p class="small" style="color:var(--err)">${err}</p>`}
        ${live != null && html`<p class="small" style="color:var(--a2)">Filled in: ${live} nodes, ready to run. Nothing was rendered.</p>`}
        <div class="chips" style="margin:12px 0 8px">${["curl", "Python", "JavaScript", "Comfy SDK"].map((l) => html`<button class=${"chip" + (lang === l ? " on" : "")} onClick=${() => setLang(l)}>${l}</button>`)}<span class="grow"></span><button class="btn small primary" onClick=${copy}>${copied ? "Copied" : "Copy"}</button></div>
        <pre class="apicode"><code>${snippet}</code></pre>
        ${detail && detail.fills && html`<div class="apifills"><span class="small">The studio fills in:</span> ${detail.fills.map((f) => html`<code>${f}</code>`)}</div>`}
        <div style="margin-top:14px"><${GraphBody} detail=${detail}/></div>
      </div>`}
    </div></div>`;
}
