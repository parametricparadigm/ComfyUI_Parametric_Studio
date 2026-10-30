/* The API page: every graph the studio runs, as something you can call. Pick a graph, copy working code, inspect the real JSON, or fill it in live without rendering. */
import { useEffect, useMemo, useState } from "preact/hooks";
import { html, api, post } from "./common.js";
import { useShowcase, LiveMedia } from "./showcase.js";

const code = (lang, goal, base) => {
  const body = JSON.stringify({ goal, prompt: "a lighthouse at dawn" });
  if (lang === "curl") return `curl -s -X POST ${base}/api/generate \\\n  -H 'Content-Type: application/json' \\\n  -d '${body}'\n\n# then poll the job it returns\ncurl -s ${base}/api/jobs/JOB_ID`;
  if (lang === "Python") return `import requests, time\nbase = "${base}"\njob = requests.post(base + "/api/generate", json=${body}).json()["job"]\nwhile (s := requests.get(f"{base}/api/jobs/{job}").json())["status"] not in ("done", "error"):\n    time.sleep(2)\nprint(s["files"])`;
  if (lang === "JavaScript") return `const base = "${base}";\nconst { job } = await (await fetch(base + "/api/generate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(${body}) })).json();\nlet s;\ndo { await new Promise((r) => setTimeout(r, 2000)); s = await (await fetch(base + "/api/jobs/" + job)).json(); } while (s.status !== "done" && s.status !== "error");\nconsole.log(s.files);`;
  return `# pip install comfy-sdk\nimport requests\nfrom comfy_sdk import Comfy\ngraph = requests.post("${base}/api/graph", json=${body}).json()["graph"]\nclient = Comfy()   # your server with COMFY_BASE_URL, or Comfy Cloud with COMFY_API_KEY\njob = client.run(client.workflows.from_json(graph))\nfor out in job.outputs: out.to_file(out.name)`;
};

export function ApiPage({ goTab }) {
  const [list, setList] = useState([]); const [goal, setGoal] = useState("image"); const [detail, setDetail] = useState(null); const [lang, setLang] = useState("curl"); const [copied, setCopied] = useState(false); const [live, setLive] = useState(null); const [err, setErr] = useState(""); const [json, setJson] = useState(false); const items = useShowcase();
  const base = location.origin === "null" ? "http://localhost:8310" : location.origin;
  useEffect(() => { api("/api/graphs").then(setList).catch((e) => setErr(e.message)); }, []);
  useEffect(() => { setDetail(null); setLive(null); api("/api/graphs/" + goal).then(setDetail).catch((e) => setErr(e.message)); }, [goal]);
  const nodes = useMemo(() => (detail ? Object.entries(detail.graph) : []), [detail]); const cur = list.find((x) => x.goal === goal); const snippet = code(lang, goal, base);
  const copy = async () => { try { await navigator.clipboard.writeText(snippet); setCopied(true); setTimeout(() => setCopied(false), 1500); } catch {} };
  const fill = async () => { setErr(""); try { const r = await post("/api/graph", { goal, prompt: "a lighthouse at dawn" }); setLive(Object.keys(r.graph).length); } catch (e) { setErr(e.message); } };
  return html`<div>
    <section class="apihero"><div><h2>Your studio <em>is an API.</em></h2><p>Every graph here is plain ComfyUI API format. Call it from your app, an agent or a script. No account, no key, and on your own GPU no credits.</p></div>
      <div class="apistats"><div><b>${list.length}</b><span>graphs</span></div><div><b>0</b><span>keys needed</span></div><div><b>1</b><span>call to render</span></div></div></section>
    <div class="apigrid">
      <div class="apilist" role="listbox" aria-label="graphs">${list.map((g) => { const m = items.find((x) => x.goal === g.goal && x.kind !== "audio"); return html`<button role="option" aria-selected=${goal === g.goal} class=${"apirow" + (goal === g.goal ? " on" : "")} onClick=${() => setGoal(g.goal)}>${m ? html`<${LiveMedia} item=${m} cls="apithumb"/>` : html`<span class="apithumb gblank"></span>`}<span><b>${g.label}</b><small>${g.model}</small></span></button>`; })}</div>
      <div class="apimain">
        <div class="apihead"><div><h3>${cur ? cur.label : goal}</h3><code>POST /api/generate</code> <code>GET /api/graphs/${goal}</code></div><div class="row" style="margin:0"><button class="btn small" onClick=${fill}>Fill it in live</button><button class="btn small" onClick=${() => { location.hash = "create"; setTimeout(() => dispatchEvent(new CustomEvent("prime-action", { detail: { type: "set_goal", goal } })), 80); setTimeout(() => goTab && goTab("pro"), 200); }}>See it in 3D</button></div></div>
        ${err && html`<p class="small" style="color:var(--err)">${err}</p>`}
        ${live != null && html`<p class="small" style="color:var(--a2)">Filled in: ${live} nodes, ready to run. Nothing was rendered.</p>`}
        <div class="chips" style="margin:12px 0 8px">${["curl", "Python", "JavaScript", "Comfy SDK"].map((l) => html`<button class=${"chip" + (lang === l ? " on" : "")} onClick=${() => setLang(l)}>${l}</button>`)}<span class="grow"></span><button class="btn small primary" onClick=${copy}>${copied ? "Copied" : "Copy"}</button></div>
        <pre class="apicode"><code>${snippet}</code></pre>
        ${detail && html`<div class="apifills"><span class="small">The studio fills in:</span> ${detail.fills.map((f) => html`<code>${f}</code>`)}</div>`}
        <div class="row" style="margin:14px 0 8px"><b>The real graph: ${nodes.length} nodes</b><span class="grow"></span><button class="btn small" onClick=${() => setJson(!json)}>${json ? "Show nodes" : "Show JSON"}</button></div>
        ${json ? html`<pre class="apicode apijson"><code>${detail ? JSON.stringify(detail.graph, null, 2) : ""}</code></pre>` : html`<div class="apinodes">${nodes.map(([id, n]) => html`<span class="apinode"><i>${id}</i>${n.class_type}</span>`)}</div>`}
      </div>
    </div></div>`;
}
